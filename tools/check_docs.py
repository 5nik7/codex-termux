#!/usr/bin/env python3
"""Check repository-local Markdown links without network requests."""
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
count = 0
for file in [*ROOT.glob('*.md'), *sorted((ROOT / 'docs').rglob('*.md'))]:
    for target in re.findall(r'(?<!!)\[[^\]]+\]\(([^\s)]+)\)', file.read_text(encoding='utf-8')):
        link = urlsplit(target)
        if link.scheme or not link.path:
            continue
        resolved = (file.parent / unquote(link.path)).resolve()
        try:
            resolved.relative_to(ROOT)
        except ValueError:
            raise SystemExit(f'{file.name}: local link escapes repository: {target}')
        if not resolved.exists():
            raise SystemExit(f'{file.name}: missing local link: {target}')
        count += 1
print(f'Documentation links passed: {count} local targets (fragments not checked).')
