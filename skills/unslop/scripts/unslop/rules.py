"""문체 규칙 — 레지스터(문서 종류)별 검사기.

레지스터
  report  연구보고서·기술보고서 본문. 서술형 「~다」체 산문
  slide   발표·연구노트 슬라이드. 개조식(명사형 종결)
  brief   공문·내부 개조식 보고서. □ ○ - · 계층 기호, 「~함/~임」·명사 종결

규칙 하나 = 코드·수준(error/warn)·적용 레지스터·적용 단위 종류·설명·고치는 법·나쁜 예/좋은 예·검사 함수.
error 는 게이트를 막는다. warn 은 보고만 한다.
모든 검사는 정규식·통계로만 한다(LLM 호출 0회) — 같은 입력이면 항상 같은 결과가 나온다.
"""
from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .units import Unit

REGISTERS = ("report", "slide", "brief")


@dataclass
class Finding:
    code: str
    level: str
    unit_id: int
    kind: str
    msg: str
    hint: str
    text: str = ""
    span: Optional[Tuple[int, int]] = None

    def to_dict(self) -> Dict:
        return dict(code=self.code, level=self.level, unit=self.unit_id, kind=self.kind,
                    msg=self.msg, hint=self.hint, text=self.text, span=self.span)


@dataclass
class Rule:
    code: str
    level: str
    registers: Sequence[str]
    title: str
    why: str
    hint: str
    bad: str
    good: str
    kinds: Optional[Sequence[str]] = None          # None = 모든 종류
    unit_check: Optional[Callable[[Unit], Optional[Tuple[int, int]]]] = None
    doc_check: Optional[Callable[[List[Unit]], List[Tuple[int, Optional[Tuple[int, int]]]]]] = None
    fixable: bool = False

    def applies(self, register: str, kind: str) -> bool:
        return register in self.registers and (self.kinds is None or kind in self.kinds)


RULES: List[Rule] = []


def rule(**kw):
    def deco(fn):
        if kw.pop("doc", False):
            kw["doc_check"] = fn
        else:
            kw["unit_check"] = fn
        RULES.append(Rule(**kw))
        return fn
    return deco


def _search(pat: re.Pattern, text: str):
    m = pat.search(text)
    return (m.start(), m.end()) if m else None


def _strip_tail(t: str) -> str:
    return re.sub(r"[\s\)\]」』\"'”’]+$", "", t)


ALL = REGISTERS
SHORT = ("title", "subtitle", "label", "body", "cell", "heading", "bullet")

# ── 공통 ─────────────────────────────────────────────────────────────────
SPACED_PARTICLE = re.compile(
    r"(?<=[A-Za-z0-9%\)\]`」』])\s(?:는|은|이|가|을|를|에서|에게|에|의|으로|로|와|과|도|만|까지|부터)(?=[\s,.)」·:]|$)")   # 코드 표기(`…`)·낫표 뒤도 포함


@rule(code="C01", level="error", registers=ALL, fixable=True,
      title="영문·숫자 뒤 조사 띄어 쓰기",
      why="한글 맞춤법상 조사는 앞말에 붙여 쓴다. 「v4 는」처럼 띄우면 기계가 만든 글처럼 보인다.",
      hint="조사를 붙여 쓴다", bad="v4 는 JSON 을 내지 못했다", good="v4는 JSON을 내지 못했다")
def _c01(u: Unit):
    return _search(SPACED_PARTICLE, u.text)


DASH_JOIN = re.compile(r"\S\s+[—–]\s+\S")


@rule(code="C02", level="error", registers=ALL,
      kinds=("para", "bullet", "body", "subtitle", "label", "cell", "quote"),
      title="줄표(—)로 문장 잇기",
      why="「X — Y」로 앞뒤를 잇는 것은 AI 글의 대표 습관이다. 결론을 꼬리에 매달거나 교훈을 덧붙이는 데 쓰인다.",
      hint="조사·연결어미·쌍점(:)·쉼표로 풀거나 두 문장으로 나눈다",
      bad="v4는 실패했다 — 원인은 데이터 구성이다", good="v4가 실패한 원인은 데이터 구성이다")
def _c02(u: Unit):
    return _search(DASH_JOIN, u.text)


EMOJI = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F000-\U0001F2FF]")


