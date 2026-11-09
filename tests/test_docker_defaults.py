"""Tests verifying Docker image and compose production defaults (Phase 9E)."""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_image_defaults_to_production():
    """Dockerfile final stage sets ENV APP_ENV=production."""
    dockerfile_content = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    stage = dockerfile_content[dockerfile_content.rfind("\nFROM "):]
    assert re.search(r"^ENV APP_ENV=production$", stage, re.MULTILINE) is not None


def test_compose_pins_production():
    """docker-compose.yml pins APP_ENV=production and does not interpolate ${APP_ENV."""
    compose_content = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    assert "- APP_ENV=production" in compose_content
    assert "${APP_ENV" not in compose_content
