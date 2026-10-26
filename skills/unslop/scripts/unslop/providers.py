"""LLM 연결부. 요청문(system, user)을 받아 응답 문자열을 돌려준다.

  none        호출하지 않는다. 요청 파일만 만들고 멈춘다(에이전트·사람이 처리 → unslop apply)
  claude-cli  Claude Code CLI 를 헤드리스로 부른다: claude -p (로그인된 Claude Code 계정 사용)
  anthropic   Anthropic Python SDK (pip install 'unslop[anthropic]', ANTHROPIC_API_KEY 또는 ant auth login)
  cmd         임의 명령. 요청문을 표준입력으로 주고 표준출력을 응답으로 받는다(--cmd "...")
"""
from __future__ import annotations

import shlex
import shutil
import subprocess
from typing import Callable, Optional

DEFAULT_MODEL = "claude-opus-5-5"
# 서버 쪽 대체 모델(refusal 시 다른 모델로 재실행)을 지원하는 모델
_FALLBACK_MODELS = ("claude-opus-5-5", "claude-opus-5", "claude-fable-5-1", "claude-sonnet-5-5")


class ProviderError(RuntimeError):
    pass


Provider = Callable[[str, str], str]


def _join(system: str, user: str) -> str:
    return system + "\n\n---\n\n" + user


def claude_cli(model: Optional[str] = None, timeout: int = 900) -> Provider:
    exe = shutil.which("claude")
    if not exe:
        raise ProviderError("claude 명령을 찾지 못했습니다. Claude Code 를 설치하거나 --provider anthropic 을 쓰세요.")

    def call(system: str, user: str) -> str:
        args = [exe, "-p", "--output-format", "text"]
        if model:
            args += ["--model", model]
        p = subprocess.run(args, input=_join(system, user), capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout)
        if p.returncode != 0:
            raise ProviderError("claude -p 실패(%d): %s" % (p.returncode, (p.stderr or p.stdout)[:400]))
        return p.stdout
    return call


def command(cmd: str, timeout: int = 900) -> Provider:
    args = shlex.split(cmd, posix=False) if "\\" in cmd else shlex.split(cmd)

    def call(system: str, user: str) -> str:
        p = subprocess.run(args, input=_join(system, user), capture_output=True, text=True,
                           encoding="utf-8", timeout=timeout)
        if p.returncode != 0:
            raise ProviderError("명령 실패(%d): %s" % (p.returncode, (p.stderr or p.stdout)[:400]))
        return p.stdout
    return call


def anthropic_api(model: str = DEFAULT_MODEL, effort: str = "medium", fallback: bool = True) -> Provider:
    try:
        import anthropic
    except ImportError as e:
        raise ProviderError("anthropic 패키지가 필요합니다: pip install 'unslop[anthropic]'") from e
    client = anthropic.Anthropic()

    def call(system: str, user: str) -> str:
        kwargs = dict(
            model=model,
            max_tokens=16000,
            # 시스템 문(규칙)은 레지스터마다 고정이다 — 캐시해서 묶음 요청마다 다시 내지 않는다
            system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
            messages=[{"role": "user", "content": user}],
            output_config={"effort": effort},
        )
        try:
            if fallback and model in _FALLBACK_MODELS:
                # 안전 분류기가 요청을 거절하면 서버가 다른 모델로 다시 돌린다(기본 켬, --no-fallback 으로 끔)
                resp = client.beta.messages.create(betas=["server-side-fallback-2026-07-01"], fallbacks="default", **kwargs)
            else:
                resp = client.messages.create(**kwargs)
        except anthropic.AuthenticationError as e:
            raise ProviderError("인증 실패 — ANTHROPIC_API_KEY 또는 `ant auth login` 을 확인하세요") from e
        except anthropic.RateLimitError as e:
            raise ProviderError("요청 한도 초과 — 잠시 뒤 다시 실행하세요") from e
        except anthropic.APIStatusError as e:
            raise ProviderError("API 오류 %s: %s" % (e.status_code, e.message)) from e
        except anthropic.APIConnectionError as e:
            raise ProviderError("네트워크 오류: %s" % e) from e
        if resp.stop_reason == "refusal":
            raise ProviderError("모델이 요청을 거절했습니다(%s)" % getattr(resp.stop_details, "category", None))
        if resp.stop_reason == "max_tokens":
            raise ProviderError("응답이 max_tokens 에서 잘렸습니다 — --batch-chars 를 줄이세요")
        return "".join(b.text for b in resp.content if b.type == "text")
    return call


def make(name: Optional[str], model: Optional[str] = None, effort: str = "medium",
         fallback: bool = True, cmd: Optional[str] = None) -> Optional[Provider]:
    if name in (None, "none"):
        return None
    if name == "claude-cli":
        return claude_cli(model)
    if name == "anthropic":
        return anthropic_api(model or DEFAULT_MODEL, effort, fallback)
    if name == "cmd":
        if not cmd:
            raise ProviderError("--provider cmd 에는 --cmd \"명령\" 이 필요합니다")
        return command(cmd)
    raise ProviderError("모르는 provider: %s" % name)
