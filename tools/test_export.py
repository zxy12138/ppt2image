# -*- coding: utf-8 -*-
"""无界面验证导出链路：页码解析、命名模板、子目录、冲突策略。

用法：
    .venv\\Scripts\\python.exe tools\\test_export.py
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QCoreApplication      # noqa: E402

from app.converter import DocumentLoader, RenderOptions   # noqa: E402
from app.engines import available_engines                 # noqa: E402
from app.pages import build_filename, parse_page_spec     # noqa: E402
from app.worker import ExportWorker, FileTask             # noqa: E402

OUT = ROOT / "samples" / "_export"


def check_pages() -> None:
    cases = [
        ("1,3,5-9", 10, [1, 3, 5, 6, 7, 8, 9]),
        ("1-3", 5, [1, 2, 3]),
        ("9-2", 10, [2, 3, 4, 5, 6, 7, 8, 9]),
        (" 2 ， 4 ", 6, [2, 4]),
        ("1,99", 5, [1]),
    ]
    for spec, total, expect in cases:
        got = parse_page_spec(spec, total)
        assert got == expect, f"{spec} -> {got} != {expect}"
    print("[OK] 页码解析", len(cases), "组")

    for bad in ("", "abc", "1-", ",,"):
        try:
            parse_page_spec(bad, 10)
        except ValueError:
            pass
        else:
            raise AssertionError(f"应当报错：{bad!r}")
    print("[OK] 非法页码抛错")


def check_naming() -> None:
    samples = [
        ("{name}_{page:03d}", "报告", 7, 20, "png", "报告_007.png"),
        ("{name}-{page}", "报告", 7, 20, "jpg", "报告-7.jpg"),
        ("第{page}页_{name}", "报告", 2, 20, "png", "第2页_报告.png"),
        ("{index:02d}", "报告", 3, 20, "webp", "03.webp"),
    ]
    for tpl, stem, page, total, ext, expect in samples:
        got = build_filename(tpl, stem, page, total, ext)
        assert got == expect, f"{tpl} -> {got} != {expect}"
    print("[OK] 命名模板", len(samples), "组")


def main() -> int:
    check_pages()
    check_naming()

    if OUT.exists():
        shutil.rmtree(OUT, ignore_errors=True)

    engine = (available_engines() or [None])[0]
    print("引擎:", engine.label if engine else "无（只能处理 PDF）")

    app = QCoreApplication(sys.argv[:1])
    loader = DocumentLoader(ROOT / "samples" / "_cache_test")

    tasks = [
        FileTask(ROOT / "samples" / "测试演示.pptx", "range", "1,3", 1),
        FileTask(ROOT / "samples" / "测试文档.pdf", "all", "", 1),
    ]
    opt = RenderOptions(fmt="PNG", size_mode="dpi", dpi=144)
    worker = ExportWorker(loader, tasks, opt, OUT, True,
                          "{name}_p{page:02d}", "rename", engine)

    result = {}

    def on_done(files: int, images: int, outdir: str) -> None:
        result.update(files=files, images=images, outdir=outdir)
        app.quit()

    worker.finished_all.connect(on_done)
    worker.failed.connect(lambda p, m: print("  ✗", Path(p).name, m))
    worker.file_done.connect(lambda p, c: print("  ✓", Path(p).name, c, "张"))
    worker.progress.connect(lambda d, t, n: None)
    worker.start()
    app.exec()

    print("结果:", result)
    for path in sorted(OUT.rglob("*")):
        if path.is_file():
            print("   ", path.relative_to(OUT), path.stat().st_size, "bytes")

    ok = result.get("files") == 2 and result.get("images") == 5
    print("测试通过" if ok else "测试失败：期望 2 个文件 5 张图")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
