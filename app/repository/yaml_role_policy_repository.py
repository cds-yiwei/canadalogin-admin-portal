from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from loguru import logger


class YamlRolePolicyRepository:
    def __init__(self, policy_path: Path):
        self._policy_path = policy_path

    @lru_cache(maxsize=1)
    def _load_policy(self) -> dict[str, list[str]]:
        try:
            with self._policy_path.open("r", encoding="utf-8") as handle:
                data = yaml.safe_load(handle) or {}
                return {key: value or [] for key, value in data.items()}
        except FileNotFoundError:
            logger.warning("Role policy file not found at {}", self._policy_path)
            return {}
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to load role policy: {}", exc)
            return {}

    def load_policy(self) -> dict[str, list[str]]:
        return self._load_policy()
