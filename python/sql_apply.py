"""Safe apply of studio-generated SQL packs (dry-run default).

Rejects destructive statements. Optional live apply via mysql/mariadb CLI
when JFTSE_DATABASE_URL or DATABASE_URL is set.
"""

from __future__ import annotations

import os
import re
import shlex
import subprocess
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

_BANNED = re.compile(
    r"\b(DROP\s+TABLE|DROP\s+DATABASE|TRUNCATE\s+TABLE|ALTER\s+TABLE|CREATE\s+USER|"
    r"GRANT\s+|REVOKE\s+|LOAD\s+DATA|INTO\s+OUTFILE)\b",
    re.IGNORECASE,
)
_DELETE = re.compile(r"^\s*DELETE\s+FROM\b", re.IGNORECASE)
_INSERT = re.compile(r"^\s*INSERT\s+INTO\b", re.IGNORECASE)


def split_sql_statements(sql: str) -> list[str]:
    """Split on `;` outside simple quotes (studio packs are plain ASCII SQL)."""
    parts: list[str] = []
    buf: list[str] = []
    in_single = False
    for ch in sql:
        if ch == "'" and not in_single:
            in_single = True
            buf.append(ch)
            continue
        if ch == "'" and in_single:
            in_single = False
            buf.append(ch)
            continue
        if ch == ";" and not in_single:
            stmt = "".join(buf).strip()
            if stmt:
                parts.append(stmt)
            buf = []
            continue
        buf.append(ch)
    tail = "".join(buf).strip()
    if tail:
        parts.append(tail)
    return parts


def audit_statements(statements: list[str]) -> dict[str, Any]:
    banned: list[str] = []
    deletes: list[str] = []
    inserts = 0
    comments_only = 0
    for stmt in statements:
        body = "\n".join(
            line for line in stmt.splitlines() if not line.strip().startswith("--")
        ).strip()
        if not body:
            comments_only += 1
            continue
        if _BANNED.search(body):
            banned.append(body[:120])
        if _DELETE.match(body):
            deletes.append(body[:120])
        if _INSERT.match(body):
            inserts += 1
    return {
        "statementCount": len(statements),
        "insertCount": inserts,
        "deleteCount": len(deletes),
        "commentOnly": comments_only,
        "banned": banned,
        "deletes": deletes,
        "safe": len(banned) == 0,
    }


def parse_database_url(url: str) -> dict[str, str]:
    """Parse mysql://user:pass@host:port/db → connection fields."""
    raw = url.strip()
    if "://" not in raw:
        raise ValueError("DATABASE_URL_INVALID")
    parsed = urlparse(raw)
    if parsed.scheme not in ("mysql", "mariadb"):
        raise ValueError("DATABASE_URL_SCHEME")
    return {
        "host": parsed.hostname or "127.0.0.1",
        "port": str(parsed.port or 3306),
        "user": unquote(parsed.username or ""),
        "password": unquote(parsed.password or ""),
        "database": (parsed.path or "/").lstrip("/") or "",
    }


def apply_sql_file(
    path: Path,
    *,
    dry_run: bool = True,
    database_url: str | None = None,
    allow_deletes: bool = False,
) -> dict[str, Any]:
    if not path.is_file():
        return {"ok": False, "error": "SQL_FILE_MISSING", "path": str(path)}
    sql = path.read_text(encoding="utf-8")
    statements = split_sql_statements(sql)
    audit = audit_statements(statements)
    if not audit["safe"]:
        return {
            "ok": False,
            "error": "SQL_BANNED_STATEMENT",
            "audit": audit,
            "path": str(path),
        }
    if audit["deletes"] and not allow_deletes:
        return {
            "ok": False,
            "error": "SQL_DELETE_REQUIRES_FLAG",
            "audit": audit,
            "path": str(path),
            "hint": "Pass allowDeletes=true for Map_2_Scenarios DELETE patches only.",
        }
    result: dict[str, Any] = {
        "ok": True,
        "path": str(path),
        "dryRun": dry_run,
        "audit": audit,
        "applied": False,
    }
    if dry_run:
        result["note"] = "Dry-run only; no database connection opened."
        return result

    url = (database_url or os.environ.get("JFTSE_DATABASE_URL") or os.environ.get("DATABASE_URL") or "").strip()
    if not url:
        return {
            "ok": False,
            "error": "DATABASE_URL_REQUIRED",
            "path": str(path),
            "hint": "Set JFTSE_DATABASE_URL=mysql://user:pass@host:3306/jftse",
        }
    try:
        conn = parse_database_url(url)
    except ValueError as exc:
        return {"ok": False, "error": str(exc), "path": str(path)}

    # Prefer mysql client; fall back to mariadb
    client_bin = "mysql"
    for candidate in ("mysql", "mariadb"):
        if subprocess.run(["which", candidate], capture_output=True).returncode == 0:
            client_bin = candidate
            break
    else:
        return {
            "ok": False,
            "error": "MYSQL_CLIENT_MISSING",
            "path": str(path),
            "hint": "Install mysql or mariadb client for live apply.",
        }

    cmd = [
        client_bin,
        "-h",
        conn["host"],
        "-P",
        conn["port"],
        "-u",
        conn["user"],
        conn["database"],
    ]
    env = os.environ.copy()
    if conn["password"]:
        env["MYSQL_PWD"] = conn["password"]
    proc = subprocess.run(
        cmd,
        input=sql,
        text=True,
        capture_output=True,
        env=env,
        timeout=120,
        check=False,
    )
    result["applied"] = proc.returncode == 0
    result["exitCode"] = proc.returncode
    if proc.returncode != 0:
        result["ok"] = False
        result["error"] = "MYSQL_APPLY_FAILED"
        result["stderr"] = (proc.stderr or "")[:2000]
    else:
        result["stdout"] = (proc.stdout or "")[:500]
    return result
