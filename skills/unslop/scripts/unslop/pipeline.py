"""전체 흐름.

  추출 → 자동 수정 → 검사(전) → [요청 파일 저장] → 윤문(묶음별) → 게이트 → 실패 단위만 지적을 붙여 재시도
  → 끝까지 실패한 단위는 원문 유지 → 반영(문서 또는 생성 스크립트) → 검사(후) → 보고서

작업 폴더(기본 .unslop/<파일이름>-<시각>/)에 단계별 산출물을 남긴다 — 무엇을 왜 바꿨는지 나중에 추적할 수 있게.
"""
from __future__ import annotations

import datetime
import io
import json
import os
from typing import Dict, List, Optional

from . import formats, gate, prompt, report
from .fix import fix_units
from .lint import lint, summary
from .providers import Provider
from .units import Unit, dump_lines, parse_lines


def _workdir(path: str, workdir: Optional[str]) -> str:
    if workdir:
        os.makedirs(workdir, exist_ok=True)
        return workdir
    stem = os.path.splitext(os.path.basename(path))[0]
    d = os.path.join(os.path.dirname(os.path.abspath(path)), ".unslop",
                     "%s-%s" % (stem, datetime.datetime.now().strftime("%Y%m%d-%H%M%S")))
    os.makedirs(d, exist_ok=True)
    return d


