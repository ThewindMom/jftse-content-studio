#!/usr/bin/env python3
"""Launch a bpy script in Blender; this host script uses only Python's stdlib."""

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys


def executable_path(value):
    """Accept an executable path, PATH command, or macOS .app bundle."""
    expanded = Path(value).expanduser()
    if expanded.suffix.lower() == ".app" and expanded.is_dir():
        for name in ("Blender", "blender"):
            candidate = expanded / "Contents" / "MacOS" / name
            if candidate.is_file() and os.access(candidate, os.X_OK):
                return str(candidate.resolve())
    located = shutil.which(str(expanded))
    if located:
        return str(Path(located).resolve())
    if expanded.is_file() and os.access(expanded, os.X_OK):
        return str(expanded.resolve())
    raise ValueError("Blender executable not found or not executable: " + value)


def discover_blender(explicit=None):
    requested = explicit or os.environ.get("BLENDER_BIN")
    if requested:
        return executable_path(requested)
    candidates = ["blender"]
    if sys.platform == "darwin":
        candidates.extend([
            "/Applications/Blender.app",
            str(Path.home() / "Applications" / "Blender.app"),
        ])
    for candidate in candidates:
        try:
            return executable_path(candidate)
        except ValueError:
            pass
    raise ValueError("Blender was not found. Set BLENDER_BIN or pass --blender /path/to/blender.")


def existing_file(value):
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise argparse.ArgumentTypeError("File does not exist: " + str(path))
    return path


def positive_timeout(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise argparse.ArgumentTypeError("Timeout must be a positive, finite number of seconds.")
    return number


def build_command(blender, script, blend=None, script_args=()):
    # Blender processes options in order. Load data BEFORE executing the script.
    command = [blender, "--background", "--factory-startup", "--disable-autoexec"]
    if blend is not None:
        command.append(str(blend))
    command.extend(["--python-exit-code", "1", "--python", str(script)])
    if script_args:
        command.extend(["--", *script_args])
    return command


def stop_process(process):
    """Stop this invocation; on POSIX include children in its new process group."""
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=2)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait()
    except ProcessLookupError:
        process.wait()


def main(argv=None):
    arguments = list(sys.argv[1:] if argv is None else argv)
    if "--" in arguments:
        separator = arguments.index("--")
        runner_args, script_args = arguments[:separator], arguments[separator + 1:]
    else:
        runner_args, script_args = arguments, []
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog="Script arguments must follow --. The script controls its own outputs; this runner does not save files.",
    )
    parser.add_argument("--blender", help="Executable or macOS .app; overrides BLENDER_BIN and PATH discovery.")
    parser.add_argument("--script", type=existing_file, required=True, help="Python file executed inside Blender.")
    parser.add_argument("--blend", type=existing_file, help="Existing .blend to load before the script.")
    parser.add_argument("--timeout", type=positive_timeout, default=300.0, help="Maximum seconds; default 300. Increase for long renders.")
    parser.add_argument("--dry-run", action="store_true", help="Print the resolved argv as JSON without launching Blender.")
    parser.add_argument("--plan", type=existing_file, help="Required evidence plan for task scripts; the bundled read-only probe is exempt.")
    args = parser.parse_args(runner_args)
    bundled_probe = Path(__file__).resolve().with_name('probe_blender.py')
    if args.script != bundled_probe:
        if args.plan is None:
            parser.error('A task script requires --plan. Read the capability overview, select features, read source and seal an evidence plan first.')
        try:
            from evidence import validate
            validate(args.plan, args.script)
        except (ValueError, KeyError, FileNotFoundError, SyntaxError) as error:
            parser.error(str(error))
    try:
        blender = discover_blender(args.blender)
    except ValueError as error:
        parser.error(str(error))
    command = build_command(blender, args.script, args.blend, script_args)
    if args.dry_run:
        print(json.dumps({"argv": command, "timeout_seconds": args.timeout}, ensure_ascii=False, indent=2))
        return 0
    print("Blender argv: " + json.dumps(command, ensure_ascii=False), file=sys.stderr, flush=True)
    try:
        process = subprocess.Popen(command, start_new_session=(os.name == "posix"))
    except OSError as error:
        print("Could not launch Blender: " + str(error), file=sys.stderr)
        return 2
    try:
        result = process.wait(timeout=args.timeout)
        return 128 - result if result < 0 else result
    except subprocess.TimeoutExpired:
        stop_process(process)
        print("Blender exceeded timeout ({} seconds).".format(args.timeout), file=sys.stderr)
        return 124
    except KeyboardInterrupt:
        stop_process(process)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
