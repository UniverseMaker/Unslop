"""Markdown(·txt) 단위 추출과 반영.

한 줄 = 한 단위. 표는 칸마다 한 단위. 줄 앞의 서식 기호(#, -, 1., >, □ ○ - ·)는 단위 밖에 두고
되돌려 넣을 때 그대로 붙인다. 코드 블록·머리말(front matter)·HTML 주석·표 구분선은 건드리지 않는다.
"""
from __future__ import annotations

import io
import re
from typing import Dict, List, Tuple

from ..units import Unit, hangul_count

HEAD = re.compile(r"^(\s{0,3}#{1,6}\s+)(.*)$")
BULLET = re.compile(r"^(\s*(?:[-*+]|\d+[.)])\s+)(.*)$")
BRIEF = re.compile(r"^(\s*([□■○◦\-·※])\s+)(.*)$")
QUOTE = re.compile(r"^(\s*>\s?)(.*)$")
TABLE_SEP = re.compile(r"^\s*\|?\s*:?-{2,}:?\s*(\|\s*:?-{2,}:?\s*)*\|?\s*$")


def _cells(line: str):
    """「| a | b |」 → [(시작, 끝, 내용)] (내용 앞뒤 공백 제외 위치)."""
    out, pos = [], 0
    s = line
    if not s.strip().startswith("|"):
        return None
    idx = [m.start() for m in re.finditer(r"(?<!\\)\|", s)]
    for a, b in zip(idx, idx[1:]):
        seg = s[a + 1:b]
        lead = len(seg) - len(seg.lstrip())
        trail = len(seg) - len(seg.rstrip())
        out.append((a + 1 + lead, b - trail, seg.strip()))
    return out


def extract(path: str, min_hangul: int = 2) -> Tuple[List[Unit], Dict]:
    lines = io.open(path, encoding="utf-8").read().split("\n")
    units: List[Unit] = []
    in_code = in_front = in_comment = False
    for i, line in enumerate(lines):
        st = line.strip()
        if i == 0 and st == "---":
            in_front = True
            continue
        if in_front:
            if st == "---":
                in_front = False
            continue
        if st.startswith("```") or st.startswith("~~~"):
            in_code = not in_code
            continue
        if in_code:
            continue
        if "<!--" in st and "-->" not in st:
            in_comment = True
            continue
        if in_comment:
            if "-->" in st:
                in_comment = False
            continue
        if not st or TABLE_SEP.match(line) or st.startswith("<!--"):
            continue

        def add(kind, text, loc):
            if hangul_count(text) >= min_hangul:
                units.append(Unit(len(units) + 1, kind, text, loc))

        cells = _cells(line)
        if cells is not None:
            for c, (a, b, txt) in enumerate(cells):
                add("cell", txt, {"line": i, "start": a, "end": b, "cell": c})
            continue
        for pat, kind in ((HEAD, "heading"), (QUOTE, "quote")):
            m = pat.match(line)
            if m:
                add(kind, m.group(2).rstrip(), {"line": i, "prefix": m.group(1)})
                break
        else:
            m = BRIEF.match(line)
            if m and m.group(2) in "□■○◦※·":
                add("bullet", m.group(3).rstrip(), {"line": i, "prefix": m.group(1), "marker": m.group(2)})
                continue
            m = BULLET.match(line)
            if m:
                marker = "-" if m.group(1).strip() in ("-", "*", "+") else None
                add("bullet", m.group(2).rstrip(), {"line": i, "prefix": m.group(1), "marker": marker})
                continue
            lead = line[:len(line) - len(line.lstrip())]
            add("para", line.strip(), {"line": i, "prefix": lead})
    return units, {"lines": lines}


def write(ctx: Dict, units: List[Unit], out: str) -> Dict:
    lines = list(ctx["lines"])
    # 표 칸은 한 줄에 여러 개라 뒤 칸부터 바꿔야 앞 칸 위치가 어긋나지 않는다
    for u in sorted(units, key=lambda x: (x.loc["line"], -x.loc.get("start", 0))):
        i = u.loc["line"]
        if "cell" in u.loc:
            s = lines[i]
            lines[i] = s[:u.loc["start"]] + u.text + s[u.loc["end"]:]
        else:
            lines[i] = u.loc.get("prefix", "") + u.text
    io.open(out, "w", encoding="utf-8").write("\n".join(lines))
    return {"written": out, "units": len(units)}
