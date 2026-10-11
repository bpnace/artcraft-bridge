"""Check that VERSION, package metadata and changelog agree."""
from pathlib import Path
import re
import sys

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root / "src"))
from recraft_bridge import __version__

version = (root / "VERSION").read_text().strip()
assert re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", version), "Invalid version"
assert version == __version__, "VERSION disagrees with package"
assert f"## [{version}]" in (root / "CHANGELOG.md").read_text(), "Missing changelog entry"
print(f"Version {version} is consistent")
