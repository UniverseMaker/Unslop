# -*- coding: utf-8 -*-
from unslop import gate, protect
from unslop.fix import fix_text
from unslop.units import Unit


def test_protect_tokens():
    t = "v4는 12.95M 토큰, 41.9%를 D:\\usai\\research\\papers에 저장(arXiv 2401.03129, LoRA r32)"
    toks = protect.tokens(t)
    for x in ["v4", "12.95M", "41.9%", "D:\\usai\\research\\papers", "2401.03129", "LoRA", "r32"]:
        assert x in toks, (x, toks)


def test_protect_does_not_treat_korean_slash_as_path():
    assert "공공문서/산불" not in "".join(protect.tokens("공공문서/산불/시설 3종"))


def test_number_unit_not_split_korean_word():
    """「524 원인」을 「524 원」+「인」으로 쪼개면 「원인」을 고칠 수 없다(실제 사례)."""
    assert "524 원" not in protect.tokens("HTTP 524 원인 및 해결")
    assert protect.counter("선행연구 190편을 읽었다") == protect.counter("선행연구 190편 조사")
    assert protect.counter("산불 데이터의 42%가 같은 틀") == protect.counter("중복 42% 이상 발견")


def test_mark_roundtrip():
    t = "v4는 JSON 0/16"
    assert protect.unmark(protect.mark(t)) == t


def test_gate_number_change_blocked():
    u = [Unit(1, "body", "JSON 14 → 0 (/16)")]
    v = gate.check(u, {1: ("body", "JSON 14 → 1 (/16)")}, "slide")
    assert not v[0].ok and any(r.startswith("G2") for r in v[0].reasons)


def test_gate_path_with_particle_ok():
    """경로 뒤에 붙은 조사가 빠져도 경로가 바뀐 것으로 보면 안 된다(실제 오탐 사례)."""
    u = [Unit(1, "subtitle", "PDF는 모두 D:\\usai\\research\\papers에 있다")]
    v = gate.check(u, {1: ("subtitle", "PDF 위치: D:\\usai\\research\\papers")}, "slide")
    assert v[0].ok, v[0].reasons


def test_gate_length_and_lint():
    u = [Unit(1, "title", "선행연구 190편을 받아서 열고 본문을 읽었다")]
    ok = gate.check(u, {1: ("title", "선행연구 190편 조사 및 연구완료")}, "slide")[0]
    assert ok.ok, ok.reasons
    bad = gate.check(u, {1: ("title", "선행연구 190편을 모두 조사했다")}, "slide")[0]
    assert any(r.startswith("G4") for r in bad.reasons)


def test_gate_keep_unit():
    u = [Unit(1, "body", "재난 유형: 화재 / 신뢰: 95%", keep=True)]
    v = gate.check(u, {1: ("body", "재난 유형 화재, 신뢰 95%")}, "slide")[0]
    assert any(r.startswith("G5") for r in v.reasons)


def test_fix_particles_and_period():
    assert fix_text("v4 는 JSON 을 못 냈다", "report", "para") == "v4는 JSON을 못 냈다"
    assert fix_text("폴더 통째 복사(과제 규칙).", "slide", "body") == "폴더 통째 복사(과제 규칙)"
    assert fix_text("버전 1.", "slide", "body") == "버전 1."
    assert fix_text("`--keep` 으로 뺀다", "report", "para") == "`--keep`으로 뺀다"
    assert fix_text("「원문 유지」 에 적힌다", "report", "para") == "「원문 유지」에 적힌다"
    assert fix_text("실패 → 원인 실측→재설계", "slide", "subtitle") == "실패 > 원인 실측 > 재설계"
    assert fix_text("100번 넘게 나온 줄 집계", "slide", "subtitle") == "100회 이상 나온 줄 집계"
    assert fix_text("망각 없음(EEVE) ↔ 하락(KMMLU)", "slide", "body") == "망각 없음(EEVE) vs 하락(KMMLU)"
    assert fix_text("`a -> b` 는 코드다", "report", "para") == "`a -> b`는 코드다"   # 인라인 코드 안은 그대로
