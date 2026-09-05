"""Local test copies only. Publish a complete generation with one atomic pointer.

Never update a running client tree in place. The caller launches the returned
clientPath directly, not a launcher. Native acceptance is a separate lab gate.
"""
import configparser
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import uuid
import zipfile


def tree_hashes(root, allow_file_links=False):
    files = {}
    for folder, directories, names in os.walk(root):
        for name in directories:
            if (Path(folder) / name).is_symlink():
                raise ValueError("Client source must not contain directory symlinks")
        for name in sorted(names):
            path = Path(folder) / name
            if not path.is_file() or (path.is_symlink() and not allow_file_links):
                raise ValueError("Client tree contains a non-file entry")
            with path.open("rb") as stream:
                files[path.relative_to(root).as_posix()] = hashlib.file_digest(stream, "sha256").hexdigest()
    return dict(sorted(files.items()))


def local_endpoint(path):
    parser = configparser.ConfigParser(interpolation=None, strict=True)
    parser.optionxform = str
    parser.read_string(path.read_text(encoding="utf-8-sig"))
    if (set(parser.sections()) != {"Default", "Area0"}
            or set(parser["Default"]) != {"AreaCount"}
            or set(parser["Area0"]) != {"Name", "Count", "IP_1", "Port_1"}
            or parser["Default"]["AreaCount"] != "1" or parser["Area0"]["Count"] != "1"
            or parser["Area0"]["Name"] != "Ini3"):
        raise ValueError("Unsupported ServerInfo.ini sections/keys; refusing ambiguous endpoints")
    path.write_bytes(b"[Default]\r\nAreaCount=1\r\n\r\n[Area0]\r\nName=Ini3\r\nCount=1\r\n\r\nIP_1=127.0.0.1\r\nPort_1=5894\r\n")


def roots(source, store):
    source, store = Path(source).resolve(), Path(store).absolute()
    if not source.is_dir() or not (source / "Res").is_dir():
        raise ValueError("Pristine client source is missing Res")
    for path in (store, *store.parents):
        if path.is_symlink():
            raise ValueError("Test store cannot use symlinks")
    store = store.resolve()
    if source == store or source in store.parents or store in source.parents:
        raise ValueError("Test store and pristine client must be separate trees")
    return source, store


@contextmanager
def locked_store(source, store):
    source, store = roots(source, store)
    marker = store / "studio-test-store.json"
    if store.exists() and any(store.iterdir()) and not marker.is_file():
        raise ValueError("Refusing to adopt a nonempty unmanaged directory")
    store.mkdir(parents=True, exist_ok=True)
    if not marker.exists():
        try:
            with marker.open("x") as stream:
                json.dump({"version": 1, "source": str(source)}, stream)
        except FileExistsError:
            pass
    if marker.is_symlink() or json.loads(marker.read_text()) != {"version": 1, "source": str(source)}:
        raise ValueError("Test store belongs to another source")
    lock = store / "operation.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(descriptor, "w") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError("Another test-client operation is running") from None
        yield source, store


