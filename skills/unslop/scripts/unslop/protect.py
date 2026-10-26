"""보호 토큰 — 윤문해도 절대 바뀌면 안 되는 조각.

수치·단위·버전·이슈 번호·경로·URL·코드·이메일·arXiv 번호·영문 용어를 찾는다.
LLM 에 보낼 때는 ⟦ ⟧ 로 감싸 표시하고, 게이트는 단위마다 보호 토큰의 다중집합이 같은지 본다.
"""
from __future__ import annotations

import collections
import re
from typing import List

L, R = "⟦", "⟧"

_PATTERNS = [
    r"https?://[^\s)」\]>]+",                                   # URL
    r"[A-Za-z]:\\[^\s,)」\]가-힣⟦⟧]+",                          # Windows 경로 (한글 조사 앞에서 끊는다)
    # 상대·POSIX 경로 (a/b/c, _workspace/). \w 는 한글도 잡아 「공공문서/산불」을 경로로 오인하므로 ASCII 로 한정한다
    r"(?<![A-Za-z0-9_/])(?:\.{0,2}/)?(?:[A-Za-z0-9_.-]+/)+[A-Za-z0-9_.*-]*",
    r"[\w.*-]+\.(?:md|csv|py|json|png|jpg|pptx|docx|xlsx|pdf|log|txt|yaml|yml)\b",  # 파일명
    r"`[^`]+`",                                                 # 인라인 코드
    r"[\w.+-]+@[\w-]+\.[\w.]+",                                 # 이메일
    r"\b\d{4}\.\d{4,5}(?:v\d+)?\b",                             # arXiv id
    r"(?:v|#|P)\d+(?:\.\d+)*",                                  # 버전·이슈 번호·등급(P1)
    # 수치. %·영문 단위(GB·M 등)는 함께 묶고, 한글 단위(편·건·원…)는 묶지 않고 숫자만 비교한다.
    # 한글 단위를 묶으면 조사와 엉킨다: 「190편을」≠「190편 조사」, 「524 원인」을 「524 원」+「인」으로 쪼갬(둘 다 실제 사례)
    r"[±~]?\d+(?:[.,:]\d+)*(?:%|\s?(?:GB|GiB|MB|TB|KB|ms|M|K|B)(?![A-Za-z]))?",
    r"[A-Za-z][A-Za-z0-9_+.-]*[A-Za-z0-9+]|[A-Za-z]",           # 영문 용어 (LoRA, JSON, gemma-4-12B)
]
TOKEN = re.compile("|".join("(?:%s)" % p for p in _PATTERNS))


def tokens(text: str) -> List[str]:
    """보호 토큰 목록(앞에서부터, 겹치지 않게)."""
    t = text.replace(L, "").replace(R, "")
    return [m.group(0).rstrip(".,") for m in TOKEN.finditer(t) if m.group(0).strip()]


def counter(text: str) -> collections.Counter:
    return collections.Counter(tokens(text))


def mark(text: str) -> str:
    """LLM 에 보낼 때 보호 토큰을 ⟦ ⟧ 로 감싼다."""
    return TOKEN.sub(lambda m: L + m.group(0) + R if m.group(0).strip() else m.group(0), text)


def unmark(text: str) -> str:
    return text.replace(L, "").replace(R, "")
