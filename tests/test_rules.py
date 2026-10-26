# -*- coding: utf-8 -*-
"""규칙 회귀 시험. 실제 업무에서 지적받은 문장을 고정 사례로 둔다(2026-10, 도시안전 AI 연구노트)."""
import pytest

from unslop.lint import lint
from unslop.rules import RULES
from unslop.units import Unit


def codes(text, kind="body", register="slide"):
    return {f.code for f in lint([Unit(1, kind, text)], register) if f.level == "error"}


@pytest.mark.parametrize("kind,text,code", [
    ("title", "선행연구 190편을 받아서 열고 본문을 읽었다", "S01"),
    ("subtitle", "사용자 지시: 「임의로 전처리·학습하지 말고 선행연구부터 싹 다 조사해서 계획부터 다시 짜라」", "C05"),
    ("subtitle", "사용자 지시: 「임의로 전처리·학습하지 말고 선행연구부터 싹 다 조사해서 계획부터 다시 짜라」", "C04"),
    ("title", "검증 손실은 좋아졌고 판정 능력은 나빠졌다", "S01"),
    ("body", "학습은 살렸다. nvidia-smi 기준으로 교체", "S03"),
    ("body", "v4는 실패 — 원인은 데이터 구성", "C02"),
    ("body", "v4 는 실패", "C01"),
    ("body", "백업은 폴더 통째 복사(과제 규칙).", "S04"),
    ("body", "이렇게 하면 됩니다", "S02"),
    ("body", "✅ 학습 완료", "C03"),
    ("body", "이 파일은 최종 결과가 아니다", "S01"),   # 앞 글자 목록 방식이 놓치던 종결
    ("body", "모델을 고친다", "S01"),
])
def test_slide_bad(kind, text, code):
    assert code in codes(text, kind)


@pytest.mark.parametrize("kind,text", [
    ("title", "선행연구 190편 조사 및 연구완료"),
    ("subtitle", "선행연구 조사 및 재계획"),
    ("title", "검증 손실 개선, 판정 능력 하락"),
    ("cell", "공공문서·산불·시설"),
    ("body", "학습데이터 문체를 그대로 모방한 출력"),
    ("cell", "12.95M 토큰 학습데이터"),
    ("body", "v4 실패 원인: 데이터 구성"),
    ("body", "긴급도 3단계와 P1~P5 대응표 확정 필요"),     # 「필요」를 존댓말 「~요」로 오탐하던 버그
    ("cell", "주요 결정 사항과 개요"),
    ("body", "학습데이터"),                               # 「데이터」를 「~다」 종결로 오탐하면 안 된다
    ("cell", "사업 개요(1차년도)"),
    ("cell", "예상보다 빠른 수렴"),
    ("cell", "월마다"),
])
def test_slide_good(kind, text):
    assert codes(text, kind) == set()


@pytest.mark.parametrize("kind,text,code", [
    # 2026-10-26 사용자 지적 사례
    ("title", "이번 달 한눈에", "S07"),
    ("title", "데이터 품질, 왜 중요한가", "S07"),
    ("subtitle", "실패 → 원인 실측 → 선행연구 → 재설계", "C09"),
    ("cell", "공공문서 1.44 → 1.41", "C09"),
    ("subtitle", "학습데이터 전체에서 100번 넘게 나온 줄 집계", "C10"),
])
def test_user_feedback_bad(kind, text, code):
    assert code in codes(text, kind)


@pytest.mark.parametrize("kind,text", [
    ("title", "월간 요약"),
    ("title", "산불 데이터 중복 건수 42% 이상 발견"),
    ("subtitle", "100회 이상 중복데이터 집계"),
    ("subtitle", "실패 > 원인 실측 > 선행연구 > 재설계"),
    ("cell", "공공문서 1.44 > 1.41"),
    ("label", "쉬운 정리본: 00_한눈에_정리.md"),   # 파일명 안의 「한눈에」는 제목 표현이 아님(실제 오탐)
])
def test_user_feedback_good(kind, text):
    assert codes(text, kind) == set()


def test_report_mixed_endings():
    units = [Unit(1, "para", "데이터를 정제했다."), Unit(2, "para", "결과는 다음과 같습니다."),
             Unit(3, "para", "검증 손실은 1.41이다.")]
    fs = lint(units, "report")
    assert [f.unit_id for f in fs if f.code == "R01"] == [2]


def test_report_polite_doc_is_not_mixed():
    """「~ㅂ니다」 일관 문서를 혼용으로 오탐하던 버그(README 자기 검사에서 발견) · 「아니다」를 존댓말로 보던 버그."""
    units = [Unit(1, "para", "문장을 고칩니다."), Unit(2, "para", "형식을 다룹니다."), Unit(3, "para", "원문은 남습니다.")]
    assert not [f for f in lint(units, "report") if f.code == "R01"]
    plain = [Unit(1, "para", "이 파일은 최종 결과가 아니다."), Unit(2, "para", "반영은 스킬이 한다.")]
    assert not [f for f in lint(plain, "report") if f.code == "R01"]


def test_report_translationese_and_modifiers():
    fs = lint([Unit(1, "para", "데이터 검증에 있어서 다양한 데이터를 효과적으로 활용하는 것이 중요하다.")], "report")
    got = {f.code for f in fs}
    assert {"R02", "R03"} <= got


def test_report_heading_sentence():
    assert {f.code for f in lint([Unit(1, "heading", "3. 학습 결과는 좋지 않았다")], "report")} == {"R07"}


def test_report_allows_plain_prose():
    assert not [f for f in lint([Unit(1, "para", "공공문서 1,908건을 정제해 검증 손실을 1.44에서 1.41로 낮췄다.")], "report") if f.level == "error"]


def test_contrast_repeat_doc_level():
    units = [Unit(i, "para", t) for i, t in enumerate(
        ["문제는 모델이 아니라 데이터다.", "핵심은 양이 아니라 질이다.", "기준은 손실이 아니라 지표다."], 1)]
    assert len([f for f in lint(units, "report") if f.code == "R05"]) == 3


def test_contrast_repeat_in_one_paragraph():
    u = [Unit(1, "para", "문제는 모델이 아니라 데이터였다. 핵심은 양이 아니라 질이다. 기준은 손실이 아니라 지표다.")]
    assert any(f.code == "R05" for f in lint(u, "report"))


def test_brief_marker_jump():
    units = [Unit(1, "bullet", "개요", {"marker": "□"}), Unit(2, "bullet", "세부 내용", {"marker": "-"})]
    assert any(f.code == "B01" for f in lint(units, "brief"))


def test_every_rule_documented():
    for r in RULES:
        assert r.title and r.why and r.hint and r.bad and r.good, r.code
    assert len({r.code for r in RULES}) == len(RULES)


def test_rules_catch_their_own_bad_example():
    """각 규칙의 「나쁜 예」는 그 규칙에 걸려야 한다(문서와 코드가 어긋나지 않게)."""
    for r in RULES:
        if r.bad.startswith("(") or r.doc_check:
            continue
        kind = (r.kinds or ["body"])[0]
        reg = r.registers[0]
        got = {f.code for f in lint([Unit(1, kind, r.bad)], reg)}
        assert r.code in got, (r.code, r.bad, got)
