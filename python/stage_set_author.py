"""Author stage Info.res .set scripts (decrypt → edit → encrypt)."""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import Any

from client_crypto import decrypt_set_file, encrypt_set_file


def _safe_member_name(member: str) -> str:
    if (
        not member
        or member in {".", ".."}
        or "/" in member
        or "\\" in member
        or Path(member).name != member
    ):
        raise ValueError("PATH_MEMBER_INVALID")
    return member


def load_stage_set_plain(client_root: Path, member: str) -> tuple[bytes, bytes]:
    """Return (encrypted raw, plaintext)."""
    member = _safe_member_name(member)
    archive = client_root / "Res" / "Stage" / "Info.res"
    with zipfile.ZipFile(archive, "r") as zin:
        raw = zin.read(member)
    return raw, decrypt_set_file(raw)


def apply_stage_field_overrides(plain: str, fields: dict[str, str]) -> str:
    """Replace or insert key = value under [Default] for simple fields."""
    text = plain
    for key, value in fields.items():
        if not key or value is None:
            continue
        # Match Key= "..." or Key= ...
        pattern = re.compile(
            rf'^({re.escape(key)}\s*=\s*).*$',
            re.MULTILINE | re.IGNORECASE,
        )
        replacement = f'{key}= "{value}"' if not value.startswith('"') else f"{key}= {value}"
        if pattern.search(text):
            text = pattern.sub(replacement, text, count=1)
        else:
            # Insert after [Default]
            text = re.sub(
                r"(\[Default\]\s*\n)",
                rf"\1{replacement}\n",
                text,
                count=1,
                flags=re.IGNORECASE,
            )
    return text


def append_object_layer(plain: str, file_path: str, level: int = 0) -> str:
    block = f'\n[Object]\nFile= "{file_path}"\nLevel= {level}\n'
    return plain.rstrip() + block


def write_stage_set(
    client_root: Path,
    member: str,
    *,
    out_dir: Path,
    fields: dict[str, str] | None = None,
    append_objects: list[dict[str, Any]] | None = None,
    plaintext_override: str | None = None,
) -> dict[str, Any]:
    member = _safe_member_name(member)
    raw, plain_b = load_stage_set_plain(client_root, member)
    plain = plaintext_override if plaintext_override is not None else plain_b.decode(
        "utf-8", errors="replace"
    )
    if fields:
        plain = apply_stage_field_overrides(plain, fields)
    for obj in append_objects or []:
        plain = append_object_layer(
            plain,
            str(obj.get("file", "")),
            int(obj.get("level", 0)),
        )
    encrypted = encrypt_set_file(plain.encode("utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    set_path = out_dir / member
    set_path.write_bytes(encrypted)
    # Also wrap in Info.res clone with patched member
    stock = client_root / "Res" / "Stage" / "Info.res"
    out_res = out_dir / "Info.res"
    with zipfile.ZipFile(stock, "r") as zin:
        with zipfile.ZipFile(out_res, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                payload = encrypted if info.filename == member else zin.read(info.filename)
                zout.writestr(info, payload)
    return {
        "ok": True,
        "member": member,
        "setPath": str(set_path),
        "infoArchive": str(out_res),
        "destRelative": "Res/Stage/Info.res",
        "encryptedBytes": len(encrypted),
        "stockBytes": len(raw),
        "sizeMatch": len(encrypted) == len(raw),
        "plaintextPreview": plain[:400],
    }
