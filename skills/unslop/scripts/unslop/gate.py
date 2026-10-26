"""게이트 — 윤문 결과를 반영해도 되는지 코드로 판정한다(LLM 호출 0회).

  G1 구성     번호·종류가 원문과 같다
  G2 보호     단위마다 보호 토큰(수치·버전·경로·URL·코드·영문 용어)의 다중집합이 같다
  G3 길이     slide·brief ≤ 원문×1.15+2, report 는 원문의 0.5~1.3배 (내용 삭제·부풀림 방지)
  G4 규칙     윤문본에 error 수준 규칙 위반이 없다
  G5 보존     keep 단위는 한 글자도 바뀌지 않았다

판정은 단위별로 낸다. 통과한 단위만 반영하고, 실패 단위는 재시도하거나 원문으로 둔다.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from . import protect
from .lint import lint
from .units import Unit


@dataclass
class UnitVerdict:
    id: int
    ok: bool
    reasons: List[str] = field(default_factory=list)


def length_ok(before: str, after: str, register: str) -> bool:
    if register in ("slide", "brief"):
        return len(after) <= len(before) * 1.15 + 2
    lo, hi = len(before) * 0.5 - 5, len(before) * 1.3 + 5
    return lo <= len(after) <= hi


def check(units: List[Unit], new_text: Dict[int, tuple], register: str) -> List[UnitVerdict]:
    """new_text: {번호: (종류, 윤문본)} — 바뀌지 않은 단위는 빠져 있어도 된다."""
    after_units = []
    verdicts: Dict[int, UnitVerdict] = {}
    for u in units:
        v = UnitVerdict(u.id, True)
        if u.id in new_text:
            kind, txt = new_text[u.id]
            if kind != u.kind:
                v.reasons.append("G1 종류 바뀜 %s→%s" % (u.kind, kind))
            if u.keep and txt != u.text:
                v.reasons.append("G5 보존 단위 변경")
            if protect.counter(u.text) != protect.counter(txt):
                lost = protect.counter(u.text) - protect.counter(txt)
                added = protect.counter(txt) - protect.counter(u.text)
                v.reasons.append("G2 보호 토큰 변경 (빠짐 %s / 추가 %s)" % (list(lost.elements())[:5], list(added.elements())[:5]))
            if not length_ok(u.text, txt, register):
                v.reasons.append("G3 길이 %d→%d" % (len(u.text), len(txt)))
            after_units.append(Unit(u.id, u.kind, txt, u.loc, u.keep))
        else:
            after_units.append(u)
        verdicts[u.id] = v
    extra = set(new_text) - {u.id for u in units}
    for uid in extra:
        verdicts[uid] = UnitVerdict(uid, False, ["G1 없는 번호"])
    for f in lint(after_units, register):
        if f.level == "error" and f.unit_id in new_text:
            verdicts[f.unit_id].reasons.append("G4 %s %s" % (f.code, f.msg))
    for v in verdicts.values():
        v.ok = not v.reasons
    return [verdicts[k] for k in sorted(verdicts)]


def format_verdicts(vs: List[UnitVerdict], show: int = 15) -> str:
    bad = [v for v in vs if not v.ok]
    lines = ["게이트: 단위 %d 중 통과 %d · 실패 %d" % (len(vs), len(vs) - len(bad), len(bad))]
    for v in bad[:show]:
        lines.append("  [%d] %s" % (v.id, "; ".join(v.reasons)))
    return "\n".join(lines)
