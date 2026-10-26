"""문서를 만드는 스크립트(예: python-pptx 생성기)에 윤문 결과를 되돌려 넣는다.

PPT 를 코드로 만들면 PPT 파일이 아니라 스크립트가 정본이다. PPT 만 고치면 다음 생성 때 되돌아간다.
그래서 스크립트 안의 문자열을 바꾼다.

규칙
- 긴 문구부터 바꾼다(짧은 문구가 긴 문구 안에 들어 있을 때 먼저 바꿔 버리는 사고 방지).
- 스크립트에 한 번만 나오거나, 모든 등장이 따옴표로 감싼 완전한 문자열일 때만 바꾼다.
- 원형으로 못 찾고 문구에 \\ 가 있으면 이스케이프된 형태(\\\\)로 다시 찾는다.
- 원문은 없고 바뀐 문구만 있으면 「이미 반영됨」으로 센다.
"""
from __future__ import annotations

import io
from typing import Dict, List, Tuple


def apply(source: str, pairs: List[Tuple[int, str, str]], out: str = None) -> Dict:
    src = io.open(source, encoding="utf-8").read()
    changed, already, missing = [], [], []
    for n, x, y in sorted(pairs, key=lambda p: -len(p[1])):
        if x == y:
            continue
        if "\\" in x and src.count(x) == 0:
            x, y = x.replace("\\", "\\\\"), y.replace("\\", "\\\\")
        total, quoted = src.count(x), src.count('"%s"' % x) + src.count("'%s'" % x)
        if total == 1:
            src = src.replace(x, y)
        elif total > 1 and quoted == total:
            src = src.replace('"%s"' % x, '"%s"' % y).replace("'%s'" % x, "'%s'" % y)
        elif total == 0 and src.count(y) >= 1:
            already.append(n)
            continue
        else:
            missing.append({"id": n, "text": x, "count": total})
            continue
        changed.append(n)
    io.open(out or source, "w", encoding="utf-8").write(src)
    return {"written": out or source, "changed": sorted(changed), "already": sorted(already), "missing": missing}
