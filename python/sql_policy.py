"""Lexical policy for studio-generated INSERT statements."""

from __future__ import annotations

import re
from typing import TypeAlias

JsonValue: TypeAlias = (
    str | int | bool | None | list["JsonValue"] | dict[str, "JsonValue"]
)
SqlAudit: TypeAlias = dict[str, JsonValue]

_ALLOWED_TABLES = {
    "s_product",
    "product",
    "s_maps",
    "m_scenarios",
    "map_2_scenarios",
    "guardian_2_maps",
}
_INSERT_SHAPE = re.compile(
    r"^INSERT\s+INTO\s+`?([A-Za-z][A-Za-z0-9_]*)`?\s*\(.+\)\s+"
    + r"VALUES\s*\(.+\)(?:\s*,\s*\(.+\))*(?:\s+ON\s+DUPLICATE\s+KEY\s+"
    + r"UPDATE\s+.+)?$",
    re.IGNORECASE | re.DOTALL,
)
_FORBIDDEN_VERB = re.compile(
    r"\b(DROP|DELETE|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|LOAD|OUTFILE|"
    + r"SELECT|CALL|USE|SET)\b",
    re.IGNORECASE,
)


class SqlParseError(Exception):
    """Raised when SQL cannot be safely classified."""


def split_sql_statements(sql: str) -> list[str]:
    """Strip line comments and split semicolons outside quoted strings."""
    statements: list[str] = []
    buffer: list[str] = []
    in_string = False
    index = 0
    while index < len(sql):
        char = sql[index]
        following = sql[index + 1] if index + 1 < len(sql) else ""
        if in_string:
            if char == "\\":
                raise SqlParseError("backslash escapes are not allowed")
            if char == "'" and following == "'":
                buffer.extend((char, following))
                index += 2
                continue
            if char == "'":
                in_string = False
            buffer.append(char)
            index += 1
            continue
        if char == "'":
            in_string = True
            buffer.append(char)
            index += 1
            continue
        if char == "-" and following == "-":
            newline = sql.find("\n", index + 2)
            if newline == -1:
                break
            buffer.append("\n")
            index = newline + 1
            continue
        if char == "/" and following == "*":
            raise SqlParseError("block comments are not allowed")
        if char == "\\":
            raise SqlParseError("backslashes are not allowed")
        if char == ";":
            statement = "".join(buffer).strip()
            if statement:
                statements.append(statement)
            buffer = []
            index += 1
            continue
        buffer.append(char)
        index += 1
    if in_string:
        raise SqlParseError("unterminated string")
    tail = "".join(buffer).strip()
    if tail:
        statements.append(tail)
    return statements


def _structural_sql(statement: str) -> str:
    chars: list[str] = []
    in_string = False
    index = 0
    while index < len(statement):
        char = statement[index]
        following = statement[index + 1] if index + 1 < len(statement) else ""
        if in_string:
            if char == "'" and following == "'":
                chars.extend((" ", " "))
                index += 2
                continue
            if char == "'":
                in_string = False
                chars.append(char)
            else:
                chars.append(" ")
            index += 1
            continue
        if char == "'":
            in_string = True
        chars.append(char)
        index += 1
    return "".join(chars).strip()


def audit_statements(statements: list[str]) -> SqlAudit:
    tables: list[JsonValue] = []
    rejected: list[JsonValue] = []
    for statement in statements:
        structure = _structural_sql(statement)
        match = _INSERT_SHAPE.fullmatch(structure)
        table = match.group(1).lower() if match else ""
        if (
            match is None
            or table not in _ALLOWED_TABLES
            or _FORBIDDEN_VERB.search(structure)
        ):
            rejected.append(" ".join(statement.split())[:160])
            continue
        tables.append(table)
    return {
        "statementCount": len(statements),
        "insertCount": len(tables),
        "tables": tables,
        "rejected": rejected,
        "safe": bool(statements) and not rejected,
    }


def invalid_audit(summary: str) -> SqlAudit:
    return {
        "statementCount": 0,
        "insertCount": 0,
        "tables": [],
        "rejected": [summary[:160]],
        "safe": False,
    }
