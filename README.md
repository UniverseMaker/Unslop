# unslop

**Strip the AI slop from Korean reports, slides, and briefs.**
**한국어 보고서·슬라이드·개조식 문서에서 AI 티를 걷어 냅니다.**

unslop is a rule linter, a gate, and an LLM rewrite step for Korean business documents (.md, .pptx, .docx).
Style rules are checked by code, sentences are rewritten by an LLM, and the **gate** decides in code whether each rewrite is applied.
A rewrite that changes a number, path, or English term, or that still breaks a rule, is never applied.

연구보고서, 발표 PPT, 공문식 개조식 보고서의 한국어 문장을 업무 문서답게 고치는 도구입니다.
문체 규칙은 코드 검사기가 찾고, 문장은 LLM이 고치고, 반영 여부는 **게이트**가 코드로 정합니다.
수치·경로·영문 용어가 바뀌거나 규칙 위반이 남은 문장은 반영하지 않습니다.

## Why / 왜 만들었나

A general prose rewriter was run over a research-note deck, and sentences like these were still left.

일반 산문 윤문 도구로 연구노트 PPT를 고쳤는데도 이런 문장이 남았습니다.

| After a prose rewriter / 윤문 도구를 거친 결과 | What was actually needed / 실제로 필요했던 문장 |
|---|---|
| 선행연구 190편을 받아서 열고 본문을 읽었다 | 선행연구 190편 조사 및 연구 완료 |
| 사용자 지시: 「…계획부터 다시 짜라」 | 선행연구 조사 및 재계획 지시 |
| 검증 손실은 좋아졌고 판정 능력은 나빠졌다 | 검증 손실 개선, 판정 능력 하락 |
| v4 는 JSON 을 내지 못했다 (보고서 본문) | v4는 JSON을 내지 못했다 |

A prose rewriter turns a 「~했다」 sentence into a smoother 「~했다」 sentence. It does not turn it into the noun-ending bullet style (개조식) that slides need.
It also lets clear mistakes slide, such as a verbatim quote of a spoken instruction or a particle split off by a space, unless they dominate the text.
Business documents have a correct form for each document type, so the form can be enforced by rules. That is why checking is done in code, not left to the LLM's judgment.

산문 윤문 도구는 「~했다」 문장을 더 자연스러운 「~했다」 문장으로 고칩니다. 슬라이드에 필요한 개조식으로는 바꾸지 않습니다.
대화 중 지시를 그대로 옮긴 인용이나 띄어 쓴 조사처럼 확실히 틀린 것도 글 전체의 큰 문제가 아니면 그냥 넘어갑니다.
업무 문서는 문서 종류마다 정답 형식이 있어서 규칙으로 강제할 수 있습니다. 그래서 검사를 LLM 판단에 맡기지 않고 코드로 했습니다.

## What it does / 하는 일

```
document / 문서 (.md .pptx .docx)
 > extract units      단위 추출 (줄·표 칸·PPT 글자 조각·문단, 종류 표시)
 > safe auto-fix      자동 수정 (띄어 쓴 조사·줄 끝 마침표처럼 의미가 바뀔 수 없는 것만)
 > rule lint          규칙 검사 (레지스터별 오류·경고)
 > protect tokens     보호 토큰 표시 (수치·버전·경로·코드·영문 용어를 ⟦ ⟧로)
 > LLM rewrite        LLM 윤문 (지적 사항을 줄마다 붙여서)
 > gate               게이트 (줄 구성·보호 토큰·길이·규칙 위반 0·보존 단위)
 > retry failures     실패한 줄만 사유를 붙여 재시도, 끝까지 실패하면 원문 유지
 > apply              반영 (원래 서식 유지, 또는 PPT 생성 스크립트에 반영)
 > report             보고서 (전후 점수, 규칙별 건수, 바뀐 예, 원문 유지 사유)
```

## Registers / 문서 종류(레지스터)

| Register | Document / 문서 | Key rules / 핵심 규칙 |
|---|---|---|
| `report` | Research and technical reports / 연구·기술보고서 본문 | One sentence ending (「~다」), less translationese, empty modifiers, and recap filler; headings as noun phrases / 「~다」체 통일, 번역투·공허한 수식어·되풀이 요약 줄이기, 절 제목은 명사구 |
| `slide` | Presentation and research-note slides / 발표·연구노트 슬라이드 | Noun-ending bullets in every box, no quoted speech, one sentence per box, never longer than the original / 모든 칸 개조식, 발화 인용 금지, 한 칸 한 문장, 원문보다 길게 쓰지 않기 |
| `brief` | Official and internal briefs (□ ○ - ·) / 공문·내부 개조식 보고서 | 「~함/~임」 or noun endings, marker hierarchy order / 「~함/~임」·명사 종결, 계층 기호 순서 |

