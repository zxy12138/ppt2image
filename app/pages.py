# -*- coding: utf-8 -*-
"""页码解析与输出文件命名规则。"""

from __future__ import annotations

import re

# 支持 {name} {page} {index} {total}，并支持 {page:03d} 这类补零格式
_PLACEHOLDER = re.compile(r"\{(name|page|index|total)(?::(0?)(\d+)d)?\}")


def parse_page_spec(spec: str, total: int) -> list[int]:
    """把 "1,3,5-9" 解析成 [1,3,5,6,7,8,9]（页码从 1 开始，去重、升序、越界忽略）。

    非法输入抛 ValueError，方便界面提示用户。
    """
    if not spec or not spec.strip():
        raise ValueError("页码不能为空")

    result: set[int] = set()
    for chunk in re.split(r"[,，;；\s]+", spec.strip()):
        if not chunk:
            continue
        if "-" in chunk or "~" in chunk or "－" in chunk:
            parts = re.split(r"[-~－]", chunk, maxsplit=1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                raise ValueError(f"页码范围格式错误：{chunk}")
            try:
                start, end = int(parts[0]), int(parts[1])
            except ValueError:
                raise ValueError(f"页码范围格式错误：{chunk}")
            if start > end:
                start, end = end, start
            for n in range(start, end + 1):
                if 1 <= n <= total:
                    result.add(n)
        else:
            try:
                n = int(chunk)
            except ValueError:
                raise ValueError(f"无法识别的页码：{chunk}")
            if 1 <= n <= total:
                result.add(n)

    if not result:
        raise ValueError(f"页码超出范围（文档共 {total} 页）")
    return sorted(result)


def validate_page_spec(spec: str) -> str | None:
    """只校验语法，返回错误信息；合法时返回 None。"""
    if not spec or not spec.strip():
        return "页码不能为空，例如 1,3,5-9"
    for chunk in re.split(r"[,，;；\s]+", spec.strip()):
        if not chunk:
            continue
        if "-" in chunk or "~" in chunk or "－" in chunk:
            parts = re.split(r"[-~－]", chunk, maxsplit=1)
            if len(parts) != 2:
                return f"页码范围格式错误：{chunk}"
            try:
                int(parts[0])
                int(parts[1])
            except ValueError:
                return f"页码范围格式错误：{chunk}"
        else:
            try:
                int(chunk)
            except ValueError:
                return f"无法识别的页码：{chunk}"
    return None


def build_filename(template: str, stem: str, page_no: int, total: int, ext: str) -> str:
    """按模板生成文件名。

    占位符：
        {name}   源文件名（不含扩展名）
        {page}   页码，从 1 开始
        {index}  输出序号，从 1 开始（批量多文件时连续递增）
        {total}  总页数
    """
    if not template or not template.strip():
        template = "{name}_{page:03d}"

    def _sub(match: re.Match) -> str:
        key = match.group(1)
        pad_flag = match.group(2)
        width = match.group(3)
        if key == "name":
            return stem
        value = {"page": page_no, "index": page_no, "total": total}[key]
        if width:
            text = str(value).zfill(int(width)) if pad_flag else str(value).rjust(int(width))
            return text
        return str(value)

    name = _PLACEHOLDER.sub(_sub, template)
    # 清理 Windows 非法字符
    name = re.sub(r'[\\/:*?"<>|]', "_", name).strip(" .")
    if not name:
        name = f"{stem}_{page_no:03d}"
    if not name.lower().endswith("." + ext.lower()):
        name = f"{name}.{ext}"
    return name


def human_size(num: int) -> str:
    """字节数转可读体积。"""
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.0f} {unit}" if unit == "B" else f"{num:.1f} {unit}"
        num /= 1024.0
    return f"{num:.1f} GB"
