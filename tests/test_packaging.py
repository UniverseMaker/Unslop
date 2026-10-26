# -*- coding: utf-8 -*-
"""스킬 폴더가 그 자체로 완결돼 있는지 — 복사·업로드만으로 동작해야 한다."""
import io
import os
import shutil
import subprocess
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILL = os.path.join(ROOT, "skills", "unslop")


def test_skill_folder_runs_without_install(tmp_path):
    """스킬 폴더만 복사한 뒤 PYTHONPATH 없이 실행기가 돈다."""
    dst = tmp_path / "unslop"
    shutil.copytree(SKILL, dst, ignore=shutil.ignore_patterns("__pycache__"))
    doc = tmp_path / "s.md"
    doc.write_text("- 선행연구 190편을 받아서 열고 본문을 읽었다\n", encoding="utf-8")
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["PYTHONIOENCODING"] = "utf-8"
    p = subprocess.run([sys.executable, str(dst / "scripts" / "run_unslop.py"), "lint", str(doc), "--register", "slide"],
                       capture_output=True, cwd=str(tmp_path), env=env)
    out = p.stdout.decode("utf-8")
    assert p.returncode == 1 and "S01" in out, out + p.stderr.decode("utf-8", "replace")


def test_skill_md_frontmatter():
    text = io.open(os.path.join(SKILL, "SKILL.md"), encoding="utf-8").read()
    assert text.startswith("---\nname: unslop\ndescription: ")
    desc = text.split("description: ", 1)[1].split("\n", 1)[0]
    assert len(desc) <= 1024


def test_build_zip_layout(tmp_path):
    sys.path.insert(0, os.path.join(ROOT, "scripts"))
    import build_skill
    path = build_skill.build(str(tmp_path))
    names = zipfile.ZipFile(path).namelist()
    assert "unslop/SKILL.md" in names
    assert "unslop/scripts/run_unslop.py" in names
    assert "unslop/scripts/unslop/cli.py" in names
    assert "unslop/references/RULES.md" in names
    assert "unslop/LICENSE.txt" in names
    assert not [n for n in names if "__pycache__" in n or n.endswith(".pyc")]
    assert all(n.startswith("unslop/") for n in names)


def test_rules_doc_in_sync():
    from unslop.rules import catalog_markdown
    doc = io.open(os.path.join(SKILL, "references", "RULES.md"), encoding="utf-8", newline="").read()
    assert doc == catalog_markdown(), "규칙 문서가 코드와 다릅니다 — python scripts/build_skill.py 전에 RULES.md 를 다시 만드세요"


def test_plugin_manifest_points_to_existing_parts():
    import json
    pj = json.load(io.open(os.path.join(ROOT, ".claude-plugin", "plugin.json"), encoding="utf-8"))
    assert pj["name"] == "unslop"
    assert os.path.exists(os.path.join(ROOT, "skills", "unslop", "SKILL.md"))
    assert os.path.exists(os.path.join(ROOT, "agents", "unslop-rewriter.md"))
