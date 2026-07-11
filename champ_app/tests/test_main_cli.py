import importlib
import sys
from pathlib import Path

from src import main


def test_main_rejects_malformed_bbox_argument(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path)
    monkeypatch.setattr(sys, "argv", ["main.py", "--bbox", "1.0,2.0"])

    exit_code = main.main()

    assert exit_code == 2
