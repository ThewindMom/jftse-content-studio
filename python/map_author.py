"""Greenfield map SQL authoring (S_Maps + relations)."""

from __future__ import annotations

from typing import Any, Mapping

from map_sql_export import (
    Guardian2MapRow,
    Map2ScenarioRow,
    ScenarioRow,
    SMapRow,
    build_map_pack_sql,
    format_guardian2maps_insert,
    format_map2scenario_insert,
    format_s_maps_insert,
)
from map_sql_models import apply_map_draft


def next_map_ids(existing: list[SMapRow]) -> tuple[int, int]:
    """Return (next_db_id, next_map_byte)."""
    if not existing:
        return 1, 1
    next_id = max(row.id for row in existing) + 1
    next_byte = max(row.map for row in existing) + 1
    return next_id, next_byte


def create_map_row(
    existing: list[SMapRow],
    draft: Mapping[str, Any],
) -> SMapRow:
    next_id, next_byte = next_map_ids(existing)
    base = SMapRow(
        id=int(draft.get("id", next_id)),
        map=int(draft.get("map", next_byte)),
        name=str(draft.get("name", f"Custom Map {next_id}")),
        is_boss_stage=bool(draft.get("isBossStage", False)),
        boss_play_time=draft.get("bossPlayTime"),
        breath_time=int(draft.get("breathTime", 100)),
        description=draft.get("description"),
        play_time=draft.get("playTime"),
        trigger_boss_time=draft.get("triggerBossTime"),
        use_breath_time=bool(draft.get("useBreathTime", True)),
    )
    # Normalize optional ints
    if base.boss_play_time is not None:
        base = apply_map_draft(base, {"bossPlayTime": base.boss_play_time})
    return apply_map_draft(base, dict(draft))


def build_create_map_sql(
    row: SMapRow,
    *,
    scenario_ids: list[int] | None = None,
    guardians: list[dict[str, Any]] | None = None,
    stage_script: str | None = None,
    include_scenarios: bool = True,
    include_guardians: bool = True,
) -> str:
    map2 = [
        Map2ScenarioRow(scenario_id=int(sid), map_id=row.id)
        for sid in (scenario_ids or [])
    ]
    g_rows: list[Guardian2MapRow] = []
    for i, g in enumerate(guardians or []):
        g_rows.append(
            Guardian2MapRow(
                id=int(g.get("id", 10_000 + row.id * 10 + i)),
                side=str(g.get("side", "Left")),
                boss_guardian_id=g.get("bossGuardianId"),
                guardian_id=g.get("guardianId"),
                map_id=row.id,
                scenario_id=int(g.get("scenarioId", map2[0].scenario_id if map2 else 0)),
                status_id=int(g.get("statusId", 0)),
            )
        )
    stage_by = {str(row.id): stage_script} if stage_script else {}
    sql = build_map_pack_sql(
        maps=[row],
        map2=map2,
        guardians=g_rows,
        scenarios=[],
        stage_by_map_id=stage_by,
        include_scenarios=include_scenarios and bool(map2),
        include_guardians=include_guardians and bool(g_rows),
        include_m_scenarios=False,
    )
    # Ensure S_Maps insert present even if helper skips empty
    if "S_Maps" not in sql and "INSERT INTO" not in sql:
        sql = format_s_maps_insert(row) + "\n" + sql
    return sql


def patch_relations_sql(
    map_id: int,
    *,
    add_scenario_ids: list[int] | None = None,
    remove_scenario_ids: list[int] | None = None,
    add_guardians: list[dict[str, Any]] | None = None,
) -> str:
    lines = ["-- map relation patches"]
    for sid in remove_scenario_ids or []:
        lines.append(
            f"DELETE FROM Map_2_Scenarios WHERE map_id={map_id} AND scenario_id={int(sid)};"
        )
    for sid in add_scenario_ids or []:
        lines.append(
            format_map2scenario_insert(
                Map2ScenarioRow(scenario_id=int(sid), map_id=map_id)
            )
        )
    for i, g in enumerate(add_guardians or []):
        lines.append(
            format_guardian2maps_insert(
                Guardian2MapRow(
                    id=int(g.get("id", 20_000 + map_id * 10 + i)),
                    side=str(g.get("side", "Left")),
                    boss_guardian_id=g.get("bossGuardianId"),
                    guardian_id=g.get("guardianId"),
                    map_id=map_id,
                    scenario_id=int(g.get("scenarioId", 0)),
                    status_id=int(g.get("statusId", 0)),
                )
            )
        )
    return "\n".join(lines) + "\n"
