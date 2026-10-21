# -*- coding: utf-8 -*-
"""转换引擎：检测本机可用的 Office / LibreOffice，并把演示文稿转成 PDF 或图片。

设计原则
--------
* 检测阶段只读注册表，不启动任何 Office 进程，避免开机就弹出 WPS/PPT 窗口。
* 真正转换时按优先级逐个尝试：Microsoft PowerPoint -> WPS 演示 -> LibreOffice。
* 每个引擎失败都会抛 EngineError，由上层自动降级到下一个引擎。
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

try:
    import winreg
except ImportError:  # 非 Windows 平台
    winreg = None  # type: ignore[assignment]

# Office 系列扩展名（需要外部引擎渲染）
OFFICE_EXTS = {
    ".ppt", ".pptx", ".pptm", ".pps", ".ppsx", ".ppsm", ".pot", ".potx", ".potm",
    ".odp",
}
PDF_EXTS = {".pdf"}
SUPPORTED_EXTS = OFFICE_EXTS | PDF_EXTS


class EngineError(RuntimeError):
    """某个引擎转换失败。"""


@dataclass
class Engine:
    """一个可用的转换引擎描述。"""

    id: str
    label: str
    kind: str                     # "com" / "soffice"
    progid: str = ""              # COM ProgID
    exe: str = ""                 # LibreOffice 可执行文件
    available: bool = False
    detail: str = ""              # 供界面展示的说明
    notes: list[str] = field(default_factory=list)

    @property
    def is_com(self) -> bool:
        return self.kind == "com"


# --------------------------------------------------------------------------- #
# 注册表探测
# --------------------------------------------------------------------------- #

def _read_reg(path: str, value: str = "") -> str | None:
    """在 32/64 位两个视图里读取注册表字符串。"""
    if winreg is None:
        return None
    for view in (winreg.KEY_WOW64_32KEY, winreg.KEY_WOW64_64KEY):
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, path, 0,
                                winreg.KEY_READ | view) as key:
                data, _ = winreg.QueryValueEx(key, value)
                if data:
                    return str(data)
        except OSError:
            continue
    return None


def _parse_exe_path(raw: str) -> str:
    """从注册表的服务器命令行里取出可执行文件路径。

    形如 '"C:\\...\\wpp.exe" /Automation' 或 'C:\\...\\wps.exe" /prometheus'
    都能正确取出路径。
    """
    raw = raw.strip()
    if raw.startswith('"'):
        end = raw.find('"', 1)
        if end > 0:
            return raw[1:end]
        return raw.strip('"')
    lower = raw.lower()
    idx = lower.find(".exe")
    if idx > 0:
        return raw[: idx + 4]
    return raw.split(" ")[0]


def _com_server_exe(progid: str) -> str:
    """取 ProgID 对应的服务器可执行文件路径，取不到返回空串。"""
    clsid = _read_reg(rf"{progid}\CLSID")
    if not clsid:
        return ""
    for sub in ("LocalServer32", "InprocServer32"):
        raw = _read_reg(rf"CLSID\{clsid}\{sub}")
        if raw:
            return _parse_exe_path(raw)
    return ""


def _find_soffice() -> str:
    """找 LibreOffice 的 soffice.exe。"""
    candidates = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        r"C:\Program Files\LibreOffice 7\program\soffice.exe",
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    found = shutil.which("soffice") or shutil.which("soffice.exe")
    return found or ""


def detect_engines() -> list[Engine]:
    """探测本机所有可用引擎（按优先级排序，可用在前）。"""
    engines: list[Engine] = []

    # 1) Microsoft PowerPoint
    ppt_exe = _com_server_exe("PowerPoint.Application")
    ppt_ok = bool(ppt_exe) and "POWERPNT.EXE" in ppt_exe.upper()
    engines.append(Engine(
        id="powerpoint",
        label="Microsoft PowerPoint",
        kind="com",
        progid="PowerPoint.Application",
        exe=ppt_exe,
        available=ppt_ok,
        detail=ppt_exe or "未安装",
    ))

    # 2) WPS 演示
    wps_exe = _com_server_exe("KWPP.Application")
    if not wps_exe:
        # 兜底：直接扫安装目录
        for base in (
            os.path.expandvars(r"%LOCALAPPDATA%\Kingsoft\WPS Office"),
            r"C:\Program Files (x86)\Kingsoft\WPS Office",
            r"C:\Program Files\Kingsoft\WPS Office",
        ):
            if os.path.isdir(base):
                for entry in sorted(os.listdir(base), reverse=True):
                    cand = os.path.join(base, entry, "office6", "wpp.exe")
                    if os.path.exists(cand):
                        wps_exe = cand
                        break
            if wps_exe:
                break
    engines.append(Engine(
        id="wps",
        label="WPS 演示",
        kind="com",
        progid="KWPP.Application",
        exe=wps_exe,
        available=bool(wps_exe) and os.path.exists(wps_exe),
        detail=wps_exe or "未安装",
    ))
    # 3) LibreOffice
    soffice = _find_soffice()
    engines.append(Engine(
        id="soffice",
        label="LibreOffice",
        kind="soffice",
        exe=soffice,
        available=bool(soffice) and os.path.exists(soffice),
        detail=soffice or "未安装",
    ))

    engines.sort(key=lambda e: (not e.available,))
    return engines


def available_engines() -> list[Engine]:
    return [e for e in detect_engines() if e.available]


# --------------------------------------------------------------------------- #
# Office -> PDF
# --------------------------------------------------------------------------- #

# 单次转换的超时时间（秒）。Office 卡死时父进程会直接 kill 子进程。
COM_TIMEOUT = 300


def release_com() -> None:
    """保留接口：转换已改为子进程执行，主进程无需持有 COM 实例。"""


def _worker_command(engine: Engine, src: Path, dst: Path) -> list[str]:
    """构造转换子进程的命令行。

    打包成 exe 后没有 python 解释器可用，这时让 exe 自己以
    「--office-worker」模式充当子进程（见 main.py 的入口分发）。
    """
    if getattr(sys, "frozen", False):
        return [sys.executable, "--office-worker", engine.progid, str(src), str(dst)]
    script = Path(__file__).resolve().parent / "office_worker.py"
    return [sys.executable, str(script), engine.progid, str(src), str(dst)]


def _com_convert(engine: Engine, src: Path, dst: Path) -> Path:
    """通过独立子进程调用 Office/WPS 把演示文稿另存为 PDF。

    子进程隔离的原因见 app/office_worker.py：COM 卡死可以超时终止，
    Office 实例也不会在本进程累积残留。
    """
    err_file = dst.with_suffix(dst.suffix + ".err")
    try:
        err_file.unlink()
    except OSError:
        pass

    cmd = _worker_command(engine, src, dst)
    try:
        proc = subprocess.run(
            cmd, capture_output=True, timeout=COM_TIMEOUT,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except subprocess.TimeoutExpired as exc:
        raise EngineError(
            f"{engine.label} 转换超时（超过 {COM_TIMEOUT} 秒），已强制终止。"
            f"请检查该文件是否弹出对话框或体积过大") from exc

    # 打包成窗口程序后子进程没有 stderr，错误信息通过 .err 文件回传
    message = ""
    if err_file.exists():
        try:
            message = err_file.read_text(encoding="utf-8", errors="ignore").strip()
            err_file.unlink()
        except OSError:
            pass
    if not message and proc.stderr:
        message = proc.stderr.decode("utf-8", "ignore").strip()

    if proc.returncode != 0:
        raise EngineError(message or f"{engine.label} 转换失败（返回码 {proc.returncode}）")

    if not dst.exists() or dst.stat().st_size == 0:
        raise EngineError(message or f"{engine.label} 未能生成 PDF")
    return dst


def _soffice_convert(engine: Engine, src: Path, dst: Path) -> Path:
    """通过 LibreOffice 无头模式转 PDF。"""
    outdir = dst.parent
    profile = Path(tempfile.gettempdir()) / "ppt2img_lo_profile"
    cmd = [
        engine.exe,
        f"-env:UserInstallation=file:///{profile.as_posix()}",
        "--headless", "--norestore", "--invisible",
        "--convert-to", "pdf",
        "--outdir", str(outdir),
        str(src),
    ]
    try:
        proc = subprocess.run(cmd, capture_output=True, timeout=300,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except subprocess.TimeoutExpired as exc:
        raise EngineError("LibreOffice 转换超时（超过 5 分钟）") from exc
    produced = outdir / (src.stem + ".pdf")
    if not produced.exists():
        msg = (proc.stderr or proc.stdout or b"").decode("utf-8", "ignore").strip()
        raise EngineError(f"LibreOffice 转换失败：{msg[:300] or '无输出'}")
    if produced.resolve() != dst.resolve():
        try:
            shutil.move(str(produced), str(dst))
        except Exception as exc:
            raise EngineError(f"无法写入 PDF：{exc}") from exc
    return dst


def office_to_pdf(src: Path, workdir: Path, engine: Engine, stem: str | None = None) -> Path:
    """把 ppt/pptx/odp 转成 PDF，返回 PDF 路径。"""
    src = Path(src).resolve()          # Office COM 不接受相对路径
    workdir = Path(workdir).resolve()
    workdir.mkdir(parents=True, exist_ok=True)
    dst = workdir / f"{stem or src.stem}.pdf"
    if engine.kind == "com":
        return _com_convert(engine, src, dst)
    if engine.kind == "soffice":
        return _soffice_convert(engine, src, dst)
    raise EngineError(f"未知引擎类型：{engine.kind}")
