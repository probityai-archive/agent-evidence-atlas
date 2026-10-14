"""Pin the checks that keep release versions, star counts and their ledger rows current.

A release the page calls current must be read from one place, re-read weekly, and quoted by
the claim ledger as the page shows it; a star refresh must rewrite only the entries that
carry a count, and move each quoted count's read time with it.
"""
import re
import tomllib
from pathlib import Path

import pytest

import build
import gen_atlas
import refresh_stars
import rederive

ROOT = Path(__file__).resolve().parents[1]
DATA = tomllib.loads((ROOT / "data/atlas.toml").read_text(encoding="utf-8"))
CLAIMS = (ROOT / "CLAIMS.md").read_text(encoding="utf-8")
CADENCE = tomllib.loads((ROOT / "data/claim_cadence.toml").read_text(encoding="utf-8"))["cadence"]

SAMPLE = '''[meta]
stars_read = "2026-10-01 07:04:40 UTC"

[[entry]]
name = "One"
repo = "example/one"
stars = 10
[[entry]]
name = "A standard"
url = "https://example.org/standard"
[[corpus]]
dir = "pinned"
repo = "example/elsewhere"
commit = "0123456789abcdef0123456789abcdef01234567"
'''
SAMPLE_CLAIMS = (
    "| A-01 | One: 10 stars | GitHub API | stars 2026-10-01 07:04:40 | rederive | attention |\n"
    "| A-02 | A release read 2026-10-01 07:04:40 | tags | 2026-10-01 07:04:40 | rederive | none |\n"
)


class TestCurrentReleaseCadence:
    def test_the_ledger_has_no_release_row_that_can_outlive_its_release(self):
        assert build.release_cadence_violations(CLAIMS, CADENCE) == []

    @pytest.mark.parametrize("cadence", [30, "none", None])
    def test_a_current_release_row_needs_a_weekly_cadence(self, cadence):
        claims = "| A-38 | Current releases: tool v1.0 | tags | 2026-10-14 | rederive | none |\n"
        bad = build.release_cadence_violations(claims, {} if cadence is None else {"A-38": cadence})
        assert len(bad) == 1 and bad[0].startswith("A-38 ")

    def test_a_latest_release_row_is_held_to_the_same_rule(self):
        claims = "| C-99 | The latest release is 2.0 | PyPI | 2026-10-14 | read it | none |\n"
        assert build.release_cadence_violations(claims, {"C-99": "none"})

    def test_a_version_pinned_by_number_may_never_expire(self):
        claims = "| A-60 | Release v0.18.1 carries 1,197 members | manifest | 2026-10-13 | count | pinned |\n"
        assert build.release_cadence_violations(claims, {"A-60": "none"}) == []


class TestArtifactVersions:
    def test_every_artifact_shows_the_version_rederive_reads(self):
        gen_atlas.check_artifact_versions(DATA["artifact"])
        rows = {cid: recorded for cid, recorded, _ in rederive.artifact_release_rows()}
        assert rows == {f"A-38 {a['name']}": a["version"] for a in DATA["artifact"]}

    def test_the_ledger_row_quotes_every_version_the_page_shows(self):
        a38 = next(line for line in CLAIMS.splitlines() if line.startswith("| A-38 |"))
        for a in DATA["artifact"]:
            assert a["version"] in a38, a["name"]

    @pytest.mark.parametrize("change, message", [
        ({"release": "0.1.1 on crates.io", "version": "0.1.2"}, "does not show version"),
        ({"version_from": "github:example/x"}, "version_from must start"),
        ({"version": None}, "no version"),
    ])
    def test_an_artifact_that_disagrees_with_itself_is_refused(self, change, message):
        artifact = {"name": "x", "release": "0.1.2 on crates.io", "version": "0.1.2", "version_from": "crate:x"}
        artifact.update(change)
        artifact = {k: v for k, v in artifact.items() if v is not None}
        with pytest.raises(SystemExit, match=message):
            gen_atlas.check_artifact_versions([artifact])

    def test_only_pull_request_contributions_get_a_state_row(self):
        rows = [cid for cid, _, _ in rederive.contribution_state_rows()]
        pulls = [c for c in DATA["contribution"] if re.match(r"https://github\.com/.+/pull/[0-9]+$", c["url"])]
        assert rows == [f"A-39 {c['where']}" for c in pulls]


class TestStarRefresh:
    def test_a_corpus_repo_is_not_counted_as_a_star_entry(self):
        assert refresh_stars.entry_counts(SAMPLE) == [("example/one", 10)]

    def test_blocks_split_the_file_losslessly(self):
        assert "".join(refresh_stars.blocks(SAMPLE)) == SAMPLE

    def test_rewrite_moves_counts_and_their_read_time_only(self):
        text, claims, changed = refresh_stars.rewrite(SAMPLE, SAMPLE_CLAIMS, {"example/one": 12},
                                                      "2026-10-14 23:00 UTC")
        assert "stars = 12" in text and 'repo = "example/elsewhere"' in text
        assert 'stars_read = "2026-10-14 23:00 UTC"' in text
        assert changed == 1
        first, second = claims.splitlines()
        assert first == "| A-01 | One: 12 stars | GitHub API | stars 2026-10-14 23:00 | rederive | attention |"
        assert second == SAMPLE_CLAIMS.splitlines()[1]

    def test_an_entry_with_a_repo_and_no_count_is_refused(self):
        broken = SAMPLE.replace("stars = 10\n", "")
        with pytest.raises(refresh_stars.RefreshError):
            refresh_stars.entry_counts(broken)

    def test_the_real_data_file_refreshes(self):
        found = refresh_stars.entry_counts((ROOT / "data/atlas.toml").read_text(encoding="utf-8"))
        assert len(found) == sum(1 for e in DATA["entry"] if "repo" in e) > 0

    def test_main_writes_nothing_when_a_read_fails(self, monkeypatch, tmp_path):
        data, claims = tmp_path / "atlas.toml", tmp_path / "CLAIMS.md"
        data.write_text(SAMPLE, encoding="utf-8")
        claims.write_text(SAMPLE_CLAIMS, encoding="utf-8")
        monkeypatch.setattr(refresh_stars, "DATA", data)
        monkeypatch.setattr(refresh_stars, "CLAIMS", claims)

        def fail(repo):
            raise OSError("offline")

        assert refresh_stars.main([], reader=fail) == 2
        assert data.read_text(encoding="utf-8") == SAMPLE
        assert claims.read_text(encoding="utf-8") == SAMPLE_CLAIMS
