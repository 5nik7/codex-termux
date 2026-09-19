#!/usr/bin/env python3
"""Verify shippable artifacts, reproducibility, and source-bundle installation."""
import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / 'VERSION').read_text().strip()
BASH = shutil.which('bash')


class ReleaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='codex-termux-release-test-')
        cls.root = Path(cls.tmp.name)
        cls.outputs = [cls.root / 'first', cls.root / 'second']
        for output in cls.outputs:
            subprocess.run([sys.executable, '-B', str(ROOT / 'tools/release.py'), '--tag', 'v' + VERSION, '--output', str(output)], check=True, stdout=subprocess.DEVNULL, timeout=15)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_repeatable_assets_and_both_checksum_manifests(self):
        first, second = self.outputs
        self.assertEqual(len(list(first.iterdir())), 15)
        self.assertEqual({f.name: f.read_bytes() for f in first.iterdir()}, {f.name: f.read_bytes() for f in second.iterdir()})
        for name, count in [('SHA256SUMS', 11), ('RELEASE-SHA256SUMS', 14)]:
            lines = (first / name).read_text().splitlines()
            self.assertEqual(len(lines), count)
            for line in lines:
                digest, asset = line.split('  ')
                self.assertEqual(hashlib.sha256((first / asset).read_bytes()).hexdigest(), digest, asset)

    def test_archive_parity_and_extracted_source_installation(self):
        prefix = 'codex-termux-' + VERSION
        extraction = self.root / 'extracted'; extraction.mkdir()
        with zipfile.ZipFile(self.outputs[0] / (prefix + '.zip')) as archive:
            zip_files = {}
            for info in archive.infolist():
                self.assertTrue(info.filename.startswith(prefix + '/'))
                self.assertNotIn('..', Path(info.filename).parts)
                self.assertNotIn('.git', Path(info.filename).parts)
                self.assertNotIn('dist', Path(info.filename).parts)
                self.assertEqual(info.external_attr >> 16 & 0o170000, 0o100000)
                data = archive.read(info); zip_files[info.filename] = data
                file = extraction / info.filename; file.parent.mkdir(parents=True, exist_ok=True)
                file.write_bytes(data); file.chmod(info.external_attr >> 16 & 0o777)
        with tarfile.open(self.outputs[0] / (prefix + '.tar.gz')) as archive:
            tar_files = {}
            for member in archive:
                self.assertTrue(member.isfile())
                tar_files[member.name] = archive.extractfile(member).read()
        self.assertEqual(zip_files, tar_files)
        source = extraction / prefix
        self.assertTrue((source / 'man/codex-termux.1').is_file())
        self.assertTrue((source / 'docs/evidence/0.3.1/verification.json').is_file())
        subprocess.run([sys.executable, '-B', str(source / 'tools/build.py'), '--check'], check=True, stdout=subprocess.DEVNULL)
        destination = self.root / 'owned prefix'; destination.mkdir()
        home = self.root / 'owned home'; home.mkdir()
        temp = self.root / 'tmp'; temp.mkdir()
        utility_dirs = dict.fromkeys(str(Path(shutil.which(name)).parent) for name in ['bash', 'sha256sum', 'stat', 'cp'])
        env = {'HOME': str(home), 'PREFIX': str(destination), 'TMPDIR': str(temp), 'PATH': ':'.join(utility_dirs)}
        child = subprocess.run([BASH, str(source / 'install.sh'), '--source', str(source), '--yes'], env=env, capture_output=True, text=True, timeout=8)
        self.assertEqual(child.returncode, 0, child.stdout + child.stderr)
        self.assertEqual((destination / 'libexec/codex-termux/current/VERSION').read_text().strip(), VERSION)
        child = subprocess.run([BASH, str(destination / 'bin/codex-termux'), '--wrapper-version'], env=env, capture_output=True, text=True, timeout=5)
        self.assertEqual(child.returncode, 0, child.stderr)
        self.assertEqual(child.stdout, 'codex-termux ' + VERSION + '\n')

    def test_rejects_wrong_tag_and_existing_output_without_overwriting(self):
        for args in [('--tag', 'v9999.0.0', '--output', str(self.root / 'wrong')), ('--output', str(self.outputs[0]))]:
            child = subprocess.run([sys.executable, '-B', str(ROOT / 'tools/release.py'), *args], capture_output=True, text=True, timeout=5)
            self.assertNotEqual(child.returncode, 0)
        self.assertFalse((self.root / 'wrong').exists())
        self.assertEqual(len(list(self.outputs[0].iterdir())), 15)


if __name__ == '__main__':
    unittest.main(verbosity=2)
