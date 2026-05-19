from __future__ import annotations

from pathlib import Path
from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
IMAGE_DIR = ROOT / "astro-site" / "public" / "images" / "articles"
MAX_SIZE = (1280, 720)
QUALITY = 82


def optimize_image(path: Path) -> tuple[int, int] | None:
    before = path.stat().st_size
    with Image.open(path) as image:
        image = image.convert("RGB")
        image.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
        image.save(path, "WEBP", quality=QUALITY, method=6)
    after = path.stat().st_size
    return before, after


def main() -> None:
    if not IMAGE_DIR.exists():
        raise SystemExit(f"image directory not found: {IMAGE_DIR}")

    total_before = 0
    total_after = 0
    count = 0

    for path in sorted(IMAGE_DIR.glob("*.webp")):
        result = optimize_image(path)
        if not result:
            continue
        before, after = result
        total_before += before
        total_after += after
        count += 1
        print(f"{path.name}: {before // 1024}KB -> {after // 1024}KB")

    saved = total_before - total_after
    print(f"optimized {count} images, saved {saved // 1024}KB")


if __name__ == "__main__":
    main()