@rule(code="C03", level="error", registers=ALL,
      title="이모지", why="업무 문서·보고서에 이모지는 쓰지 않는다.",
      hint="지운다. 강조가 필요하면 표·굵게로", bad="✅ 학습 완료 🎉", good="학습 완료")
def _c03(u: Unit):
    return _search(EMOJI, u.text)


SLANG = re.compile(r"(병신|존나|개빡|ㅋㅋ|ㅎㅎ|진짜|너무너무|완전 |대박|짱|싹 다|이따구|헐|ㅠㅠ)")


@rule(code="C04", level="error", registers=ALL,
      title="비속어·감정어·구어", why="업무 문서는 감정 표현과 구어를 쓰지 않는다. 회의 발화를 옮길 때 특히 섞여 들어온다.",
      hint="업무 용어로 바꾸거나 지운다", bad="데이터가 진짜 너무 별로였다", good="데이터 품질 미흡")
def _c04(u: Unit):
    return _search(SLANG, u.text)


IMPER = re.compile(r"(해라|하라|짜라|해봐|해 봐|하지 ?말고|하지 ?마라?|만들어봐|돌려버려|해줘|해 줘)")
QUOTE = re.compile(r"[「“\"]([^」”\"]{6,})[」”\"]")


@rule(code="C05", level="error", registers=ALL,
      title="명령형 발화를 그대로 인용", why="「…계획부터 다시 짜라」처럼 지시를 그대로 옮기면 문서가 아니라 대화록이 된다.",
      hint="지시의 요지를 업무 용어로 요약한다(예: 「선행연구 조사 및 재계획 지시」)",
      bad="사용자 지시: 「계획부터 다시 짜라」", good="선행연구 조사 및 재계획 지시(10.13)")
def _c05(u: Unit):
    for m in QUOTE.finditer(u.text):
        if IMPER.search(m.group(1)):
            return (m.start(), m.end())
    m = IMPER.search(u.text)
    return (m.start(), m.end()) if m else None


CHATBOT = re.compile(r"(물론입니다|도움이 되셨|도움이 되길|궁금한 점이 있으시면|다음은 .{1,20}입니다[:：]|요청하신 .{1,15}(?:입니다|드립니다)|제가 .{1,10}(?:드리|해 드리))")


@rule(code="C06", level="error", registers=ALL,
      title="챗봇 말투 잔재", why="AI 답변을 그대로 붙여 넣으면 머리말·맺음말이 남는다.",
      hint="지운다", bad="물론입니다! 다음은 요약입니다:", good="(삭제)")
def _c06(u: Unit):
    return _search(CHATBOT, u.text)


MD_BOLD = re.compile(r"\*\*[^*]+\*\*")


@rule(code="C07", level="warn", registers=("report",), kinds=("para", "bullet"),
      title="굵게 남발", why="문단마다 굵은 글씨가 여러 개면 무엇이 중요한지 오히려 흐려진다.",
      hint="한 문단에 1개 이하로", bad="**데이터**는 **반드시** **검증**해야 한다", good="데이터는 반드시 검증해야 한다")
def _c07(u: Unit):
    ms = list(MD_BOLD.finditer(u.text))
    return (ms[0].start(), ms[-1].end()) if len(ms) >= 3 else None


EN_PAREN = re.compile(r"[가-힣]+\s?\([A-Za-z][A-Za-z \-]{2,}\)")


@rule(code="C08", level="warn", registers=ALL,
      title="한글(영어) 병기 과다", why="한 문장에 영어 병기가 3개 이상이면 번역투로 읽힌다. 처음 한 번만 병기한다.",
      hint="첫 등장에만 병기하고 이후에는 한쪽만 쓴다",
      bad="지속 학습(continual learning)과 망각(forgetting), 재생(replay)", good="지속 학습(continual learning)과 망각, 재생")
def _c08(u: Unit):
    ms = list(EN_PAREN.finditer(u.text))
    return (ms[0].start(), ms[-1].end()) if len(ms) >= 3 else None


ARROW = re.compile(r"\s*(?:→|⇒|➜|➔|⟶|->|=>)\s*")


@rule(code="C09", level="error", registers=ALL, fixable=True,
      title="화살표(→) 사용", why="문장 안의 화살표는 AI 요약체의 표지다. 업무 문서에서는 꺾쇠(>)로 단계·변화를 표시한다.",
      hint="「>」로 바꾼다. 양방향(↔)은 대비이므로 「vs」 (자동 수정)", bad="실패 → 원인 실측 → 재설계", good="실패 > 원인 실측 > 재설계")
