# 기여 안내

## 규칙 추가

1. `skills/unslop/scripts/unslop/rules.py`에 `@rule(...)`로 규칙을 하나 더한다.
   - `code`: 레지스터 머리글자 + 번호 (공통 C, 보고서 R, 슬라이드 S, 개조식 보고서 B)
   - `level`: `error`는 게이트를 막는다. 오탐이 걱정되면 `warn`으로 시작한다
   - `bad` / `good`: 실제로 본 문장을 쓴다. 시험이 `bad`가 이 규칙에 걸리는지 자동으로 확인한다
   - 단위 하나로 판단할 수 있으면 `unit_check`, 문서 전체를 봐야 하면 `doc=True`
2. 오탐 사례를 `tests/test_rules.py`의 좋은 예 목록에 넣는다.
   - 이 저장소는 「필요」를 존댓말 「~요」로, 「데이터」를 「~다」 종결로 오탐한 적이 있다
   - 한 번 생긴 오탐은 시험으로 고정한다
3. `python -m unslop rules --markdown > skills/unslop/references/RULES.md`로 문서를 다시 만든다. 시험이 코드와 문서가 같은지 확인한다.

## 정규식 주의

- 파이썬 `\w`는 한글도 잡는다. 경로·파일명처럼 ASCII만 와야 하는 자리에는 `[A-Za-z0-9_]`를 쓴다.
- 경로 뒤에 붙은 조사(「papers에」)를 경로의 일부로 읽지 않게 한글 앞에서 끊는다.

## 저장소 구조

코드는 `skills/unslop/scripts/unslop/` 에 있다. 스킬 폴더 하나만 복사하거나 zip 으로 올려도 동작하게 하기 위해서다. 사본을 따로 두지 않는다.

- Claude 앱 업로드용 zip: `python scripts/build_skill.py` 를 실행하면 `dist/unslop-<버전>.zip` 이 생긴다
- 시험이 스킬 폴더의 자립 실행, zip 구조, SKILL.md 앞머리를 확인한다

## 시험

```
pip install -e ".[dev]"
python -m pytest -q
```

LLM을 부르는 시험은 두지 않는다. 흐름 시험은 정해진 답을 돌려주는 가짜 provider로 한다.
