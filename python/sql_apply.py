"""Strict apply of studio-generated INSERT-only SQL packs."""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import TypeAlias
from urllib.parse import unquote, urlparse

from sql_policy import (
    JsonValue,
    SqlParseError,
    audit_statements,
    invalid_audit,
    split_sql_statements,
)

SqlResult: TypeAlias = dict[str, JsonValue]


def _validated_sql_path(path: Path) -> tuple[Path | None, str | None]:
    candidate = path.expanduser()
    if candidate.is_symlink():
        return None, "SQL_SYMLINK"
    if not candidate.exists() or not candidate.is_file():
        return None, "SQL_FILE_MISSING"
    exports_value = os.environ.get("JFTSE_STUDIO_EXPORTS", "").strip()
    if not exports_value:
        return None, "SQL_OUTSIDE_EXPORTS"
    resolved = candidate.resolve()
    exports_root = Path(exports_value).expanduser().resolve()
    if not resolved.is_relative_to(exports_root) or resolved.suffix.lower() != ".sql":
        return None, "SQL_OUTSIDE_EXPORTS"
    return resolved, None


def parse_database_url(url: str) -> dict[str, str]:
    """Parse a MySQL URL into CLI connection fields."""
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        raise ValueError("DATABASE_URL_INVALID")
    if parsed.scheme not in ("mysql", "mariadb"):
        raise ValueError("DATABASE_URL_SCHEME")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": str(parsed.port or 3306),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "/").lstrip("/"),
    }


def apply_sql_file(path: Path, *, dry_run: bool = True) -> SqlResult:
    validated_path, path_error = _validated_sql_path(path)
    if path_error or validated_path is None:
        return {
            "ok": False,
            "error": path_error or "SQL_FILE_MISSING",
            "path": str(path),
        }

    sql = validated_path.read_text(encoding="utf-8")
    try:
        statements = split_sql_statements(sql)
    except SqlParseError as exc:
        return {
            "ok": False,
            "error": "SQL_PARSE_FAILED",
            "audit": invalid_audit(str(exc)),
            "path": str(validated_path),
        }
    audit = audit_statements(statements)
    if not bool(audit["safe"]):
        return {
            "ok": False,
            "error": "SQL_STATEMENT_NOT_ALLOWED",
            "audit": audit,
            "path": str(validated_path),
        }

    result: SqlResult = {
        "ok": True,
        "path": str(validated_path),
        "dryRun": dry_run,
        "audit": audit,
        "applied": False,
    }
    if dry_run:
        result["note"] = "Dry-run only; no database connection opened."
        return result

    url = os.environ.get("JFTSE_DATABASE_URL", "").strip()
    if not url:
        return {
            "ok": False,
            "error": "DATABASE_URL_REQUIRED",
            "path": str(validated_path),
            "hint": "Set JFTSE_DATABASE_URL=mysql://user:pass@host:3306/jftse",
        }
    try:
        connection = parse_database_url(url)
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "path": str(validated_path)}

    client = next(
        (candidate for candidate in ("mysql", "mariadb") if shutil.which(candidate)),
        None,
    )
    if client is None:
        return {
            "ok": False,
            "error": "MYSQL_CLIENT_MISSING",
            "path": str(validated_path),
            "hint": "Install mysql or mariadb client for live apply.",
        }
    command = [
        client,
        "-h",
        connection["host"],
        "-P",
        connection["port"],
        "-u",
        connection["user"],
        connection["database"],
    ]
    environment = os.environ.copy()
    if connection["password"]:
        environment["MYSQL_PWD"] = connection["password"]
    process = subprocess.run(
        command,
        input=sql,
        text=True,
        capture_output=True,
        env=environment,
        timeout=120,
        check=False,
    )
    result["applied"] = process.returncode == 0
    result["exitCode"] = process.returncode
    if process.returncode != 0:
        result["ok"] = False
        result["error"] = "MYSQL_APPLY_FAILED"
        result["stderr"] = (process.stderr or "")[:2000]
    else:
        result["stdout"] = (process.stdout or "")[:500]
    return result
