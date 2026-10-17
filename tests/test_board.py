"""A row shows as Verified only when its signature, its report bytes and its pinned corpus re-verify."""
import base64
import copy
import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
spec = importlib.util.spec_from_file_location("board", ROOT / "tools/board.py")
board = importlib.util.module_from_spec(spec)
sys.modules["board"] = board
spec.loader.exec_module(board)
sign_spec = importlib.util.spec_from_file_location("board_sign", ROOT / "tools/board_sign.py")
board_sign = importlib.util.module_from_spec(sign_spec)
sign_spec.loader.exec_module(board_sign)

DIGEST = "ab" * 32
MANIFEST = "cd" * 32
COMMIT = "1" * 40
RUN = board.RUN_URL_PREFIX + "123"
IDS = [f"v{i:016x}" for i in range(10)]


def seed(n: int) -> str:
    return (bytes([n]) * 32).hex()


def public_hex(seed_hex: str) -> str:
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
    return key.public_key().public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw).hex()


RUNNER = seed(1)
COMMUNITY = seed(2)
STRANGER = seed(3)


def pins_toml(releases=("0.19.0",)) -> str:
    rows = []
    for i, rel in enumerate(releases):
        rows.append(f'[[release]]\nrelease = "{rel}"\ntag = "v{rel}"\ncommit = "{str(i) * 40}"\ncorpus = "vectors"\n'
                    f'suiteRevision = {32 + i}\ncorpusDigest = "{DIGEST if i == 0 else format(i, "x") * 64}"\n'
                    f'manifestSha256 = "{MANIFEST if i == 0 else format(i + 1, "x") * 64}"\nvectors = {len(IDS)}\n')
    return "\n".join(rows)


def make_root(tmp_path: Path, releases=("0.19.0",)) -> Path:
    root = tmp_path / "repo"
    (root / "board/keys").mkdir(parents=True)
    (root / "board/entries").mkdir()
    (root / "board/corpus-releases.toml").write_text(pins_toml(releases))
    (root / "board/keys/verified-runners.toml").write_text(
        f'[[key]]\nkeyid = "runner-1"\npublicKeyHex = "{public_hex(RUNNER)}"\n')
    return root


def report(fails=(), release="0.19.0", digest=DIGEST, manifest=MANIFEST, revision=32, refusals=0) -> dict:
    rows = [{"id": i, "status": "FAIL" if i in fails else "PASS"} for i in IDS]
    return {"suite": "vectors",
            "corpus": {"release": release, "suiteRevision": revision, "corpusDigest": digest, "manifestSha256": manifest},
            "totals": {"vectors": len(IDS), "pass": len(IDS) - len(fails), "fail": len(fails),
                       "suiteRefusals": refusals, "notExercised": 0},
            "vectors": rows}


def entry_toml(name: str, tier: str, release="0.19.0", xfail=()) -> str:
    text = (f'name = "{name}"\nsummary = "A verifier"\nrepository = "https://github.com/example/{name}"\n'
            f'commit = "{COMMIT}"\nversion = "1.0.0"\nlanguage = "Go"\ntier = "{tier}"\ntoolchain = "go"\n'
            f'toolchain_version = "1.24"\nbuild = "go build -o v ./cmd/v"\nverifier = "v -json"\n'
            f'release = "{release}"\ncorpora = ["vectors"]\n')
    if tier == "community":
        text += f'keyid = "me"\npublic_key_hex = "{public_hex(COMMUNITY)}"\nkey_url = "https://example.org/key"\n'
    for vid in xfail:
        text += f'\n[[xfail]]\ncorpus = "vectors"\nid = "{vid}"\nreason = "known"\nlink = "https://example.org/issue/1"\n'
    return text


def add_entry(root: Path, name: str, tier="verified", rep=None, key=None, keyid=None, run_url=RUN,
              release="0.19.0", xfail=()) -> Path:
    d = root / "board/entries" / name
    d.mkdir()
    (d / "entry.toml").write_text(entry_toml(name, tier, release, xfail))
    raw = (json.dumps(rep or report(release=release), indent=2) + "\n").encode()
    (d / "vectors.report.json").write_bytes(raw)
    entry = board.load_entry(d / "entry.toml")
    pin = board.load_pins(root)[(release, "vectors")]
    stmt = board_sign.statement(entry, "vectors", json.loads(raw), raw, pin, run_url, "2026-10-17T00:00:00Z")
    payload = json.dumps(stmt, sort_keys=True).encode()
    key = key or (RUNNER if tier == "verified" else COMMUNITY)
    keyid = keyid or ("runner-1" if tier == "verified" else "me")
    (d / "vectors.dsse.json").write_text(json.dumps(board_sign.sign(payload, key, keyid)))
    return d


def test_signed_pinned_row_shows_verified_tier_1(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "alpha")
    [row] = board.load_board(root)
    assert (row.shown_tier, row.level, board.tier_label(row)) == ("verified", "Tier 1", "Verified")
    assert row.results["vectors"].scored_passed == len(IDS)
    page = board.markdown([row], board.load_pins(root))
    assert "| [alpha](#impl-alpha) 1.0.0 | Verified | Tier 1 | 10 / 10 |" in page
    assert "{#impl-alpha}" in page


