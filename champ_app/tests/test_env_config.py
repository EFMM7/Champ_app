import importlib
import os

from src import tokens


def test_load_environment_reads_dotenv_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("JWT_SECRET_KEY=from-dotenv\nENV=production\n", encoding="utf-8")

    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    monkeypatch.chdir(tmp_path)

    from src import config

    config.load_environment(env_file)

    assert os.environ["JWT_SECRET_KEY"] == "from-dotenv"
    assert os.environ["ENV"] == "production"


def test_production_environment_requires_secret(monkeypatch):
    monkeypatch.setenv("ENV", "production")
    monkeypatch.delenv("JWT_SECRET_KEY", raising=False)
    importlib.reload(tokens)

    try:
        tokens.get_secret_key()
    except RuntimeError as exc:
        assert "JWT_SECRET_KEY" in str(exc)
    else:
        raise AssertionError("Expected RuntimeError for missing production secret")