If no register is given, `.pptx` uses `slide`, documents with many □○ markers use `brief`, and everything else uses `report`.
The full rule list is in [skills/unslop/references/RULES.md](skills/unslop/references/RULES.md), generated from the code.

지정하지 않으면 `.pptx`는 `slide`, □○ 기호가 많은 문서는 `brief`, 나머지는 `report`로 정합니다.
규칙 전체는 [skills/unslop/references/RULES.md](skills/unslop/references/RULES.md)에 있습니다. 이 문서는 코드에서 자동으로 만듭니다.

## Install / 설치

There are four ways to install. The code lives inside the skill folder (`skills/unslop/`), so each one works from that single folder.

설치 방법은 네 가지입니다. 코드가 스킬 폴더(`skills/unslop/`) 안에 들어 있으므로 어느 방법이든 스킬 폴더 하나로 동작합니다.

**1. Claude Code plugin (recommended) / Claude Code 플러그인 (권장)**

```
/plugin marketplace add UniverseMaker/Unslop
/plugin install unslop@unslop
```

This installs the `unslop` skill and the `unslop-rewriter` agent. From a local clone you can also load it with `claude --plugin-dir <repo path>`.

스킬 `unslop`와 에이전트 `unslop-rewriter`가 함께 설치됩니다. 저장소를 내려받았다면 `claude --plugin-dir <저장소 경로>`로 바로 불러올 수도 있습니다.

**2. Copy the skill folder / Claude Code 스킬 폴더 복사**

Copy `skills/unslop/` under `~/.claude/skills/`. The install scripts also copy the agent.

`skills/unslop/`를 `~/.claude/skills/` 아래에 복사합니다. 설치 스크립트를 쓰면 에이전트까지 함께 복사됩니다.

```
powershell -ExecutionPolicy Bypass -File scripts/install_claude.ps1     # Windows
bash scripts/install_claude.sh                                          # macOS·Linux
```

**3. Upload to the Claude app (claude.ai, desktop) / Claude 앱 스킬 업로드**

```
python scripts/build_skill.py          # creates / 생성: dist/unslop-<version>.zip
```

Upload the zip under Settings > Capabilities > Skills in the Claude app. The zip has `unslop/SKILL.md` at the top. The zip built by GitHub Actions is also available as the `skill-zip` artifact.

만들어진 zip을 Claude 앱의 설정 > 기능 > 스킬에서 업로드합니다. zip 최상단에 `unslop/SKILL.md`가 있는 구조입니다. GitHub Actions가 만든 zip은 `skill-zip` 산출물에서도 받을 수 있습니다.

**4. Command-line tool (pip) / 명령줄 도구 (pip)**

```
pip install "unslop[pptx,docx]"        # with PPTX and DOCX support / PPTX·DOCX 처리 포함
pip install "unslop[all]"              # + Anthropic API
```

To use it from the repository, run `pip install -e ".[dev]"`. Without installing, run `python skills/unslop/scripts/run_unslop.py <command>`.

저장소에서 바로 쓰려면 `pip install -e ".[dev]"`를 실행합니다. 설치 없이 `python skills/unslop/scripts/run_unslop.py <명령>`으로도 실행됩니다.

## Usage / 사용법

Lint only / 검사만 하기:

```
unslop lint 보고서.md
unslop lint 연구노트.pptx --keep "재난 유형:"      # skip text that must stay verbatim / 인용 원문처럼 바꾸면 안 되는 문구는 제외
```

Fix only what cannot change meaning / 의미가 바뀔 수 없는 것만 자동으로 고치기:

```
unslop fix 보고서.md                              # output / 결과: 보고서.unslop.md
```

Rewrite with an LLM / LLM으로 윤문하기:

```
unslop run 연구노트.pptx --provider anthropic       # Anthropic API (claude-opus-5-5)
unslop run 보고서.md --provider claude-cli          # headless logged-in Claude Code / 로그인된 Claude Code를 헤드리스로
unslop run 보고서.md --provider cmd --cmd "my-llm"  # any command that reads the request on stdin / 표준입력으로 요청을 받는 아무 명령
```

Rewrite by an agent or by hand / 에이전트나 사람이 직접 윤문하기:

```
unslop run 보고서.md                       # default provider none: only writes request files / 기본값 none: 요청 파일만 만든다
# read 02_system_prompt.md and 02_user_prompt.md in the work folder, write final.txt as "[id|kind] text" lines
# 작업 폴더의 02_system_prompt.md · 02_user_prompt.md를 보고 「[번호|종류] 본문」 줄로 final.txt 작성
unslop apply <work folder / 작업 폴더> final.txt   # applies only gate-passing lines / 게이트 통과분만 반영
```

