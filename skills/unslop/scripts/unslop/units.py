"""문서 단위(Unit)와 줄 형식 직렬화.

문서는 형식(Markdown·PPTX·DOCX)과 상관없이 「단위」 목록으로 바뀐다. 단위 하나는 윤문의 최소 단위다
(Markdown 한 줄, 표 칸 하나, PPT 글자 조각 하나, DOCX 문단 하나).

LLM 과 주고받는 줄 형식:  [번호|종류] 본문
"""
from __future__ import annotations

import io
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional

# 단위 종류. 규칙은 종류마다 다르게 적용된다.
KINDS = (
    "title",     # 슬라이드 제목
    "subtitle",  # 슬라이드 부제
    "label",     # 상자 제목·글머리 머리·태그 (굵은 짧은 글)
    "heading",   # 문서 제목·절 제목
    "para",      # 서술 문단
    "bullet",    # 글머리 항목
    "cell",      # 표 칸
    "quote",     # 인용 블록
    "body",      # 슬라이드 본문
)

LINE = re.compile(r"^\[(\d+)\|([a-z]+)\]\s?(.*)$")


@dataclass
class Unit:
    id: int
    kind: str
    text: str
    loc: Dict = field(default_factory=dict)   # 원래 자리(형식별 위치 정보) — 되돌려 넣을 때 쓴다
    keep: bool = False                         # True 면 윤문하지 않는다(인용 원문 등)

    def line(self) -> str:
        return "[%d|%s] %s" % (self.id, self.kind, self.text)


def dump_lines(units: Iterable[Unit]) -> str:
    return "\n".join(u.line() for u in units) + "\n"


def parse_lines(text: str) -> Dict[int, tuple]:
    """「[번호|종류] 본문」 줄들을 {번호: (종류, 본문)} 으로. 다른 줄은 무시한다."""
    out: Dict[int, tuple] = {}
    for raw in text.splitlines():
        m = LINE.match(raw.strip())
        if m:
            out[int(m.group(1))] = (m.group(2), m.group(3).strip())
    return out


def read_lines(path: str) -> Dict[int, tuple]:
    return parse_lines(io.open(path, encoding="utf-8").read())


def by_id(units: List[Unit]) -> Dict[int, Unit]:
    return {u.id: u for u in units}


def hangul_count(text: str) -> int:
    return len(re.findall(r"[가-힣]", text))


def find(units: List[Unit], uid: int) -> Optional[Unit]:
    for u in units:
        if u.id == uid:
            return u
    return None
