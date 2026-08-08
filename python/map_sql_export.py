"""JFTSE map SQL seed parse + pack emission (wiki schema-aligned).

Tables: S_Maps, M_Scenarios, Map_2_Scenarios, Guardian_2_Maps.
"""

from __future__ import annotations

import re
from typing import Final, Mapping

from map_sql_models import (
    Guardian2MapRow,
    Map2ScenarioRow,
    ScenarioRow,
    SMapRow,
    apply_map_draft,
    parse_optional_int,
    parse_optional_str,
    sql_literal,
)

# Re-export for bridge import path stability.
__all__ = [
    "SMapRow",
    "ScenarioRow",
    "Map2ScenarioRow",
    "Guardian2MapRow",
    "apply_map_draft",
    "parse_s_maps",
    "parse_map2scenarios",
    "parse_guardian2maps",
    "parse_scenarios",
    "build_map_pack_sql",
    "format_s_maps_insert",
    "format_m_scenarios_insert",
    "format_map2scenario_insert",
    "format_guardian2maps_insert",
    "sql_literal",
]

_S_MAPS_RE: Final = re.compile(
    r"VALUES\("
    r"(?P<id>\d+),\s*"
    r"[^,]*,\s*"
    r"[^,]*,\s*"
    r"(?P<bossPlayTime>NULL|\d+),\s*"
    r"(?P<breathTime>\d+),\s*"
    r"(?P<description>NULL|'[^']*'),\s*"
    r"(?P<isBossStage>[01]),\s*"
    r"(?P<map>\d+),\s*"
    r"'(?P<name>[^']*)',\s*"
    r"(?P<playTime>NULL|\d+),\s*"
    r"(?P<triggerBossTime>NULL|\d+),\s*"
    r"(?P<useBreathTime>[01])"
    r"\)",
    re.IGNORECASE,
)

_MAP2_RE: Final = re.compile(
    r"VALUES\((?P<scenario_id>\d+),\s*(?P<map_id>\d+)\)",
    re.IGNORECASE,
)

_G2M_RE: Final = re.compile(
    r"VALUES\((?P<id>\d+),[^,]*,[^,]*,\s*'(?P<side>[^']*)',\s*"
    r"(?P<boss>[^,]*),\s*(?P<guardian>[^,]*),\s*"
    r"(?P<map_id>\d+),\s*(?P<scenario_id>\d+),\s*(?P<status_id>\d+)\)",
    re.IGNORECASE,
)

_SCENARIO_RE: Final = re.compile(
    r"VALUES\("
    r"(?P<id>\d+),\s*"
    r"[^,]*,\s*"
    r"(?P<modified>NULL|'[^']*'),\s*"
    r"'(?P<description>[^']*)',\s*"
    r"'(?P<gameMode>[^']*)',\s*"
    r"(?P<isDefault>[01]),\s*"
    r"(?P<component>NULL|\d+),\s*"
    r"(?P<status_id>\d+)"
    r"\)",
    re.IGNORECASE,
)

_S_MAPS_UPSERT: Final = (
    "ON DUPLICATE KEY UPDATE "
    "bossPlayTime=VALUES(bossPlayTime), "
    "breathTime=VALUES(breathTime), "
    "description=VALUES(description), "
    "isBossStage=VALUES(isBossStage), "
    "`map`=VALUES(`map`), "
    "name=VALUES(name), "
    "playTime=VALUES(playTime), "
    "triggerBossTime=VALUES(triggerBossTime), "
    "useBreathTime=VALUES(useBreathTime), "
    "modified=VALUES(modified)"
)

_M_SCENARIOS_UPSERT: Final = (
    "ON DUPLICATE KEY UPDATE "
    "description=VALUES(description), "
    "gameMode=VALUES(gameMode), "
    "isDefault=VALUES(isDefault), "
    "component_of_id=VALUES(component_of_id), "
    "status_id=VALUES(status_id), "
    "modified=VALUES(modified)"
)

_G2M_UPSERT: Final = (
    "ON DUPLICATE KEY UPDATE "
    "side=VALUES(side), "
    "boss_guardian_id=VALUES(boss_guardian_id), "
    "guardian_id=VALUES(guardian_id), "
    "map_id=VALUES(map_id), "
    "scenario_id=VALUES(scenario_id), "
    "status_id=VALUES(status_id), "
    "modified=VALUES(modified)"
)


def parse_s_maps(text: str) -> list[SMapRow]:
    rows: list[SMapRow] = []
    for match in _S_MAPS_RE.finditer(text):
        rows.append(
            SMapRow(
                id=int(match.group("id")),
                map=int(match.group("map")),
                name=match.group("name"),
                is_boss_stage=match.group("isBossStage") == "1",
                boss_play_time=parse_optional_int(match.group("bossPlayTime")),
                breath_time=int(match.group("breathTime")),
                description=parse_optional_str(match.group("description")),
                play_time=parse_optional_int(match.group("playTime")),
                trigger_boss_time=parse_optional_int(match.group("triggerBossTime")),
                use_breath_time=match.group("useBreathTime") == "1",
            )
        )
    return rows