If your deck is generated by code, apply the rewrite to the generator script instead. Editing only the .pptx is undone on the next build.

PPT를 코드로 만든다면 PPT 대신 생성 스크립트에 반영합니다. PPT만 고치면 다음 생성 때 되돌아갑니다.

```
unslop run 연구노트.pptx --provider anthropic --source make_deck.py
```

The original file is never overwritten. Output defaults to `<name>.unslop.<ext>`, and each step is logged under `.unslop/<name>-<time>/`.

원본 파일은 덮어쓰지 않습니다. 기본 출력은 `<이름>.unslop.<확장자>`이고, 단계별 기록은 `.unslop/<이름>-<시각>/`에 남습니다.

## Gate / 게이트

| Check / 검사 | Condition / 내용 |
|---|---|
| G1 Structure / 구성 | Unit ids and kinds match the original / 번호·단위 종류가 원문과 같다 |
| G2 Protect / 보호 | Numbers, versions, paths, URLs, code, and English terms are unchanged in every unit / 단위마다 수치·버전·경로·URL·코드·영문 용어가 그대로다 |
| G3 Length / 길이 | slide and brief ≤ 1.15× the original; report 0.5–1.3× / slide·brief는 원문의 1.15배 이하, report는 0.5~1.3배 |
| G4 Rules / 규칙 | No error-level violations in the rewrite / 윤문본에 오류 수준 위반이 없다 |
| G5 Keep / 보존 | `--keep` units are unchanged to the letter / `--keep` 단위는 한 글자도 바뀌지 않았다 |

Only units that pass the gate are applied. Blocked units are listed with reasons in `report.md`.

게이트를 통과한 단위만 반영합니다. 막힌 단위는 사유와 함께 `report.md`에 남습니다.

## Example / 예제

[examples/](examples/) has before/after files and reports. Results for the slide example:

[examples/](examples/)에 전후 결과와 보고서가 있습니다. 슬라이드 예제의 결과는 다음과 같습니다.

| Before / 전 | After / 후 |
|---|---|
| 선행연구 190편을 받아서 열고 본문을 읽었다 | 선행연구 190편 조사 및 연구 완료 |
| 사용자 지시: 「임의로 전처리·학습하지 말고 … 다시 짜라」 | 임의 전처리·학습 중단, 선행연구 전수 조사 및 재계획 지시 |
| v4 는 실패했다 — 원인은 데이터 구성이다 | v4 실패, 원인은 데이터 구성 |
| 학습은 살렸다. nvidia-smi 기준으로 교체했다. | 학습 유지, nvidia-smi 기준으로 교체 |

Errors went from 11 to 0, and all 6 lines passed the gate.

오류 11건이 0건이 됐고, 6줄 모두 게이트를 통과했습니다.

## Repository layout / 저장소 구조

```
.claude-plugin/             plugin and marketplace manifests / 플러그인·마켓플레이스 매니페스트
skills/unslop/              skill folder, self-contained / 스킬 폴더 (이 폴더 하나로 완결)
  SKILL.md                  skill definition / 스킬 정의 (Claude가 읽는 절차)
  scripts/run_unslop.py     launcher, no install needed / 설치 없이 쓰는 실행기
  scripts/unslop/           linter, gate, rewrite pipeline / 검사기·게이트·윤문 흐름 코드
  references/RULES.md       rule list, generated / 규칙 목록 (코드에서 자동 생성)
agents/unslop-rewriter.md   Claude Code rewrite agent / Claude Code 윤문 에이전트
scripts/                    install scripts, zip builder / 설치 스크립트, 업로드용 zip 생성기
tests/                      tests / 시험 (스킬 자립 실행·zip 구조 포함)
examples/                   before/after examples / 전후 예제
```

## Development / 개발

```
pip install -e ".[dev]"
python -m pytest -q
python -m unslop rules --markdown > skills/unslop/references/RULES.md   # regenerate after rule changes / 규칙을 바꾸면 문서도 다시 만든다
python scripts/build_skill.py                                            # upload zip / 업로드용 zip
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a rule. Every rule needs a bad and a good example, and the tests check that each rule's bad example is actually caught by that rule.

규칙을 추가하는 방법은 [CONTRIBUTING.md](CONTRIBUTING.md)에 있습니다.
모든 규칙에는 나쁜 예와 좋은 예가 있어야 합니다. 시험은 각 규칙의 나쁜 예가 실제로 그 규칙에 걸리는지 자동으로 확인합니다.

## License / 라이선스

MIT. See [LICENSE](LICENSE). / [LICENSE](LICENSE)를 참고하세요.
