from html import escape
from pathlib import Path
import re
import subprocess


root = Path(__file__).resolve().parents[2]
readme = root / "README.md"
start = "<!-- recent-changes:start -->"
end = "<!-- recent-changes:end -->"

content = readme.read_text(encoding="utf-8")
if content.count(start) != 1 or content.count(end) != 1:
    raise SystemExit("README must contain exactly one pair of recent changes markers")
before, rest = content.split(start)
old_section, after = rest.split(end)

history = subprocess.check_output(
    [
        "git", "log", "--first-parent", "-5", "-z", "--format=%h%x00%s",
        "--", ".", ":(exclude)README.md",
    ],
    cwd=root,
).decode("utf-8").split("\0")

entries = []
for sha, subject in zip(history[0::2], history[1::2]):
    subject = re.sub(r"([\\`*_{}\[\]()#+.!|>~-])", r"\\\1", escape(subject))
    entries.append(f"- `{sha}` {subject}")

section = "\n" + ("\n".join(entries) if entries else "No changes recorded yet.") + "\n"
if section != old_section:
    readme.write_text(before + start + section + end + after, encoding="utf-8")
