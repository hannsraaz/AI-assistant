from __future__ import annotations

import logging
import pytest

from config import AppConfig, DesktopConfig, TTSConfig, STTConfig, LLMConfig
from desktop_controller import DesktopController
from intent_router import IntentRouter


@pytest.fixture
def app_config() -> AppConfig:
    cfg = AppConfig()
    cfg.speak_responses = False
    return cfg


@pytest.fixture
def desktop_controller(app_config: AppConfig) -> DesktopController:
    return DesktopController(app_config.desktop)


@pytest.fixture
def intent_router(app_config: AppConfig, desktop_controller: DesktopController) -> IntentRouter:
    return IntentRouter(config=app_config, desktop=desktop_controller)


@pytest.fixture
def test_logger() -> logging.Logger:
    logger = logging.getLogger("test_friday")
    logger.setLevel(logging.DEBUG)
    return logger
