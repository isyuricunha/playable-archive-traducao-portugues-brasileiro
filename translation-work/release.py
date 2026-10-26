"""Verified PTBR GitHub Releases. CI invokes main; tests exercise HTTP paths."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
sys.dont_write_bytecode = True
import time
import urllib.error
import urllib.parse
import urllib.request

from native import Invalid, DEPLOY
from storage import json_bytes, read_json, sha
from toolkit import Project, BUILD, WORK

REPOSITORY = "isyuricunha/playable-archive-traducao-portugues-brasileiro"
SEMVER = re.compile(r"v(\d+)\.(\d+)\.(\d+)$")


def git(root, *args, allow_failure=False):
    p = subprocess.run(["git", "-C", str(root), *args], capture_output=True)
    if p.returncode and not allow_failure:
        raise Invalid("GIT_ERROR: "+p.stderr.decode("utf-8", errors="replace"))
    return p


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Invalid("API_REDIRECT: refusing to forward credentials")


class Client:
    def __init__(self, token, repository=REPOSITORY, transport=None, sleeper=time.sleep):
        if repository != REPOSITORY:
            raise Invalid("Release publishing is restricted to the canonical repository")
        self.repository, self.token = repository, token
        self.transport, self.sleeper = transport or self.http, sleeper
        self.root = "/repos/"+repository

    def http(self, method, url, headers, body):
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.build_opener(NoRedirect).open(req, timeout=60) as r:
                return r.status, r.read(), dict(r.headers)
        except urllib.error.HTTPError as e:
            return e.code, e.read(), dict(e.headers)

    def request(self, method, endpoint="", data=None, missing=False, upload=False):
        if endpoint and not endpoint.startswith("/"):
            raise Invalid("API endpoint must be repository-relative")
        base = "https://uploads.github.com" if upload else "https://api.github.com"
        url = base+self.root+endpoint
        parsed = urllib.parse.urlparse(url)
        if parsed.hostname not in {"api.github.com", "uploads.github.com"} or parsed.scheme != "https":
            raise Invalid("Unsafe API host")
        raw = data if isinstance(data, bytes) else json_bytes(data) if data is not None else None
        headers = {"Accept": "application/vnd.github+json", "Authorization": "Bearer "+self.token,
                   "User-Agent": "PlayableArchive-PTBR-Release", "X-GitHub-Api-Version": "2022-11-28"}
        if not self.token:
            del headers["Authorization"]
        if raw is not None:
            headers["Content-Type"] = "application/zip" if upload else "application/json"
        for attempt in range(3):
            status, response, response_headers = self.transport(method, url, headers, raw)
            if status == 404 and missing:
                return None
            if status in {429, 500, 502, 503, 504} and method == "GET" and attempt < 2:
                self.sleeper(min(2**attempt, 4))
                continue
            if not 200 <= status < 300:
                # Never print request headers or a response potentially containing secrets.
                raise Invalid(f"GITHUB_HTTP_{status}: {method} {parsed.path}; check permissions, resource access and rerun safely")
            return json.loads(response) if response else None
        raise Invalid("GITHUB_RETRY_EXHAUSTED")

    def releases(self):
        result = []
        for page in range(1, 101):
            batch = self.request("GET", f"/releases?per_page=100&page={page}")
            result.extend(batch)
            if len(batch) < 100:
                return result
        raise Invalid("Release pagination exceeds safe bound")

    def tag_sha(self, tag):
        ref = self.request("GET", "/git/ref/tags/"+urllib.parse.quote(tag, safe=""), missing=True)
        if ref is None:
            return None
        obj = ref["object"]
        for _ in range(8):
            if obj["type"] == "commit":
                return obj["sha"]
            if obj["type"] != "tag":
                break
            obj = self.request("GET", "/git/tags/"+obj["sha"])["object"]
        raise Invalid("Unsupported or cyclic tag object")


def history_rows(project, ref):
    manifest = json.loads(git(project.root, "show", f"{ref}:{WORK}translations/manifest.json").stdout)
    result = {}
    for b in manifest["batches"]:
        data = git(project.root, "show", f"{ref}:{WORK}translations/{b}").stdout
        for line in data.decode("utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                if row["id"] in result:
                    raise Invalid("Duplicate historic ID")
                result[row["id"]] = row
    return result


def changelog(project, previous, current, receipt):
    rows = history_rows(project, current)
    if previous is None:
        body = (f"Primeira versão completa do corpus gerenciado: {receipt['completed']} entradas em PT-BR, "
                f"distribuídas em {len(receipt['profile']['tables'])} tabelas.\n\n")
    else:
        old = history_rows(project, previous)
        added, removed = set(rows)-set(old), set(old)-set(rows)
        shared = set(rows)&set(old)
        modified = {rid for rid in shared if (rows[rid]["EN"], rows[rid]["PTBR"]) != (old[rid]["EN"], old[rid]["PTBR"])}
        body = (f"Entradas: {len(added)} adicionadas, {len(modified)} alteradas, "
                f"{len(removed)} removidas e {len(shared)-len(modified)} mantidas.\n\n")
        if not added and not removed and not modified:
            body += "Os arquivos nativos mudaram sem mudanças nos textos PT-BR.\n\n"
        changed = git(project.root, "diff", "--name-only", previous, current, "--", "PTBR/").stdout.decode().splitlines()
        body += "Recursos nativos alterados: "+", ".join(f"`{v}`" for v in changed)+".\n\n"
        old_receipt = json.loads(git(project.root, "show", f"{previous}:{BUILD}").stdout)
        if old_receipt.get("provenance") != receipt.get("provenance"):
            body += "A origem/versão da fonte mudou; confira a compatibilidade antes de instalar.\n\n"
        body += f"[Comparação de commits](https://github.com/{REPOSITORY}/compare/{previous}...{current}).\n\n"
    body += ("Arquivo: **PTBR.zip**, com `Playable Archive_Data/resources.assets` na raiz. "
             "Faça backup do arquivo original e extraia o ZIP na pasta do jogo, mantendo o idioma inglês.\n\n"
             f"Fonte: Unity {receipt['profile']['unity']}; origem `{json.dumps(receipt['provenance'], ensure_ascii=False)}`. "
             "Validação técnica concluída; testes visuais e execução no jogo não são comprovados pelo build. "
             "Áudio e textos fora das tabelas não estão incluídos.\n\n")
    body += "<!-- ptbr-fingerprint: "+sha(json_bytes(receipt["outputs"]))+" -->"
    return body


def docs_status(project, published):
    warnings = []
    if published and not published.get("draft", True):
        assets = published.get("assets", [])
        if not any(a.get("name") == "PTBR.zip" and a.get("state") == "uploaded" for a in assets):
            raise Invalid("Docs reconciliation requires a confirmed published PTBR.zip")
        for rel in ["README.md", WORK+"README.md"]:
            try:
                text = project.path(rel).read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                warnings.append({"file": rel, "claim": "missing or unreadable documentation",
                                 "action": "Restore and reconcile this document with the confirmed Release"})
                continue
            if "<!-- release-state: unavailable -->" in text:
                warnings.append({"file": rel, "claim": "release-state: unavailable",
                                 "action": f"Confirm {published['tag_name']}, update download/coverage text, then replace marker with release-state: available"})
    return {"published": published.get("tag_name") if published else None, "warnings": warnings,
            "read_only": True}


def publish(project, client, commit):
    receipt = project.verify_output()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise Invalid("Invalid exact commit SHA")
    if git(project.root, "rev-parse", "HEAD").stdout.decode().strip() != commit:
        raise Invalid("HEAD is not the verified triggering commit")
    if git(project.root, "status", "--porcelain", "--untracked-files=no").stdout.strip():
        raise Invalid("Tracked working tree differs from commit")
    metadata = client.request("GET")  # canonical /repos/owner/repo, no trailing slash
    if metadata.get("full_name", "").lower() != REPOSITORY.lower():
        raise Invalid("Repository identity mismatch")
    branch = metadata["default_branch"]

    def current_head():
        head = client.request("GET", "/commits/"+urllib.parse.quote(branch, safe=""))["sha"]
        if head != commit:
            raise Invalid("STALE_COMMIT: default branch advanced; only its current verified PTBR may publish")

    current_head()
    releases = client.releases()
    stable = [r for r in releases if not r.get("draft") and not r.get("prerelease") and SEMVER.fullmatch(r["tag_name"])]
    stable.sort(key=lambda r: tuple(map(int, SEMVER.fullmatch(r["tag_name"]).groups())))
    previous = stable[-1] if stable else None
    if previous:
        tag = previous["tag_name"]
        previous_sha = client.tag_sha(tag)
        if not previous_sha or git(project.root, "merge-base", "--is-ancestor", previous_sha, commit, allow_failure=True).returncode:
            raise Invalid("NON_ANCESTOR_TAG: previous stable release must be an ancestor")
        prior = json.loads(git(project.root, "show", f"{previous_sha}:{BUILD}").stdout)
        prior_bytes = git(project.root, "show", f"{previous_sha}:PTBR/{DEPLOY}").stdout
        if prior.get("outputs") != {DEPLOY: sha(prior_bytes)}:
            raise Invalid("Previous release manifest does not match tagged native files")
        if prior["outputs"] == receipt["outputs"]:
            confirmed = client.request("GET", f"/releases/{previous['id']}")
            if confirmed.get("draft") or not any(a.get("name") == "PTBR.zip" and a.get("state") == "uploaded" for a in confirmed.get("assets", [])):
                raise Invalid("Published release lacks a confirmed PTBR.zip")
            return {"status": "unchanged", "tag": tag, "docs": docs_status(project, confirmed)}
        a, b, c = map(int, SEMVER.fullmatch(tag).groups())
        version = f"v{a}.{b}.{c+1}"
    else:
        version = "v1.0.0"
    existing = client.tag_sha(version)
    if existing and existing != commit:
        raise Invalid("TAG_CONFLICT: existing version points to another commit; never retag")
    body = changelog(project, client.tag_sha(previous["tag_name"]) if previous else None, commit, receipt)
    fingerprint = "<!-- ptbr-fingerprint: "+sha(json_bytes(receipt["outputs"]))+" -->"
    drafts = [r for r in releases if r["tag_name"] == version]
    if len(drafts) > 1:
        raise Invalid("Ambiguous release candidates")
    if drafts:
        release = client.request("GET", f"/releases/{drafts[0]['id']}")
        if not release.get("draft") or release.get("target_commitish") != commit or fingerprint not in release.get("body", ""):
            raise Invalid("Interrupted release does not belong to this build/commit")
    else:
        release = client.request("POST", "/releases", {"tag_name": version, "target_commitish": commit,
                    "name": "Playable Archive — PT-BR "+version, "body": body, "draft": True, "prerelease": False})
    archive = project.package()
    archive_bytes = Path(archive["zip"]).read_bytes()
    assets = client.request("GET", f"/releases/{release['id']}/assets?per_page=100")
    matches = [a for a in assets if a["name"] == "PTBR.zip"]
    if len(matches) > 1:
        raise Invalid("Duplicate release ZIP assets")
    if matches:
        asset = matches[0]
        if asset.get("state") != "uploaded" or asset.get("digest") != "sha256:"+sha(archive_bytes) or asset.get("size") != len(archive_bytes):
            raise Invalid("Interrupted asset differs; inspect draft rather than silently replace")
    else:
        asset = client.request("POST", f"/releases/{release['id']}/assets?name=PTBR.zip", archive_bytes, upload=True)
        if asset.get("state") != "uploaded" or asset.get("digest") != "sha256:"+sha(archive_bytes) or asset.get("size") != len(archive_bytes):
            raise Invalid("Uploaded ZIP not confirmed")
    current_head()
    client.request("PATCH", f"/releases/{release['id']}", {"draft": False, "body": body})
    published = client.request("GET", f"/releases/{release['id']}")
    if (published.get("draft") or published.get("tag_name") != version
            or client.tag_sha(version) != commit
            or not any(a.get("name") == "PTBR.zip" and a.get("state") == "uploaded"
                       and a.get("digest") == "sha256:"+sha(archive_bytes) for a in published.get("assets", []))):
        raise Invalid("Post-publication asset/tag verification failed; rerun safely")
    return {"status": "published", "tag": version, "docs": docs_status(project, published)}


def main():
    project = Project(Path(__file__).resolve().parent.parent)
    try:
        client = Client(os.environ["GITHUB_TOKEN"], os.environ["GITHUB_REPOSITORY"])
        if len(sys.argv) == 2 and sys.argv[1] == "--docs-status":
            stable = [r for r in client.releases() if not r.get("draft") and not r.get("prerelease") and SEMVER.fullmatch(r["tag_name"])]
            stable.sort(key=lambda r: tuple(map(int, SEMVER.fullmatch(r["tag_name"]).groups())))
            published = client.request("GET", f"/releases/{stable[-1]['id']}") if stable else None
            result = docs_status(project, published)
        else:
            if os.environ.get("GITHUB_EVENT_NAME") not in {"push", "workflow_dispatch"}:
                raise Invalid("Only default-branch push/manual release events are allowed")
            metadata = client.request("GET")
            if os.environ.get("GITHUB_REF") != "refs/heads/"+metadata["default_branch"]:
                raise Invalid("Publishing requires canonical default branch")
            result = publish(project, client, os.environ["GITHUB_SHA"])
        print(json.dumps(result, ensure_ascii=False, indent=2))
        for warning in result.get("docs", result).get("warnings", []):
            print(f"::warning file={warning['file']}::{warning['action']}")
        return 0
    except (Invalid, OSError, KeyError, ValueError) as e:
        print(str(e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
