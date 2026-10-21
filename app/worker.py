# -*- coding: utf-8 -*-
"""后台线程：文件解析（取页数 / 生成预览）与批量导出。

注意：跨线程只通过基础类型（str/int/tuple）传信号，不传 dict，
避免 PySide6 在队列连接下对复杂对象序列化时出现顺序错乱。
"""

from __future__ import annotations

import queue
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from .converter import DocumentError, DocumentLoader, RenderOptions
from .engines import Engine, EngineError, release_com
from .pages import build_filename, parse_page_spec

# Office COM 是单实例的，解析与导出必须串行
COM_LOCK = threading.Lock()


@dataclass
class FileTask:
    """一个待解析/导出的文件。"""

    path: Path
    page_mode: str = "all"      # all / current / range
    page_spec: str = ""
    current_page: int = 1


# --------------------------------------------------------------------------- #
# 解析线程
# --------------------------------------------------------------------------- #

class ParseWorker(QThread):
    """常驻线程：把文件转成 PDF、读取页数、生成预览缩略图。"""

    parsed = Signal(str, int, int, int)      # 路径, 页数, 宽pt, 高pt
    failed = Signal(str, str)                # 路径, 错误
    preview_ready = Signal(str, int, bytes)  # 路径, 页码, PNG 字节

    def __init__(self, loader: DocumentLoader, workdir: Path, parent=None):
        super().__init__(parent)
        self._loader = loader
        self._queue: queue.Queue[tuple[str, object] | None] = queue.Queue()
        self._engine: Engine | None = None
        self._stop = False

    def set_engine(self, engine: Engine | None) -> None:
        self._engine = engine

    def request_parse(self, path: Path) -> None:
        self._queue.put(("parse", Path(path)))

    def request_preview(self, path: Path, page_no: int, dpi: int = 96) -> None:
        self._queue.put(("preview", (Path(path), page_no, dpi)))

    def request_stop(self) -> None:
        self._stop = True
        self._queue.put(None)

    def run(self) -> None:  # noqa: D102
        while not self._stop:
            item = self._queue.get()
            if item is None:
                break
            kind, payload = item
            try:
                if kind == "parse":
                    self._do_parse(payload)  # type: ignore[arg-type]
                elif kind == "preview":
                    self._do_preview(payload)  # type: ignore[arg-type]
            except Exception:  # pragma: no cover - 兜底防止线程退出
                traceback.print_exc()
        release_com()

    # -- 内部 ------------------------------------------------------------- #
    def _do_parse(self, path: Path) -> None:
        try:
            with COM_LOCK:
                doc = self._loader.open(path, self._engine)
            try:
                count = doc.page_count
                w, h = doc.page_size(1) if count else (0.0, 0.0)
            finally:
                doc.close()
            self.parsed.emit(str(path), int(count), int(round(w)), int(round(h)))
        except (DocumentError, EngineError) as exc:
            self.failed.emit(str(path), str(exc))
        except Exception as exc:
            self.failed.emit(str(path), f"解析失败：{exc}")

    def _do_preview(self, payload: tuple[Path, int, int]) -> None:
        path, page_no, dpi = payload
        try:
            with COM_LOCK:
                doc = self._loader.open(path, self._engine)
            try:
                page_no = max(1, min(page_no, doc.page_count))
                opt = RenderOptions(fmt="PNG", size_mode="width", width_px=1400,
                                    background="white")
                data = doc.render_page(page_no, opt)
            finally:
                doc.close()
            self.preview_ready.emit(str(path), int(page_no), data)
        except Exception as exc:
            self.failed.emit(str(path), f"预览失败：{exc}")


# --------------------------------------------------------------------------- #
# 导出线程
# --------------------------------------------------------------------------- #

class ExportWorker(QThread):
    """批量导出：按每个文件的页码设置逐页渲染并落盘。"""

    progress = Signal(int, int, str)     # 已完成, 总数, 当前描述
    file_done = Signal(str, int)         # 路径, 生成张数
    failed = Signal(str, str)
    finished_all = Signal(int, int, str)  # 文件数, 图片数, 输出根目录

    def __init__(self, loader: DocumentLoader, tasks: list[FileTask],
                 opt: RenderOptions, out_root: Path, subfolder: bool,
                 template: str, conflict: str, engine: Engine | None, parent=None):
        super().__init__(parent)
        self._loader = loader
        self._tasks = tasks
        self._opt = opt
        self._out_root = Path(out_root)
        self._subfolder = subfolder
        self._template = template
        self._conflict = conflict      # overwrite / skip / rename
        self._engine = engine
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:  # noqa: D102
        try:
            self._run_all()
        finally:
            release_com()

    def _run_all(self) -> None:
        total_files = len(self._tasks)
        total_images = 0
        done_files = 0
        try:
            self._out_root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            self.failed.emit(str(self._out_root), f"无法创建输出目录：{exc}")
            self.finished_all.emit(0, 0, str(self._out_root))
            return

        for task in self._tasks:
            if self._cancel:
                break
            try:
                count = self._export_one(task)
                total_images += count
                done_files += 1
                self.file_done.emit(str(task.path), count)
            except (DocumentError, EngineError, ValueError) as exc:
                self.failed.emit(str(task.path), str(exc))
            except Exception as exc:
                self.failed.emit(str(task.path), f"导出异常：{exc}")
            self.progress.emit(done_files, total_files, task.path.name)

        self.finished_all.emit(done_files, total_images, str(self._out_root))

    # -- 单个文件 --------------------------------------------------------- #
    def _export_one(self, task: FileTask) -> int:
        with COM_LOCK:
            doc = self._loader.open(task.path, self._engine)

        try:
            pages = self._resolve_pages(task, doc.page_count)
            if self._subfolder:
                target = self._out_root / task.path.stem
            else:
                target = self._out_root
            target.mkdir(parents=True, exist_ok=True)

            written = 0
            for page_no in pages:
                if self._cancel:
                    break
                name = build_filename(self._template, task.path.stem, page_no,
                                      doc.page_count, self._opt.ext)
                out_path = self._unique_path(target / name)
                if out_path is None:
                    continue  # skip 模式
                data = doc.render_page(page_no, self._opt)
                tmp = out_path.with_suffix(out_path.suffix + ".part")
                tmp.write_bytes(data)
                tmp.replace(out_path)
                written += 1
            return written
        finally:
            doc.close()

    def _resolve_pages(self, task: FileTask, total: int) -> list[int]:
        if task.page_mode == "all":
            return list(range(1, total + 1))
        if task.page_mode == "current":
            page = max(1, min(task.current_page, total))
            return [page]
        return parse_page_spec(task.page_spec, total)

    def _unique_path(self, path: Path) -> Path | None:
        """按冲突策略决定最终路径；skip 模式返回 None。"""
        if not path.exists():
            return path
        if self._conflict == "overwrite":
            return path
        if self._conflict == "skip":
            return None
        stem, suffix = path.stem, path.suffix
        for i in range(2, 1000):
            cand = path.with_name(f"{stem}_{i}{suffix}")
            if not cand.exists():
                return cand
        return path
