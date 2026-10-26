"""결과 보고서(JSON·Markdown)."""
from __future__ import annotations

from collections import Counter
from typing import Dict, List

from .lint import summary
from .rules import Finding, RULES
from .units import Unit

_TITLE = {r.code: r.title for r in RULES}


def build(before: List[Unit], after: List[Unit], f_before: List[Finding], f_after: List[Finding],
          register: str, rejected: Dict[int, List[str]], fixes, write_info: Dict) -> Dict:
    changed = [(b, a) for b, a in zip(before, after) if b.text != a.text]
    codes = sorted(set(f.code for f in f_before) | set(f.code for f in f_after))
    cb, ca = Counter(f.code for f in f_before), Counter(f.code for f in f_after)
    return {
        "register": register,
        "before": summary(f_before, before),
        "after": summary(f_after, after),
        "by_code": [{"code": c, "title": _TITLE.get(c, ""), "before": cb[c], "after": ca[c]} for c in codes],
        "changed_units": len(changed),
        "total_units": len(before),
        "examples": [{"id": b.id, "kind": b.kind, "before": b.text, "after": a.text} for b, a in changed[:20]],
        "auto_fixed": len(fixes),
        "rejected": [{"id": k, "reasons": v} for k, v in sorted(rejected.items())],
        "residual_errors": [f.to_dict() for f in f_after if f.level == "error"],
        "write": write_info,
    }


def markdown(rep: Dict) -> str:
    b, a = rep["before"], rep["after"]
    L = ["# 윤문 결과", "",
         "| 항목 | 전 | 후 |", "|---|---:|---:|",
         "| 오류 | %d | %d |" % (b["errors"], a["errors"]),
         "| 경고 | %d | %d |" % (b["warnings"], a["warnings"]),
         "| 등급 (1천 자당 점수) | %s (%.2f) | %s (%.2f) |" % (b["grade"], b["score_per_1k"], a["grade"], a["score_per_1k"]),
         "| 바뀐 단위 | | %d / %d |" % (rep["changed_units"], rep["total_units"]),
         "| 자동 수정 | | %d |" % rep["auto_fixed"],
         "| 게이트에서 막혀 원문 유지 | | %d |" % len(rep["rejected"]), "",
         "## 규칙별", "", "| 코드 | 규칙 | 전 | 후 |", "|---|---|---:|---:|"]
    for r in rep["by_code"]:
        L.append("| %s | %s | %d | %d |" % (r["code"], r["title"], r["before"], r["after"]))
    L += ["", "## 바뀐 예", "", "| # | 종류 | 전 | 후 |", "|---|---|---|---|"]
    for e in rep["examples"]:
        L.append("| %d | %s | %s | %s |" % (e["id"], e["kind"], e["before"].replace("|", "\\|"), e["after"].replace("|", "\\|")))
    if rep["rejected"]:
        L += ["", "## 원문 유지 (게이트 실패)", ""]
        for r in rep["rejected"]:
            L.append("- [%d] %s" % (r["id"], "; ".join(r["reasons"])))
    if rep["residual_errors"]:
        L += ["", "## 남은 오류", ""]
        for f in rep["residual_errors"]:
            L.append("- [%d|%s] %s %s — %s" % (f["unit"], f["kind"], f["code"], f["msg"], f["text"][:80]))
    return "\n".join(L) + "\n"