def parse_map2scenarios(text: str) -> list[Map2ScenarioRow]:
    return [
        Map2ScenarioRow(
            scenario_id=int(match.group("scenario_id")),
            map_id=int(match.group("map_id")),
        )
        for match in _MAP2_RE.finditer(text)
    ]


def parse_guardian2maps(text: str) -> list[Guardian2MapRow]:
    rows: list[Guardian2MapRow] = []
    for match in _G2M_RE.finditer(text):
        rows.append(
            Guardian2MapRow(
                id=int(match.group("id")),
                side=match.group("side"),
                boss_guardian_id=parse_optional_int(match.group("boss").strip()),
                guardian_id=parse_optional_int(match.group("guardian").strip()),
                map_id=int(match.group("map_id")),
                scenario_id=int(match.group("scenario_id")),
                status_id=int(match.group("status_id")),
            )
        )
    return rows


def parse_scenarios(text: str) -> list[ScenarioRow]:
    rows: list[ScenarioRow] = []
    for match in _SCENARIO_RE.finditer(text):
        rows.append(
            ScenarioRow(
                id=int(match.group("id")),
                description=match.group("description"),
                game_mode=match.group("gameMode"),
                is_default=match.group("isDefault") == "1",
                component_of_id=parse_optional_int(match.group("component")),
                status_id=int(match.group("status_id")),
            )
        )
    return rows


def format_s_maps_insert(row: SMapRow) -> str:
    return (
        "INSERT INTO S_Maps (id, created, modified, bossPlayTime, breathTime, "
        "description, isBossStage, `map`, name, playTime, triggerBossTime, useBreathTime) "
        f"VALUES({row.id}, NOW(6), NOW(6), "
        f"{sql_literal(row.boss_play_time)}, {row.breath_time}, "
        f"{sql_literal(row.description)}, {1 if row.is_boss_stage else 0}, "
        f"{row.map}, {sql_literal(row.name)}, {sql_literal(row.play_time)}, "
        f"{sql_literal(row.trigger_boss_time)}, {1 if row.use_breath_time else 0}) "
        f"{_S_MAPS_UPSERT};"
    )


def format_m_scenarios_insert(row: ScenarioRow) -> str:
    return (
        "INSERT INTO M_Scenarios (id, created, modified, description, gameMode, "
        "isDefault, component_of_id, status_id) VALUES("
        f"{row.id}, NOW(6), NOW(6), {sql_literal(row.description)}, "
        f"{sql_literal(row.game_mode)}, {1 if row.is_default else 0}, "
        f"{sql_literal(row.component_of_id)}, {row.status_id}) "
        f"{_M_SCENARIOS_UPSERT};"
    )


def format_map2scenario_insert(row: Map2ScenarioRow) -> str:
    return (
        "INSERT INTO Map_2_Scenarios (scenario_id, map_id) "
        f"VALUES({row.scenario_id}, {row.map_id}) "
        "ON DUPLICATE KEY UPDATE scenario_id=VALUES(scenario_id), map_id=VALUES(map_id);"
    )


def format_guardian2maps_insert(row: Guardian2MapRow) -> str:
    return (
        "INSERT INTO Guardian_2_Maps (id, created, modified, side, boss_guardian_id, "
        "guardian_id, map_id, scenario_id, status_id) VALUES("
        f"{row.id}, NOW(6), NOW(6), {sql_literal(row.side)}, "
        f"{sql_literal(row.boss_guardian_id)}, {sql_literal(row.guardian_id)}, "
        f"{row.map_id}, {row.scenario_id}, {row.status_id}) "
        f"{_G2M_UPSERT};"
    )


def build_map_pack_sql(
    *,
    maps: list[SMapRow],
    map2: list[Map2ScenarioRow],
    guardians: list[Guardian2MapRow],
    scenarios: list[ScenarioRow],
    stage_by_map_id: Mapping[str, str],
    include_scenarios: bool = True,
    include_guardians: bool = True,
    include_m_scenarios: bool = True,
) -> str:
    lines: list[str] = [
        "-- JFTSE Content Studio map pack",
        "-- Relational metadata export aligned with wiki Database Schema",
        "-- (client stage geometry remains stock-bound)",
        "",
        "-- === S_Maps ===",
    ]
    for row in maps:
        lines.append(format_s_maps_insert(row))
        stage = stage_by_map_id.get(str(row.id))
        if stage:
            lines.append(
                f"-- stage bind map_id={row.id} map_byte={row.map}: Stage/Info.res::{stage}"
            )

    if include_scenarios and include_m_scenarios and scenarios:
        lines.extend(["", "-- === M_Scenarios ==="])
        for row in scenarios:
            lines.append(format_m_scenarios_insert(row))

    if include_scenarios and map2:
        lines.extend(["", "-- === Map_2_Scenarios ==="])
        for row in map2:
            lines.append(format_map2scenario_insert(row))

    if include_guardians and guardians:
        lines.extend(["", "-- === Guardian_2_Maps ==="])
        for row in guardians:
            lines.append(format_guardian2maps_insert(row))

    return "\n".join(lines) + "\n"
