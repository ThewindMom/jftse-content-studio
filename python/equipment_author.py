"""Equipment authoring: clone mesh into export RES, catalog patch, item SQL."""

from __future__ import annotations

import re
import zipfile
from html import escape
from pathlib import Path
from typing import Any

import importlib

from client_crypto import decrypt_set_file, encrypt_set_file

_item_mesh = importlib.import_module("python.item_mesh")
parse_item_mesh_entries = _item_mesh.parse_item_mesh_entries
resolve_item_mesh_path = _item_mesh.resolve_item_mesh_path


def _patch_zip_members(
    archive_path: Path,
    replacements: dict[str, bytes],
    out_path: Path,
) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "r") as zin:
        missing = replacements.keys() - set(zin.namelist())
        if missing:
            raise ValueError(f"ITEM_MEMBER_MISSING: {', '.join(sorted(missing))}")
        with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                zout.writestr(info, replacements.get(info.filename, zin.read(info.filename)))


def _set_xml_attribute(record: str, name: str, value: str) -> str:
    pattern = re.compile(rf'\b{re.escape(name)}="[^"]*"', re.IGNORECASE)
    replacement = f'{name}="{escape(value, quote=True)}"'
    if pattern.search(record):
        return pattern.sub(replacement, record, count=1)
    return record[:-2].rstrip() + f" {replacement}/>"


def _patch_item_parts(
    plaintext: str,
    *,
    source_item_index: int,
    target_item_index: int,
    char: str,
    part: str,
    effect: int,
) -> str:
    record_re = re.compile(r'<Item\b[^>]*\bIndex="(\d+)"[^>]*/>', re.IGNORECASE)
    records = list(record_re.finditer(plaintext))
    source = next(
        (match.group(0) for match in records if int(match.group(1)) == source_item_index),
        None,
    )
    if source is None:
        raise ValueError("SOURCE_ITEM_BINDING_MISSING")
    target = source
    for name, value in (
        ("Index", str(target_item_index)),
        ("Char", char.upper()),
        ("Part", part.upper()),
        ("Mesh", str(target_item_index)),
        ("Effect", str(effect)),
    ):
        target = _set_xml_attribute(target, name, value)
    existing = next(
        (match.group(0) for match in records if int(match.group(1)) == target_item_index),
        None,
    )
    if existing is not None:
        return plaintext.replace(existing, target, 1)
    return plaintext.replace(source, source + "\n" + target, 1)


def clone_equipment_mesh(
    client_root: Path,
    *,
    mesh_index: int | str,
    char: str,
    out_dir: Path,
    dat_override: Path | None = None,
    new_member_name: str | None = None,
) -> dict[str, Any]:
    """Copy stock item DAT (optional override bytes) into a new Item*.res under out_dir."""
    resolved = resolve_item_mesh_path(client_root, mesh_index, char=char)
    if resolved is None:
        return {"ok": False, "error": "MESH_NOT_FOUND"}
    stock_archive = client_root / resolved["archive"]
    member = resolved["member"]
    out_dir.mkdir(parents=True, exist_ok=True)
    out_archive = out_dir / Path(resolved["archive"]).name
    data = (
        dat_override.read_bytes()
        if dat_override is not None and dat_override.is_file()
        else None
    )
    write_member = new_member_name or member
    with zipfile.ZipFile(stock_archive, "r") as zin:
        with zipfile.ZipFile(out_archive, "w", compression=zipfile.ZIP_DEFLATED) as zout:
            for info in zin.infolist():
                if info.filename == member:
                    payload = data if data is not None else zin.read(info.filename)
                    # Keep original member name for fixed path compatibility
                    zout.writestr(info, payload)
                else:
                    zout.writestr(info, zin.read(info.filename))
            if write_member != member and data is not None:
                zout.writestr(write_member, data)
    dest_rel = resolved["archive"]
    return {
        "ok": True,
        "archive": str(out_archive),
        "destRelative": dest_rel,
        "member": member,
        "sourceIndex": resolved["index"],
        "char": resolved["char"],
        "path": resolved["path"],
        "desc": resolved["desc"],
    }


