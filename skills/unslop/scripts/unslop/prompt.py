"""윤문 요청문(프롬프트) 만들기와 응답 해석.

시스템 문은 레지스터마다 고정이라 캐시가 잘 맞는다(요청마다 바뀌는 내용은 사용자 문에만 둔다).
"""
from __future__ import annotations

from typing import Dict, List

from . import protect
from .rules import Finding, rules_for
from .units import Unit, parse_lines

STYLE = {
    "report": """# 문서 종류: 연구보고서·기술보고서 본문
- 서술형 「~다」체 산문으로 쓴다. 문서 안에서 「~습니다」체와 섞지 않는다.
- 사실·수치·결정을 먼저 쓰고, 꾸미는 말(다양한·효과적인·혁신적인)과 되풀이 요약(「이처럼」「결론적으로」)은 뺀다.
- 번역투(되어지다, ~에 있어서, ~을 가지고 있다, ~하는 것이 중요하다)를 직접 서술로 바꾼다.
- 줄표(—)로 문장을 잇지 않는다. 「A가 아니라 B」 대구를 반복하지 않는다.
- 절 제목은 명사구로 둔다.""",
    "slide": """# 문서 종류: 발표·연구노트 슬라이드 (개조식)
- 모든 칸(제목·부제·라벨·본문·표)을 명사형으로 끝낸다. 「~했다/~이다/~습니다」 문장으로 끝내지 않는다.
- 공공기관 보고서식 개조식을 따른다: 「및」「완료」「확인」「필요」「원인」「현황」「결과」「방안」「예정」.
  예) 「선행연구 190편을 받아서 열고 본문을 읽었다」 > 「선행연구 190편 조사 및 연구 완료」
  예) 「검증 손실은 좋아졌고 판정 능력은 나빠졌다」 > 「검증 손실 개선, 판정 능력 하락」
- 사람이 한 말(지시·회의 발화)을 그대로 옮기지 않고 업무 용어로 요약한다.
  예) 「사용자 지시: 「…계획부터 다시 짜라」」 > 「선행연구 조사 및 재계획」
- 현상을 풀어 설명하지 말고 「무엇을 + 수치 + 업무 용어(발견·집계·확인·도출·착수·완료·필요)」로 쓴다.
  예) 「산불 데이터의 42%가 같은 틀 문장」 > 「산불 데이터 중복 건수 42% 이상 발견」
  예) 「숫자만 다른 줄은 같은 틀로 간주, 학습데이터 전체에서 100번 넘게 나온 줄 집계」 > 「100회 이상 중복데이터 집계」
  예) 「같은 틀 문장」 > 「중복 문장」, 「외운 값」 > 「암기 결과」
- 제목에 구어·홍보체를 쓰지 않는다. 예) 「이번 달 한눈에」 > 「월간 요약」, 「~살펴보기」 > 「~검토」
- 화살표(→)를 쓰지 않는다. 단계·변화는 꺾쇠(>)로 표시한다. 예) 「1.44 → 1.41」 > 「1.44 > 1.41」
- 한 칸에 두 문장을 넣지 않는다. 줄 끝에 마침표를 찍지 않는다. 줄표로 잇지 않는다.
- 칸 크기가 정해져 있으므로 원문보다 길게 쓰지 않는다(최대 1.15배). 짧을수록 좋다.""",
    "brief": """# 문서 종류: 공문·내부 개조식 보고서 (□ ○ - · 계층)
- 항목은 명사 또는 「~함/~임/~음」으로 끝낸다. 「~다」 문장을 쓰지 않는다.
- 계층 기호(□ ○ - ·)는 단위 밖에 있으니 건드리지 않는다.
- 한 항목에 한 내용만 쓴다. 줄 끝 마침표를 찍지 않는다.
- 원문보다 길게 쓰지 않는다(최대 1.15배).""",
}

COMMON = """# 공통 규칙
- 의미를 바꾸지 않는다. 원문에 없는 사실·성과·수식어를 넣지 않는다. 실패·하락·결함을 약하게 바꾸지 않는다.
- ⟦ ⟧ 로 감싼 조각(수치·버전·경로·코드·영문 용어)은 글자 하나 바꾸지 말고 그대로 쓴다. ⟦ ⟧ 기호는 출력에 남겨도 되고 지워도 된다.
- 영문·숫자 뒤 조사는 붙여 쓴다(「v4 는」 > 「v4는」).
- 화살표(→)를 쓰지 않는다. 꺾쇠(>)를 쓴다. 「100번 넘게」 같은 구어 수량은 「100회 이상」으로 쓴다.
- 이모지, 비속어·감정어, 챗봇 말투(「물론입니다」「도움이 되셨길」)를 쓰지 않는다.
- 이미 좋은 줄은 그대로 둔다.

# 출력 형식 (엄수)
- 입력과 같은 「[번호|종류] 본문」 줄만 출력한다. 설명·머리말·코드 블록을 붙이지 않는다.
- 번호·종류·줄 수·순서를 바꾸지 않는다. 줄을 합치거나 나누지 않는다."""


def system_prompt(register: str) -> str:
    rules = "\n".join("- %s %s: %s (예: 「%s」 > 「%s」)" % (r.code, r.title, r.hint, r.bad, r.good)
                      for r in rules_for(register) if r.level == "error")
    return "\n\n".join([
        "당신은 한국어 업무 문서(연구보고서·발표자료·개조식 보고서) 윤문 담당이다. "
        "AI가 쓴 티가 나는 문장을 해당 문서 종류의 관행에 맞는 자연스러운 한국어로 고친다.",
        STYLE[register], "# 반드시 없애야 할 위반 (검사기가 코드로 확인한다)\n" + rules, COMMON])


def user_prompt(units: List[Unit], findings: List[Finding], feedback: Dict[int, List[str]] = None) -> str:
    by_unit: Dict[int, List[str]] = {}
    for f in findings:
        by_unit.setdefault(f.unit_id, []).append("%s %s" % (f.code, f.msg))
    lines = []
    for u in units:
        lines.append("[%d|%s] %s" % (u.id, u.kind, protect.mark(u.text)))
    notes = []
    for uid in sorted(by_unit):
        notes.append("[%d] 검사기 지적: %s" % (uid, ", ".join(sorted(set(by_unit[uid])))))
    if feedback:
        for uid in sorted(feedback):
            notes.append("[%d] 지난 시도가 게이트에서 막힘: %s" % (uid, "; ".join(feedback[uid])))
    parts = ["다음 줄들을 윤문하라.", "\n".join(lines)]
    if notes:
        parts += ["# 줄별 지적 사항", "\n".join(notes)]
    return "\n\n".join(parts)


def parse_response(text: str) -> Dict[int, tuple]:
    out = {}
    for uid, (kind, body) in parse_lines(text).items():
        out[uid] = (kind, protect.unmark(body).strip())
    return out


def batches(units: List[Unit], max_chars: int = 5000) -> List[List[Unit]]:
    """요청 하나가 너무 길지 않게 나눈다(문서 순서 유지)."""
    out, cur, n = [], [], 0
    for u in units:
        if cur and n + len(u.text) > max_chars:
            out.append(cur)
            cur, n = [], 0
        cur.append(u)
        n += len(u.text) + 12
    if cur:
        out.append(cur)
    return out
