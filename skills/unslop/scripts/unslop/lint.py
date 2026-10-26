"""규칙 실행과 점수."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .rules import Finding, Rule, rules_for
from .units import Unit


def lint(units: List[Unit], register: str) -> List[Finding]:
    rules = rules_for(register)
    out: List[Finding] = []
    active = [u for u in units if not u.keep]
    for r in rules:
        if r.doc_check:
            scope = [u for u in active if r.kinds is None or u.kind in r.kinds]
            for uid, span in r.doc_check(scope):
                u = next(x for x in active if x.id == uid)
                out.append(_finding(r, u, span))
        else:
            for u in active:
                if r.applies(register, u.kind):
                    span = r.unit_check(u)
                    if span:
                        out.append(_finding(r, u, span))
    out.sort(key=lambda f: (f.unit_id, f.code))
    return out


def _finding(r: Rule, u: Unit, span) -> Finding:
    return Finding(code=r.code, level=r.level, unit_id=u.id, kind=u.kind, msg=r.title, hint=r.hint, text=u.text, span=span)


def summary(findings: List[Finding], units: List[Unit]) -> Dict:
    chars = sum(len(u.text) for u in units if not u.keep) or 1
    err = [f for f in findings if f.level == "error"]
    warn = [f for f in findings if f.level == "warn"]
    # 짧은 글은 경고 1건만으로 점수가 부풀어 D 가 나온다(예제 실측) — 분모를 최소 500자로 둔다
    per_k = 1000.0 * (len(err) * 2 + len(warn)) / max(chars, 500)
    grade = "A" if per_k < 1 else "B" if per_k < 4 else "C" if per_k < 10 else "D"
    return {
        "units": len(units), "chars": chars,
        "errors": len(err), "warnings": len(warn),
        "units_with_errors": len({f.unit_id for f in err}),
        "by_code": dict(Counter(f.code for f in findings).most_common()),
        "score_per_1k": round(per_k, 2), "grade": grade,
    }


def format_summary(s: Dict, findings: List[Finding], show: int = 20) -> str:
    lines = ["단위 %d · 오류 %d · 경고 %d · 등급 %s (1천 자당 %.2f)" % (
        s["units"], s["errors"], s["warnings"], s["grade"], s["score_per_1k"])]
    for code, n in s["by_code"].items():
        lines.append("  %-4s %d" % (code, n))
    for f in findings[:show]:
        lines.append("  [%d|%s] %s %s  ← %s" % (f.unit_id, f.kind, f.code, f.text[:60], f.msg))
    if len(findings) > show:
        lines.append("  … 외 %d건" % (len(findings) - show))
    return "\n".join(lines)
