# -*- coding: utf-8 -*-
"""unslop 실행기 — 설치 없이 스킬 폴더에서 바로 실행한다.

    python <스킬 폴더>/scripts/run_unslop.py lint 보고서.md
    python <스킬 폴더>/scripts/run_unslop.py run 연구노트.pptx
    python <스킬 폴더>/scripts/run_unslop.py apply <작업 폴더> <작업 폴더>/final.txt

pip install 로 설치했다면 `unslop ...` 또는 `python -m unslop ...` 와 같다.
PPTX·DOCX 를 다루려면 python-pptx·python-docx 가 필요하다
(Claude 앱의 코드 실행 환경에는 이미 들어 있다).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from unslop.cli import main  # noqa: E402

if __name__ == "__main__":
    raise SystemExit(main())
