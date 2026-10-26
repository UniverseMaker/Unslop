# 플러그인 없이 Claude Code 에 스킬·에이전트를 복사 설치한다.
# 기존 설치본이 있으면 ~/.claude/backups/<시각>/ 으로 옮긴 뒤 복사한다(지우지 않는다).
$ErrorActionPreference = "Stop"
$repo = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$home2 = Join-Path $env:USERPROFILE ".claude"
$ts = Get-Date -Format "yyyyMMdd-HHmmss"
$items = @(
  @{ src = Join-Path $repo "skills\unslop"; dst = Join-Path $home2 "skills\unslop" },
  @{ src = Join-Path $repo "agents\unslop-rewriter.md"; dst = Join-Path $home2 "agents\unslop-rewriter.md" }
)
foreach ($t in $items) {
  New-Item -ItemType Directory -Force (Split-Path -Parent $t.dst) | Out-Null
  if (Test-Path $t.dst) {
    $bk = Join-Path $home2 ("backups\" + $ts + "\" + (Split-Path -Leaf $t.dst))
    New-Item -ItemType Directory -Force (Split-Path -Parent $bk) | Out-Null
    Move-Item $t.dst $bk
    "backup: $bk"
  }
  Copy-Item $t.src $t.dst -Recurse
  "installed: $($t.dst)"
}
"스킬 폴더에 코드가 들어 있어 추가 설치는 필요 없습니다(PPTX·DOCX 처리에는 python-pptx·python-docx 필요)."