def test_tampered_report_bytes_stop_the_build(tmp_path):
    root = make_root(tmp_path)
    d = add_entry(root, "alpha")
    rep = json.loads((d / "vectors.report.json").read_text())
    rep["vectors"][0]["status"] = "FAIL"
    rep["totals"]["pass"] -= 1
    (d / "vectors.report.json").write_text(json.dumps(rep))
    with pytest.raises(board.BoardError, match="signed subject is not these report bytes"):
        board.load_board(root)


def test_altered_signature_stops_the_build(tmp_path):
    root = make_root(tmp_path)
    d = add_entry(root, "alpha")
    env = json.loads((d / "vectors.dsse.json").read_text())
    sig = bytearray(base64.b64decode(env["signatures"][0]["sig"]))
    sig[0] ^= 1
    env["signatures"][0]["sig"] = base64.b64encode(bytes(sig)).decode()
    (d / "vectors.dsse.json").write_text(json.dumps(env))
    with pytest.raises(board.BoardError, match="does not verify"):
        board.load_board(root)


def test_verified_claim_signed_by_a_non_runner_key_is_refused(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "alpha", key=STRANGER, keyid="runner-1")
    with pytest.raises(board.BoardError, match="does not verify"):
        board.load_board(root)
    root2 = make_root(tmp_path / "b")
    add_entry(root2, "alpha", key=STRANGER, keyid="someone")
    with pytest.raises(board.BoardError, match="no signature by a key this tier accepts"):
        board.load_board(root2)


def test_community_key_cannot_make_a_row_verified(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "alpha", key=COMMUNITY, keyid="me")
    with pytest.raises(board.BoardError, match="no signature by a key this tier accepts"):
        board.load_board(root)


def test_verified_entry_cannot_bring_its_own_key(tmp_path):
    root = make_root(tmp_path)
    d = add_entry(root, "alpha", key=COMMUNITY, keyid="me")
    (d / "entry.toml").write_text(entry_toml("alpha", "verified") +
                                  f'keyid = "me"\npublic_key_hex = "{public_hex(COMMUNITY)}"\nkey_url = "https://e.org/k"\n')
    with pytest.raises(board.BoardError, match="declares no key of its own"):
        board.load_board(root)


def test_unpinned_corpus_digest_stops_the_build(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "alpha", rep=report(digest="ef" * 32))
    with pytest.raises(board.BoardError, match="does not re-verify against the pinned"):
        board.load_board(root)


def test_unpinned_release_stops_the_build(tmp_path):
    root = make_root(tmp_path)
    d = root / "board/entries/alpha"
    d.mkdir()
    (d / "entry.toml").write_text(entry_toml("alpha", "verified", release="0.18.0"))
    (d / "vectors.report.json").write_text(json.dumps(report(release="0.18.0")))
    (d / "vectors.dsse.json").write_text(json.dumps({"payloadType": board.PAYLOAD_TYPE, "payload": "", "signatures": []}))
    with pytest.raises(board.BoardError):
        board.load_board(root)


def test_verified_record_must_name_this_repositorys_runner(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "alpha", run_url="https://github.com/someone/else/actions/runs/1")
    with pytest.raises(board.BoardError, match="board-run workflow"):
        board.load_board(root)


def test_community_row_verifies_under_its_declared_key(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "beta", tier="community", run_url="https://github.com/example/beta/actions/runs/9")
    [row] = board.load_board(root)
    assert (row.shown_tier, board.tier_label(row)) == ("community", "Community")


def test_levels_and_suite_refusals(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "two", rep=report(fails=IDS[:2]))
    add_entry(root, "low", rep=report(fails=IDS[:3]))
    add_entry(root, "refused", rep=report(refusals=1))
    levels = {r.name: r.level for r in board.load_board(root)}
    assert levels == {"two": "Tier 2", "low": "Below Tier 2", "refused": "Below Tier 2"}


def test_signed_totals_must_match_the_report(tmp_path):
    root = make_root(tmp_path)
    d = add_entry(root, "alpha")
    env = json.loads((d / "vectors.dsse.json").read_text())
    stmt = json.loads(base64.b64decode(env["payload"]))
    stmt["predicate"]["totals"]["pass"] = 0
    payload = json.dumps(stmt).encode()
    (d / "vectors.dsse.json").write_text(json.dumps(board_sign.sign(payload, RUNNER, "runner-1")))
    with pytest.raises(board.BoardError, match="totals disagrees"):
        board.load_board(root)


def test_xfail_must_actually_fail_and_still_counts(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "alpha", rep=report(fails=[IDS[0]]), xfail=[IDS[0]])
    [row] = board.load_board(root)
    assert row.level == "Tier 2" and row.results["vectors"].xfail[0]["id"] == IDS[0]
    stale = make_root(tmp_path / "s")
    add_entry(stale, "alpha", xfail=[IDS[0]])
    with pytest.raises(board.BoardError, match="did not fail in this run"):
        board.load_board(stale)


