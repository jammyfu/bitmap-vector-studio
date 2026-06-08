from __future__ import annotations

import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"


def main() -> None:
    DIST.mkdir(exist_ok=True)
    archive = shutil.make_archive(str(DIST / "bitmap-vector-studio"), "zip", ROOT)
    print(f"Created {archive}")


if __name__ == "__main__":
    main()