def patch_item_mesh_catalog(
    client_root: Path,
    *,
    char: str,
    source_index: int | str,
    new_index: int | str,
    path: str,
    desc: str,
    out_dir: Path,
    source_item_index: int | str = 10728,
    part: str = "Racket",
    effect: int = 0,
) -> dict[str, Any]:
    """Patch mesh catalog and runtime item tuple into one exported Item.res."""
    if effect not in {0, 15}:
        raise ValueError("EQUIPMENT_EFFECT_UNSUPPORTED")
    item_res = client_root / "Res" / "Script" / "Item.res"
    if not item_res.is_file():
        return {"ok": False, "error": "ITEM_RES_MISSING"}
    with zipfile.ZipFile(item_res, "r") as zin:
        raw = zin.read("Info_Item_Mesh.set")
        raw_parts = zin.read("Item_Parts.set")
    plain = decrypt_set_file(raw).decode("utf-8", errors="replace")
    want = str(int(source_index))
    char_u = char.upper()
    # Prefer exact line clone then replace index/path/desc
    entry_re = re.compile(
        r'<Item\s+Char="([^"]+)"\s+Index="(\d+)"\s+Path="([^"]+)"(?:\s+Desc="([^"]*)")?\s*/>',
    )
    source_line: str | None = None
    for m in entry_re.finditer(plain):
        if m.group(2) == want and m.group(1).upper() == char_u:
            source_line = m.group(0)
            break
    if source_line is None:
        for m in entry_re.finditer(plain):
            if m.group(2) == want:
                source_line = m.group(0)
                break
    new_line = (
        f'<Item Char="{char_u}" Index="{int(new_index)}" '
        f'Path="{escape(path.replace(chr(92), "/"), quote=True)}" '
        f'Desc="{escape(desc, quote=True)}"/>'
    )
    if f'Index="{int(new_index)}"' in plain and char_u in plain:
        # Replace existing new index
        plain2 = re.sub(
            rf'<Item\s+Char="{re.escape(char_u)}"\s+Index="{int(new_index)}"[^/]*/>',
            new_line,
            plain,
            count=1,
            flags=re.IGNORECASE,
        )
    elif source_line:
        plain2 = plain.replace(source_line, source_line + "\n" + new_line, 1)
    else:
        # Append before closing root if any
        if "</" in plain:
            idx = plain.rfind("</")
            plain2 = plain[:idx] + new_line + "\n" + plain[idx:]
        else:
            plain2 = plain + "\n" + new_line + "\n"

    encrypted = encrypt_set_file(plain2.encode("utf-8"))
    # Prefer fixed size when possible (pad by re-encrypt with nulls if shorter fails)
    if len(encrypted) != len(raw):
        # Try size-preserving pad on plaintext
        pad = len(raw) - len(encrypted)
        if pad > 0:
            encrypted = encrypt_set_file(plain2.encode("utf-8") + (b"\n" * pad))
        # If still different, write anyway (install uses full member replace)
    parts_plain = decrypt_set_file(raw_parts).decode("utf-8", errors="replace")
    patched_parts = _patch_item_parts(
        parts_plain,
        source_item_index=int(source_item_index),
        target_item_index=int(new_index),
        char=char_u,
        part=part,
        effect=effect,
    )
    encrypted_parts = encrypt_set_file(patched_parts.encode("utf-8"))
    out_dir.mkdir(parents=True, exist_ok=True)
    out_item = out_dir / "Item.res"
    _patch_zip_members(
        item_res,
        {
            "Info_Item_Mesh.set": encrypted,
            "Item_Parts.set": encrypted_parts,
        },
        out_item,
    )
    return {
        "ok": True,
        "itemArchive": str(out_item),
        "destRelative": "Res/Script/Item.res",
        "newIndex": str(int(new_index)),
        "path": path,
        "char": char_u,
        "desc": desc,
        "encryptedBytes": len(encrypted),
        "stockBytes": len(raw),
        "sizeMatch": len(encrypted) == len(raw),
        "itemBinding": {
            "sourceItemIndex": int(source_item_index),
            "itemIndex": int(new_index),
            "mesh": int(new_index),
            "effect": effect,
            "encryptedBytes": len(encrypted_parts),
        },
    }


def build_item_sql_pack(
    *,
    product_index: int,
    name: str,
    mesh: int,
    part: str = "Racket",
    tex: int = 0,
    effect: int = 0,
    gold: int = 0,
) -> str:
    """Minimal designer SQL stub for custom shop rows (JFTSE-aligned fields)."""
    def sql_literal(value: str) -> str:
        escaped = value.replace("'", "''")
        return f"'{escaped}'"

    name_sql = sql_literal(name)
    part_sql = sql_literal(part)
    lines = [
        "-- jftse-content-studio item pack",
        f"-- product index {product_index} mesh {mesh}",
        (
            "INSERT INTO S_Product (`index`, name, part, mesh, tex, effect, gold) "
            f"VALUES ({product_index}, {name_sql}, {part_sql}, {mesh}, {tex}, {effect}, {gold}) "
            "ON DUPLICATE KEY UPDATE name=VALUES(name), part=VALUES(part), mesh=VALUES(mesh), "
            "tex=VALUES(tex), effect=VALUES(effect), gold=VALUES(gold);"
        ),
        (
            "INSERT INTO product (`index`, name, part, mesh, tex, effect, gold) "
            f"VALUES ({product_index}, {name_sql}, {part_sql}, {mesh}, {tex}, {effect}, {gold}) "
            "ON DUPLICATE KEY UPDATE name=VALUES(name), mesh=VALUES(mesh);"
        ),
    ]
    return "\n".join(lines) + "\n"


def list_catalog_max_index(client_root: Path, char: str = "NIKI") -> int:
    max_i = 0
    for e in parse_item_mesh_entries(client_root):
        if e["char"].upper() != char.upper():
            continue
        max_i = max(max_i, int(e["index"]))
    return max_i
