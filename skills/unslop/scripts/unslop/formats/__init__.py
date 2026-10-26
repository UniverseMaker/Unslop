"""문서 형식별 단위 추출·반영. 형식마다 extract(path, opts) -> (units, ctx) 와 write(ctx, units, out) 를 둔다."""
from __future__ import annotations

import os
from typing import Dict, List, Tuple

import re

from ..units import Unit, hangul_count

_FIXABLE = re.compile(r"→|⇒|➜|➔|⟶|↔|⇄|⟷|\d\s?번\s?넘게")


def detect(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    return {".md": "markdown", ".markdown": "markdown", ".txt": "markdown",
            ".pptx": "pptx", ".docx": "docx"}.get(ext, "markdown")


def extract(path: str, keep: List[str] = (), min_hangul: int = 2) -> Tuple[List[Unit], Dict]:
    fmt = detect(path)
    if fmt == "pptx":
        from . import pptx_io as m
    elif fmt == "docx":
        from . import docx_io as m
    else:
        from . import markdown_io as m
    raw, ctx = m.extract(path, min_hangul=0)
    # 한글이 적은 칸도 자동 수정 대상(화살표 등)이 있으면 넣는다 — 「JSON 14 → 3 → 0」 같은 칸을 놓치던 문제
    units = [u for u in raw if hangul_count(u.text) >= min_hangul or _FIXABLE.search(u.text)]
    for i, u in enumerate(units, 1):
        u.id = i
    for u in units:
        if any(k and k in u.text for k in keep):
            u.keep = True
    ctx["format"] = fmt
    ctx["path"] = path
    ctx["original"] = {u.id: u.text for u in units}
    return units, ctx


def write(ctx: Dict, units: List[Unit], out: str) -> Dict:
    fmt = ctx["format"]
    if fmt == "pptx":
        from . import pptx_io as m
    elif fmt == "docx":
        from . import docx_io as m
    else:
        from . import markdown_io as m
    return m.write(ctx, units, out)


def default_register(fmt: str, units: List[Unit]) -> str:
    if fmt == "pptx":
        return "slide"
    markers = sum(1 for u in units if u.loc.get("marker") in ("□", "○"))
    return "brief" if markers >= 3 else "report"