def _c09(u: Unit):
    m = re.search(r"→|⇒|➜|➔|⟶|↔|⇄|⟷|(?<![<=!-])->|(?<![<=!])=>", u.text)
    return (m.start(), m.end()) if m else None


INFORMAL_QTY = re.compile(r"(\d[\d,.]*)\s?(?:번|개|건|명|회)\s?(?:넘게|넘는|넘은|이상으로|가량)")


@rule(code="C10", level="error", registers=ALL, fixable=True,
      title="수량 구어 표현", why="「100번 넘게」는 말투다. 보고서는 「100회 이상」처럼 단위와 범위를 정확히 쓴다.",
      hint="「N회 이상」「N건 이상」으로 쓴다 (「번 넘게」는 자동 수정)", bad="100번 넘게 나온 줄", good="100회 이상 중복 줄")
def _c10(u: Unit):
    return _search(INFORMAL_QTY, u.text)


# 제목·라벨에 쓰는 구어·홍보체 표현 → 보고서 용어
CASUAL_HEAD = {
    "한눈에": "요약", "한 눈에": "요약", "이번 달": "월간·○월", "이번달": "월간·○월", "이번 주": "주간",
    "살펴보기": "검토", "알아보기": "개요", "들여다보기": "분석", "짚어보기": "검토", "정리해 보면": "요약",
    "핵심 한 줄": "요지", "의 모든 것": "개요", "총정리": "종합", "꿀팁": "유의 사항", "체크포인트": "점검 항목",
    "무엇이 달라졌나": "변경 사항", "왜 중요한가": "필요성", "어떻게 할까": "추진 방안", "한 걸음 더": "추가 과제",
}
CASUAL_RE = re.compile("|".join(re.escape(k) for k in sorted(CASUAL_HEAD, key=len, reverse=True)) + r"|[가-힣]+(?:은|는) 왜\??$|\?$")


@rule(code="S07", level="error", registers=("slide", "brief", "report"), kinds=("title", "subtitle", "label", "heading"),
      title="구어·홍보체 제목", why="「이번 달 한눈에」「~살펴보기」「~는 왜?」는 블로그·AI 요약체다. 보고서 제목은 「월간 요약」「현황」「추진 방안」처럼 쓴다.",
      hint="보고서 용어로 바꾼다(한눈에>요약, 이번 달>월간·10월, 살펴보기>검토, 의문문>명사구)",
      bad="이번 달 한눈에", good="월간 요약")
def _s07(u: Unit):
    # 파일명·경로 안의 낱말(「00_한눈에_정리.md」)은 제목 표현이 아니다 — 보호 토큰을 지우고 본다(실제 오탐)
    from .protect import TOKEN
    t = TOKEN.sub(lambda m: " " * len(m.group(0)) if re.search(r"[./\\_]", m.group(0)) else m.group(0), u.text.strip())
    return _search(CASUAL_RE, t)


# ── 연구보고서(report) ────────────────────────────────────────────────────
_YO = re.compile(r"(세요|어요|아요|여요|해요|에요|예요|래요|네요|군요|거든요|는데요|죠)[.!?]?\s*$")
_NIDA = re.compile(r"([가-힣])니다[.!?]?\s*$")


def is_polite(s: str) -> bool:
    """합쇼체(~ㅂ니다/~습니다)·해요체 종결인가.

    「니다」 앞 글자에 받침 ㅂ 이 있을 때만 합쇼체로 본다 — 「습·합·칩·룹·갑」은 맞고 「아니다」는 아니다.
    (「합니다」만 보면 「고칩니다」를 놓치고, 「니다」만 보면 「아니다」를 오탐한다 — 둘 다 실제로 겪었다)
    """
    s = s.rstrip()
    if _YO.search(s):
        return True
    m = _NIDA.search(s)
    return bool(m) and (ord(m.group(1)) - 0xAC00) % 28 == 17


class _Polite:
    """기존 POLITE.search 호출부와 같은 모양으로 쓰려는 얇은 감싸개."""

    @staticmethod
    def search(s: str):
        return is_polite(s) or None


POLITE = _Polite()
PLAIN = re.compile(r"(다|함|음|임)[.!?]?\s*$")


