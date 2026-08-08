"""Allowlisted local-client installs (never stock client)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


class InstallError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def resolve_stock_client(jftse: Path) -> Path:
    env = os.environ.get("JFTSE_STOCK_CLIENT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    for candidate in (
        jftse / "FantaTennis-Local-Client" / "client",
        jftse / ".jftse-client-linux" / "client",
    ):
        if candidate.is_dir():
            return candidate.resolve()
    return (jftse / ".jftse-client-linux" / "client").resolve()


def assert_install_allowed(target: Path, *, jftse: Path) -> Path:
    stock = resolve_stock_client(jftse)
    resolved = target.expanduser().resolve()
    if resolved == stock:
        raise InstallError("REFUSE_STOCK_CLIENT")

    local_client = os.environ.get("JFTSE_LOCAL_CLIENT", "").strip()
    allow_prefix = os.environ.get("JFTSE_INSTALL_ALLOW_PREFIX", "").strip()
    allowed = False
    if local_client and resolved == Path(local_client).expanduser().resolve():
        allowed = True
    if allow_prefix and str(resolved).startswith(
        str(Path(allow_prefix).expanduser().resolve())
    ):
        allowed = True
    if str(resolved).startswith("/tmp/") or "/tmp/" in str(resolved):
        allowed = True
    # Studio exports/ is never a client root; allow any target under /tmp
    if not allowed:
        raise InstallError("TARGET_NOT_ALLOWLISTED")
    return resolved


def install_files(
    target_client: Path,
    files: list[dict[str, str]],
    *,
    jftse: Path,
) -> dict[str, Any]:
    """Copy files into target client.

    Each file: {source: abs path, destRelative: path under client e.g. Res/…}
    """
    root = assert_install_allowed(target_client, jftse=jftse)
    installed: dict[str, str] = {}
    for entry in files:
        source = Path(entry["source"]).expanduser().resolve()
        dest_rel = entry["destRelative"].replace("\\", "/").lstrip("/")
        if ".." in dest_rel.split("/"):
            raise InstallError("INVALID_DEST_PATH")
        if not source.is_file():
            raise InstallError(f"SOURCE_MISSING:{source}")
        dest = root / dest_rel
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(source.read_bytes())
        installed[dest_rel] = str(dest)
    return {"ok": True, "targetClient": str(root), "installed": installed}
