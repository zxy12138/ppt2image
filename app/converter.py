# -*- coding: utf-8 -*-
"""渲染核心：把 PDF / PPT 的每一页渲染成图片字节流。

统一走「先转 PDF，再用 PyMuPDF 光栅化」这条链路，好处是：
* 文字是矢量的，任意分辨率都清晰；
* PDF / PPT / PPTX / ODP 共用同一套渲染与命名逻辑；
* 单页、指定页码、全量导出只是页码列表不同，没有第二套代码。
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

try:  # PyMuPDF 1.24+ 推荐 pymupdf，旧版只有 fitz
    import pymupdf as fitz  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover
    import fitz  # type: ignore[no-redef]

from PIL import Image

from .engines import Engine, office_to_pdf

# 单页最长边像素上限，防止 600DPI + A0 直接把内存打爆
MAX_EDGE = 16000


@dataclass
class RenderOptions:
    """导出参数。"""

    fmt: str = "PNG"              # PNG / JPG / WEBP
    size_mode: str = "dpi"        # dpi / width / height
    dpi: int = 150
    width_px: int = 1920
    height_px: int = 1080
    background: str = "white"     # white / black / transparent
    quality: int = 92             # JPG / WEBP 质量

    @property
    def ext(self) -> str:
        return {"JPG": "jpg", "JPEG": "jpg", "WEBP": "webp"}.get(self.fmt.upper(), "png")

    @property
    def pil_format(self) -> str:
        return {"JPG": "JPEG", "JPEG": "JPEG", "WEBP": "WEBP"}.get(self.fmt.upper(), "PNG")

    @property
    def supports_alpha(self) -> bool:
        return self.pil_format in ("PNG", "WEBP")

    @property
    def bg_color(self) -> tuple[int, int, int]:
        return (0, 0, 0) if self.background == "black" else (255, 255, 255)


class DocumentError(RuntimeError):
    """文档无法打开或渲染。"""


class RenderedDocument:
    """一份已经转换好的 PDF 文档，可按页渲染。"""

    def __init__(self, pdf_path: Path, source_path: Path):
        self.pdf_path = Path(pdf_path)
        self.source_path = Path(source_path)
        try:
            self._doc = fitz.open(str(self.pdf_path))
        except Exception as exc:
            raise DocumentError(f"无法打开 PDF：{exc}") from exc
        if getattr(self._doc, "needs_pass", False) or not self._doc.is_pdf:
            self._doc.close()
            raise DocumentError("该文件已加密（需要打开密码），请先解除密码后再导出")

    # -- 基本信息 --------------------------------------------------------- #
    @property
    def page_count(self) -> int:
        return self._doc.page_count

    def page_size(self, page_no: int) -> tuple[float, float]:
        """返回页面宽高（单位 pt）。"""
        rect = self._doc.load_page(page_no - 1).rect
        return rect.width, rect.height

    def close(self) -> None:
        try:
            self._doc.close()
        except Exception:
            pass

    # -- 渲染 ------------------------------------------------------------- #
    def render_page(self, page_no: int, opt: RenderOptions) -> bytes:
        """把第 page_no 页（从 1 开始）渲染成图片字节。"""
        if not 1 <= page_no <= self.page_count:
            raise DocumentError(f"页码 {page_no} 超出范围（共 {self.page_count} 页）")

        page = self._doc.load_page(page_no - 1)
        rect = page.rect

        if opt.size_mode == "width":
            zoom = max(0.05, opt.width_px / max(rect.width, 1e-6))
        elif opt.size_mode == "height":
            zoom = max(0.05, opt.height_px / max(rect.height, 1e-6))
        else:
            zoom = max(0.05, opt.dpi / 72.0)

        # 限制超大画布
        long_edge = max(rect.width, rect.height) * zoom
        if long_edge > MAX_EDGE:
            zoom *= MAX_EDGE / long_edge

        want_alpha = opt.background == "transparent" and opt.supports_alpha
        matrix = fitz.Matrix(zoom, zoom)
        try:
            pix = page.get_pixmap(matrix=matrix, alpha=want_alpha, colorspace=fitz.csRGB)
        except Exception as exc:
            raise DocumentError(f"第 {page_no} 页渲染失败：{exc}") from exc

        mode = "RGBA" if pix.alpha else "RGB"
        img = Image.frombytes(mode, (pix.width, pix.height), pix.samples)

        if mode == "RGBA":
            if want_alpha:
                img = img.copy()
            else:
                base = Image.new("RGB", img.size, opt.bg_color)
                base.paste(img, mask=img.getchannel("A"))
                img = base
        elif opt.background == "black":
            # 已是 RGB，直接保留（PDF 白底会盖住黑底，属正常表现）
            img = img.copy()

        return _encode(img, opt)


def _encode(img: Image.Image, opt: RenderOptions) -> bytes:
    buf = io.BytesIO()
    fmt = opt.pil_format
    if fmt == "JPEG":
        img.convert("RGB").save(buf, format="JPEG", quality=int(opt.quality),
                                subsampling=0 if opt.quality >= 95 else 2,
                                optimize=True)
    elif fmt == "WEBP":
        img.save(buf, format="WEBP", quality=int(opt.quality), method=4)
    else:
        img.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# 打开源文件（PDF 直接开，Office 先转 PDF）
# --------------------------------------------------------------------------- #

class DocumentLoader:
    """负责把各种源文件变成 RenderedDocument，并缓存转换结果。"""

    def __init__(self, workdir: Path):
        self.workdir = Path(workdir)
        self.workdir.mkdir(parents=True, exist_ok=True)
        self._converted: dict[str, Path] = {}   # 源路径 -> PDF 路径

    def _cache_key(self, path: Path) -> str:
        try:
            st = path.stat()
            return f"{path.resolve()}|{st.st_mtime_ns}|{st.st_size}"
        except OSError:
            return str(path)

    def pdf_for(self, src: Path, engine: Engine | None, force: bool = False) -> Path:
        """返回源文件对应的 PDF 路径（Office 文件会先转换并缓存）。"""
        src = Path(src)
        if src.suffix.lower() == ".pdf":
            return src

        key = self._cache_key(src)
        if not force and key in self._converted and self._converted[key].exists():
            return self._converted[key]

        if engine is None:
            raise DocumentError(
                "没有可用的转换引擎：请安装 Microsoft PowerPoint、WPS 演示或 LibreOffice"
            )

        # 缓存目录名带 hash，避免同名文件互相覆盖
        import hashlib
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()[:10]
        stem = f"{src.stem}_{digest}"
        pdf = office_to_pdf(src, self.workdir, engine, stem=stem)
        self._converted[key] = pdf
        return pdf

    def open(self, src: Path, engine: Engine | None) -> RenderedDocument:
        pdf = self.pdf_for(src, engine)
        return RenderedDocument(pdf, src)

    def cleanup(self) -> None:
        """清空临时转换目录。"""
        import shutil
        try:
            shutil.rmtree(self.workdir, ignore_errors=True)
        except Exception:
            pass
