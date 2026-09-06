#!/usr/bin/env python3
"""Run INSIDE Blender to report runtime identity and requested RNA capabilities."""

import argparse
import json
import os
from pathlib import Path
import re
import sys
import tempfile


def normalize_symbol(value, prefix, segments):
    name = value.removeprefix(prefix)
    parts = name.split(".")
    if len(parts) != segments or not all(re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", part) for part in parts):
        raise argparse.ArgumentTypeError("Expected " + prefix + ".".join(["identifier"] * segments))
    return name


def json_value(value):
    if isinstance(value, bytes):
        return value.decode("utf-8", "replace")
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, tuple)):
        return [json_value(item) for item in value]
    return str(value)


def describe_property(prop):
    result = {"identifier": prop.identifier, "type": prop.type}
    for key in ("name", "description", "subtype", "is_readonly", "is_required", "is_array", "array_length", "hard_min", "hard_max", "default"):
        try:
            result[key] = json_value(getattr(prop, key))
        except (AttributeError, TypeError):
            pass
    if prop.type == "ENUM":
        # Dynamic/context-dependent enum callbacks may not enumerate every choice.
        result["enum_identifiers"] = [item.identifier for item in prop.enum_items]
        result["enum_caveat"] = "RNA enumeration may omit dynamic/context-dependent choices."
    try:
        result["fixed_type"] = prop.fixed_type.identifier
    except AttributeError:
        pass
    return result


def check_type(bpy, name):
    result = {"kind": "type", "symbol": "bpy.types." + name, "exists": False}
    try:
        cls = getattr(bpy.types, name)
        rna = cls.bl_rna
        result.update(exists=True, rna_identifier=rna.identifier,
                      properties=[item.identifier for item in rna.properties],
                      functions=[item.identifier for item in rna.functions])
    except (AttributeError, RuntimeError) as error:
        result["error"] = str(error)
    return result


def check_operator(bpy, name):
    result = {"kind": "operator", "symbol": "bpy.ops." + name, "exists": False}
    category, identifier = name.split(".")
    try:
        op = getattr(getattr(bpy.ops, category), identifier)
        # bpy.ops resolves lazily; hasattr alone cannot prove registration.
        rna = op.get_rna_type()
        result.update(exists=True, rna_identifier=rna.identifier,
                      properties=[describe_property(item) for item in rna.properties if item.identifier != "rna_type"])
        try:
            result["poll_in_current_context"] = bool(op.poll())
        except (RuntimeError, TypeError) as error:
            result["poll_error"] = str(error)
    except (AttributeError, RuntimeError) as error:
        result["error"] = str(error)
    return result


def check_property(bpy, name):
    result = {"kind": "property", "symbol": "bpy.types." + name, "exists": False}
    owner, identifier = name.split(".")
    try:
        prop = getattr(bpy.types, owner).bl_rna.properties.get(identifier)
        if prop is not None:
            result.update(exists=True, rna=describe_property(prop))
    except (AttributeError, RuntimeError) as error:
        result["error"] = str(error)
    return result


def write_report(path, report):
    destination = Path(path).expanduser().resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=destination.parent, delete=False) as output:
            temporary = output.name
            json.dump(report, output, ensure_ascii=False, indent=2)
            output.write("\n")
        os.replace(temporary, destination)
    finally:
        if temporary and os.path.exists(temporary):
            os.unlink(temporary)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="Write clean JSON here; Blender stdout also includes its own logs.")
    parser.add_argument("--type", action="append", default=[], type=lambda value: normalize_symbol(value, "bpy.types.", 1))
    parser.add_argument("--operator", action="append", default=[], type=lambda value: normalize_symbol(value, "bpy.ops.", 2))
    parser.add_argument("--property", action="append", default=[], type=lambda value: normalize_symbol(value, "bpy.types.", 2))
    parser.add_argument("--doc-version", default="5.2", help="Documentation major.minor for comparison; default 5.2.")
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    try:
        import bpy
    except ImportError as error:
        raise RuntimeError("Run this script with Blender --background --python, not host Python.") from error
    try:
        doc_version = tuple(int(part) for part in args.doc_version.split("."))
        if len(doc_version) != 2:
            raise ValueError
    except ValueError:
        parser.error("--doc-version must have the form major.minor")
    runtime = {}
    for key in ("version", "version_string", "version_cycle", "build_branch", "build_hash", "build_date", "build_time", "build_platform", "build_type", "binary_path", "background"):
        runtime[key] = json_value(getattr(bpy.app, key, None))
    build_options = {}
    for name in dir(bpy.app.build_options):
        if not name.startswith("_"):
            value = getattr(bpy.app.build_options, name)
            if isinstance(value, bool):
                build_options[name] = value
    checks = []
    types = args.type or (["Object", "Mesh", "Scene"] if not (args.operator or args.property) else [])
    checks.extend(check_type(bpy, name) for name in types)
    checks.extend(check_operator(bpy, name) for name in args.operator)
    checks.extend(check_property(bpy, name) for name in args.property)
    report = {
        "schema_version": 1,
        "documentation_target": list(doc_version),
        "runtime": runtime,
        "runtime_matches_documentation_major_minor": tuple(bpy.app.version[:2]) == doc_version,
        "build_options": build_options,
        "context": {"mode": bpy.context.mode, "has_window": bpy.context.window is not None,
                    "has_area": bpy.context.area is not None, "has_region": bpy.context.region is not None},
        "checks": checks,
        "all_requested_symbols_exist": all(item["exists"] for item in checks),
        "interpretation": "Symbol presence and poll describe this runtime and current context only; they do not prove an operation succeeds, a GPU is usable, or all documentation features are installed.",
    }
    if args.output:
        write_report(args.output, report)
    print("BLENDER_PROBE_JSON=" + json.dumps(report, ensure_ascii=False, sort_keys=True), flush=True)
    return report


if __name__ == "__main__":
    main()
