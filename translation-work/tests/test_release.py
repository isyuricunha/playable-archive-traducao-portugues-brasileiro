import copy
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import urllib.parse

sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from native import Invalid, DEPLOY, fixture
from storage import durable, sha
from toolkit import Project, WORK
import release
from test_toolkit import setup_root, payload


class GitHubMock:
    """Exercises Client.request URL/headers/body and publication side effects."""
    def __init__(self, head):
        self.head = head
        self.releases = []
        self.tags = {}
        self.calls = []
        self.fail_upload = False
        self.statuses = []

    def transport(self, method, url, headers, raw):
        parsed = urllib.parse.urlparse(url)
        base = "/repos/"+release.REPOSITORY
        path = parsed.path
        self.calls.append((method, parsed.netloc, path, parsed.query))
        assert headers["Authorization"] == "Bearer test-token"
        assert path.startswith(base)
        endpoint = path[len(base):]
        assert not endpoint.endswith("/")
        if self.statuses:
            status = self.statuses.pop(0)
            if status != 200:
                return status, b'{}', {}
        data = json.loads(raw) if raw and "json" in headers.get("Content-Type", "") else None
        status, result = 200, None
        if endpoint == "":
            result = {"full_name": release.REPOSITORY, "default_branch": "main"}
        elif endpoint == "/commits/main":
            result = {"sha": self.head}
        elif endpoint == "/releases" and method == "GET":
            result = copy.deepcopy(self.releases)
        elif endpoint.startswith("/git/ref/tags/"):
            tag = urllib.parse.unquote(endpoint.split("/tags/", 1)[1])
            if tag in self.tags:
                result = {"object": {"type": "commit", "sha": self.tags[tag]}}
            else:
                status, result = 404, {"message": "Not Found"}
        elif endpoint == "/releases" and method == "POST":
            result = {**data, "id": len(self.releases)+1, "assets": []}
            self.releases.append(result)
        elif endpoint.startswith("/releases/"):
            parts = endpoint.split("/")
            rid = int(parts[2])
            r = next(r for r in self.releases if r["id"] == rid)
            if len(parts) == 4 and parts[3] == "assets":
                if method == "GET":
                    result = r["assets"]
                else:
                    assert parsed.netloc == "uploads.github.com"
                    assert parsed.query == "name=PTBR.zip"
                    if self.fail_upload:
                        return 403, b'{}', {}
                    result = {"name": "PTBR.zip", "id": 100+rid, "state": "uploaded",
                              "digest": "sha256:"+sha(raw), "size": len(raw)}
                    r["assets"].append(result)
            elif method == "PATCH":
                r.update(data)
                if not r["draft"]:
                    self.tags[r["tag_name"]] = r["target_commitish"]
                result = r
            else:
                result = r
        else:
            raise AssertionError((method, url))
        return status, json.dumps(result).encode(), {}


class ReleaseTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        setup_root(self.root)
        self.project = Project(self.root)
        with self.project.store.lock():
            self.project.sync(fixture(count=3), initial=True)
            self.project.apply(payload(self.project))
            self.project.build()
        self.g("init", "-q", "-b", "main")
        self.g("config", "user.email", "fixture@example.invalid")
        self.g("config", "user.name", "Fixture")
        durable(self.root/".gitignore", b"translation-work/.state/\nPTBR.zip\n__pycache__/\n")
        self.commit()
        self.server = GitHubMock(self.head())
        self.client = release.Client("test-token", transport=self.server.transport, sleeper=lambda _: None)

    def tearDown(self):
        self.temp.cleanup()

    def g(self, *args):
        return subprocess.check_output(["git", "-C", str(self.root), *args], stderr=subprocess.DEVNULL)

    def head(self):
        return self.g("rev-parse", "HEAD").decode().strip()

    def commit(self):
        self.g("add", ".")
        self.g("commit", "-qm", "Fixture build")

    def publish(self):
        return release.publish(self.project, self.client, self.head())

    def changed_build(self):
        with self.project.store.lock():
            self.project.apply(payload(self.project, [0], "Changed fixture %?"), replace=True)
            self.project.build()
        self.commit()
        self.server.head = self.head()

    def test_first_publish_exact_paths_asset_confirmation_and_docs(self):
        result = self.publish()
        self.assertEqual(result["tag"], "v1.0.0")
        self.assertEqual(result["status"], "published")
        self.assertEqual(len(result["docs"]["warnings"]), 2)
        paths = [c[2] for c in self.server.calls]
        self.assertIn("/repos/"+release.REPOSITORY, paths)
        self.assertTrue(any(c[0] == "POST" and c[1] == "uploads.github.com" for c in self.server.calls))
        self.assertEqual(self.server.tags["v1.0.0"], self.head())
        self.assertFalse(self.server.releases[0]["draft"])

    def test_next_patch_real_changelog_and_rerun_idempotence(self):
        self.publish()
        self.changed_build()
        result = self.publish()
        self.assertEqual(result["tag"], "v1.0.1")
        self.assertIn("1 alteradas", self.server.releases[-1]["body"])
        self.assertIn("PTBR/"+DEPLOY, self.server.releases[-1]["body"])
        self.assertEqual(self.publish()["status"], "unchanged")
        self.assertEqual(len(self.server.releases), 2)

    def test_identical_outputs_and_readme_only_commit_skip(self):
        self.publish()
        durable(self.root/"README.md", b"<!-- release-state: available -->\nDownload confirmado.\n")
        durable(self.root/(WORK+"README.md"), b"<!-- release-state: available -->\nBuild completo.\n")
        self.commit()
        self.server.head = self.head()
        result = self.publish()
        self.assertEqual(result["status"], "unchanged")
        self.assertEqual(result["docs"]["warnings"], [])
        self.assertEqual(len(self.server.releases), 1)

    def test_draft_resume_after_upload_permission_failure(self):
        self.server.fail_upload = True
        with self.assertRaisesRegex(Invalid, "GITHUB_HTTP_403"):
            self.publish()
        self.assertEqual(len(self.server.releases), 1)
        self.assertTrue(self.server.releases[0]["draft"])
        self.server.fail_upload = False
        self.assertEqual(self.publish()["tag"], "v1.0.0")
        self.assertEqual(len(self.server.releases), 1)

    def test_resume_after_uploaded_asset_no_duplicate(self):
        original = self.server.transport
        failed = False
        def transport(method, url, headers, raw):
            nonlocal failed
            if method == "PATCH" and not failed:
                failed = True
                return 503, b'{}', {}
            return original(method, url, headers, raw)
        self.client.transport = transport
        with self.assertRaisesRegex(Invalid, "GITHUB_HTTP_503"):
            self.publish()
        self.assertEqual(len(self.server.releases[0]["assets"]), 1)
        self.publish()
        self.assertEqual(len(self.server.releases[0]["assets"]), 1)

    def test_stale_commit_and_invalid_existing_tag_fail_closed(self):
        self.server.head = "f"*40
        with self.assertRaisesRegex(Invalid, "STALE_COMMIT"):
            self.publish()
        self.server.head = self.head()
        self.server.tags["v1.0.0"] = "f"*40
        with self.assertRaisesRegex(Invalid, "TAG_CONFLICT"):
            self.publish()
        self.assertEqual(self.server.releases, [])

    def test_non_ancestor_published_tag_fails(self):
        self.publish()
        self.server.tags["v1.0.0"] = "f"*40
        with self.assertRaisesRegex(Invalid, "NON_ANCESTOR"):
            self.publish()

    def test_stale_build_never_calls_github(self):
        with self.project.store.lock():
            self.project.apply(payload(self.project, [0], "Changed fixture %?"), replace=True)
        with self.assertRaisesRegex(Invalid, "INVALID_OUTPUT"):
            self.publish()
        self.assertEqual(self.server.calls, [])

    def test_auth_missing_api_and_transient_errors(self):
        for status in [401, 403, 404]:
            self.server.statuses = [status]
            with self.assertRaisesRegex(Invalid, f"GITHUB_HTTP_{status}"):
                self.client.request("GET")
        self.server.statuses = [503, 429, 200]
        self.assertEqual(self.client.request("GET")["default_branch"], "main")
        self.assertIsNone(self.client.tag_sha("missing/tag with spaces"))
        self.assertTrue(any("missing%2Ftag%20with%20spaces" in c[2] for c in self.server.calls))

    def test_docs_readonly_without_release_and_after_publication(self):
        before = (self.root/"README.md").read_bytes()
        self.assertEqual(release.docs_status(self.project, None)["warnings"], [])
        self.publish()
        result = release.docs_status(self.project, self.server.releases[0])
        self.assertEqual(result["warnings"][0]["file"], "README.md")
        self.assertEqual((self.root/"README.md").read_bytes(), before)

    def test_workflow_contract(self):
        source = Path(__file__).resolve().parents[2]
        text = (source/".github/workflows/release.yml").read_text(encoding="utf-8")
        self.assertIn("contents: write", text)
        self.assertIn("paths: ['PTBR/**']", text)
        self.assertIn("concurrency:", text)
        self.assertIn("workflow_dispatch", text)
        self.assertIn("verify-output", text)
        self.assertNotIn("toolkit.py build", text)


if __name__ == "__main__":
    unittest.main()
