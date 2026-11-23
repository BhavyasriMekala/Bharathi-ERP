"""Remove black matte and export tight transparent Bharathi logo PNG."""

from __future__ import annotations

from collections import deque
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
SRC_CANDIDATES = (
    ROOT / "assets" / "bharathi-enterprises-logo-source.jpg",
    Path(
        r"C:\Users\satee\.cursor\projects\c-Users-satee-OneDrive-Desktop-Bharathi-Enterprises-ERP\assets"
        r"\c__Users_satee_AppData_Roaming_Cursor_User_workspaceStorage_49a250033b99dc397dccc9d2d1909d47_images_image-648e3451-e191-47db-aaa1-4bd96a47327e.png"
    ),
)
OUT_PUBLIC = ROOT / "public" / "bharathi-enterprises-logo.png"
OUT_SRC = ROOT / "src" / "assets" / "bharathi-enterprises-logo.png"
BLACK_THRESH = 34


def is_matte_black(r: int, g: int, b: int) -> bool:
    return r <= BLACK_THRESH and g <= BLACK_THRESH and b <= BLACK_THRESH


def is_emblem_green(r: int, g: int, b: int) -> bool:
    return g >= 95 and g >= r + 35 and g >= b + 25 and r <= 95


def is_wordmark_color(r: int, g: int, b: int) -> bool:
    if is_matte_black(r, g, b):
        return False
    if r >= 100 and r >= g + 25 and b <= 120:
        return True
    if r >= 125 and g >= 80 and b <= 140 and g >= 70:
        return True
    return False


def emblem_region_mask(
    pixels: list[list[tuple[int, int, int, int]]], w: int, h: int
) -> list[list[bool]]:
    """Left emblem greens + interior black cutouts only."""
    seeds: list[tuple[int, int]] = []
    cut_x = int(w * 0.38)
    for y in range(h):
        for x in range(cut_x):
            if is_emblem_green(*pixels[y][x][:3]):
                seeds.append((x, y))
    if not seeds:
        return [[False] * w for _ in range(h)]

    xs = [x for x, _y in seeds]
    ys = [y for _x, y in seeds]
    pad = 2
    x0, x1 = max(0, min(xs) - pad), min(w, max(xs) + pad + 1)
    y0, y1 = max(0, min(ys) - pad), min(h, max(ys) + pad + 1)

    allow = [[False] * w for _ in range(h)]
    for y in range(y0, y1):
        for x in range(x0, x1):
            allow[y][x] = True

    green = [[is_emblem_green(*pixels[y][x][:3]) for x in range(w)] for y in range(h)]
    keep = [[False] * w for _ in range(h)]
    q: deque[tuple[int, int]] = deque(seeds)

    seen = [[False] * w for _ in range(h)]
    while q:
        x, y = q.popleft()
        if not allow[y][x] or seen[y][x]:
            continue
        seen[y][x] = True
        r, g, b, _a = pixels[y][x]
        if green[y][x]:
            keep[y][x] = True
        elif is_matte_black(r, g, b):
            keep[y][x] = True
        else:
            continue
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (0, 1)):
            nx, ny = x + dx, y + dy
            if allow[ny][nx]:
                q.append((nx, ny))
    return keep


def main() -> None:
    src = next((p for p in SRC_CANDIDATES if p.is_file()), ROOT / "public" / "bharathi-enterprises-logo.png")
    img = Image.open(src).convert("RGBA")
    w, h = img.size
    px = img.load()
    grid = [[px[x, y] for x in range(w)] for y in range(h)]

    emblem_mask = emblem_region_mask(grid, w, h)

    xs: list[int] = []
    ys: list[int] = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[x, y]
            if is_wordmark_color(r, g, b):
                xs.append(x)
                ys.append(y)
                continue
            if emblem_mask[y][x] and (is_emblem_green(r, g, b) or is_matte_black(r, g, b)):
                xs.append(x)
                ys.append(y)
                continue
            px[x, y] = (0, 0, 0, 0)

    if not xs:
        raise SystemExit("No logo pixels after background removal")

    pad = 4
    x0, x1 = max(0, min(xs) - pad), min(w, max(xs) + pad + 1)
    y0, y1 = max(0, min(ys) - pad), min(h, max(ys) + pad + 1)
    cropped = img.crop((x0, y0, x1, y1))

    min_w = 720
    if cropped.width < min_w:
        scale = min_w / cropped.width
        target_w = int(cropped.width * scale)
        target_h = max(1, int(cropped.height * scale))
        out = cropped.resize((target_w, target_h), Image.Resampling.LANCZOS)
    else:
        out = cropped
    for dest in (OUT_PUBLIC, OUT_SRC):
        dest.parent.mkdir(parents=True, exist_ok=True)
        out.save(dest, optimize=True)
    print(f"wrote {OUT_PUBLIC} and {OUT_SRC} size={out.size} (crop {cropped.size})")


if __name__ == "__main__":
    main()