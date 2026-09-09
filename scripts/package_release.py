"""
Packaging script for Standalone QS Quantification Engine Phase-1 Production Release.
Excludes virtual environments, caches, and IDE artifacts.
"""

import zipfile
from pathlib import Path

ROOT_DIR = Path(__file__).parents[1]
OUTPUT_ZIPS = [
    ROOT_DIR / "qs_quantification_engine_phase1_production_ready.zip",
    ROOT_DIR / "qs_quantification_engine_updated.zip"
]

EXCLUDE_DIRS = {
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".git",
    ".idea",
    ".vscode",
    "node_modules",
    "dist",
    "build"
}

EXCLUDE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".DS_Store",
    ".zip"
}


def package():
    for target_zip in OUTPUT_ZIPS:
        count = 0
        with zipfile.ZipFile(target_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
            for p in ROOT_DIR.rglob("*"):
                if p in OUTPUT_ZIPS:
                    continue
                # Check exclusions
                parts = p.relative_to(ROOT_DIR).parts
                if any(part in EXCLUDE_DIRS for part in parts):
                    continue
                if p.suffix in EXCLUDE_EXTENSIONS:
                    continue
                if p.is_file():
                    arcname = p.relative_to(ROOT_DIR)
                    zipf.write(p, arcname)
                    count += 1

        print(f"[SUCCESS] Packaged {count} files into {target_zip.name} ({target_zip.stat().st_size / (1024 * 1024):.2f} MB)")


if __name__ == "__main__":
    package()
