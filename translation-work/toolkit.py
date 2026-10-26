#!/usr/bin/env python3
"""Playable Archive PT-BR engineering CLI; never performs translation."""
from __future__ import annotations

import argparse
import collections
import json
import os
from pathlib import Path
import platform
import re
import sys
sys.dont_write_bytecode = True
import zipfile

import native
from native import Invalid, DEPLOY
from storage import Store, canonical, digest, json_bytes, read_json, safe, sha

WORK = "translation-work/"
MANIFEST = WORK+"translations/manifest.json"
BUILD = WORK+"build-manifest.json"
REPORT = WORK+"reports/sync-latest.json"
SCHEMA = 1


def lines_bytes(rows):
    return b"".join((json.dumps(r, ensure_ascii=False, sort_keys=True)+"\n").encode("utf-8") for r in rows)


def source_fingerprint(record):
    return sha(json_bytes({k: record[k] for k in ["source_file", "table", "key", "EN", "original_languages"]}))


def parse_source(data):
    rows, profile = native.extract(data)
    for r in rows:
        r["source_fingerprint"] = source_fingerprint(r)
    return rows, profile


class Project:
    def __init__(self, root):
        self.root = Path(root).resolve()
        config_path = safe(self.root, WORK+"config.json")
        self.config = read_json(config_path) if config_path.exists() else {}
        self.store = Store(self.root, **self.config.get("retention", {}))

    def path(self, rel):
        return safe(self.root, rel)

    def integrity(self):
        runtime = read_json(self.path(WORK+"runtime-support.json"))
        toolchain = self.path(WORK+"toolchain.json")
        if sha(canonical(toolchain.read_bytes())) != runtime["toolchain_sha256"]:
            raise Invalid("CHECKSUM_MISMATCH: toolchain.json (Git LF bytes)")
        spec = read_json(toolchain)
        for rel, expected in spec["files"].items():
            raw = self.path(rel).read_bytes()
            if expected["mode"] == "git-lf":
                raw = canonical(raw)
            elif expected["mode"] != "binary":
                raise Invalid("Invalid integrity mode")
            if sha(raw) != expected["sha256"]:
                raise Invalid(f"CHECKSUM_MISMATCH: {rel}; restore reviewed tooling, do not rebaseline blindly")
        if sys.version_info < (3, 10):
            raise Invalid("MISSING_RUNTIME: Python >= 3.10 required")
        return runtime

    def load(self, deep=False):
        self.store.clean_state()
        manifest = read_json(self.path(MANIFEST))
        if manifest.get("schema") != SCHEMA or manifest.get("deployment") != DEPLOY:
            raise Invalid("Unsupported manifest schema/deployment")
        batches = manifest["batches"]
        if (len(set(batches)) != len(batches) or
                any(not re.fullmatch(r"batch-\d{4,}\.jsonl", v) for v in batches)):
            raise Invalid("Invalid/duplicate batch inventory")
        actual = sorted(p.name for p in self.path(WORK+"translations").glob("batch-*.jsonl"))
        if sorted(batches) != actual:
            raise Invalid("Batch inventory differs from manifest")
        records, membership, expected = [], {}, {MANIFEST: digest(self.path(MANIFEST))}
        for batch in batches:
            rel = WORK+"translations/"+batch
            raw = self.path(rel).read_bytes()
            expected[rel] = sha(raw)
            parsed = [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]
            if len(parsed) > manifest["batch_size"]:
                raise Invalid(f"Batch exceeds cap: {batch}")
            for row in parsed:
                if row["id"] in membership:
                    raise Invalid(f"Duplicate ID: {row['id']}")
                membership[row["id"]] = batch
            records.extend(parsed)
        catalog = manifest["catalog"]
        base = {r["id"]: r for r in catalog}
        if len(base) != len(catalog) or len(records) != manifest["entries"] or set(membership) != set(base):
            raise Invalid("Record/catalog count or identity mismatch")
        for r in records:
            if set(r) != set(base[r["id"]]) or any(r[k] != base[r["id"]][k] for k in r if k != "PTBR"):
                raise Invalid(f"Immutable source field changed: {r['id']}")
            if not isinstance(r["PTBR"], str):
                raise Invalid("PTBR must be a string")
            if r["source_fingerprint"] != source_fingerprint(r):
                raise Invalid("Record fingerprint mismatch")
            if r["PTBR"]:
                native.validate_text(r["EN"], r["PTBR"])
        source_rel = "EN/"+DEPLOY
        expected[source_rel] = digest(self.path(source_rel))
        if deep:
            if expected[source_rel] != manifest["source_sha256"]:
                raise Invalid("SOURCE_CHANGED: run sync to accept and diff the candidate EN")
            rows, info = parse_source(self.path(source_rel).read_bytes())
            if rows != catalog or info != manifest["profile"]:
                raise Invalid("Native source mapping differs from accepted catalog")
        return manifest, records, membership, expected

    def translation_hash(self, manifest):
        return sha(json_bytes({b: sha(canonical(self.path(WORK+"translations/"+b).read_bytes()))
                               for b in manifest["batches"]}))

    def status(self):
        storage = self.store.stats()
        if storage["protected"]:
            return {"recovery_required": True, "next": "recover", "storage": storage}
        manifest, rows, _, _ = self.load()
        complete = sum(bool(r["PTBR"].strip()) for r in rows)
        output = "absent"
        if self.path(BUILD).exists() or self.path("PTBR").exists():
            try:
                self.verify_output()
                output = "verified"
            except (Invalid, OSError, KeyError, ValueError):
                output = "stale-or-invalid"
        return {"game": "Playable Archive", "generation": manifest["generation"],
                "entries": len(rows), "completed": complete, "pending": len(rows)-complete,
                "batches": len(manifest["batches"]), "PTBR": output,
                "source_changed": digest(self.path("EN/"+DEPLOY)) != manifest["source_sha256"],
                "next": next((r["id"] for r in rows if not r["PTBR"]), None),
                "storage": self.store.stats()}

    def sync(self, data, *, initial=False, dry=False, batch_size=500, provenance=None):
        self.integrity()
        candidate, profile = parse_source(data)
        expected = {}
        previous, oldrows, members = None, [], {}
        if self.path(MANIFEST).exists():
            if initial:
                raise Invalid("EXISTS: extract refuses to overwrite progress; use sync")
            previous, oldrows, members, expected = self.load()
            if set(previous["profile"]["tables"])-set(profile["tables"]):
                raise Invalid("INCOMPLETE_SOURCE: a localization table disappeared; explicit adapter review required")
            batch_size = previous["batch_size"]
            # Known complete localized outputs must never become English inputs.
            if self.path(BUILD).exists() and sha(data) in read_json(self.path(BUILD)).get("outputs", {}).values():
                raise Invalid("TRANSLATED_SOURCE: candidate is a known PTBR build")
        elif not initial:
            initial = True
        if not 1 <= batch_size <= 500:
            raise Invalid("Batch size must be between 1 and 500")
        old = {r["id"]: r for r in oldrows}
        report = {"previous_generation": previous["generation"] if previous else None,
                  "generation": sha(data), "resources": {"added": [DEPLOY] if not previous else [],
                  "modified": [DEPLOY] if previous and sha(data) != previous["source_sha256"] else [], "removed": []},
                  "counts": dict.fromkeys(["added", "modified", "removed", "moved", "unchanged", "preserved_translations"], 0),
                  "changes": [], "affected_batches": [], "validation": "passed",
                  "warnings": [], "next": "Ella: inspect changes and translate only pending entries; build only when complete."}
        batches = {b: [] for b in previous["batches"]} if previous else {"batch-0001.jsonl": []}
        history = []
        for row in candidate:
            prior = old.pop(row["id"], None)
            kind = "added"
            if prior:
                if row["source_fingerprint"] == prior["source_fingerprint"]:
                    row["PTBR"] = prior["PTBR"]
                    kind = "moved" if (row["row"], row["path_id"]) != (prior["row"], prior["path_id"]) else "unchanged"
                    report["counts"]["preserved_translations"] += bool(row["PTBR"])
                else:
                    kind = "modified"
                    history.append({"generation": report["generation"], "classification": kind, "previous": prior})
                batch = members[row["id"]]
            else:
                batch = list(batches)[-1]
                # Include not-yet-visited retained rows when assessing capacity.
                reserved = sum(1 for r in oldrows if members[r["id"]] == batch and r["id"] in old)
                if len(batches[batch])+reserved >= batch_size:
                    batch = f"batch-{max(int(b[6:-6]) for b in batches)+1:04d}.jsonl"
                    batches[batch] = []
            batches[batch].append(row)
            report["counts"][kind] += 1
            if kind != "unchanged":
                report["changes"].append({"classification": kind, "id": row["id"], "source_file": DEPLOY,
                                          "batch": batch, "previous": prior, "current": row})
        for prior in old.values():
            report["counts"]["removed"] += 1
            change = {"generation": report["generation"], "classification": "removed", "previous": prior}
            history.append(change)
            report["changes"].append({**change, "id": prior["id"], "current": None,
                                      "source_file": DEPLOY, "batch": members[prior["id"]]})
        # Preserve order/bytes of existing batches whenever membership is stable;
        # native reconstruction uses row locators rather than physical JSONL order.
        old_order = {r["id"]: i for i, r in enumerate(oldrows)}
        candidate_order = {r["id"]: i for i, r in enumerate(candidate)}
        for values in batches.values():
            values.sort(key=lambda r: old_order.get(r["id"], len(oldrows)+candidate_order[r["id"]]))
        catalog = [{**r, "PTBR": ""} for r in candidate]
        manifest = {"schema": SCHEMA, "game": "Playable Archive", "deployment": DEPLOY,
                    "source_sha256": sha(data), "generation": sha(data), "entries": len(candidate),
                    "batch_size": batch_size, "batches": list(batches), "profile": profile,
                    "provenance": provenance or (previous or {}).get("provenance", {"kind": "supplied-original"}),
                    "catalog": catalog}
        changes = {"EN/"+DEPLOY: data, MANIFEST: json_bytes(manifest)}
        for batch, values in batches.items():
            rel = WORK+"translations/"+batch
            new = lines_bytes(values)
            # Do not change an unaffected file just because it was authored with
            # another JSON spacing/key order or platform newline convention.
            if self.path(rel).exists():
                current = self.path(rel).read_bytes()
                if [json.loads(v) for v in current.decode("utf-8").splitlines() if v.strip()] == values:
                    new = current
            if digest(self.path(rel)) != sha(new):
                report["affected_batches"].append(batch)
            changes[rel] = new
        report["existing_pending"] = sum(not r["PTBR"] for r in oldrows)
        report["pending"] = sum(not r["PTBR"] for r in candidate)
        unchanged = previous == manifest and all(digest(self.path(k)) == sha(v) for k, v in changes.items())
        report["status"] = "unchanged" if unchanged else "updated"
        if unchanged or dry:
            report["dry_run"] = dry
            return report
        if history:
            changes[WORK+f"history/source-{previous['generation']}-{sha(data)}.json"] = json_bytes(history)
        # Durable catalog/history is versioned; local transaction backups are bounded.
        report["transaction"] = self.store.new_id()
        report["recovery_snapshot"] = WORK+".state/transactions/"+report["transaction"]
        from datetime import datetime, timezone
        report["created_utc"] = datetime.now(timezone.utc).isoformat()
        changes[REPORT] = json_bytes(report)
        changes[WORK+"reports/sync-latest.md"] = ("# Sincronização de fontes\n\n"
            +f"Geração: `{report['generation']}`\n\n"
            +"\n".join(f"- {k}: {v}" for k, v in report["counts"].items())
            +"\n\nConsulte sync-latest.json para IDs, textos anteriores e PT-BR histórico.\n").encode("utf-8")
        if not previous:
            expected.update({k: digest(self.path(k)) for k in changes})
        self.store.commit(changes, expected, "sync", transaction_id=report["transaction"])
        return report

    def apply(self, payload, replace=False, partial=False):
        self.integrity()
        manifest, rows, members, expected = self.load(deep=True)
        if payload.get("generation") != manifest["generation"]:
            raise Invalid("WRONG_GENERATION: payload must match accepted source generation")
        updates = payload.get("updates")
        if not isinstance(updates, list) or len(updates) != payload.get("expected_count"):
            raise Invalid("Payload updates/expected_count mismatch")
        ids = [u.get("id") for u in updates]
        lookup = {r["id"]: r for r in rows}
        if len(ids) != len(set(ids)) or any(i not in lookup for i in ids):
            raise Invalid("Duplicate or unknown payload ID")
        accepted, rejected, changed = [], [], set()
        for update in updates:
            rid = update["id"]
            row = lookup[rid]
            try:
                if set(update) != {"id", "source_fingerprint", "PTBR"} or update["source_fingerprint"] != row["source_fingerprint"]:
                    raise Invalid("Immutable field or source fingerprint mismatch")
                native.validate_text(row["EN"], update["PTBR"])
                if row["PTBR"] and row["PTBR"] != update["PTBR"] and not replace:
                    raise Invalid("Already translated; use --replace after review")
                if row["PTBR"] != update["PTBR"]:
                    row["PTBR"] = update["PTBR"]
                    changed.add(members[rid])
                accepted.append(rid)
            except Invalid as e:
                rejected.append({"id": rid, "error": str(e)})
        if rejected and not partial:
            raise Invalid("No changes applied: "+json.dumps(rejected, ensure_ascii=False))
        changes = {WORK+"translations/"+b: lines_bytes([r for r in rows if members[r["id"]] == b]) for b in changed}
        txid = self.store.commit(changes, expected, "apply")
        return {"accepted": accepted, "rejected": rejected, "changed_batches": sorted(changed), "transaction": txid}

    def build(self):
        self.integrity()
        manifest, rows, _, expected = self.load(deep=True)
        if any(not r["PTBR"].strip() for r in rows):
            raise Invalid("INCOMPLETE: all entries must have reviewed PTBR before build; previous PTBR preserved")
        output = native.build(self.path("EN/"+DEPLOY).read_bytes(), rows)
        receipt = {"schema": SCHEMA, "complete": True, "entries": len(rows), "completed": len(rows),
                   "generation": manifest["generation"], "source_sha256": manifest["source_sha256"],
                   "translations_sha256": self.translation_hash(manifest),
                   "manifest_sha256": sha(canonical(self.path(MANIFEST).read_bytes())),
                   "profile": manifest["profile"], "provenance": manifest["provenance"],
                   "toolchain_sha256": sha(canonical(self.path(WORK+"toolchain.json").read_bytes())),
                   "outputs": {DEPLOY: sha(output)}, "in_game_verified": False}
        changes = {"PTBR/"+DEPLOY: output, BUILD: json_bytes(receipt)}
        # Unexpected output members cannot be silently removed by a build.
        if self.path("PTBR").exists():
            files = self.inventory("PTBR")
            if set(files)-{DEPLOY}:
                raise Invalid("Unexpected PTBR files; inspect before building")
        for rel in changes:
            expected[rel] = digest(self.path(rel))
        return {"transaction": self.store.commit(changes, expected, "build"), "build": receipt}

    def inventory(self, prefix):
        folder = self.path(prefix)
        result = {}
        folded = set()
        for base, dirs, files in os.walk(folder, followlinks=False):
            for name in dirs+files:
                safe(self.root, (Path(base)/name).relative_to(self.root).as_posix())
            for name in files:
                p = Path(base)/name
                rel = p.relative_to(folder).as_posix()
                if rel.casefold() in folded:
                    raise Invalid("Case-folded output collision")
                folded.add(rel.casefold())
                result[rel] = digest(p)
        return result

    def verify_output(self):
        self.integrity()
        manifest, rows, _, _ = self.load()
        receipt = read_json(self.path(BUILD))
        if (receipt.get("schema") != SCHEMA or receipt.get("complete") is not True
                or not rows or any(not r["PTBR"].strip() for r in rows)
                or receipt.get("entries") != len(rows) or receipt.get("completed") != len(rows)
                or receipt.get("generation") != manifest["generation"]
                or receipt.get("source_sha256") != digest(self.path("EN/"+DEPLOY))
                or receipt.get("source_sha256") != manifest["source_sha256"]
                or receipt.get("manifest_sha256") != sha(canonical(self.path(MANIFEST).read_bytes()))
                or receipt.get("translations_sha256") != self.translation_hash(manifest)
                or receipt.get("toolchain_sha256") != sha(canonical(self.path(WORK+"toolchain.json").read_bytes()))
                or receipt.get("profile") != manifest["profile"]
                or receipt.get("provenance") != manifest["provenance"]
                or set(receipt.get("outputs", {})) != {DEPLOY}
                or self.inventory("PTBR") != receipt["outputs"]):
            raise Invalid("INVALID_OUTPUT: incomplete, stale, tampered or inconsistent build")
        return receipt

    def package(self, destination=None):
        receipt = self.verify_output()
        destination = Path(destination) if destination else self.root/"PTBR.zip"
        if destination.resolve().is_relative_to(self.path("PTBR")) or destination.resolve().is_relative_to(self.path("EN")):
            raise Invalid("Package destination may not overlap native trees")
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as z:
            for rel in sorted(receipt["outputs"]):
                info = zipfile.ZipInfo(rel, (2020, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o100644 << 16
                z.writestr(info, self.path("PTBR/"+rel).read_bytes())
        self.verify_zip(destination, receipt)
        return {"zip": str(destination), "sha256": digest(destination), "files": list(receipt["outputs"])}

    @staticmethod
    def verify_zip(path, receipt):
        with zipfile.ZipFile(path) as z:
            if z.testzip() or len(z.namelist()) != len(set(z.namelist())) or set(z.namelist()) != set(receipt["outputs"]):
                raise Invalid("ZIP inventory mismatch or duplicate members")
            for rel, expected in receipt["outputs"].items():
                if sha(z.read(rel)) != expected:
                    raise Invalid("ZIP member checksum mismatch")

    def doctor(self, require_arm64=True):
        self.integrity()
        if require_arm64 and (platform.system() != "Linux" or platform.machine().lower() not in {"aarch64", "arm64"}):
            raise Invalid(f"UNSUPPORTED_ARCHITECTURE: expected Linux ARM64; found {platform.system()} {platform.machine()}")
        try:
            raw = self.path(WORK+"tests/fixtures/minimal.assets").read_bytes()
            rows, _ = parse_source(raw)
            for r in rows:
                r["PTBR"] = r["EN"]
            if native.build(raw, rows) != raw:
                raise Invalid("Fixture no-op differs")
            for r in rows:
                r["PTBR"] = "Synthetic ç ã é %?"
            rewritten = native.build(raw, rows)
            if native.extract(rewritten)[0][0]["EN"] != rows[0]["PTBR"]:
                raise Invalid("Fixture Unicode rebuild failed")
            if self.path(MANIFEST).exists():
                self.load(deep=True)
        except (ValueError, KeyError, OSError) as e:
            raise Invalid(f"MALFORMED_TEST_DATA: {e}")
        return {"doctor": "passed", "system": platform.system(), "architecture": platform.machine(),
                "python": platform.python_version(), "dependencies": "stdlib only",
                "read_only": True, "arm64_execution": require_arm64,
                "in_game_test": "not performed"}


def validate_game(project, root):
    root = Path(root).resolve()
    if root == project.root or root.is_relative_to(project.root) or project.root.is_relative_to(root):
        raise Invalid("OVERLAP: repository and game installation must be separate")
    app = safe(root, "Playable Archive_Data/app.info")
    if app.read_text(encoding="utf-8").splitlines() != ["DarkStone Digital", "Playable Archive"]:
        raise Invalid("WRONG_GAME: app.info differs")
    data = safe(root, DEPLOY).read_bytes()
    parse_source(data)
    provenance = {"kind": "identified-installation", "identity": "DarkStone Digital / Playable Archive"}
    steam = root.parent.parent/"appmanifest_5356470.acf"
    if steam.exists():
        text = steam.read_text(encoding="utf-8")
        fields = dict(re.findall(r'"(appid|buildid|installdir|language)"\s+"([^"]+)"', text))
        if fields.get("appid") != "5356470" or fields.get("installdir") != root.name or fields.get("language", "english") != "english":
            raise Invalid("STEAM_IDENTITY_MISMATCH: appid/install directory/language")
        provenance.update({"kind": "steam-metadata", "appid": 5356470, "buildid": fields["buildid"]})
    if project.path(MANIFEST).exists():
        manifest = read_json(project.path(MANIFEST))
        if (provenance.get("buildid") == manifest.get("provenance", {}).get("buildid")
                and sha(data) != manifest["source_sha256"]):
            raise Invalid("SOURCE_PROVENANCE: same Steam build with different bytes; restore originals via Steam before importing")
    return data, provenance


def discover_game(project):
    candidates = []
    local = project.path(WORK+".state/local-install.json")
    if local.exists():
        candidates.append(Path(read_json(local)["game_root"]))
    libraries = []
    if os.name == "nt":
        for drive in "CDEFGHIJKLMNOPQRSTUVWXYZ":
            libraries.append(Path(drive+":/SteamLibrary"))
        libraries.append(Path(os.environ.get("ProgramFiles(x86)", "C:/Program Files (x86)"))/"Steam")
    else:
        libraries += [Path.home()/".steam/steam", Path.home()/".local/share/Steam"]
    for library in list(libraries):
        vdf = library/"steamapps/libraryfolders.vdf"
        if vdf.is_file():
            for name in re.findall(r'"path"\s+"([^"]+)"', vdf.read_text(encoding="utf-8")):
                libraries.append(Path(name.replace("\\\\", "\\")))
    for library in libraries:
        manifest = library/"steamapps/appmanifest_5356470.acf"
        if manifest.exists():
            text = manifest.read_text(encoding="utf-8")
            match = re.search(r'"installdir"\s+"([^"]+)"', text)
            if match:
                candidates.append(library/"steamapps/common"/match[1])
    valid, errors = {}, []
    for candidate in candidates:
        try:
            data, prov = validate_game(project, candidate)
            valid[str(candidate.resolve())] = (candidate.resolve(), data, prov)
        except (OSError, ValueError, KeyError) as e:
            errors.append(str(e))
    if len(valid) != 1:
        raise Invalid("AUTODISCOVERY: expected one verified installation; use update-sources --game-root \"/path/to/Playable Archive\". "+"; ".join(errors))
    return next(iter(valid.values()))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["extract", "sync", "update-sources", "check", "diff", "status", "resume", "apply", "build", "verify-output", "package", "doctor", "gc", "recover", "rollback", "docs-status"])
    parser.add_argument("--game-root")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--source-file")
    group.add_argument("--source-root")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--payload")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--partial", action="store_true")
    parser.add_argument("--break-lock", action="store_true")
    parser.add_argument("--local", action="store_true", help="doctor: validate locally without requiring Linux ARM64")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    project = Project(Path(__file__).resolve().parent.parent)
    try:
        command = args.command
        source_commands = {"extract", "sync", "update-sources", "diff"}
        if args.dry_run and command not in source_commands | {"gc"}:
            raise Invalid("--dry-run is supported only by extract/sync/update-sources/diff/gc")
        if args.game_root and command not in source_commands:
            raise Invalid("--game-root requires a source command")
        if (args.source_file or args.source_root) and command not in {"extract", "sync", "diff"}:
            raise Invalid("--source-file/--source-root require extract/sync/diff")
        if (args.payload or args.replace or args.partial) and command != "apply":
            raise Invalid("--payload/--replace/--partial require apply")
        if args.local and command != "doctor":
            raise Invalid("--local requires doctor")
        write = command in {"extract", "sync", "update-sources", "apply", "build", "rollback", "recover", "package", "gc"} and not args.dry_run
        if args.break_lock:
            if command != "recover":
                raise Invalid("--break-lock is only valid with recover")
            project.store.break_lock()
        import contextlib
        with project.store.lock() if write else contextlib.nullcontext():
            if command in {"extract", "sync", "update-sources", "diff"}:
                game = None
                provenance = None
                if args.game_root or command == "update-sources":
                    if args.game_root:
                        game = Path(args.game_root).resolve()
                        data, provenance = validate_game(project, game)
                    else:
                        game, data, provenance = discover_game(project)
                elif args.source_file or args.source_root:
                    data = (Path(args.source_file) if args.source_file else safe(Path(args.source_root), DEPLOY)).read_bytes()
                    provenance = {"kind": "supplied-original", "verification": "user supplied; official pristine bytes not independently provable"}
                elif command == "diff" and project.path(REPORT).exists():
                    result = read_json(project.path(REPORT))
                    result["accepted_generation_now"] = read_json(project.path(MANIFEST))["generation"]
                    result["candidate_source_sha256"] = digest(project.path("EN/"+DEPLOY))
                    result["report_matches_current_source"] = result["generation"] == result["candidate_source_sha256"]
                    print(json.dumps(result, ensure_ascii=False, indent=2))
                    return 0
                else:
                    data = project.path("EN/"+DEPLOY).read_bytes()
                result = project.sync(data, initial=command == "extract", dry=args.dry_run or command == "diff", batch_size=args.batch_size, provenance=provenance)
                if game:
                    result["detected_game_root"] = str(game)
                    result["provenance"] = provenance
                if game and write:
                    from storage import durable
                    local_path = project.path(WORK+".state/local-install.json")
                    local_data = json_bytes({"game_root": str(game)})
                    if digest(local_path) != sha(local_data):
                        durable(local_path, local_data)
            elif command in {"status", "resume"}:
                result = project.status()
            elif command == "check":
                project.integrity()
                project.load(deep=True)
                result = project.status()
                result["check"] = "passed"
            elif command == "apply":
                if not args.payload:
                    raise Invalid("apply requires --payload <JSON>")
                result = project.apply(read_json(Path(args.payload)), args.replace, args.partial)
            elif command == "build":
                result = project.build()
            elif command == "verify-output":
                result = project.verify_output()
            elif command == "package":
                result = project.package()
            elif command == "doctor":
                result = project.doctor(not args.local)
            elif command == "gc":
                result = {"dry_run": args.dry_run, "eligible": project.store.gc(args.dry_run)}
            elif command == "recover":
                result = {"restored": project.store.recover()}
            elif command == "rollback":
                result = {"transaction": project.store.rollback()}
            else:
                from release import Client, REPOSITORY, SEMVER, docs_status
                client = Client(os.environ.get("GITHUB_TOKEN", ""))
                published = [r for r in client.releases() if not r.get("draft") and not r.get("prerelease") and SEMVER.fullmatch(r["tag_name"])]
                published.sort(key=lambda r: tuple(map(int, SEMVER.fullmatch(r["tag_name"]).groups())))
                latest = client.request("GET", f"/releases/{published[-1]['id']}") if published else None
                result = docs_status(project, latest)
        displayed = result
        if not args.json and isinstance(result, dict) and "changes" in result:
            displayed = {k: v for k, v in result.items() if k != "changes"}
            displayed["detailed_report"] = REPORT
        print(json.dumps(displayed, ensure_ascii=False, indent=2))
        return 1 if command == "apply" and result["rejected"] else 0
    except (Invalid, OSError, KeyError, TypeError, ValueError) as e:
        print(json.dumps({"error": str(e), "command": args.command}, ensure_ascii=False), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