def atomic_json(path, value):
    temporary = path.with_name(path.name + "." + uuid.uuid4().hex + ".tmp")
    try:
        with temporary.open("x") as stream:
            json.dump(value, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def active_receipt(store):
    active = store / "active.json"
    if not active.exists():
        return None
    if active.is_symlink():
        raise ValueError("Invalid active pointer")
    pointer = json.loads(active.read_text())
    generation = pointer.get("generation", "")
    if len(generation) != 32 or any(c not in "0123456789abcdef" for c in generation) or pointer.get("copy") not in ("client", "backup"):
        raise ValueError("Invalid test-client generation")
    directory = store / generation
    if directory.is_symlink() or (directory / "receipt.json").is_symlink():
        raise ValueError("Invalid receipt path")
    receipt = json.loads((directory / "receipt.json").read_text())
    if receipt.get("generation") != generation or (directory / pointer["copy"]).is_symlink():
        raise ValueError("Receipt generation mismatch or aliased client")
    receipt.update(clientPath=str(directory / pointer["copy"]), restored=pointer["copy"] == "backup")
    return receipt


def package_files(bundle):
    result = {}
    seen = set()
    with zipfile.ZipFile(bundle) as archive:
        if sum(item.file_size for item in archive.infolist()) > 1024**3:
            raise ValueError("Export exceeds test installer capacity")
        for item in archive.infolist():
            name = item.filename
            if name.casefold() in seen or stat.S_ISLNK(item.external_attr >> 16):
                raise ValueError("Duplicate or symlink package member")
            seen.add(name.casefold())
            if name in {"README.txt", "layout.json", "2_Twinkle_Town.set.txt", "native-export.json"}:
                continue
            parts = name.split("/")
            if (len(parts) < 2 or parts[0] != "Res" or not name.endswith(".res")
                    or any(not p or p in (".", "..") or "\\" in p or ":" in p for p in parts)):
                raise ValueError("Export contains a non-resource or unsafe path")
            raw = archive.read(item)
            result[name] = raw
    if "Res/Stage/Info.res" not in result:
        raise ValueError("Export is missing Info.res")
    return result


def install(source, store, bundle, expected_source):
    with locked_store(source, store) as (source, store):
        if tree_hashes(source, allow_file_links=True) != expected_source:
            raise ValueError("Pristine source changed since export began")
        resources = package_files(bundle)
        generation = uuid.uuid4().hex
        directory = store / generation
        directory.mkdir()
        try:
            backup, client = directory / "backup", directory / "client"
            shutil.copytree(source, backup)
            if tree_hashes(backup) != expected_source:
                raise ValueError("Pristine copy hash mismatch")
            local_endpoint(backup / "ServerInfo.ini")
            before = tree_hashes(backup)
            shutil.copytree(backup, client)
            for name, raw in resources.items():
                destination = client / name
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(raw)
            local_endpoint(client / "ServerInfo.ini")
            after = tree_hashes(client)
            expected = {**before, **{name: hashlib.sha256(raw).hexdigest() for name, raw in resources.items()}}
            if after != dict(sorted(expected.items())) or tree_hashes(source, allow_file_links=True) != expected_source:
                raise ValueError("Source or installed resource verification failed")
            receipt = {"version": 1, "generation": generation, "source": str(source),
                       "sourceHashes": expected_source, "beforeHashes": before, "afterHashes": after,
                       "installed": sorted(resources), "installedPath": str(client), "backupPath": str(backup),
                       "nativeRuntimeVerified": False, "executablePresent": (client / "FantaTennis.exe").is_file(),
                       "endpoint": "127.0.0.1:5894", "launch": "Run FantaTennis.exe directly with clientPath as working directory. Do not run the updater.",
                       "rollback": "Close the test client, then use Restore pristine test copy. This selects the verified local-endpoint backup; it never writes pristine."}
            atomic_json(directory / "receipt.json", receipt)
        except BaseException:
            # The active pointer is published last; partial generations are never selected.
            shutil.rmtree(directory)
            raise
        atomic_json(store / "active.json", {"generation": generation, "copy": "client"})
        return active_receipt(store)


def restore(source, store):
    with locked_store(source, store) as (_, store):
        receipt = active_receipt(store)
        if receipt is None:
            raise ValueError("No test copy to restore")
        backup = store / receipt["generation"] / "backup"
        if backup.is_symlink() or tree_hashes(backup) != receipt["beforeHashes"]:
            raise ValueError("Backup has changed; refusing restore")
        atomic_json(store / "active.json", {"generation": receipt["generation"], "copy": "backup"})
        return active_receipt(store)


def status(source, store):
    source, store = roots(source, store)
    if not store.exists():
        return None
    with locked_store(source, store):
        return active_receipt(store)
