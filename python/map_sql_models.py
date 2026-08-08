"""Typed map SQL seed models + draft application (JFTSE wiki schema)."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any, Mapping


def sql_literal(value: int | str | None) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, int):
        return str(value)
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def parse_optional_int(raw: str) -> int | None:
    token = raw.strip()
    if token.upper() == "NULL":
        return None
    return int(token)


def parse_optional_str(raw: str) -> str | None:
    token = raw.strip()
    if token.upper() == "NULL":
        return None
    if token.startswith("'") and token.endswith("'"):
        return token[1:-1]
    return token


@dataclass(frozen=True, slots=True)
class SMapRow:
    id: int
    map: int
    name: str
    is_boss_stage: bool
    boss_play_time: int | None
    breath_time: int
    description: str | None
    play_time: int | None
    trigger_boss_time: int | None
    use_breath_time: bool

    def as_catalog_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "map": self.map,
            "name": self.name,
            "isBossStage": self.is_boss_stage,
            "bossPlayTime": self.boss_play_time,
            "breathTime": self.breath_time,
            "description": self.description,
            "playTime": self.play_time,
            "triggerBossTime": self.trigger_boss_time,
            "useBreathTime": self.use_breath_time,
        }


@dataclass(frozen=True, slots=True)
class ScenarioRow:
    id: int
    description: str
    game_mode: str
    is_default: bool
    component_of_id: int | None
    status_id: int

    def as_catalog_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.description,
            "description": self.description,
            "gameMode": self.game_mode,
            "isDefault": self.is_default,
            "componentOfId": self.component_of_id,
            "statusId": self.status_id,
        }


@dataclass(frozen=True, slots=True)
class Map2ScenarioRow:
    scenario_id: int
    map_id: int


@dataclass(frozen=True, slots=True)
class Guardian2MapRow:
    id: int
    side: str
    boss_guardian_id: int | None
    guardian_id: int | None
    map_id: int
    scenario_id: int
    status_id: int

    def as_catalog_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "side": self.side,
            "bossGuardianId": self.boss_guardian_id,
            "guardianId": self.guardian_id,
            "mapId": self.map_id,
            "scenarioId": self.scenario_id,
            "statusId": self.status_id,
        }


def apply_map_draft(row: SMapRow, draft: Mapping[str, Any] | None) -> SMapRow:
    if not draft:
        return row
    name = draft.get("name")
    is_boss = draft.get("isBossStage", draft.get("is_boss_stage"))
    updates: dict[str, Any] = {}
    if isinstance(name, str) and name.strip():
        updates["name"] = name.strip()
    if isinstance(is_boss, bool):
        updates["is_boss_stage"] = is_boss
    for key, attr in (
        ("bossPlayTime", "boss_play_time"),
        ("playTime", "play_time"),
        ("triggerBossTime", "trigger_boss_time"),
        ("breathTime", "breath_time"),
    ):
        if key not in draft:
            continue
        raw = draft[key]
        if raw is None:
            updates[attr] = None
        elif isinstance(raw, (int, float)) and not isinstance(raw, bool):
            updates[attr] = int(raw)
    if "useBreathTime" in draft and isinstance(draft["useBreathTime"], bool):
        updates["use_breath_time"] = draft["useBreathTime"]
    if "description" in draft:
        desc = draft["description"]
        updates["description"] = None if desc is None else str(desc)
    return replace(row, **updates) if updates else row
