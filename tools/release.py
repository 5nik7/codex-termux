#!/usr/bin/env python3
"""Create flat GitHub Release assets and deterministic source archives; never publish."""
import argparse
import gzip
import hashlib
import io
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import zipfile

from build import ASSETS, EXECUTABLES, ROOT, version


def source_files():
    # Copy documented source trees, not .git, caches or arbitrary root files.
    names = {'.gitignore', 'AGENTS.md', 'README.md', 'CHANGELOG.md', 'RELEASING.md',
             'VALIDATION.md', 'LICENSE', 'VERSION', 'config.example',
             'PACKAGE-SHA256SUMS', 'install.sh', 'uninstall.sh',
             'bin/codex-termux', 'completions/codex-termux.bash', 'completions/_codex-termux'}
    for directory in ['src', 'man', 'tools', 'tests', 'docs', '.github/workflows']:
        base = ROOT / directory
        if base.is_symlink():
            raise SystemExit('Refusing symlink source directory: ' + directory)
        for file in base.rglob('*'):
            if any(part.startswith('.') for part in file.relative_to(base).parts):
                continue
            # A version directory such as 0.3.1 has a .1 suffix like a manual.
            # Skip real directories; selected symlinks still fail validation below.
            if file.is_dir() and not file.is_symlink():
                continue
            if file.name == 'SHA256SUMS' or file.suffix in {'.sh', '.cjs', '.py', '.md', '.json', '.log', '.yml', '.yaml', '.1', '.in'}:
                names.add(file.relative_to(ROOT).as_posix())
    for name in sorted(names):
        file = ROOT / name
        if file.is_symlink() or not file.is_file():
            raise SystemExit('Expected regular source file: ' + name)
        yield name, file.read_bytes(), 0o755 if name in EXECUTABLES else 0o644


def archives(destination, release):
    files = list(source_files())
    prefix = 'codex-termux-' + release
    with zipfile.ZipFile(destination / (prefix + '.zip'), 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data, mode in files:
            info = zipfile.ZipInfo(prefix + '/' + name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100000 | mode) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data)
    with (destination / (prefix + '.tar.gz')).open('wb') as raw:
        with gzip.GzipFile(filename='', mode='wb', fileobj=raw, mtime=0, compresslevel=9) as compressed:
            with tarfile.open(fileobj=compressed, mode='w', format=tarfile.USTAR_FORMAT) as archive:
                for name, data, mode in files:
                    info = tarfile.TarInfo(prefix + '/' + name)
                    info.size = len(data); info.mode = mode; info.mtime = 0
                    info.uid = info.gid = 0; info.uname = info.gname = ''
                    archive.addfile(info, io.BytesIO(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, help='A new output directory; default dist/vVERSION')
    parser.add_argument('--tag', help='Refuse a release tag that does not exactly match VERSION')
    options = parser.parse_args()
    release = version()
    if options.tag is not None and options.tag != 'v' + release:
        parser.error('--tag must exactly match v' + release)
    subprocess.run([sys.executable, '-B', str(ROOT / 'tools/build.py'), '--check'], check=True)
    output = (options.output or ROOT / 'dist' / ('v' + release)).absolute()
    if output.exists() or output.is_symlink():
        parser.error('output already exists; use a new --output directory')
    output.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.codex-termux-release-', dir=output.parent))
    try:
        for asset, source in ASSETS.items():
            shutil.copyfile(ROOT / source, stage / asset)
            (stage / asset).chmod(0o755 if source in EXECUTABLES else 0o644)
        shutil.copyfile(ROOT / 'PACKAGE-SHA256SUMS', stage / 'SHA256SUMS')
        archives(stage, release)
        (stage / 'RELEASE-SHA256SUMS').write_text(''.join(
            hashlib.sha256(file.read_bytes()).hexdigest() + '  ' + file.name + '\n'
            for file in sorted(stage.iterdir())), encoding='utf-8')
        stage.rename(output)
    finally:
        if stage.exists():
            shutil.rmtree(stage)
    print('Release assets: ' + str(output))
    print('No release was uploaded or published.')


if __name__ == '__main__':
    main()
