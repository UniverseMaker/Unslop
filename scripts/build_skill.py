# -*- coding: utf-8 -*-
"""Claude 앱(claude.ai·데스크톱) 스킬 업로드용 zip 을 만든다.

    python scripts/build_skill.py            # → dist/unslop-<버전>.zip

zip 최상단은 `unslop/` 폴더 하나이고, 그 안에 SKILL.md·scripts/·references/·LICENSE.txt 가 있다.
Claude 앱의 「스킬 업로드」는 이 모양(SKILL.md 가 든 폴더 하나)을 기대한다.
캐시(__pycache__·*.pyc)는 넣지 않는다.
"""
import io
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "unslop")


def version() -> str:
    init = io.open(os.path.join(SKILL, "scripts", "unslop", "__init__.py"), encoding="utf-8").read()
    return re.search(r'__version__ = "([^"]+)"', init).group(1)


def check_skill_md(path: str) -> None:
    text = io.open(path, encoding="utf-8").read()
    m = re.match(r"---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise SystemExit("SKILL.md 앞머리(--- … ---)가 없습니다")
    meta = dict(re.findall(r"^(\w+):\s*(.+)$", m.group(1), re.M))
    if not re.fullmatch(r"[a-z0-9-]{1,64}", meta.get("name", "")):
        raise SystemExit("SKILL.md name 은 영문 소문자·숫자·하이픈 64자 이내여야 합니다: %r" % meta.get("name"))
    if not 1 <= len(meta.get("description", "")) <= 1024:
        raise SystemExit("SKILL.md description 은 1~1024자여야 합니다 (현재 %d자)" % len(meta.get("description", "")))


def build(out_dir: str = None) -> str:
    check_skill_md(os.path.join(SKILL, "SKILL.md"))
    out_dir = out_dir or os.path.join(ROOT, "dist")
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "unslop-%s.zip" % version())
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for base, dirs, files in os.walk(SKILL):
            # 캐시와 pip 설치 흔적(*.egg-info — pip install -e 가 스킬 폴더 안에 만든다)은 넣지 않는다
            dirs[:] = sorted(d for d in dirs if d != "__pycache__" and not d.endswith(".egg-info"))
            for f in sorted(files):
                if f.endswith((".pyc", ".pyo")):
                    continue
                full = os.path.join(base, f)
                arc = os.path.join("unslop", os.path.relpath(full, SKILL)).replace(os.sep, "/")
                z.write(full, arc)
        z.write(os.path.join(ROOT, "LICENSE"), "unslop/LICENSE.txt")
    return out


if __name__ == "__main__":
    path = build(sys.argv[1] if len(sys.argv) > 1 else None)
    with zipfile.ZipFile(path) as z:
        names = z.namelist()
    print("%s (%d개 파일)" % (path, len(names)))
