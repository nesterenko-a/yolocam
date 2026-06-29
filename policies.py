from __future__ import annotations

import time
from enum import Enum


class Action(Enum):
    ARCHIVE = "archive"
    ALERT = "alert"
    NONE = "none"
    ALERT_AND_ARCHIVE = "alert_and_archive"


class PolicyEngine:
    def __init__(
        self,
        policies: dict[str, Action],
        default_action: Action = Action.ARCHIVE,
        alert_cooldown: float = 60,
    ):
        self._policies = policies
        self._default = default_action
        self._alert_cooldown = alert_cooldown
        self._last_alert: dict[str, float] = {}

    def get_action(self, person_name: str) -> Action:
        return self._policies.get(person_name, self._default)

    def can_alert(self, person_name: str) -> bool:
        now = time.time()
        last = self._last_alert.get(person_name, 0)
        if now - last >= self._alert_cooldown:
            self._last_alert[person_name] = now
            return True
        return False
