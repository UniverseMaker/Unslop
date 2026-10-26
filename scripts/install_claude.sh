#!/usr/bin/env bash
# 플러그인 없이 Claude Code 에 스킬·에이전트를 복사 설치한다.
# 기존 설치본이 있으면 ~/.claude/backups/<시각>/ 으로 옮긴 뒤 복사한다(지우지 않는다).
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HOME2="${CLAUDE_HOME:-$HOME/.claude}"
TS="$(date +%Y%m%d-%H%M%S)"
install_one() {
  local src="$1" dst="$2"
  mkdir -p "$(dirname "$dst")"
  if [ -e "$dst" ]; then
    mkdir -p "$HOME2/backups/$TS"
    mv "$dst" "$HOME2/backups/$TS/"
    echo "backup: $HOME2/backups/$TS/$(basename "$dst")"
  fi
  cp -R "$src" "$dst"
  echo "installed: $dst"
}
install_one "$REPO/skills/unslop" "$HOME2/skills/unslop"
install_one "$REPO/agents/unslop-rewriter.md" "$HOME2/agents/unslop-rewriter.md"
echo "스킬 폴더에 코드가 들어 있어 추가 설치는 필요 없습니다(PPTX·DOCX 처리에는 python-pptx·python-docx 필요)."
