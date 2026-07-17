"""Configuration d'un logging structuré (JSON) pour l'application.

Approche volontairement sans dépendance externe : un simple `Formatter` JSON
au-dessus du module `logging` de la bibliothèque standard. Chaque ligne de
log est un objet JSON exploitable par n'importe quel agrégateur (CloudWatch,
Loki, ELK, Datadog...) sans configuration supplémentaire côté application.

Niveau configurable via la variable d'environnement LOG_LEVEL (INFO par défaut).
"""

import json
import logging
import os
import sys
from datetime import datetime, timezone

# Attributs standards d'un LogRecord — on ne les recopie pas tels quels dans
# le JSON, ils sont déjà couverts par timestamp/level/logger/message, ou non
# pertinents pour un log applicatif.
_RESERVED_LOGRECORD_ATTRS = {
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
}


class JsonFormatter(logging.Formatter):
    """Formate chaque enregistrement de log en une ligne JSON unique."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Champs additionnels passés via logger.info("...", extra={...})
        for key, value in record.__dict__.items():
            if key in _RESERVED_LOGRECORD_ATTRS or key.startswith("_"):
                continue
            payload[key] = value

        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)

        return json.dumps(payload, ensure_ascii=False, default=str)


def get_log_level() -> int:
    raw = os.environ.get("LOG_LEVEL", "INFO").upper()
    return getattr(logging, raw, logging.INFO)


def setup_logging() -> None:
    """Configure un handler stdout unique, formaté en JSON, pour toute l'application.

    Idempotent : peut être appelé plusieurs fois (rechargement uvicorn, imports
    multiples en tests...) sans dupliquer les handlers ni les lignes de log.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(get_log_level())

    already_configured = any(getattr(h, "_champ_app_json", False) for h in root_logger.handlers)
    if already_configured:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    handler._champ_app_json = True
    root_logger.handlers = [handler]

    # uvicorn a ses propres loggers ; on les fait passer par le même handler
    # plutôt que de dupliquer la configuration.
    for logger_name in ("uvicorn", "uvicorn.error", "uvicorn.access"):
        uv_logger = logging.getLogger(logger_name)
        uv_logger.handlers = []
        uv_logger.propagate = True


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)