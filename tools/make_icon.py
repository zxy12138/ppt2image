# -*- coding: utf-8 -*-
"""生成程序图标 assets/app.ico（多尺寸），供窗口与 exe 使用。

用法：
    .venv\\Scripts\\python.exe tools\\make_icon.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "app.ico"

PRIMARY = (42, 109, 244, 255)
PRIMARY_DARK = (24, 73, 174, 255)
WHITE = (255, 255, 255, 255)


def draw_icon(size: int) -> Image.Image:
    scale = 4                      # 超采样，边缘更平滑
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = int(s * 0.03)
    radius = int(s * 0.23)
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=radius, fill=PRIMARY)

    # 幻灯片主体
    bx0, by0 = int(s * 0.22), int(s * 0.24)
    bx1, by1 = int(s * 0.78), int(s * 0.58)
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=int(s * 0.05), fill=WHITE)

    # 幻灯片里的两条「文字条」
    inner_pad = int(s * 0.05)
    bar_h = max(2, int(s * 0.045))
    d.rounded_rectangle([bx0 + inner_pad, by0 + inner_pad,
                         bx1 - int(s * 0.12), by0 + inner_pad + bar_h],
                        radius=bar_h // 2, fill=PRIMARY)
    d.rounded_rectangle([bx0 + inner_pad, by0 + inner_pad * 2 + bar_h,
                         bx1 - int(s * 0.22), by0 + inner_pad * 2 + bar_h * 2],
                        radius=bar_h // 2, fill=(150, 180, 245, 255))

    # 下方两条横线，暗示「多页」
    for i, width_ratio in enumerate((0.56, 0.38)):
        y = int(s * (0.68 + i * 0.1))
        d.rounded_rectangle([int(s * 0.22), y, int(s * (0.22 + width_ratio)), y + bar_h],
                            radius=bar_h // 2, fill=WHITE if i == 0 else (200, 218, 250, 255))

    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    sizes = [16, 24, 32, 48, 64, 128, 256]
    images = [draw_icon(sz) for sz in sizes]
    images[-1].save(OUT, format="ICO", sizes=[(s, s) for s in sizes],
                    append_images=images[:-1])
    # 同时存一份 PNG 方便预览
    images[-1].save(OUT.with_suffix(".png"))
    print("已生成", OUT, OUT.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