@rule(code="R01", level="error", registers=("report",), kinds=("para", "bullet", "quote"), doc=True,
      title="「합니다」체와 「한다」체 혼용", why="한 보고서 안에서 종결 어미가 섞이면 여러 사람이 쓴 글처럼 보인다.",
      hint="문서의 주된 문체(대개 「한다」체)로 통일한다", bad="데이터를 정제했다. 결과는 다음과 같습니다.",
      good="데이터를 정제했다. 결과는 다음과 같다.")
def _r01(units: List[Unit]):
    sents = [(u, s) for u in units if u.kind in ("para", "bullet", "quote")
             for s in re.split(r"(?<=[.!?])\s+", u.text) if s.strip()]
    pol = [u.id for u, s in sents if POLITE.search(s)]
    pla = [u.id for u, s in sents if PLAIN.search(s) and not POLITE.search(s)]
    if pol and pla:
        minority = pol if len(pol) <= len(pla) else pla
        return [(i, None) for i in sorted(set(minority))]
    return []


EMPTY_MOD = re.compile(r"(다양한|효과적인|효과적으로|혁신적인|획기적인|체계적인|체계적으로|성공적으로|원활한|원활하게|극대화|시너지|고도화|선도적|차별화된|최적의|탁월한|폭넓은|중요한 역할)")


@rule(code="R02", level="warn", registers=("report", "brief"), kinds=("para", "bullet", "body"),
      title="공허한 수식어 밀집", why="「다양한·효과적인·혁신적인」이 한 문장에 2개 이상 몰리면 내용 없이 꾸미는 글로 읽힌다.",
      hint="수식어 대신 수치·대상·조건을 쓴다", bad="다양한 데이터를 효과적으로 활용해 혁신적인 성과를 냈다",
      good="공공문서 1,908건을 정제해 검증 손실을 1.44에서 1.41로 낮췄다")
def _r02(u: Unit):
    ms = list(EMPTY_MOD.finditer(u.text))
    return (ms[0].start(), ms[-1].end()) if len(ms) >= 2 else None


TRANSLATIONESE = re.compile(r"(되어진|되어지는|되어져|에 있어서|에 있어|을 가지고 있|를 가지고 있|에 의해 .{0,8}되|하는 것이 (?:중요|필요)하다|하는 것이 가능하다|함에 있어)")


@rule(code="R03", level="warn", registers=("report", "brief"), kinds=("para", "bullet", "body", "cell"),
      title="번역투", why="이중 피동(되어지다), 「~에 있어서」, 「~을 가지고 있다」, 「~하는 것이 중요하다」는 영어 직역 습관이다.",
      hint="능동·직접 서술로 바꾼다(「되어진다」>「된다」, 「~하는 것이 중요하다」>「~해야 한다」)",
      bad="데이터 검증에 있어서 정제 과정이 수행되어진다", good="데이터를 검증할 때 먼저 정제한다")
def _r03(u: Unit):
    return _search(TRANSLATIONESE, u.text)


PIVOT = re.compile(r"^(결론적으로|요약하면|종합하면|정리하면|요컨대|이처럼|이와 같이|즉,)\s")


@rule(code="R04", level="warn", registers=("report",), kinds=("para",), doc=True,
      title="결론 피벗으로 문단 닫기", why="문단마다 「결론적으로/이처럼」으로 시작해 앞 내용을 되풀이하면 AI 글의 틀이 드러난다.",
      hint="되풀이 문단을 지우거나, 새 정보(수치·결정)로 시작한다", bad="이처럼 데이터 품질은 매우 중요하다.",
      good="(삭제하거나) 산불 데이터의 41.9%가 반복 문장이었다.")
def _r04(units: List[Unit]):
    hits = [(u.id, _search(PIVOT, u.text)) for u in units if u.kind == "para" and PIVOT.search(u.text)]
    return hits if len(hits) >= 2 else []


CONTRAST = re.compile(r"(?:[가-힣]+)(?:이|가) 아니라 ")


@rule(code="R05", level="warn", registers=("report", "slide", "brief"), doc=True,
      title="「A가 아니라 B」 대구 반복", why="대조 구문을 문서 곳곳에서 반복하면 단정과 반전으로 끌고 가는 AI 글의 리듬이 된다.",
      hint="핵심 1~2곳만 남기고 긍정 단언으로 바꾼다", bad="문제는 모델이 아니라 데이터다. 핵심은 양이 아니라 질이다.",
      good="문제는 데이터 구성이다. 양보다 질이 핵심이다.")
