import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import twinkle_install as installer

INI = b"[Default]\r\nAreaCount=1\r\n\r\n[Area0]\r\nName=Ini3\r\nCount=1\r\nIP_1=example.invalid\r\nPort_1=9999\r\n"


class InstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source, self.store = self.root / "pristine", self.root / "managed"
        (self.source / "Res/Stage").mkdir(parents=True)
        (self.source / "Res/Stage/Info.res").write_bytes(b"stock-info")
        (self.source / "ServerInfo.ini").write_bytes(INI)
        (self.source / "keep.txt").write_bytes(b"preserved")
        self.before = installer.tree_hashes(self.source)
        self.bundle = self.root / "export.zip"
        self.package({"Res/Stage/Info.res": b"new-info", "Res/StageObj/Oktoberfest.res": b"new-models", "Res/Collision.res": b"new-collision"})

    def package(self, members):
        with zipfile.ZipFile(self.bundle, "w") as archive:
            for name, raw in members.items(): archive.writestr(name, raw)

    def install(self):
        return installer.install(self.source, self.store, self.bundle, self.before)

    def test_full_dependency_copy_local_endpoint_and_durable_restore(self):
        receipt = self.install()
        client = Path(receipt["clientPath"])
        self.assertEqual(installer.tree_hashes(client), receipt["afterHashes"])
        self.assertEqual((client / "Res/Collision.res").read_bytes(), b"new-collision")
        endpoint = (client / "ServerInfo.ini").read_bytes()
        self.assertIn(b"IP_1=127.0.0.1\r\nPort_1=5894\r\n", endpoint)
        self.assertNotIn(b"\n", endpoint.replace(b"\r\n", b""))
        self.assertEqual(installer.tree_hashes(self.source), self.before)
        self.assertFalse(receipt["executablePresent"])
        self.assertFalse(receipt["nativeRuntimeVerified"])
        restored = installer.restore(self.source, self.store)
        self.assertEqual(installer.tree_hashes(Path(restored["clientPath"])), receipt["beforeHashes"])
        self.assertFalse((Path(restored["clientPath"]) / "Res/Collision.res").exists())
        self.assertEqual(installer.restore(self.source, self.store), restored)
        self.assertEqual(installer.status(self.source, self.store), restored)

    def test_failed_second_install_never_changes_active_tree_or_pointer(self):
        first = self.install()
        pointer = (self.store / "active.json").read_bytes()
        original = Path.write_bytes
        def fail_collision(path, data):
            if path.name == "Collision.res": raise OSError("injected disk failure")
            return original(path, data)
        with patch.object(Path, "write_bytes", fail_collision), self.assertRaises(OSError): self.install()
        self.assertEqual((self.store / "active.json").read_bytes(), pointer)
        self.assertEqual(installer.tree_hashes(Path(first["clientPath"])), first["afterHashes"])
        self.assertEqual(installer.tree_hashes(self.source), self.before)

    def test_publication_failure_leaves_old_copy_selected(self):
        first = self.install()
        original = installer.atomic_json
        def fail_pointer(path, value):
            if path.name == "active.json": raise OSError("injected publication failure")
            return original(path, value)
        with patch.object(installer, "atomic_json", fail_pointer), self.assertRaises(OSError): self.install()
        self.assertEqual(installer.status(self.source, self.store), first)

    def test_source_changes_fail_before_apply(self):
        (self.source / "keep.txt").write_text("changed externally")
        with self.assertRaisesRegex(ValueError, "source changed"): self.install()
        self.assertFalse((self.store / "active.json").exists())

    def test_missing_or_ambiguous_endpoint_never_publishes(self):
        for ini in (b"[Other]\nIP_1=example.invalid\n", INI+b"[Area1]\nIP_1=example.invalid\n", INI.replace(b"Count=1", b"Count=2")):
            (self.source / "ServerInfo.ini").write_bytes(ini)
            self.before = installer.tree_hashes(self.source)
            with self.assertRaises(ValueError): self.install()
            self.assertFalse((self.store / "active.json").exists())

    def test_path_traversal_duplicate_and_nonres_rejected(self):
        for name in ("Res/../escape.res", "Res/x\\y.res", "Res/C:/evil.res", "/Res/a.res", "Res/a.exe", "unexpected.txt", "res/stage/Info.res"):
            self.package({"Res/Stage/Info.res": b"info", name: b"bad"})
            with self.assertRaises(ValueError): self.install()
        self.package({"Res/Stage/Info.res": b"a", "Res/Stage/INFO.res": b"b"})
        with self.assertRaises(ValueError): self.install()

    def test_managed_root_alias_overlap_and_unmanaged_directory_rejected(self):
        for store in (self.source, self.source / "nested", self.root):
            with self.assertRaises(ValueError): installer.install(self.source, store, self.bundle, self.before)
        self.store.symlink_to(self.source, target_is_directory=True)
        with self.assertRaises(ValueError): self.install()
        self.store.unlink()
        self.store.mkdir()
        (self.store / "precious").write_text("keep")
        with self.assertRaises(ValueError): self.install()
        self.assertEqual((self.store / "precious").read_text(), "keep")

    def test_backup_corruption_or_alias_prevents_restore(self):
        receipt = self.install()
        backup_file = Path(receipt["backupPath"]) / "keep.txt"
        backup_file.write_text("corrupt")
        with self.assertRaises(ValueError): installer.restore(self.source, self.store)
        backup_file.unlink()
        backup_file.symlink_to(self.source / "keep.txt")
        with self.assertRaises(ValueError): installer.restore(self.source, self.store)
        self.assertFalse(installer.status(self.source, self.store)["restored"])

    def test_lock_rejects_concurrent_install(self):
        with installer.locked_store(self.source, self.store):
            with self.assertRaisesRegex(ValueError, "operation is running"): self.install()

    def test_reinstall_starts_from_pristine_not_previous_overrides(self):
        first = self.install()
        self.package({"Res/Stage/Info.res": b"second-map"})
        second = self.install()
        self.assertNotEqual(first["clientPath"], second["clientPath"])
        self.assertFalse((Path(second["clientPath"]) / "Res/Collision.res").exists())
        self.assertTrue((Path(first["clientPath"]) / "Res/Collision.res").exists())
        self.assertEqual(installer.tree_hashes(self.source), self.before)


if __name__ == "__main__": unittest.main()
