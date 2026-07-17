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