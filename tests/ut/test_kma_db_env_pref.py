"""``KMA_DB_*`` environment variables take precedence over legacy ``DB_*``."""

import os

from kma.db import build_db_url


def test_build_db_url_prefers_kma_over_legacy() -> None:
    prev = {k: os.environ.get(k) for k in ("KMA_DB_HOST", "DB_HOST", "KMA_DB_PORT", "DB_PORT")}
    os.environ["KMA_DB_HOST"] = "kma.example"
    os.environ["DB_HOST"] = "legacy.example"
    os.environ["KMA_DB_PORT"] = "6543"
    os.environ["DB_PORT"] = "5432"
    try:
        url = build_db_url()
        assert "kma.example" in url
        assert "6543" in url
        assert "legacy.example" not in url
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_build_db_url_falls_back_to_legacy_when_kma_unset() -> None:
    prev_kma = os.environ.pop("KMA_DB_HOST", None)
    prev_db = os.environ.get("DB_HOST")
    os.environ["DB_HOST"] = "only.legacy"
    try:
        assert "only.legacy" in build_db_url()
    finally:
        if prev_db is None:
            os.environ.pop("DB_HOST", None)
        else:
            os.environ["DB_HOST"] = prev_db
        if prev_kma is not None:
            os.environ["KMA_DB_HOST"] = prev_kma
