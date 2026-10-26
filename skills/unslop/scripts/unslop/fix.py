"""결정적 자동 수정 — 의미가 바뀔 수 없는 것만 고친다(LLM 호출 0회).

  C01 영문·숫자·코드 표기 뒤 띄어 쓴 조사 → 붙여 쓰기
  C09 화살표(→ ⇒ ➜ -> =>) → 꺾쇠(>), 양방향(↔ ⇄) → vs
  C10 「N번 넘게」 → 「N회 이상」
  S04 개조식 줄 끝 마침표 → 지우기 (slide·brief)
  공백 정리: 연속 공백 → 한 칸
인라인 코드(`…`) 안은 건드리지 않는다.
"""
from __future__ import annotations

import re
from typing import List, Tuple

from .rules import SPACED_PARTICLE
from .units import Unit

_ARROW = re.compile(r"\s*(?:→|⇒|➜|➔|⟶|(?<![<=!-])->|(?<![<=!])=>)\s*")
_QTY = re.compile(r"(\d[\d,.]*)\s?번\s?넘게")
_BIARROW = re.compile(r"\s*(?:↔|⇄|⟷|<->)\s*")   # 양방향 화살표는 대비라서 「>」가 아니라 「vs」


def _outside_code(text: str, fn) -> str:
    parts = re.split(r"(`[^`]*`)", text)
    return "".join(p if p.startswith("`") and p.endswith("`") and len(p) > 1 else fn(p) for p in parts)


def _plain_fixes(t: str) -> str:
    t = _BIARROW.sub(" vs ", t)
    t = _ARROW.sub(" > ", t)
    t = _QTY.sub(lambda m: m.group(1) + "회 이상", t)
    return t


def fix_text(text: str, register: str, kind: str) -> str:
    t = _outside_code(text, _plain_fixes)
    t = SPACED_PARTICLE.sub(lambda m: m.group(0).lstrip(), t)
    t = re.sub(r"(?<=\S) {2,}(?=\S)", " ", t)
    t = t.strip() if text == text.strip() else t
    if register in ("slide", "brief") and kind != "para":
        if re.search(r"[가-힣A-Za-z0-9\)」]\.$", t.rstrip()) and not re.search(r"(\.\.\.|…|\d\.)$", t.rstrip()):
            t = t.rstrip()[:-1]
    return t


def fix_units(units: List[Unit], register: str) -> List[Tuple[int, str, str]]:
    """제자리에서 고치고 (번호, 전, 후) 목록을 돌려준다."""
    changed = []
    for u in units:
        if u.keep:
            continue
        new = fix_text(u.text, register, u.kind)
        if new != u.text:
            changed.append((u.id, u.text, new))
            u.text = new
    return changed
