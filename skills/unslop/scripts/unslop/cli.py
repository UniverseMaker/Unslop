"""명령줄 도구 `unslop`.

  unslop lint   FILE                 규칙 검사만 (오류가 있으면 종료 코드 1)
  unslop fix    FILE [-o OUT]        의미가 바뀔 수 없는 것만 자동 수정
  unslop run    FILE [-o OUT]        윤문 전체 흐름 (provider 를 고르면 LLM 호출, none 이면 요청 파일만)
  unslop apply  WORKDIR FINAL        에이전트·사람이 쓴 윤문본을 게이트에 통과시켜 반영
  unslop rules  [--markdown]         규칙 목록
"""
from __future__ import annotations

import argparse
import io
import os
import json
import sys

from . import __version__, formats, pipeline
from .fix import fix_units
from .lint import format_summary, lint, summary
from .providers import ProviderError, make
from .rules import RULES, REGISTERS, catalog_markdown


def _common(p):
    p.add_argument("--register", choices=REGISTERS, help="문서 종류 (기본: pptx→slide, □○ 기호가 많으면 brief, 그 밖은 report)")
    p.add_argument("--keep", action="append", default=[], help="이 문자열이 든 단위는 건드리지 않는다(인용 원문 등, 여러 번)")
    p.add_argument("--min-hangul", type=int, default=2, help="한글이 이 글자 수보다 적은 단위는 건너뛴다")


def cmd_lint(a) -> int:
    units, ctx = formats.extract(a.file, keep=a.keep, min_hangul=a.min_hangul)
    reg = a.register or formats.default_register(ctx["format"], units)
    fs = lint(units, reg)
    s = summary(fs, units)
    print("레지스터: %s" % reg)
    print(format_summary(s, fs, a.show))
    if a.json:
        json.dump({"register": reg, "summary": s, "findings": [f.to_dict() for f in fs]},
                  io.open(a.json, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    return 1 if s["errors"] else 0


def cmd_fix(a) -> int:
    units, ctx = formats.extract(a.file, keep=a.keep, min_hangul=a.min_hangul)
    reg = a.register or formats.default_register(ctx["format"], units)
    changed = fix_units(units, reg)
    out = a.output or pipeline.default_out(a.file)
    formats.write(ctx, units, out)
    print("자동 수정 %d곳 → %s" % (len(changed), out))
    for uid, x, y in changed[:a.show]:
        print("  [%d] %s\n     → %s" % (uid, x, y))
    return 0


def cmd_run(a) -> int:
    try:
        prov = make(a.provider, a.model, a.effort, not a.no_fallback, a.cmd)
    except ProviderError as e:
        print("오류:", e, file=sys.stderr)
        return 2
    prep = pipeline.prepare(a.file, a.register, a.keep, a.workdir, a.min_hangul, a.only_flagged)
    s = summary(prep["findings"], prep["units"])
    print("레지스터: %s · 작업 폴더: %s" % (prep["register"], prep["workdir"]))
    print("검사(전): " + format_summary(s, prep["findings"], 0).splitlines()[0])
    if prov is None:
        print("provider 가 none 이라 요청 파일만 만들었습니다:")
        print("  시스템 문  %s" % os.path.join(prep["workdir"], "02_system_prompt.md"))
        print("  윤문 대상  %s (%d단위)" % (os.path.join(prep["workdir"], "02_user_prompt.md"), len(prep["targets"])))
        print("윤문본을 「[번호|종류] 본문」 줄로 작성한 뒤:  unslop apply %s <윤문본>" % prep["workdir"])
        return 0
    try:
        accepted = pipeline.rewrite(prep, prov, a.rounds, a.batch_chars)
    except ProviderError as e:
        print("오류:", e, file=sys.stderr)
        return 2
    rep = pipeline.finalize(prep, accepted, a.output, a.source)
    return _print_report(rep)


def cmd_apply(a) -> int:
    rep = pipeline.apply_final(a.workdir, a.final, a.output, a.source)
    return _print_report(rep)


def _print_report(rep) -> int:
    b, f = rep["before"], rep["after"]
    print("오류 %d → %d · 경고 %d → %d · 등급 %s → %s · 바뀐 단위 %d/%d · 원문 유지 %d" % (
        b["errors"], f["errors"], b["warnings"], f["warnings"], b["grade"], f["grade"],
        rep["changed_units"], rep["total_units"], len(rep["rejected"])))
    print("반영: %s" % json.dumps(rep["write"], ensure_ascii=False))
    print("보고서: %s" % os.path.join(rep["workdir"], "report.md"))
    return 1 if f["errors"] else 0


def cmd_rules(a) -> int:
    if a.markdown:
        # 바이트로 쓴다 — Windows 표준출력은 \n 을 \r\n 으로 바꿔 references/RULES.md 와 어긋난다(CI 비교 실패)
        sys.stdout.flush()
        sys.stdout.buffer.write(catalog_markdown().encode("utf-8"))
        return 0
    for r in RULES:
        if a.register and a.register not in r.registers:
            continue
        print("%s %-5s %-30s %s" % (r.code, r.level, r.title, ",".join(r.registers)))
    return 0


def main(argv=None) -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(prog="unslop", description="연구보고서·PPT·개조식 보고서 한국어 윤문 도구 (unslop %s)" % __version__)
    ap.add_argument("--version", action="version", version=__version__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("lint", help="규칙 검사")
    p.add_argument("file")
    _common(p)
    p.add_argument("--json")
    p.add_argument("--show", type=int, default=30)
    p.set_defaults(func=cmd_lint)

    p = sub.add_parser("fix", help="결정적 자동 수정")
    p.add_argument("file")
    p.add_argument("-o", "--output")
    _common(p)
    p.add_argument("--show", type=int, default=20)
    p.set_defaults(func=cmd_fix)

    p = sub.add_parser("run", help="윤문 전체 흐름")
    p.add_argument("file")
    p.add_argument("-o", "--output", help="결과 파일 (기본: <이름>.unslop.<확장자>, 원본은 덮어쓰지 않는다)")
    _common(p)
    p.add_argument("--provider", choices=("none", "claude-cli", "anthropic", "cmd"), default="none")
    p.add_argument("--cmd", help="--provider cmd 일 때 실행할 명령(요청문을 표준입력으로 받는다)")
    p.add_argument("--model", help="모델 ID (anthropic 기본 claude-opus-5-5)")
    p.add_argument("--effort", default="medium", choices=("low", "medium", "high", "xhigh", "max"))
    p.add_argument("--no-fallback", action="store_true", help="anthropic: 서버 쪽 대체 모델 끄기")
    p.add_argument("--rounds", type=int, default=2, help="게이트 실패 단위 재시도 횟수 포함 최대 회차")
    p.add_argument("--batch-chars", type=int, default=5000)
    p.add_argument("--only-flagged", action="store_true", help="검사기가 지적한 단위만 윤문")
    p.add_argument("--source", help="문서를 만드는 스크립트에 결과를 반영(PPT 생성기 등)")
    p.add_argument("--workdir")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("apply", help="윤문본 반영")
    p.add_argument("workdir")
    p.add_argument("final", help="「[번호|종류] 본문」 줄로 된 윤문본")
    p.add_argument("-o", "--output")
    p.add_argument("--source")
    p.set_defaults(func=cmd_apply)

    p = sub.add_parser("rules", help="규칙 목록")
    p.add_argument("--register", choices=REGISTERS)
    p.add_argument("--markdown", action="store_true")
    p.set_defaults(func=cmd_rules)

    a = ap.parse_args(argv)
    return a.func(a)


if __name__ == "__main__":
    raise SystemExit(main())