def test_disputed_vectors_leave_every_rows_denominator(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "alpha", rep=report(fails=[IDS[0]]))
    (root / "board/disputes.toml").write_text(
        f'[[dispute]]\ncorpus = "vectors"\nrelease = "0.19.0"\nid = "{IDS[0]}"\nreason = "two readings"\n'
        'link = "https://example.org/issue/2"\n')
    [row] = board.load_board(root)
    r = row.results["vectors"]
    assert (r.scored_passed, r.scored_total, row.level, r.disputed) == (9, 9, "Tier 1", [IDS[0]])


def test_verified_row_two_releases_behind_is_relegated(tmp_path):
    root = make_root(tmp_path, releases=("0.19.0", "0.20.0", "0.21.0"))
    add_entry(root, "alpha")
    [row] = board.load_board(root)
    assert row.relegated and row.shown_tier == "community"
    assert board.tier_label(row) == "Community (relegated from Verified)"
    current = make_root(tmp_path / "c", releases=("0.19.0", "0.20.0"))
    add_entry(current, "alpha")
    assert not board.load_board(current)[0].relegated


def test_divergence_lists_vectors_exactly_one_implementation_fails(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "alpha", rep=report(fails=[IDS[1]]))
    add_entry(root, "beta", rep=report(fails=[IDS[1], IDS[2]]))
    add_entry(root, "gamma", rep=report(fails=[IDS[3]]))
    div = board.divergence(board.load_board(root))
    assert div == {"vectors 0.19.0": [(IDS[2], "beta"), (IDS[3], "gamma")]}


def test_public_files_carry_json_twin_badge_and_signed_bytes(tmp_path):
    root = make_root(tmp_path)
    d = add_entry(root, "alpha")
    rows = board.load_board(root)
    files = board.public_files(root, rows)
    badge = json.loads(files["board/alpha.badge.json"])
    assert badge == {"schemaVersion": 1, "label": "agent-evidence-vectors",
                     "message": "Verified Tier 1 10/10 v0.19.0", "color": "brightgreen"}
    twin = json.loads(files["board/alpha.json"])
    assert twin["tier"] == "verified" and twin["results"][0]["record"]["url"].endswith("board/alpha/vectors.dsse.json")
    assert files["board/alpha/vectors.dsse.json"] == (d / "vectors.dsse.json").read_bytes()
    assert [r["name"] for r in json.loads(files["board/index.json"])["implementations"]] == ["alpha"]


def test_unexpected_files_and_bare_directories_are_refused(tmp_path):
    root = make_root(tmp_path)
    d = add_entry(root, "alpha")
    (d / "notes.txt").write_text("x")
    with pytest.raises(board.BoardError, match="unexpected files"):
        board.load_board(root)
    other = make_root(tmp_path / "o")
    (other / "board/entries/empty").mkdir()
    with pytest.raises(board.BoardError, match="without entry.toml"):
        board.load_board(other)


def test_entry_text_is_literal_in_the_page(tmp_path):
    root = make_root(tmp_path)
    d = add_entry(root, "alpha")
    text = (d / "entry.toml").read_text().replace('summary = "A verifier"', 'summary = "A [link](x) | *bold*"')
    (d / "entry.toml").write_text(text)
    rows = board.load_board(root)
    page = board.markdown(rows, board.load_pins(root))
    assert r"A \[link\]\(x\) &#124; \*bold\*" in page


def test_signer_refuses_a_report_the_pins_reject(tmp_path, monkeypatch):
    root = make_root(tmp_path)
    d = root / "board/entries/alpha"
    d.mkdir()
    (d / "entry.toml").write_text(entry_toml("alpha", "verified"))
    bad = tmp_path / "r.json"
    bad.write_text(json.dumps(report(digest="ef" * 32)))
    monkeypatch.setenv("K", RUNNER)
    out = tmp_path / "out.json"
    args = ["--entry", str(d / "entry.toml"), "--corpus", "vectors", "--report", str(bad), "--run-url", RUN,
            "--started-at", "2026-10-17T00:00:00Z", "--key-env", "K", "--keyid", "runner-1", "--out", str(out),
            "--root", str(root)]
    assert board_sign.main(args) == 1 and not out.exists()
    good = tmp_path / "g.json"
    good.write_text(json.dumps(report()))
    args[args.index(str(bad))] = str(good)
    assert board_sign.main(args) == 0
    shutil.copyfile(good, d / "vectors.report.json")
    shutil.copyfile(out, d / "vectors.dsse.json")
    assert board.load_board(root)[0].shown_tier == "verified"


def test_plan_prints_runner_inputs_without_newlines(tmp_path):
    root = make_root(tmp_path)
    add_entry(root, "alpha")
    lines = board.plan(root, "alpha")
    assert "repository=example/alpha" in lines and 'corpora=["vectors"]' in lines
    assert all("\n" not in line for line in lines)
    with pytest.raises(board.BoardError):
        board.plan(root, "../x")


def test_the_published_board_verifies():
    rows = board.load_board(ROOT)
    assert all(r.results for r in rows)
    proc = subprocess.run([sys.executable, str(ROOT / "tools/board.py"), "check"], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
