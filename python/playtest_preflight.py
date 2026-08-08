"""Truthful local-client preflight; never launches or drives the game."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import TypeAlias

from sql_apply import apply_sql_file

JsonValue: TypeAlias = (
    str | int | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)
JsonObject: TypeAlias = dict[str, JsonValue]

MANUAL_HANDOFF = (
    "You must run the launch command yourself, log in, open Equipment or map "
    "selection, equip or select the authored content, and visually verify it "
    "in the DX9 client. This preflight does not launch or control the game."
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _artifact_source(path: Path) -> bool:
    exports_value = os.environ.get("JFTSE_STUDIO_EXPORTS", "").strip()
    if not exports_value or path.is_symlink() or not path.is_file():
        return False
    return path.resolve().is_relative_to(
        Path(exports_value).expanduser().resolve(),
    )


def verify_install_plan(
    target_client: Path,
    install_plan: list[dict[str, str]],
) -> JsonObject:
    target = target_client.expanduser().resolve()
    checks: list[JsonValue] = []
    for entry in install_plan:
        source = Path(entry.get("source", "")).expanduser()
        relative = entry.get("destRelative", "").replace("\\", "/")
        destination = target.joinpath(*relative.split("/"))
        destination_safe = (
            relative.startswith("Res/")
            and ".." not in relative.split("/")
            and not destination.is_symlink()
            and destination.resolve().is_relative_to(target)
        )
        source_ok = _artifact_source(source)
        destination_ok = (
            destination_safe
            and destination.is_file()
            and not destination.is_symlink()
        )
        source_hash = _sha256(source) if source_ok else None
        installed_hash = _sha256(destination) if destination_ok else None
        matches = bool(
            source_hash
            and installed_hash
            and source_hash == installed_hash
        )
        checks.append(
            {
                "destRelative": relative,
                "source": str(source),
                "path": str(destination),
                "sourceSha256": source_hash,
                "installedSha256": installed_hash,
                "matches": matches,
                "ok": source_ok and destination_ok and matches,
            }
        )
    return {
        "ok": all(
            isinstance(check, dict) and check.get("ok") is True
            for check in checks
        ),
        "checks": checks,
        "passed": sum(
            1
            for check in checks
            if isinstance(check, dict) and check.get("ok") is True
        ),
        "total": len(checks),
    }


def _discover_launch_script(target: Path) -> Path | None:
    configured = os.environ.get("JFTSE_LAUNCH_SCRIPT", "").strip()
    candidates = (
        [Path(configured).expanduser()]
        if configured
        else []
    ) + [target.parent / "START-FANTA-TENNIS.sh"]
    for candidate in candidates:
        if (
            candidate.is_file()
            and not candidate.is_symlink()
            and candidate.stat().st_size > 0
            and os.access(candidate, os.X_OK)
        ):
            return candidate.resolve()
    return None


def run_local_preflight(
    target_client: Path,
    install_plan: list[dict[str, str]],
    *,
    sql_path: str | None = None,
    sql_apply_receipt: JsonObject | None = None,
) -> JsonObject:
    target = target_client.expanduser().resolve()
    configured_value = os.environ.get("JFTSE_LOCAL_CLIENT", "").strip()
    configured = (
        Path(configured_value).expanduser().resolve()
        if configured_value
        else None
    )
    stock_value = os.environ.get("JFTSE_STOCK_CLIENT", "").strip()
    stock = (
        Path(stock_value).expanduser().resolve()
        if stock_value
        else None
    )
    target_ok = bool(
        configured
        and target == configured
        and target != stock
        and target.is_dir()
    )
    executable = target / "FantaTennis.exe"
    dll = target / "jftse.dll"
    launch = _discover_launch_script(target)
    file_check = verify_install_plan(target, install_plan)

    checklist: list[JsonValue] = [
        {
            "id": "local-client",
            "ok": target_ok,
            "label": f"Configured local client -> {target}",
        },
        {
            "id": "client-exe",
            "ok": executable.is_file() and executable.stat().st_size > 0,
            "label": f"FantaTennis.exe -> {executable}",
        },
        {
            "id": "client-dll",
            "ok": dll.is_file() and dll.stat().st_size > 0,
            "label": f"jftse.dll -> {dll}",
        },
    ]
    raw_checks = file_check.get("checks")
    if isinstance(raw_checks, list):
        for raw_check in raw_checks:
            if isinstance(raw_check, dict):
                checklist.append(
                    {
                        "id": f"file-{raw_check.get('destRelative', '')}",
                        "ok": raw_check.get("ok") is True,
                        "label": (
                            f"Installed bytes match -> "
                            f"{raw_check.get('destRelative', '')}"
                        ),
                        "path": raw_check.get("path"),
                    }
                )

    sql_result: JsonObject | None = None
    if sql_path:
        sql_result = apply_sql_file(Path(sql_path), dry_run=True)
        audit = sql_result.get("audit")
        sql_ok = bool(
            sql_result.get("ok")
            and isinstance(audit, dict)
            and audit.get("safe") is True
        )
        checklist.append(
            {
                "id": "sql-audit",
                "ok": sql_ok,
                "label": f"Aggregate SQL audit -> {sql_path}",
            }
        )
        receipt_path = (
            str(sql_apply_receipt.get("path", ""))
            if sql_apply_receipt
            else ""
        )
        sql_apply_ok = bool(
            sql_apply_receipt
            and sql_apply_receipt.get("ok") is True
            and sql_apply_receipt.get("applied") is True
            and sql_result.get("path") == receipt_path
        )
        checklist.append(
            {
                "id": "sql-apply",
                "ok": sql_apply_ok,
                "label": "Matching live SQL apply receipt",
            }
        )

    checklist.append(
        {
            "id": "launch-script",
            "ok": launch is not None,
            "label": (
                f"Executable launch script -> {launch}"
                if launch
                else "Executable launch script not found"
            ),
        }
    )
    passed = all(
        isinstance(check, dict) and check.get("ok") is True
        for check in checklist
    )
    return {
        "ok": True,
        "preflightPassed": passed,
        "ready": passed,
        "targetClient": str(target),
        "localClient": str(target),
        "fileCheck": file_check,
        "sqlAudit": sql_result,
        "launchCommand": str(launch) if launch else None,
        "launchScript": str(launch) if launch else None,
        "launchScriptExists": launch is not None,
        "checklist": checklist,
        "manualHandoff": MANUAL_HANDOFF,
    }
