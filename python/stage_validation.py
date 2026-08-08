"""Reusable validation for stock stage scripts and referenced assets."""

from __future__ import annotations

import importlib
import os
import sys
import zipfile
from pathlib import Path
from typing import Protocol, TypeAlias, cast

JsonValue: TypeAlias = (
    str | int | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)
StageValidation: TypeAlias = dict[str, JsonValue]


class WindAssets(Protocol):
    def decrypt_set(self, encrypted: bytes) -> bytes: ...


def _wind_assets() -> WindAssets:
    root = Path(os.environ.get("JFTSE_ROOT", "")).expanduser()
    if root.is_dir() and str(root) not in sys.path:
        sys.path.insert(0, str(root))
    return cast(
        WindAssets,
        cast(
            object,
            importlib.import_module("tools.wind_dragon_slayer.wind_assets"),
        ),
    )


def list_stage_scripts(client: Path) -> list[str]:
    stage_info = client / "Res" / "Stage" / "Info.res"
    if not stage_info.is_file():
        return []
    with zipfile.ZipFile(stage_info) as archive:
        return sorted(archive.namelist())


def _decode_stage_script(client: Path, script: str) -> dict[str, str]:
    stage_info = client / "Res" / "Stage" / "Info.res"
    with zipfile.ZipFile(stage_info) as archive:
        text = _wind_assets().decrypt_set(archive.read(script)).decode(
            "utf-8",
            errors="replace",
        )
    fields: dict[str, str] = {}
    for line in text.splitlines():
        stripped = line.strip()
        if "=" not in line or stripped.startswith((";", "[")):
            continue
        key, value = line.split("=", 1)
        fields[key.strip()] = value.strip().strip('"')
    return fields


def _resolve_asset(client: Path, relative: str) -> dict[str, JsonValue]:
    normalized = relative.replace("\\", "/").lstrip("/")
    direct = client / normalized
    if direct.is_file():
        return {
            "exists": True,
            "resolved": str(direct),
            "kind": "file",
        }
    parts = Path(normalized).parts
    if len(parts) >= 2:
        member = parts[-1]
        archive = client.joinpath(*parts[:-1]).with_suffix(".res")
        if archive.is_file():
            with zipfile.ZipFile(archive) as handle:
                if member in handle.namelist():
                    return {
                        "exists": True,
                        "resolved": f"{archive}::{member}",
                        "kind": "archive-member",
                    }
    return {
        "exists": False,
        "resolved": normalized,
        "kind": "missing",
    }


def validate_stage_script(client: Path, script: str) -> StageValidation:
    if not script:
        return {
            "valid": False,
            "stageScript": script,
            "error": "STAGE_SCRIPT_REQUIRED",
            "assetChecks": [],
        }
    if script not in list_stage_scripts(client):
        return {
            "valid": False,
            "stageScript": script,
            "error": "STAGE_SCRIPT_MISSING",
            "assetChecks": [],
        }

    fields = _decode_stage_script(client, script)
    checks: list[JsonValue] = []
    for field in ("WorldFile", "SkyFile", "Collision", "Coll_Chat", "World_Chat"):
        relative = fields.get(field, "")
        if not relative:
            continue
        checks.append(
            {
                "field": field,
                "path": relative,
                **_resolve_asset(client, relative),
            }
        )
    required = [
        check
        for check in checks
        if isinstance(check, dict)
        and check.get("field") in {"WorldFile", "SkyFile", "Collision"}
    ]
    valid = bool(required) and all(
        isinstance(check, dict) and check.get("exists") is True
        for check in required
    )
    stage: dict[str, JsonValue] = {}
    for key, value in fields.items():
        stage[key] = value
    result: StageValidation = {
        "valid": valid,
        "stageScript": script,
        "stage": stage,
        "assetChecks": checks,
    }
    if not valid:
        result["error"] = "STAGE_ASSET_MISSING"
    return result
