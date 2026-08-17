from __future__ import annotations

from app.services.chat.prompts.v1 import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
)


def test_prompt_version_is_defined():
    assert PROMPT_VERSION == "v1"


def test_prompt_version_is_not_empty():
    assert PROMPT_VERSION


def test_system_prompt_is_not_empty():
    assert SYSTEM_PROMPT.strip()


def test_prompt_version_is_attached_to_expected_prompt():
    assert PROMPT_VERSION.startswith("v")