import pytest

from src import api


@pytest.fixture(autouse=True)
def _disable_rate_limiting_by_default():
    """Le limiter slowapi utilise un stockage en mémoire partagé par processus.
    On le désactive par défaut pour que les nombreux appels à /auth/register
    et /auth/login effectués par la suite de tests ne se bloquent pas les uns
    les autres. Le test dédié au rate limiting le réactive explicitement."""
    api.limiter.enabled = False
    yield
    api.limiter.enabled = False
    api.limiter.reset()

@pytest.fixture(autouse=True)
def _explicit_development_environment(monkeypatch):
    """Le secret JWT de développement n'est accepté que si ENV=development est
    défini explicitement. Les tests qui vérifient un autre comportement
    (production, absence de ENV) surchargent cette valeur."""
    monkeypatch.setenv("ENV", "development")
