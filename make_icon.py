"""Generate the app icon: mint clock/timesheet mark on a dark rounded square.

Writes assets/icon.ico with 16-256 px layers. Run once (build.ps1 runs it).
"""

import os

from PIL import Image, ImageDraw

DARK = (13, 13, 13, 255)
PANEL = (22, 22, 22, 255)
MINT = (61, 220, 151, 255)
MINT_DIM = (61, 220, 151, 90)


def draw_icon(size):
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = size

    # dark rounded-square background
    r = int(s * 0.22)
    d.rounded_rectangle([0, 0, s - 1, s - 1], radius=r, fill=DARK)

    # clock face
    cx, cy = s / 2, s / 2
    face_r = s * 0.34
    ring_w = max(1, int(s * 0.055))
    d.ellipse([cx - face_r, cy - face_r, cx + face_r, cy + face_r],
              outline=MINT, width=ring_w)

    # tick marks at 12/3/6/9 (skip at tiny sizes)
    if s >= 32:
        tick_len = s * 0.06
        tw = max(1, int(s * 0.03))
        for dx, dy in ((0, -1), (1, 0), (0, 1), (-1, 0)):
            x1 = cx + dx * (face_r - tick_len - ring_w)
            y1 = cy + dy * (face_r - tick_len - ring_w)
            x2 = cx + dx * (face_r - ring_w * 1.2)
            y2 = cy + dy * (face_r - ring_w * 1.2)
            d.line([x1, y1, x2, y2], fill=MINT_DIM, width=tw)

    # hands at ~17:30 (hour toward 5-6, minute at 6)
    hw = max(1, int(s * 0.055))
    d.line([cx, cy, cx, cy + face_r * 0.62], fill=MINT, width=hw)          # minute -> 6
    d.line([cx, cy, cx + face_r * 0.45, cy + face_r * 0.28], fill=MINT,
           width=hw)                                                        # hour -> ~5:30
    dot_r = max(1, int(s * 0.045))
    d.ellipse([cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r], fill=MINT)

    # timesheet lines bottom-right corner
    if s >= 48:
        lx = s * 0.62
        lw = max(1, int(s * 0.035))
        for i, ln in enumerate((0.26, 0.20, 0.14)):
            y = s * (0.80 + i * 0.065)
            d.line([lx, y, lx + s * ln, y], fill=MINT, width=lw)
    return img


def main():
    out_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "icon.ico")
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [draw_icon(s) for s in sizes]
    images[-1].save(out, format="ICO",
                    sizes=[(s, s) for s in sizes],
                    append_images=images[:-1])
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
