#!/usr/bin/env python3
"""Build a deterministic standalone Bash wrapper. No external dependencies."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
text = (ROOT / "src/frontend.sh").read_text()
for token, source in {
    "@@RUNTIME@@": "src/runtime.cjs",
    "@@BASH_COMPLETION@@": "completions/codex-termux.bash",
    "@@ZSH_COMPLETION@@": "completions/_codex-termux",
}.items():
    if text.count(token) != 1:
        raise SystemExit("missing or duplicate build marker: " + token)
    text = text.replace(token, (ROOT / source).read_text().rstrip("\n"))
output = ROOT / "bin/codex-termux"
output.write_text(text)
output.chmod(0o755)
print(output)
