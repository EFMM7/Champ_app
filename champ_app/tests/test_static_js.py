"""Vérifie que le JavaScript servi par l'API est syntaxiquement valide.

Une simple faute de frappe dans un <script> inline invalide le bloc entier :
la page s'affiche mais plus rien ne fonctionne. Ces tests s'appuient sur
`node --check` et sont ignorés si Node.js n'est pas installé.
"""

import re
import shutil
import subprocess
from pathlib import Path

import pytest

STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="Node.js non installé")


def _node_check(code: str, tmp_path: Path) -> subprocess.CompletedProcess:
    target = tmp_path / "script.js"
    target.write_text(code, encoding="utf-8")
    return subprocess.run([NODE, "--check", str(target)], capture_output=True, text=True)


def _inline_scripts(html: str) -> list[str]:
    return re.findall(r"<script>(.*?)</script>", html, re.S)


@pytest.mark.parametrize("html_path", sorted(STATIC_DIR.glob("*.html")), ids=lambda p: p.name)
def test_inline_scripts_of_static_pages_are_valid_javascript(html_path, tmp_path):
    scripts = _inline_scripts(html_path.read_text(encoding="utf-8"))
    assert scripts, f"aucun <script> inline trouvé dans {html_path.name}"
    for index, code in enumerate(scripts):
        result = _node_check(code, tmp_path)
        assert result.returncode == 0, f"{html_path.name} (bloc {index}) : {result.stderr.strip()}"


def test_service_worker_is_valid_javascript(tmp_path):
    code = (STATIC_DIR / "service-worker.js").read_text(encoding="utf-8")
    result = _node_check(code, tmp_path)
    assert result.returncode == 0, result.stderr.strip()