def _r05(units: List[Unit]):
    # 단위 수가 아니라 등장 횟수로 센다 — 한 문단에 세 번 몰아 쓴 경우도 잡는다
    hits = [(u.id, _search(CONTRAST, u.text)) for u in units if CONTRAST.search(u.text)]
    total = sum(len(CONTRAST.findall(u.text)) for u in units)
    return hits if total >= 3 else []


@rule(code="R06", level="warn", registers=("report",), kinds=("para", "bullet"),
      title="지나치게 긴 문장", why="한 문장이 120자를 넘으면 읽는 사람이 주어와 서술어를 놓친다.",
      hint="두 문장으로 나눈다", bad="(120자 넘는 문장)", good="(두 문장)")
def _r06(u: Unit):
    for m in re.finditer(r"[^.!?]+[.!?]?", u.text):
        if len(m.group(0).strip()) > 120:
            return (m.start(), m.end())
    return None


@rule(code="R07", level="warn", registers=("report",), kinds=("heading",),
      title="절 제목을 문장으로", why="보고서 절 제목은 명사구가 기본이다. 「~했다」로 끝나는 제목은 기사 제목처럼 읽힌다.",
      hint="명사구로 바꾼다", bad="## 3. 학습 결과는 좋지 않았다", good="## 3. 학습 결과와 한계")
def _r07(u: Unit):
    t = _strip_tail(u.text)
    return (len(t) - 1, len(t)) if DA_END.search(t) else None


# ── 슬라이드(slide) · 개조식 보고서(brief) ─────────────────────────────────
# 「~다」로 끝나면 문장으로 본다. 앞 글자 목록으로 판정하면 「고친다·쓴다·아니다」를 놓친다(실측) — 대신 「다」로 끝나는 명사·조사만 예외로 둔다
DA_NOUNS = ("데이터", "다수", "최다", "과다", "바다", "판다", "소다", "레이다", "보다", "마다", "다다")


class _DaEnd:
    @staticmethod
    def search(t: str):
        return (t.endswith("다") and not any(t.endswith(w) for w in DA_NOUNS)) or None


DA_END = _DaEnd()
YO_END = POLITE   # 합쇼체·해요체 판정은 is_polite 하나로 통일
SLIDE_KINDS = ("title", "subtitle", "label", "body", "cell", "bullet", "heading")


@rule(code="S01", level="error", registers=("slide", "brief"), kinds=SLIDE_KINDS,
      title="문장 종결(「~다」)", why="슬라이드와 개조식 보고서는 명사형으로 끝낸다. 「~읽었다」「~시작했다」는 발표 자료를 산문으로 만든다.",
      hint="명사구로 끝낸다(「완료」「확인」「필요」「원인」「현황」「결과」, 또는 「~함/~임」)",
      bad="선행연구 190편을 받아서 열고 본문을 읽었다", good="선행연구 190편 조사 및 연구 완료")
def _s01(u: Unit):
    t = _strip_tail(u.text).rstrip(".")
    if any(t.endswith(w) for w in DA_NOUNS):
        return None
    return (len(t) - 1, len(t)) if DA_END.search(t) else None


@rule(code="S02", level="error", registers=("slide", "brief"), kinds=SLIDE_KINDS,
      title="경어·구어 종결", why="「~습니다/~요」는 발표 대본 말투다. 슬라이드 문구에는 쓰지 않는다.",
      hint="명사형으로 바꾼다", bad="이렇게 하면 됩니다", good="적용 방법")
def _s02(u: Unit):
    t = _strip_tail(u.text).rstrip(".")
    return (len(t) - 2, len(t)) if YO_END.search(t) else None


@rule(code="S03", level="error", registers=("slide", "brief"), kinds=SLIDE_KINDS,
      title="한 줄에 두 문장", why="「A했다. B했다」를 한 칸에 넣으면 읽히지 않는다.",
      hint="명사구 두 개로 합치거나(「A, B」) 줄을 나눈다", bad="학습은 살렸다. 기준을 바꿨다", good="학습 유지, 판정 기준 교체")
def _s03(u: Unit):
    return _search(re.compile(r"[가-힣]다\.\s+\S"), u.text)


