#!/usr/bin/env python3
"""Set version in all source files. Used by build scripts and CI.

Usage:
  python set_version.py              # read current version from version.txt
  python set_version.py --increment  # increment minor version and patch sources
  python set_version.py --set 7.2.0  # set specific version and patch sources
"""

import re
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
VERSION_FILE = os.path.join(ROOT, "version.txt")

SOURCE_FILES = [
    (os.path.join(ROOT, "src", "Installer", "Program.cs"),
     r'(const string ModVersion = ")[^"]+(")',
     r'\g<1>{VERSION}\2'),
    (os.path.join(ROOT, "src", "Mod", "RussianLocalization.cs"),
     r'(BepInPlugin\("com\.nightcall\.russian", "Night Call Russian", ")[^"]+(")',
     r'\g<1>{VERSION}\2'),
    (os.path.join(ROOT, "src", "Mod", "RussianLocalization.cs"),
     r'(Night Call Russian Localization v)[0-9]+\.[0-9]+\.[0-9]+',
     r'\g<1>{VERSION}'),
]


def read_version():
    with open(VERSION_FILE, "r") as f:
        return f.read().strip()


def write_version(version):
    with open(VERSION_FILE, "w") as f:
        f.write(version + "\n")


def increment_version(version):
    parts = version.split(".")
    major = int(parts[0])
    minor = int(parts[1])
    minor += 1
    if minor > 9:
        major += 1
        minor = 0
    return f"{major}.{minor}.0"


def patch_sources(version):
    for filepath, pattern, replacement in SOURCE_FILES:
        if not os.path.exists(filepath):
            print(f"  [!!] File not found: {filepath}")
            continue
        with open(filepath, "r", encoding="utf-8") as f:
            content = f.read()
        repl = replacement.replace("{VERSION}", version)
        new_content, count = re.subn(pattern, repl, content)
        if count > 0:
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(new_content)
            print(f"  [OK] {os.path.basename(filepath)}: {count} replacement(s)")
        else:
            print(f"  [--] {os.path.basename(filepath)}: pattern not found")


def main():
    if len(sys.argv) >= 2 and sys.argv[1] == "--increment":
        old = read_version()
        new = increment_version(old)
        write_version(new)
        print(f"Version: {old} -> {new}")
        patch_sources(new)
    elif len(sys.argv) >= 3 and sys.argv[1] == "--set":
        version = sys.argv[2].lstrip("v")
        # Ensure 3-part version
        parts = version.split(".")
        while len(parts) < 3:
            parts.append("0")
        version = ".".join(parts[:3])
        write_version(version)
        print(f"Version: {version}")
        patch_sources(version)
    else:
        print(read_version())


if __name__ == "__main__":
    main()