def _save(d: str, name: str, obj) -> str:
    p = os.path.join(d, name)
    if isinstance(obj, str):
        io.open(p, "w", encoding="utf-8").write(obj)
    else:
        json.dump(obj, io.open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    return p


def default_out(path: str) -> str:
    stem, ext = os.path.splitext(path)
    return stem + ".unslop" + ext


def prepare(path: str, register: Optional[str] = None, keep=(), workdir: Optional[str] = None,
            min_hangul: int = 2, only_flagged: bool = False) -> Dict:
    units, ctx = formats.extract(path, keep=keep, min_hangul=min_hangul)
    register = register or formats.default_register(ctx["format"], units)
    fixes = fix_units(units, register)
    findings = lint(units, register)
    d = _workdir(path, workdir)
    flagged = {f.unit_id for f in findings}
    targets = [u for u in units if not u.keep and (not only_flagged or u.id in flagged)]
    state = {"path": os.path.abspath(path), "format": ctx["format"], "register": register,
             "units": [u.__dict__ for u in units], "ctx": {k: v for k, v in ctx.items() if k != "original"},
             "original": ctx["original"], "fixes": fixes, "targets": [u.id for u in targets]}
    _save(d, "state.json", state)
    _save(d, "01_units.txt", dump_lines(units))
    _save(d, "00_lint_before.json", {"summary": summary(findings, units), "findings": [f.to_dict() for f in findings]})
    _save(d, "02_system_prompt.md", prompt.system_prompt(register))
    _save(d, "02_user_prompt.md", prompt.user_prompt(targets, findings))
    return {"workdir": d, "units": units, "ctx": ctx, "register": register, "findings": findings,
            "targets": targets, "fixes": fixes}


def rewrite(prep: Dict, provider: Provider, rounds: int = 2, batch_chars: int = 5000, log=print) -> Dict[int, tuple]:
    units: List[Unit] = prep["units"]
    register = prep["register"]
    system = prompt.system_prompt(register)
    by_unit = {u.id: u for u in units}
    accepted: Dict[int, tuple] = {}
    feedback: Dict[int, List[str]] = {}
    pending = list(prep["targets"])
    for rnd in range(1, rounds + 1):
        if not pending:
            break
        cand: Dict[int, tuple] = {}
        for bi, batch in enumerate(prompt.batches(pending, batch_chars), 1):
            flist = [f for f in prep["findings"] if f.unit_id in {u.id for u in batch}]
            user = prompt.user_prompt(batch, flist, {k: v for k, v in feedback.items() if k in {u.id for u in batch}})
            log("윤문 %d회차 묶음 %d (%d단위)" % (rnd, bi, len(batch)))
            raw = provider(system, user)
            _save(prep["workdir"], "03_response_r%d_b%d.txt" % (rnd, bi), raw)
            got = prompt.parse_response(raw)
            for u in batch:
                if u.id in got:
                    cand[u.id] = got[u.id]
        verdicts = gate.check(units, cand, register)
        _save(prep["workdir"], "04_gate_r%d.json" % rnd, [v.__dict__ for v in verdicts if v.id in cand])
        nxt = []
        for u in pending:
            v = next((x for x in verdicts if x.id == u.id), None)
            if u.id not in cand:
                feedback[u.id] = ["응답에 이 번호가 없었다"]
                nxt.append(u)
            elif v and v.ok:
                if cand[u.id][1] != u.text:
                    accepted[u.id] = cand[u.id]
            else:
                feedback[u.id] = v.reasons if v else ["판정 없음"]
                nxt.append(u)
        log("  게이트 통과 %d · 재시도 대상 %d" % (len(pending) - len(nxt), len(nxt)))
        pending = nxt
    prep["rejected"] = {u.id: feedback.get(u.id, []) for u in pending}
    return accepted


def finalize(prep: Dict, accepted: Dict[int, tuple], out: Optional[str] = None, source: Optional[str] = None) -> Dict:
    units: List[Unit] = prep["units"]
    register = prep["register"]
    ctx = prep["ctx"]
    before = [Unit(u.id, u.kind, ctx["original"][u.id], u.loc, u.keep) for u in units]
    after = [Unit(u.id, u.kind, accepted.get(u.id, (u.kind, u.text))[1], u.loc, u.keep) for u in units]
    write_info = {}
    if source:
        from .formats import source_io
        pairs = [(u.id, ctx["original"][u.id], a.text) for u, a in zip(units, after) if ctx["original"][u.id] != a.text]
        write_info = source_io.apply(source, pairs)
    else:
        out = out or default_out(ctx["path"])
        write_info = formats.write(ctx, after, out)
    f_before = lint(before, register)
    f_after = lint(after, register)
    d = prep["workdir"]
    _save(d, "05_final_units.txt", dump_lines(after))
    _save(d, "06_lint_after.json", {"summary": summary(f_after, after), "findings": [f.to_dict() for f in f_after]})
    rep = report.build(before, after, f_before, f_after, register, prep.get("rejected", {}), prep.get("fixes", []), write_info)
    _save(d, "report.json", rep)
    _save(d, "report.md", report.markdown(rep))
    rep["workdir"] = d
    return rep


def load_state(workdir: str) -> Dict:
    st = json.load(io.open(os.path.join(workdir, "state.json"), encoding="utf-8"))
    units = [Unit(**u) for u in st["units"]]
    ctx = dict(st["ctx"])
    ctx["original"] = {int(k): v for k, v in st["original"].items()}
    findings = lint(units, st["register"])
    targets = [u for u in units if u.id in set(st["targets"])]
    return {"workdir": workdir, "units": units, "ctx": ctx, "register": st["register"], "findings": findings,
            "targets": targets, "fixes": st.get("fixes", [])}


def apply_final(workdir: str, final_path: str, out: Optional[str] = None, source: Optional[str] = None) -> Dict:
    """에이전트·사람이 작성한 윤문본(「[번호|종류] 본문」 줄)을 게이트에 통과시켜 반영한다."""
    prep = load_state(workdir)
    got = {k: (kind, txt) for k, (kind, txt) in parse_lines(io.open(final_path, encoding="utf-8").read()).items()}
    got = {k: (kind, prompt.parse_response("[%d|%s] %s" % (k, kind, txt))[k][1]) for k, (kind, txt) in got.items()}
    verdicts = gate.check(prep["units"], got, prep["register"])
    accepted, rejected = {}, {}
    for v in verdicts:
        if v.id not in got:
            continue
        if v.ok:
            accepted[v.id] = got[v.id]
        else:
            rejected[v.id] = v.reasons
    prep["rejected"] = rejected
    _save(workdir, "04_gate_apply.json", [v.__dict__ for v in verdicts if v.id in got])
    return finalize(prep, accepted, out, source)
