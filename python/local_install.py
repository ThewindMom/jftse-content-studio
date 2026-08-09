"""Allowlisted local-client installs (never stock client)."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
from pathlib import Path

InstallReceipt = dict[str, str | int | bool]
InstallResult = dict[str, bool | str | dict[str, InstallReceipt]]


class InstallError(Exception):
    code: str

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def resolve_stock_client(jftse: Path) -> Path:
    env = os.environ.get("JFTSE_STOCK_CLIENT", "").strip()
    if env:
        return Path(env).expanduser().resolve()
    for candidate in (
        jftse / ".jftse-client-linux" / "client",
        jftse / "FantaTennis-Local-Client" / "client",
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
    if not local_client:
        raise InstallError("TARGET_NOT_CONFIGURED")
    if resolved != Path(local_client).expanduser().resolve():
        raise InstallError("TARGET_NOT_ALLOWLISTED")
    return resolved


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _validated_source(raw_source: str) -> Path:
    exports_value = os.environ.get("JFTSE_STUDIO_EXPORTS", "").strip()
    source_path = Path(raw_source).expanduser()
    if source_path.is_symlink():
        raise InstallError("SOURCE_SYMLINK")
    if not source_path.exists() or not source_path.is_file():
        raise InstallError("SOURCE_MISSING")
    if not exports_value:
        raise InstallError("SOURCE_OUTSIDE_EXPORTS")
    exports_root = Path(exports_value).expanduser().resolve()
    source = source_path.resolve()
    if not source.is_relative_to(exports_root):
        raise InstallError("SOURCE_OUTSIDE_EXPORTS")
    return source


def _validated_destination(root: Path, raw_destination: str) -> tuple[str, Path]:
    if "\\" in raw_destination or raw_destination.startswith("/"):
        raise InstallError("INVALID_DEST_PATH")
    parts = raw_destination.split("/")
    if (
        not parts
        or parts[0] != "Res"
        or not raw_destination.endswith(".res")
        or any(part in {"", ".", ".."} for part in parts)
    ):
        raise InstallError("INVALID_DEST_PATH")

    current = root
    for part in parts[:-1]:
        current /= part
        if current.is_symlink():
            raise InstallError("DEST_SYMLINK_ESCAPE")
    destination = root.joinpath(*parts)
    if destination.is_symlink():
        raise InstallError("DEST_SYMLINK_ESCAPE")
    return raw_destination, destination


def _install_one(source: Path, destination: Path) -> InstallReceipt:
    destination.parent.mkdir(parents=True, exist_ok=True)
    root = Path(os.environ["JFTSE_LOCAL_CLIENT"]).expanduser().resolve()
    if not destination.parent.resolve().is_relative_to(root):
        raise InstallError("DEST_SYMLINK_ESCAPE")

    source_hash = _sha256(source)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp:
            temp_path = Path(temp.name)
            with source.open("rb") as source_stream:
                shutil.copyfileobj(source_stream, temp)
            temp.flush()
            os.fsync(temp.fileno())
        if _sha256(temp_path) != source_hash:
            raise InstallError("INSTALL_VERIFY_FAILED")
        os.replace(temp_path, destination)
        temp_path = None
        installed_hash = _sha256(destination)
        if installed_hash != source_hash:
            raise InstallError("INSTALL_VERIFY_FAILED")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    return {
        "source": str(source),
        "destination": str(destination),
        "bytes": source.stat().st_size,
        "sourceSha256": source_hash,
        "installedSha256": installed_hash,
        "matches": True,
    }


def install_files(
    target_client: Path,
    files: list[dict[str, str]],
    *,
    jftse: Path,
) -> InstallResult:
    """Copy files into target client.

    Each file: {source: abs path, destRelative: path under client e.g. Res/…}
    """
    root = assert_install_allowed(target_client, jftse=jftse)
    installed: dict[str, InstallReceipt] = {}
    for entry in files:
        raw_source = entry.get("source")
        raw_destination = entry.get("destRelative")
        if not isinstance(raw_source, str):
            raise InstallError("SOURCE_MISSING")
        if not isinstance(raw_destination, str):
            raise InstallError("INVALID_DEST_PATH")
        source = _validated_source(raw_source)
        dest_rel, destination = _validated_destination(root, raw_destination)
        installed[dest_rel] = _install_one(source, destination)
    return {"ok": True, "targetClient": str(root), "installed": installed}
