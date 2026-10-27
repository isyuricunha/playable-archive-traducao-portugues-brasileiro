import contextlib
import copy
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import zipfile

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import native
import storage
from native import Invalid, DEPLOY
from storage import Store, canonical, digest, durable, json_bytes, sha
from toolkit import Project, MANIFEST, BUILD, WORK, FONT_DEPLOY, parse_source
import consent
import release

SOURCE = Path(__file__).resolve().parents[2]
CODE = ["native.py", "storage.py", "toolkit.py", "release.py", "consent.py", "font_patch.py"]


def receipts(root):
    files = [WORK+v for v in CODE]+[WORK+"engine-shapes.json", ".gitattributes", WORK+"tests/fixtures/minimal.assets"]
    for rel in [WORK+"config.json", WORK+"vendor/courier-prime/CourierPrime-Regular.ttf", WORK+"vendor/courier-prime/OFL.txt"]:
        if (root/rel).exists():
            files.append(rel)
    spec = {"schema": 1, "files": {f: {"mode": "binary" if f.endswith((".assets", ".ttf")) else "git-lf",
            "sha256": sha((root/f).read_bytes() if f.endswith((".assets", ".ttf")) else canonical((root/f).read_bytes()))} for f in files}}
    durable(root/(WORK+"toolchain.json"), json_bytes(spec))
    durable(root/(WORK+"runtime-support.json"), json_bytes({"schema": 1, "python": ">=3.10", "dependencies": [],
             "expected_handoff": "Ubuntu 24.04 LTS ARM64", "arm64_live_verified": False,
             "toolchain_sha256": sha(canonical((root/(WORK+"toolchain.json")).read_bytes()))}))


def setup_root(root):
    for f in CODE+["engine-shapes.json"]:
        durable(root/(WORK+f), (SOURCE/(WORK+f)).read_bytes())
    durable(root/".gitattributes", (SOURCE/".gitattributes").read_bytes())
    durable(root/(WORK+"tests/fixtures/minimal.assets"), native.fixture())
    for rel in ["README.md", WORK+"README.md"]:
        durable(root/rel, b"<!-- release-state: unavailable -->\nEm preparacao.\n")
    receipts(root)


def enable_font(root):
    from font_patch import INPUT_SHA256
    original = SOURCE/"EN"/FONT_DEPLOY
    if not original.is_file() or digest(original) != INPUT_SHA256:
        raise unittest.SkipTest("Verified original sharedassets0.assets is unavailable")
    durable(root/("EN/"+FONT_DEPLOY), original.read_bytes())
    for name in ["CourierPrime-Regular.ttf", "OFL.txt"]:
        rel = WORK+"vendor/courier-prime/"+name
        durable(root/rel, (SOURCE/rel).read_bytes())
    durable(root/(WORK+"config.json"), json_bytes({"font_support": "courier-prime-v1"}))
    receipts(root)


def payload(project, indexes=None, target=None):
    m, rows, _, _ = project.load()
    selected = rows if indexes is None else [rows[i] for i in indexes]
    return {"generation": m["generation"], "expected_count": len(selected),
            "updates": [{"id": r["id"], "source_fingerprint": r["source_fingerprint"],
                         "PTBR": target if target is not None else r["EN"]} for r in selected]}


class ProjectTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        setup_root(self.root)
        self.project = Project(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def init(self, count=3, batch=500):
        with self.project.store.lock():
            return self.project.sync(native.fixture(count=count), initial=True, batch_size=batch)

    def apply(self, data, **kwargs):
        with self.project.store.lock():
            return self.project.apply(data, **kwargs)

    def complete(self):
        self.apply(payload(self.project))
        with self.project.store.lock():
            self.project.build()

    def test_native_exact_and_unicode_repacking(self):
        data = native.fixture(count=5)
        records, _ = native.extract(data)
        for r in records:
            r["PTBR"] = r["EN"]
        self.assertEqual(native.build(data, records), data)
        for value in ["ç %?", "áãõê %? long", "Synthetic extra text %?"]:
            records[0]["PTBR"] = value
            rebuilt = native.build(data, records)
            self.assertEqual(native.extract(rebuilt)[0][0]["EN"], value)
            self.assertEqual(len(rebuilt) % 4, 0)

    def test_native_corruption_and_unknown_shapes(self):
        data = bytearray(native.fixture())
        for pos in [8, 16, 24]:
            altered = bytearray(data)
            altered[pos] ^= 0xff
            with self.assertRaises(Invalid):
                native.extract(bytes(altered))
        with self.assertRaises(Invalid):
            native.extract(data[:-5])

    def test_batches_default_and_no_output_until_complete(self):
        self.init(1001)
        m, rows, members, _ = self.project.load(deep=True)
        self.assertEqual(len(m["batches"]), 3)
        self.assertEqual([sum(b == v for v in members.values()) for b in m["batches"]], [500, 500, 1])
        self.assertTrue(all(r["PTBR"] == "" for r in rows))
        with self.assertRaisesRegex(Invalid, "INCOMPLETE"):
            self.project.build()
        self.assertFalse((self.root/"PTBR").exists())

    def test_apply_only_dirty_batch_and_idempotence(self):
        self.init(7, batch=2)
        watched = self.root/(WORK+"translations/batch-0004.jsonl")
        before = watched.read_bytes(), watched.stat().st_mtime_ns
        manifest = (self.root/MANIFEST).read_bytes(), (self.root/MANIFEST).stat().st_mtime_ns
        p = payload(self.project, [0], "Synthetic %?")
        self.apply(p)
        self.assertEqual((watched.read_bytes(), watched.stat().st_mtime_ns), before)
        self.assertEqual(((self.root/MANIFEST).read_bytes(), (self.root/MANIFEST).stat().st_mtime_ns), manifest)
        count = self.project.store.stats()["transactions"]
        self.apply(p)
        self.assertEqual(self.project.store.stats()["transactions"], count)
        self.assertFalse((self.root/"PTBR").exists())

    def test_apply_bad_payloads_fail_without_changes(self):
        self.init()
        original = (self.root/(WORK+"translations/batch-0001.jsonl")).read_bytes()
        base = payload(self.project, [0])
        variations = []
        p = copy.deepcopy(base); p["generation"] = "wrong"; variations.append(p)
        p = copy.deepcopy(base); p["expected_count"] = 2; variations.append(p)
        p = copy.deepcopy(base); p["updates"] *= 2; p["expected_count"] = 2; variations.append(p)
        p = copy.deepcopy(base); p["updates"][0]["id"] = "unknown"; variations.append(p)
        p = copy.deepcopy(base); p["updates"][0]["EN"] = "edit"; variations.append(p)
        p = copy.deepcopy(base); p["updates"][0]["source_fingerprint"] = "bad"; variations.append(p)
        for p in variations:
            with self.assertRaises(Invalid):
                self.apply(p)
            self.assertEqual((self.root/(WORK+"translations/batch-0001.jsonl")).read_bytes(), original)

    def test_partial_apply_and_overwrite_protection(self):
        self.init()
        p = payload(self.project, [0, 1])
        p["updates"][1]["PTBR"] = "bad; %?"
        result = self.apply(p, partial=True)
        self.assertEqual((len(result["accepted"]), len(result["rejected"])), (1, 1))
        changed = payload(self.project, [0], "Replacement %?")
        with self.assertRaises(Invalid):
            self.apply(changed)
        self.apply(changed, replace=True)

    def test_syntax_rules_and_original_malformed_markup(self):
        for invalid in ["text", "one %? %?", "two; %?", "two\n %?", "two\x00 %?"]:
            with self.assertRaises(Invalid):
                native.validate_text("One %?", invalid)
        native.validate_text("<b>one</b><br>%+", "<b>Synthetic</b><br>%+")
        with self.assertRaises(Invalid):
            native.validate_text("<b><i>one</i></b>", "<b><i>one</b></i>")
        native.validate_text("<b>one<b>", "<b>Synthetic<b>")

    def test_sync_one_change_history_and_reorder(self):
        self.init(7, batch=2)
        self.apply(payload(self.project))
        source = native.fixture(count=7)
        changed = source.replace(b"key2;Fixture", b"key2;Changed")
        with self.project.store.lock():
            report = self.project.sync(changed)
        self.assertEqual(report["counts"]["modified"], 1)
        self.assertEqual(report["counts"]["preserved_translations"], 6)
        self.assertEqual(self.project.status()["pending"], 1)
        history = list((self.root/(WORK+"history")).glob("*.json"))
        self.assertEqual(len(history), 1)
        self.assertEqual(json.loads(history[0].read_text())[0]["previous"]["PTBR"], "Fixture %?")
        # Rewrite an existing TextAsset with rows reversed, preserving keys.
        ser, tables = native.tables(changed)
        asset = tables["Fixture"]
        script = (asset["lines"][0]+"".join(reversed(asset["lines"][1:]))).encode()
        import struct
        raw = asset["prefix"]+struct.pack("<i", len(script))+script
        raw += b"\0"*(-len(raw) % 4)
        reordered = ser.rewrite({1: raw})
        before_members = self.project.load()[2]
        with self.project.store.lock():
            report = self.project.sync(reordered)
        self.assertEqual(report["counts"]["modified"], 0)
        self.assertGreater(report["counts"]["moved"], 0)
        self.assertEqual(self.project.load()[2], before_members)

    def test_sync_manual_en_overwrite_and_add_remove(self):
        self.init(3, batch=2)
        self.apply(payload(self.project))
        source = native.fixture(count=4)
        (self.root/("EN/"+DEPLOY)).write_bytes(source)
        with self.project.store.lock():
            report = self.project.sync((self.root/("EN/"+DEPLOY)).read_bytes())
        self.assertEqual(report["counts"]["added"], 1)
        self.assertEqual(self.project.status()["completed"], 3)
        with self.project.store.lock():
            report = self.project.sync(native.fixture(count=2))
        self.assertEqual(report["counts"]["removed"], 2)
        self.assertEqual(self.project.status()["completed"], 2)

    def test_sync_noop_dry_run_and_extract_refuses_progress(self):
        self.init()
        snapshots = {p.relative_to(self.root): (digest(p), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(self.project.sync(native.fixture(count=3), dry=True)["status"], "unchanged")
        self.project.sync(native.fixture(count=5), dry=True)
        self.assertEqual(snapshots, {p.relative_to(self.root): (digest(p), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()})
        with self.assertRaisesRegex(Invalid, "EXISTS"):
            self.project.sync(native.fixture(), initial=True)

    def test_mutated_immutable_record_and_source_integrity(self):
        self.init()
        batch = self.root/(WORK+"translations/batch-0001.jsonl")
        raw = batch.read_bytes()
        batch.write_bytes(raw.replace(b'"EN": "Fixture', b'"EN": "Altered'))
        with self.assertRaisesRegex(Invalid, "Immutable"):
            self.project.load()
        batch.write_bytes(raw)
        source = self.root/("EN/"+DEPLOY)
        source.write_bytes(source.read_bytes()[:-1]+b"!")
        with self.assertRaisesRegex(Invalid, "SOURCE_CHANGED"):
            self.project.load(deep=True)

    def test_build_gate_stale_tampering_zip_and_preservation(self):
        self.init()
        self.complete()
        r = self.project.verify_output()
        result = self.project.package()
        with zipfile.ZipFile(result["zip"]) as z:
            self.assertEqual(z.namelist(), [DEPLOY])
            self.assertEqual(sha(z.read(DEPLOY)), r["outputs"][DEPLOY])
        original = (self.root/("PTBR/"+DEPLOY)).read_bytes()
        self.apply(payload(self.project, [0], "Changed %?"), replace=True)
        with self.assertRaisesRegex(Invalid, "INVALID_OUTPUT"):
            self.project.verify_output()
        self.assertEqual((self.root/("PTBR/"+DEPLOY)).read_bytes(), original)
        with self.project.store.lock():
            self.project.sync(native.fixture(text="New text %?", count=3))
            with self.assertRaisesRegex(Invalid, "INCOMPLETE"):
                self.project.build()
        self.assertEqual((self.root/("PTBR/"+DEPLOY)).read_bytes(), original)

    def test_complete_build_includes_tested_font_and_rejects_tampering(self):
        self.init()
        enable_font(self.root)
        self.project = Project(self.root)
        with self.assertRaisesRegex(Invalid, "INCOMPLETE"):
            self.project.build()
        self.assertFalse((self.root/"PTBR").exists())
        self.complete()
        receipt = self.project.verify_output()
        self.assertEqual(set(receipt["outputs"]), {DEPLOY, FONT_DEPLOY})
        from font_patch import INPUT_SHA256, OUTPUT_SHA256
        self.assertEqual(receipt["font_dependency"]["source_sha256"], INPUT_SHA256)
        self.assertEqual(receipt["outputs"][FONT_DEPLOY], OUTPUT_SHA256)
        package = self.project.package()
        with zipfile.ZipFile(package["zip"]) as z:
            self.assertEqual(set(z.namelist()), {DEPLOY, FONT_DEPLOY})
            self.assertTrue(all(not name.startswith("PTBR/") for name in z.namelist()))
        font_output = self.root/("PTBR/"+FONT_DEPLOY)
        original = font_output.read_bytes()
        font_output.write_bytes(original[:-1]+bytes([original[-1] ^ 1]))
        with self.assertRaisesRegex(Invalid, "INVALID_OUTPUT"):
            self.project.verify_output()
        font_output.write_bytes(original)
        source = self.root/("EN/"+FONT_DEPLOY)
        old = source.read_bytes()
        source.write_bytes(old[:-1]+bytes([old[-1] ^ 1]))
        with self.assertRaisesRegex(Invalid, "FONT_SOURCE_MISMATCH"):
            self.project.verify_output()
        source.write_bytes(old)
        self.project.verify_output()

    def test_forged_complete_and_extra_output_rejected(self):
        self.init()
        durable(self.root/BUILD, json_bytes({"schema": 1, "complete": True}))
        with self.assertRaises(Invalid):
            self.project.verify_output()
        self.complete()
        durable(self.root/"PTBR/unwanted.txt", b"extra")
        with self.assertRaises(Invalid):
            self.project.verify_output()

    def test_doctor_read_only_lf_nested_hashes_and_tamper(self):
        self.init()
        before = {p: (digest(p), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
        self.assertEqual(self.project.doctor(False)["doctor"], "passed")
        self.assertEqual(before, {p: (digest(p), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()})
        shape = self.root/(WORK+"engine-shapes.json")
        original = shape.read_bytes()
        shape.write_bytes(original.replace(b"\n", b"\r\n"))
        self.project.integrity()
        shape.write_bytes(original.replace(b'"6000"', b'"6001"'))
        with self.assertRaisesRegex(Invalid, "CHECKSUM_MISMATCH"):
            self.project.integrity()
        shape.write_bytes(original)
        fixture = self.root/(WORK+"tests/fixtures/minimal.assets")
        fixture.write_bytes(fixture.read_bytes()+b"tamper")
        with self.assertRaisesRegex(Invalid, "CHECKSUM_MISMATCH"):
            self.project.integrity()

    def test_doctor_diagnostics(self):
        with patch("toolkit.platform.system", return_value="Windows"):
            with self.assertRaisesRegex(Invalid, "UNSUPPORTED_ARCHITECTURE"):
                self.project.doctor()
        with patch("toolkit.sys.version_info", (3, 9)):
            with self.assertRaisesRegex(Invalid, "MISSING_RUNTIME"):
                self.project.doctor(False)
        with patch("toolkit.native.build", side_effect=Invalid("bad fixture")):
            with self.assertRaisesRegex(Invalid, "MALFORMED_TEST_DATA"):
                self.project.doctor(False)

    def test_git_index_crlf_canonical_and_binary_preservation(self):
        subprocess.run(["git", "init", "-q", str(self.root)], check=True)
        file = self.root/(WORK+"engine-shapes.json")
        original = file.read_bytes()
        file.write_bytes(original.replace(b"\n", b"\r\n"))
        subprocess.run(["git", "-C", str(self.root), "add", ".gitattributes", WORK+"engine-shapes.json", WORK+"tests/fixtures/minimal.assets"], check=True, capture_output=True)
        blob = subprocess.check_output(["git", "-C", str(self.root), "show", ":"+WORK+"engine-shapes.json"])
        binary = subprocess.check_output(["git", "-C", str(self.root), "show", ":"+WORK+"tests/fixtures/minimal.assets"])
        self.assertEqual(blob, canonical(original))
        self.assertEqual(binary, (self.root/(WORK+"tests/fixtures/minimal.assets")).read_bytes())
        file.write_bytes(blob)
        self.project.integrity()

    def test_update_with_retained_known_font_patch(self):
        from toolkit import validate_game
        dependency = {"source_sha256": sha(b"original font"), "output_sha256": sha(b"patched font")}
        durable(self.root/("EN/"+FONT_DEPLOY), b"original font")
        with tempfile.TemporaryDirectory(prefix="Updated game ") as t:
            game = Path(t)
            durable(game/"Playable Archive_Data/app.info", b"DarkStone Digital\nPlayable Archive\n")
            durable(game/DEPLOY, native.fixture())
            durable(game/FONT_DEPLOY, b"patched font")
            with patch.object(self.project, "font_dependency", return_value=dependency):
                data, _ = validate_game(self.project, game)
                self.assertEqual(data, native.fixture())
                self.assertEqual((self.root/("EN/"+FONT_DEPLOY)).read_bytes(), b"original font")
                durable(game/FONT_DEPLOY, b"unknown font")
                with self.assertRaisesRegex(Invalid, "FONT_SOURCE_MISMATCH"):
                    validate_game(self.project, game)
                durable(game/FONT_DEPLOY, b"patched font")
                durable(self.root/("EN/"+FONT_DEPLOY), b"corrupted original")
                with self.assertRaisesRegex(Invalid, "FONT_SOURCE_MISMATCH"):
                    validate_game(self.project, game)

    def test_install_validation_and_explicit_provenance(self):
        with tempfile.TemporaryDirectory(prefix="Game with spaces ") as t:
            game = Path(t)
            durable(game/"Playable Archive_Data/app.info", b"DarkStone Digital\nPlayable Archive\n")
            durable(game/DEPLOY, native.fixture())
            from toolkit import validate_game
            before = (game/DEPLOY).read_bytes()
            data, prov = validate_game(self.project, game)
            self.assertEqual(data, before)
            self.assertEqual(prov["kind"], "identified-installation")
            with self.project.store.lock():
                self.project.sync(data, provenance=prov)
            self.assertEqual((game/DEPLOY).read_bytes(), before)
            (game/"Playable Archive_Data/app.info").write_text("wrong game")
            with self.assertRaisesRegex(Invalid, "WRONG_GAME"):
                validate_game(self.project, game)
        from toolkit import discover_game, validate_game
        with self.assertRaisesRegex(Invalid, "OVERLAP"):
            validate_game(self.project, self.root)
        with patch("toolkit.validate_game", side_effect=FileNotFoundError("remote installation unavailable")), patch("toolkit.Path.home", return_value=self.root/"remote-home"):
            with self.assertRaisesRegex(Invalid, "AUTODISCOVERY"):
                discover_game(self.project)

    def test_cli_import_dry_run_noop_and_flag_guards(self):
        with tempfile.TemporaryDirectory(prefix="Game cli space ") as t:
            game = Path(t)
            durable(game/"Playable Archive_Data/app.info", b"DarkStone Digital\nPlayable Archive\n")
            durable(game/DEPLOY, native.fixture())
            command = [sys.executable, "-B", str(self.root/(WORK+"toolkit.py")), "update-sources", "--game-root", str(game)]
            before = {p.relative_to(self.root): digest(p) for p in self.root.rglob("*") if p.is_file()}
            dry = subprocess.run(command+["--dry-run"], capture_output=True)
            self.assertEqual(dry.returncode, 0, dry.stderr)
            self.assertEqual(before, {p.relative_to(self.root): digest(p) for p in self.root.rglob("*") if p.is_file()})
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            files = {p: (digest(p), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
            noop = subprocess.run(command, capture_output=True)
            self.assertEqual(noop.returncode, 0, noop.stderr)
            self.assertEqual(json.loads(noop.stdout)["status"], "unchanged")
            self.assertEqual(files, {p: (digest(p), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()})
            bad = subprocess.run([sys.executable, "-B", str(self.root/(WORK+"toolkit.py")), "build", "--dry-run"], capture_output=True)
            self.assertEqual(bad.returncode, 2)
            self.assertFalse((self.root/"PTBR").exists())


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.s = Store(self.root, count=3, budget=1024*1024)
        durable(self.root/"one.json", b"old-one")
        durable(self.root/"two.json", b"old-two")

    def tearDown(self):
        self.temp.cleanup()

    def test_interrupted_promotion_recover_and_gc_protection(self):
        with self.s.lock():
            with self.assertRaisesRegex(Invalid, "SIMULATED_CRASH"):
                self.s.commit({"one.json": b"new-one", "two.json": b"new-two"}, crash_after=1)
            with self.assertRaisesRegex(Invalid, "RECOVERY_REQUIRED"):
                self.s.gc()
            with self.assertRaisesRegex(Invalid, "RECOVERY_REQUIRED"):
                self.s.commit({"one.json": b"other"})
            self.s.recover()
        self.assertEqual((self.root/"one.json").read_bytes(), b"old-one")
        self.assertEqual((self.root/"two.json").read_bytes(), b"old-two")

    def test_staging_crash_recover(self):
        real = storage.durable
        def fail(path, data):
            if path.name.startswith("after-"):
                raise OSError("staging crash")
            real(path, data)
        with self.s.lock():
            with patch("storage.durable", side_effect=fail):
                with self.assertRaisesRegex(OSError, "staging crash"):
                    self.s.commit({"one.json": b"changed"})
            with self.assertRaises(Invalid):
                self.s.gc()
            self.s.recover()
        self.assertEqual((self.root/"one.json").read_bytes(), b"old-one")
        self.assertEqual(self.s.stats()["transactions"], 0)

    def test_conflict_preserves_external_edit_and_rollback(self):
        with self.s.lock():
            with self.assertRaisesRegex(Invalid, "CONCURRENT_EDIT"):
                self.s.commit({"one.json": b"changed"}, {"one.json": "wrong"})
            self.s.commit({"one.json": b"changed"})
            self.s.rollback()
        self.assertEqual((self.root/"one.json").read_bytes(), b"old-one")

    def test_recovery_never_overwrites_intervening_editor(self):
        with self.s.lock():
            with self.assertRaises(Invalid):
                self.s.commit({"one.json": b"changed"}, crash_after=1)
            (self.root/"one.json").write_bytes(b"editor text")
            with self.assertRaisesRegex(Invalid, "CONCURRENT_EDIT"):
                self.s.recover()
        self.assertEqual((self.root/"one.json").read_bytes(), b"editor text")

    def test_retention_budget_gc_dry_and_corrupt_receipt(self):
        with self.s.lock():
            for i in range(9):
                self.s.commit({"one.json": str(i).encode()})
            stats = self.s.stats()
            self.assertLessEqual(stats["transactions"], 3)
            self.assertLessEqual(stats["bytes"], self.s.budget)
            self.s.count = 1
            before = {p: (digest(p), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()}
            self.assertEqual(len(self.s.gc(True)), 2)
            self.assertEqual(before, {p: (digest(p), p.stat().st_mtime_ns) for p in self.root.rglob("*") if p.is_file()})
            self.s.gc()
            self.assertEqual(self.s.stats()["transactions"], 1)
            folder = next(self.s.txns.iterdir())
            (folder/"receipt.json").write_bytes(b"corrupt")
            with self.assertRaisesRegex(Invalid, "CORRUPT_RECEIPT"):
                self.s.gc()

    def test_insufficient_headroom_and_budget_no_live_mutation(self):
        with self.s.lock():
            with patch("storage.shutil.disk_usage", return_value=shutil._ntuple_diskusage(100, 99, 1)):
                with self.assertRaisesRegex(Invalid, "INSUFFICIENT_SPACE"):
                    self.s.commit({"one.json": b"changed"})
            with self.assertRaisesRegex(Invalid, "RETENTION_BUDGET"):
                self.s.commit({"one.json": b"x"*(2*1024*1024)})
        self.assertEqual((self.root/"one.json").read_bytes(), b"old-one")

    def test_paths_lock_and_symlink_escape(self):
        for rel in ["../outside", "one/../../out", "C:/out", "one\\out", "/absolute"]:
            with self.assertRaises(Invalid):
                storage.safe(self.root, rel)
        with self.s.lock():
            with self.assertRaisesRegex(Invalid, "LOCKED"):
                with self.s.lock():
                    pass
        try:
            (self.root/"link").symlink_to(self.root.parent, target_is_directory=True)
        except OSError:
            return  # Windows can require elevated symlink privileges.
        with self.assertRaisesRegex(Invalid, "UNSAFE_PATH"):
            storage.safe(self.root, "link/out")


class StressTests(ProjectTests):
    # Inherit no project tests: own subclass namespace is filtered below.
    def test_500_small_applies_101_batches_bounded(self):
        self.init(1001, batch=10)
        manifest, rows, _, _ = self.project.load()
        untouched = self.root/(WORK+"translations/batch-0101.jsonl")
        before = untouched.read_bytes(), untouched.stat().st_mtime_ns
        generation = manifest["generation"]
        for i in range(500):
            row = rows[i]
            p = {"generation": generation, "expected_count": 1, "updates": [{"id": row["id"],
                 "source_fingerprint": row["source_fingerprint"], "PTBR": row["EN"]}]}
            self.apply(p)
            if (i+1) % 100 == 0:
                print(f"STRESS progress: {i+1}/500", flush=True)
        stats = self.project.status()
        self.assertEqual((stats["batches"], stats["completed"]), (101, 500))
        self.assertLessEqual(stats["storage"]["completed"], 10)
        self.assertLess(stats["storage"]["bytes"], 2*1024*1024)
        self.assertEqual((untouched.read_bytes(), untouched.stat().st_mtime_ns), before)
        receipts_ = self.project.store.receipts()
        self.assertTrue(all(len(r[1]["files"]) == 1 for r in receipts_))
        self.assertFalse((self.root/"PTBR").exists())
        print("STRESS: 500 applies / 101 batches; retained bytes", stats["storage"]["bytes"])


# Avoid running inherited project tests twice during discovery.
for _name in list(ProjectTests.__dict__):
    if _name.startswith("test_"):
        setattr(StressTests, _name, None)


class ConsentTests(unittest.TestCase):
    def test_affirmative_scope_and_missing_consent(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            pr = {"number": 10, "pull_request": {"body": "", "user": {"login": "volunteer"}, "html_url": "https://github.com/example/project/pull/10"}}
            with self.assertRaisesRegex(Invalid, "CONSENT_MISSING"):
                consent.check(root, pr)
            pr["pull_request"]["body"] = "- [x] "+consent.ATTESTATION
            record = {"identity": "volunteer", "pull_request": pr["pull_request"]["html_url"],
                      "scope": "original contributions in this pull request", "permission": "CC-BY-NC-SA-4.0 + official-game-commercial-integration", "affirmative": True}
            durable(root/(WORK+"contributor-consents/PR-10.json"), json_bytes(record))
            self.assertEqual(consent.check(root, pr)["consent"], "recorded")
            record["affirmative"] = False
            durable(root/(WORK+"contributor-consents/PR-10.json"), json_bytes(record))
            with self.assertRaisesRegex(Invalid, "CONSENT_SCOPE"):
                consent.check(root, pr)

    def test_official_license_and_initial_public_documents(self):
        license_text = (SOURCE/"LICENSE").read_text(encoding="utf-8")
        self.assertGreater(len(license_text), 18000)
        self.assertIn("Attribution-NonCommercial-ShareAlike 4.0 International", license_text)
        for section in ["Section 1", "Section 8"]:
            self.assertIn(section, license_text)
        for rel in ["LICENSE", "GAME-DEVELOPER-PERMISSION.md", "CONTRIBUTING.md"]:
            self.assertIn(rel, (SOURCE/"README.md").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
