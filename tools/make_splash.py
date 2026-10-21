# -*- coding: utf-8 -*-
"""生成启动画面 assets/splash.png（单文件 exe 解压期间显示）。

用法：
    .venv\\Scripts\\python.exe tools\\make_splash.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "splash.png"

PRIMARY = (42, 109, 244, 255)
TEXT = (23, 32, 46, 255)
MUTED = (102, 112, 133, 255)
CARD = (255, 255, 255, 255)
BORDER = (228, 231, 236, 255)

W, H = 560, 300
FONT_CANDIDATES = [
    r"C:\Windows\Fonts\msyhbd.ttc",
    r"C:\Windows\Fonts\msyh.ttc",
    r"C:\Windows\Fonts\simhei.ttf",
]


def load_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    order = FONT_CANDIDATES if bold else [FONT_CANDIDATES[1], FONT_CANDIDATES[2]]
    for path in order:
        if Path(path).exists():
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def make_icon(size: int) -> Image.Image:
    scale = 4
    s = size * scale
    img = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    pad = int(s * 0.03)
    d.rounded_rectangle([pad, pad, s - pad, s - pad], radius=int(s * 0.23), fill=PRIMARY)
    bx0, by0 = int(s * 0.22), int(s * 0.24)
    bx1, by1 = int(s * 0.78), int(s * 0.58)
    d.rounded_rectangle([bx0, by0, bx1, by1], radius=int(s * 0.05), fill=(255, 255, 255, 255))
    bar_h = max(2, int(s * 0.045))
    inner = int(s * 0.05)
    d.rounded_rectangle([bx0 + inner, by0 + inner, bx1 - int(s * 0.12), by0 + inner + bar_h],
                        radius=bar_h // 2, fill=PRIMARY)
    d.rounded_rectangle([bx0 + inner, by0 + inner * 2 + bar_h,
                         bx1 - int(s * 0.22), by0 + inner * 2 + bar_h * 2],
                        radius=bar_h // 2, fill=(150, 180, 245, 255))
    for i, ratio in enumerate((0.56, 0.38)):
        y = int(s * (0.68 + i * 0.1))
        d.rounded_rectangle([int(s * 0.22), y, int(s * (0.22 + ratio)), y + bar_h],
                            radius=bar_h // 2,
                            fill=(255, 255, 255, 255) if i == 0 else (200, 218, 250, 255))
    return img.resize((size, size), Image.LANCZOS)


def main() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    scale = 2
    img = Image.new("RGBA", (W * scale, H * scale), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    s = scale

    d.rounded_rectangle([0, 0, W * s - 1, H * s - 1], radius=16 * s, fill=CARD)
    d.rounded_rectangle([0, 0, W * s - 1, H * s - 1], radius=16 * s, outline=BORDER, width=1 * s)

    icon = make_icon(64 * s)
    img.alpha_composite(icon, (40 * s, 40 * s))

    title_font = load_font(26 * s, bold=True)
    sub_font = load_font(14 * s)
    hint_font = load_font(12 * s)

    d.text((120 * s, 46 * s), "幻灯片转图片", font=title_font, fill=TEXT)
    d.text((120 * s, 82 * s), "把 PPT / PPTX / PDF 的每一页导出为图片",
           font=sub_font, fill=MUTED)

    # 进度条底槽
    bar_y = 176 * s
    d.rounded_rectangle([40 * s, bar_y, (W - 40) * s, bar_y + 4 * s],
                        radius=2 * s, fill=(233, 237, 243, 255))
    # 装饰性进度（静态）
    d.rounded_rectangle([40 * s, bar_y, 300 * s, bar_y + 4 * s],
                        radius=2 * s, fill=PRIMARY)

    d.text((40 * s, 206 * s), "正在准备运行环境，首次启动需要几秒钟…",
           font=sub_font, fill=TEXT)
    d.text((40 * s, 240 * s), "需要本机安装 WPS 或 Microsoft PowerPoint 才能转换 PPT 文件",
           font=hint_font, fill=MUTED)

    img = img.resize((W, H), Image.LANCZOS)
    img.save(OUT)
    print("已生成", OUT, OUT.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