@rule(code="S04", level="error", registers=("slide", "brief"), kinds=SLIDE_KINDS, fixable=True,
      title="줄 끝 마침표", why="개조식 문구는 마침표로 끝내지 않는다.",
      hint="지운다", bad="폴더 통째 복사(과제 규칙).", good="폴더 통째 복사(과제 규칙)")
def _s04(u: Unit):
    t = u.text.rstrip()
    if re.search(r"(\.\.\.|…|\d\.)$", t):
        return None
    return (len(t) - 1, len(t)) if re.search(r"[가-힣A-Za-z0-9\)」]\.$", t) else None


@rule(code="S05", level="warn", registers=("slide",), kinds=("title", "subtitle"),
      title="제목·부제 60자 초과", why="슬라이드 제목은 한눈에 읽혀야 한다.",
      hint="핵심 결과만 남기고 줄인다", bad="(60자 넘는 제목)", good="(30자 안팎 명사구)")
def _s05(u: Unit):
    return (60, len(u.text)) if len(u.text) > 60 else None


_ITEM = r"[가-힣A-Za-z0-9]+(?: [가-힣A-Za-z0-9]+)?"   # 「중복 제거」처럼 띄어 쓴 두 단어 항목까지
MIDDOT_CHAIN = re.compile(_ITEM + r"(?:\s?·\s?" + _ITEM + r"){4,}")


@rule(code="S06", level="warn", registers=("slide", "brief", "report"), kinds=("para", "body", "subtitle", "bullet"),
      title="가운뎃점으로 다섯 개 넘게 나열", why="「A·B·C·D·E」 전보체는 조사를 빼먹은 압축 문장이다. 표 칸이 아닌 서술에서는 읽기 어렵다.",
      hint="쉼표와 「및」로 묶거나 표로 옮긴다", bad="정제·중복 제거·가림·층화·분할 완료", good="정제, 중복 제거, 개인정보 가림 및 층화 분할 완료")
def _s06(u: Unit):
    return _search(MIDDOT_CHAIN, u.text)


# ── 개조식 보고서(brief) 전용 ─────────────────────────────────────────────
MARKERS = ["□", "○", "-", "·"]


@rule(code="B01", level="warn", registers=("brief",), kinds=("bullet", "para"), doc=True,
      title="계층 기호 순서 건너뜀", why="공문 개조식은 □ > ○ > - > · 순으로 내려간다. 단계를 건너뛰면 구조가 흐려진다.",
      hint="한 단계씩 내려간다", bad="□ 개요\n- 세부", good="□ 개요\n○ 항목\n- 세부")
def _b01(units: List[Unit]):
    out, prev = [], None
    for u in units:
        m = u.loc.get("marker")
        if m not in MARKERS:
            continue
        lv = MARKERS.index(m)
        if prev is not None and lv > prev + 1:
            out.append((u.id, None))
        prev = lv
    return out


def rules_for(register: str) -> List[Rule]:
    return [r for r in RULES if register in r.registers]


def catalog_markdown() -> str:
    """skills/unslop/references/RULES.md 본문을 만든다(규칙 정의가 정본)."""
    lines = ["# 규칙 목록", "", "`unslop rules --markdown` 으로 자동 생성한다. 손으로 고치지 않는다.", ""]
    for reg, name in (("report", "연구보고서"), ("slide", "슬라이드"), ("brief", "개조식 보고서")):
        lines += ["## %s (`%s`)" % (name, reg), "", "| 코드 | 수준 | 규칙 | 나쁜 예 | 좋은 예 |", "|---|---|---|---|---|"]
        for r in rules_for(reg):
            lines.append("| %s | %s | %s | %s | %s |" % (r.code, r.level, r.title, r.bad.replace("\n", " / "), r.good.replace("\n", " / ")))
        lines.append("")
    lines += ["## 규칙별 설명", ""]
    for r in RULES:
        lines += ["### %s %s" % (r.code, r.title), "", "- 수준: %s · 레지스터: %s%s" % (
            r.level, ", ".join(r.registers), (" · 단위 종류: " + ", ".join(r.kinds)) if r.kinds else ""),
            "- 이유: " + r.why, "- 고치는 법: " + r.hint + (" (자동 수정 가능)" if r.fixable else ""), ""]
    return "\n".join(lines)
