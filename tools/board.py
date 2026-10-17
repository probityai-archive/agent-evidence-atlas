#!/usr/bin/env python3
"""The conformance board: verify every signed row, then render it.

    python3 tools/board.py check            verify every entry under board/entries/ and print the rows
    python3 tools/board.py plan <entry>     print the runner inputs of one entry as GITHUB_OUTPUT lines

A row is shown only after its bytes verify. For every corpus an entry lists, the
build reads `<corpus>.report.json` and `<corpus>.dsse.json` beside `entry.toml` and
requires all of these, or the build fails:

- the DSSE envelope carries an in-toto Statement of the board run-record type, and
  one of its signatures verifies (Ed25519 over the DSSE pre-authentication encoding)
  under the key the entry's tier names: a board runner key from
  board/keys/verified-runners.toml for a Verified entry, the entry's own declared
  key for a Community entry;
- the Statement's subject digest is the SHA-256 of the report bytes;
- the predicate repeats the entry's implementation, command and corpus exactly, and
  the report's totals exactly;
- the report's corpus digest and manifest digest equal a release pinned in
  board/corpus-releases.toml;
- a Verified record names a run of this repository's board-run workflow;
- every expected failure the entry declares names a vector that actually failed.

Tier and level are separate. The tier says who ran it: Verified means the board's
own runner ran the pinned command on a pinned corpus release and signed the result;
Community means the submitter ran it and signed it. The level says how it did:
Tier 1 is every scored vector passing, Tier 2 is at least 80 percent. A Verified
entry whose release has fallen out of the two newest pinned releases of a corpus is
shown as relegated to Community until it is run again.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import html
import json
import re
import sys
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

ROOT = Path(__file__).resolve().parent.parent
BOARD = Path("board")
PREDICATE_TYPE = "https://probityai.github.io/agent-evidence-atlas/board-run-record/v1"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"
PAYLOAD_TYPE = "application/vnd.in-toto+json"
RUN_URL_PREFIX = "https://github.com/probityai/agent-evidence-atlas/actions/runs/"
BASE_URL = "https://probityai.github.io/agent-evidence-atlas/"
NAME = re.compile(r"[a-z0-9][a-z0-9-]{0,62}\Z")
HEX64 = re.compile(r"[0-9a-f]{64}\Z")
COMMIT = re.compile(r"[0-9a-f]{40}\Z")
TIERS = ("verified", "community")
TOOLCHAINS = ("go", "python", "rust", "node", "none")
TIER2_FLOOR = 0.8
RELEGATION_WINDOW = 2
ENTRY_KEYS = {"name", "summary", "repository", "commit", "version", "language", "tier",
              "toolchain", "toolchain_version", "build", "verifier", "release", "corpora",
              "keyid", "public_key_hex", "key_url", "xfail"}
ENTRY_REQUIRED = ENTRY_KEYS - {"keyid", "public_key_hex", "key_url", "xfail", "toolchain_version"}
TOTAL_KEYS = ("vectors", "pass", "fail", "suiteRefusals", "notExercised")


class BoardError(ValueError):
    """A row that does not verify. The build stops on the first one."""


@dataclass(frozen=True)
class Pin:
    release: str
    tag: str
    commit: str
    corpus: str
    suite_revision: int
    corpus_digest: str
    manifest_sha256: str
    vectors: int


@dataclass
class CorpusResult:
    corpus: str
    release: str
    suite_revision: int
    corpus_digest: str
    passed: int
    total: int
    scored_passed: int
    scored_total: int
    level: str
    run_url: str
    run_started: str
    signer: str
    record_sha256: str
    report_sha256: str
    statuses: dict[str, str]
    xfail: list[dict[str, str]]
    disputed: list[str]


@dataclass
class Row:
    name: str
    summary: str
    repository: str
    commit: str
    version: str
    language: str
    claimed_tier: str
    shown_tier: str
    relegated: bool
    toolchain: str
    build: str
    verifier: str
    results: dict[str, CorpusResult] = field(default_factory=dict)

    @property
    def level(self) -> str:
        """The weakest level across the corpora the entry ran."""
        order = ["Tier 1", "Tier 2", "Below Tier 2"]
        return max((r.level for r in self.results.values()), key=order.index)


def _toml(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise BoardError(f"{path}: {exc}") from exc


def _json(path: Path) -> tuple[bytes, dict]:
    try:
        raw = path.read_bytes()
        value = json.loads(raw)
    except (OSError, ValueError) as exc:
        raise BoardError(f"{path}: {exc}") from exc
    if type(value) is not dict:
        raise BoardError(f"{path}: expected a JSON object")
    return raw, value


def _release_key(release: str) -> tuple[int, ...]:
    if not re.fullmatch(r"\d+\.\d+\.\d+", release):
        raise BoardError(f"release {release!r} is not MAJOR.MINOR.PATCH")
    return tuple(int(p) for p in release.split("."))


def load_pins(root: Path) -> dict[tuple[str, str], Pin]:
    data = _toml(root / BOARD / "corpus-releases.toml")
    pins: dict[tuple[str, str], Pin] = {}
    for row in data.get("release", []):
        try:
            pin = Pin(row["release"], row["tag"], row["commit"], row["corpus"], int(row["suiteRevision"]),
                      row["corpusDigest"], row["manifestSha256"], int(row["vectors"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise BoardError(f"corpus-releases.toml: malformed release row {row!r}") from exc
        _release_key(pin.release)
        if pin.tag != f"v{pin.release}" or not COMMIT.fullmatch(pin.commit):
            raise BoardError(f"corpus-releases.toml: {pin.release} needs tag v{pin.release} and a full commit")
        if not HEX64.fullmatch(pin.corpus_digest) or not HEX64.fullmatch(pin.manifest_sha256):
            raise BoardError(f"corpus-releases.toml: {pin.release}/{pin.corpus} digests must be 64 lowercase hex")
        if (pin.release, pin.corpus) in pins:
            raise BoardError(f"corpus-releases.toml: {pin.release}/{pin.corpus} pinned twice")
        pins[(pin.release, pin.corpus)] = pin
    return pins


def load_runner_keys(root: Path) -> dict[str, bytes]:
    data = _toml(root / BOARD / "keys" / "verified-runners.toml")
    keys: dict[str, bytes] = {}
    for row in data.get("key", []):
        keyid, hexkey = row.get("keyid"), row.get("publicKeyHex")
        if type(keyid) is not str or not NAME.fullmatch(keyid) or type(hexkey) is not str or not HEX64.fullmatch(hexkey):
            raise BoardError(f"verified-runners.toml: malformed key row {row!r}")
        if keyid in keys:
            raise BoardError(f"verified-runners.toml: key {keyid} listed twice")
        keys[keyid] = bytes.fromhex(hexkey)
    return keys


def load_disputes(root: Path) -> dict[tuple[str, str], set[str]]:
    path = root / BOARD / "disputes.toml"
    disputes: dict[tuple[str, str], set[str]] = {}
    if not path.exists():
        return disputes
    for row in _toml(path).get("dispute", []):
        for key in ("corpus", "release", "id", "reason", "link"):
            if type(row.get(key)) is not str or not row[key]:
                raise BoardError(f"disputes.toml: dispute {row!r} needs a {key}")
        if not row["link"].startswith("https://"):
            raise BoardError(f"disputes.toml: dispute {row['id']} link must be HTTPS")
        disputes.setdefault((row["release"], row["corpus"]), set()).add(row["id"])
    return disputes


def pae(payload_type: str, payload: bytes) -> bytes:
    """DSSE v1 pre-authentication encoding."""
    t = payload_type.encode("utf-8")
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def _b64(value: object, what: str) -> bytes:
    if type(value) is not str:
        raise BoardError(f"{what} must be a base64 string")
    try:
        return base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise BoardError(f"{what} is not base64") from exc


def verify_envelope(envelope: dict, keys: dict[str, bytes], where: str) -> tuple[dict, str]:
    """Return the Statement and the keyid of the signature that verified."""
    if envelope.get("payloadType") != PAYLOAD_TYPE:
        raise BoardError(f"{where}: payloadType must be {PAYLOAD_TYPE}")
    payload = _b64(envelope.get("payload"), f"{where}: payload")
    signatures = envelope.get("signatures")
    if type(signatures) is not list or not signatures:
        raise BoardError(f"{where}: no signatures")
    message = pae(PAYLOAD_TYPE, payload)
    for sig in signatures:
        if type(sig) is not dict:
            raise BoardError(f"{where}: malformed signature")
        keyid = sig.get("keyid")
        if keyid not in keys:
            continue
        try:
            Ed25519PublicKey.from_public_bytes(keys[keyid]).verify(_b64(sig.get("sig"), f"{where}: sig"), message)
        except InvalidSignature:
            raise BoardError(f"{where}: signature by {keyid} does not verify") from None
        try:
            statement = json.loads(payload)
        except ValueError as exc:
            raise BoardError(f"{where}: payload is not JSON") from exc
        if type(statement) is not dict:
            raise BoardError(f"{where}: payload is not a JSON object")
        return statement, keyid
    raise BoardError(f"{where}: no signature by a key this tier accepts ({', '.join(sorted(keys)) or 'none'})")


def load_entry(path: Path) -> dict:
    entry = _toml(path)
    unknown = set(entry) - ENTRY_KEYS
    missing = ENTRY_REQUIRED - set(entry)
    if unknown or missing:
        raise BoardError(f"{path}: unknown keys {sorted(unknown)}, missing keys {sorted(missing)}")
    if entry["name"] != path.parent.name or not NAME.fullmatch(entry["name"]):
        raise BoardError(f"{path}: name must equal its directory and match {NAME.pattern}")
    if entry["tier"] not in TIERS:
        raise BoardError(f"{path}: tier must be one of {TIERS}")
    if entry["toolchain"] not in TOOLCHAINS:
        raise BoardError(f"{path}: toolchain must be one of {TOOLCHAINS}")
    if not str(entry["repository"]).startswith("https://github.com/") or not COMMIT.fullmatch(str(entry["commit"])):
        raise BoardError(f"{path}: repository must be a GitHub HTTPS URL and commit a full SHA")
    _release_key(entry["release"])
    corpora = entry["corpora"]
    if type(corpora) is not list or not corpora or len(set(corpora)) != len(corpora) or not all(
            type(c) is str and NAME.fullmatch(c) for c in corpora):
        raise BoardError(f"{path}: corpora must be a nonempty list of distinct corpus names")
    for key in ("build", "verifier", "summary", "version", "language"):
        if type(entry[key]) is not str or "\n" in entry[key]:
            raise BoardError(f"{path}: {key} must be a one-line string")
    if not entry["verifier"]:
        raise BoardError(f"{path}: verifier must name the command the harness runs")
    if entry["tier"] == "community":
        for key in ("keyid", "public_key_hex", "key_url"):
            if type(entry.get(key)) is not str or not entry[key]:
                raise BoardError(f"{path}: a community entry declares {key}")
        if not HEX64.fullmatch(entry["public_key_hex"]) or not entry["key_url"].startswith("https://"):
            raise BoardError(f"{path}: public_key_hex is 64 hex and key_url is HTTPS")
    elif any(k in entry for k in ("keyid", "public_key_hex", "key_url")):
        raise BoardError(f"{path}: a verified entry is signed by the board runner and declares no key of its own")
    for xf in entry.get("xfail", []):
        if type(xf) is not dict or any(type(xf.get(k)) is not str or not xf[k] for k in ("corpus", "id", "reason", "link")):
            raise BoardError(f"{path}: each xfail needs corpus, id, reason and link")
        if xf["corpus"] not in corpora or not xf["link"].startswith("https://"):
            raise BoardError(f"{path}: xfail {xf['id']} names an unlisted corpus or a non-HTTPS link")
    return entry


def level_for(passed: int, total: int, refusals: int) -> str:
    if refusals == 0 and total > 0 and passed == total:
        return "Tier 1"
    if refusals == 0 and total > 0 and passed / total >= TIER2_FLOOR:
        return "Tier 2"
    return "Below Tier 2"


def verify_corpus(entry: dict, corpus: str, directory: Path, pins: dict, runner_keys: dict,
                  disputes: dict) -> CorpusResult:
    where = f"{directory.name}/{corpus}"
    report_raw, report = _json(directory / f"{corpus}.report.json")
    record_raw, envelope = _json(directory / f"{corpus}.dsse.json")
    keys = runner_keys if entry["tier"] == "verified" else {entry["keyid"]: bytes.fromhex(entry["public_key_hex"])}
    statement, signer = verify_envelope(envelope, keys, where)
    if statement.get("_type") != STATEMENT_TYPE or statement.get("predicateType") != PREDICATE_TYPE:
        raise BoardError(f"{where}: not a board run-record Statement")
    subjects = statement.get("subject")
    report_sha = hashlib.sha256(report_raw).hexdigest()
    if type(subjects) is not list or len(subjects) != 1 or type(subjects[0]) is not dict or \
            subjects[0].get("digest") != {"sha256": report_sha}:
        raise BoardError(f"{where}: the signed subject is not these report bytes")
    pred = statement.get("predicate")
    if type(pred) is not dict:
        raise BoardError(f"{where}: predicate missing")
    rep_corpus = report.get("corpus")
    if type(rep_corpus) is not dict or report.get("suite") != corpus:
        raise BoardError(f"{where}: report is not a run of corpus {corpus}")
    pin = pins.get((entry["release"], corpus))
    if pin is None:
        raise BoardError(f"{where}: release {entry['release']} of {corpus} is not pinned in corpus-releases.toml")
    if (rep_corpus.get("release"), rep_corpus.get("corpusDigest"), rep_corpus.get("manifestSha256"),
            rep_corpus.get("suiteRevision")) != (pin.release, pin.corpus_digest, pin.manifest_sha256, pin.suite_revision):
        raise BoardError(f"{where}: the report's corpus does not re-verify against the pinned {pin.tag} digests")
    totals = report.get("totals")
    if type(totals) is not dict or any(type(totals.get(k)) is not int for k in TOTAL_KEYS):
        raise BoardError(f"{where}: report totals incomplete")
    if totals["vectors"] != pin.vectors:
        raise BoardError(f"{where}: report replayed {totals['vectors']} vectors, the pinned corpus holds {pin.vectors}")
    expected = {
        "entry": entry["name"],
        "tier": entry["tier"],
        "implementation": {"repository": entry["repository"], "commit": entry["commit"], "version": entry["version"]},
        "command": {"toolchain": entry["toolchain"], "build": entry["build"], "verifier": entry["verifier"]},
        "corpus": {"name": corpus, "release": pin.release, "suiteRevision": pin.suite_revision,
                   "corpusDigest": pin.corpus_digest, "manifestSha256": pin.manifest_sha256},
        "totals": {k: totals[k] for k in TOTAL_KEYS},
    }
    for key, value in expected.items():
        if pred.get(key) != value:
            raise BoardError(f"{where}: signed predicate field {key} disagrees with the entry or the report")
    run = pred.get("run")
    if type(run) is not dict or type(run.get("url")) is not str or type(run.get("startedAt")) is not str:
        raise BoardError(f"{where}: predicate run needs url and startedAt")
    if not re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", run["startedAt"]):
        raise BoardError(f"{where}: run startedAt must be UTC seconds")
    if entry["tier"] == "verified" and not re.fullmatch(re.escape(RUN_URL_PREFIX) + r"\d+", run["url"]):
        raise BoardError(f"{where}: a Verified record names a run of this repository's board-run workflow")
    if not run["url"].startswith("https://"):
        raise BoardError(f"{where}: run url must be HTTPS")
    vectors = report.get("vectors")
    if type(vectors) is not list:
        raise BoardError(f"{where}: report has no vector rows")
    statuses: dict[str, str] = {}
    for v in vectors:
        if type(v) is not dict or type(v.get("id")) is not str or v.get("status") not in ("PASS", "FAIL"):
            raise BoardError(f"{where}: malformed vector row")
        if v["id"] in statuses:
            raise BoardError(f"{where}: vector {v['id']} reported twice")
        statuses[v["id"]] = v["status"]
    if len(statuses) != totals["vectors"] or sum(s == "PASS" for s in statuses.values()) != totals["pass"]:
        raise BoardError(f"{where}: vector rows disagree with the report totals")
    xfail = [xf for xf in entry.get("xfail", []) if xf["corpus"] == corpus]
    for xf in xfail:
        if statuses.get(xf["id"]) != "FAIL":
            raise BoardError(f"{where}: xfail {xf['id']} did not fail in this run; remove it")
    disputed = sorted(i for i in disputes.get((pin.release, corpus), set()) if i in statuses)
    scored = {i: s for i, s in statuses.items() if i not in disputed}
    scored_passed = sum(s == "PASS" for s in scored.values())
    return CorpusResult(corpus, pin.release, pin.suite_revision, pin.corpus_digest, totals["pass"], totals["vectors"],
                        scored_passed, len(scored), level_for(scored_passed, len(scored), totals["suiteRefusals"]),
                        run["url"], run["startedAt"], signer, hashlib.sha256(record_raw).hexdigest(), report_sha,
                        statuses, xfail, disputed)


def load_board(root: Path = ROOT) -> list[Row]:
    pins = load_pins(root)
    runner_keys = load_runner_keys(root)
    disputes = load_disputes(root)
    entries_dir = root / BOARD / "entries"
    rows: list[Row] = []
    for path in sorted(entries_dir.glob("*/entry.toml")) if entries_dir.exists() else []:
        entry = load_entry(path)
        row = Row(entry["name"], entry["summary"], entry["repository"], entry["commit"], entry["version"],
                  entry["language"], entry["tier"], entry["tier"], False, entry["toolchain"], entry["build"],
                  entry["verifier"])
        for corpus in entry["corpora"]:
            row.results[corpus] = verify_corpus(entry, corpus, path.parent, pins, runner_keys, disputes)
            newest = sorted({p.release for (_, c), p in pins.items() if c == corpus}, key=_release_key)[-RELEGATION_WINDOW:]
            if entry["tier"] == "verified" and entry["release"] not in newest:
                row.relegated = True
        expected_files = {"entry.toml"} | {f"{c}.{kind}.json" for c in entry["corpora"] for kind in ("report", "dsse")}
        extra = {p.name for p in path.parent.iterdir()} - expected_files
        if extra:
            raise BoardError(f"{path.parent.name}: unexpected files {sorted(extra)}")
        if row.relegated:
            row.shown_tier = "community"
        rows.append(row)
    if entries_dir.exists():
        stray = {p.name for p in entries_dir.iterdir() if p.is_dir()} - {r.name for r in rows}
        if stray:
            raise BoardError(f"board/entries: directories without entry.toml {sorted(stray)}")
    order = {"Tier 1": 0, "Tier 2": 1, "Below Tier 2": 2}
    rows.sort(key=lambda r: (r.shown_tier != "verified", order[r.level], r.name))
    return rows


def divergence(rows: list[Row]) -> dict[str, list[tuple[str, str]]]:
    """Per corpus release, the vectors exactly one listed implementation fails, with that implementation."""
    out: dict[str, list[tuple[str, str]]] = {}
    groups: dict[str, list[tuple[str, CorpusResult]]] = {}
    for row in rows:
        for corpus, result in row.results.items():
            groups.setdefault(f"{corpus} {result.release}", []).append((row.name, result))
    for key, members in sorted(groups.items()):
        if len(members) < 2:
            continue
        ids = set().union(*(set(r.statuses) for _, r in members))
        lone = []
        for vid in sorted(ids):
            failing = [name for name, r in members if r.statuses.get(vid) == "FAIL"]
            if len(failing) == 1 and all(vid in r.statuses for _, r in members):
                lone.append((vid, failing[0]))
        out[key] = lone
    return out


def esc(value: str) -> str:
    """Keep entry text literal inside Markdown table cells and paragraphs."""
    escaped = re.sub(r"([\\`*_{}\[\]()!#<>])", r"\\\1", html.escape(value, quote=False))
    return escaped.replace("|", "&#124;")


def code(value: str) -> str:
    """A command as an inline code span; a command holding a backtick or a pipe stays escaped text."""
    return esc(value) if "`" in value or "|" in value else f"`{value}`"


def tier_label(row: Row) -> str:
    if row.relegated:
        return "Community (relegated from Verified)"
    return "Verified" if row.shown_tier == "verified" else "Community"


def corpora_of(rows: list[Row]) -> list[str]:
    return sorted({c for r in rows for c in r.results})


def markdown(rows: list[Row], pins: dict[tuple[str, str], Pin]) -> str:
    corpora = corpora_of(rows)
    lines: list[str] = []
    latest = sorted({p.release for p in pins.values()}, key=_release_key)
    lines += [f"Pinned corpus releases: {', '.join(f'`v{r}`' for r in latest) or 'none'}. "
              f"Listed implementations: {len(rows)} "
              f"({sum(r.shown_tier == 'verified' for r in rows)} Verified, "
              f"{sum(r.shown_tier == 'community' for r in rows)} Community).", ""]
    if not rows:
        lines += ["No implementation is listed yet. The [listing policy](board-policy.html) says how to join.", ""]
    else:
        head = ["Implementation", "Tier", "Level", *[f"`{c}`" for c in corpora], "Release", "Evidence"]
        lines += ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
        for row in rows:
            cells = [f"[{esc(row.name)}](#impl-{row.name}) {esc(row.version)}", tier_label(row), row.level]
            for c in corpora:
                r = row.results.get(c)
                cells.append(f"{r.scored_passed} / {r.scored_total}" if r else "not run")
            release = sorted({r.release for r in row.results.values()}, key=_release_key)
            cells.append(", ".join(f"`v{x}`" for x in release))
            cells.append(f"[record](board/{row.name}.json)")
            lines.append("| " + " | ".join(cells) + " |")
        lines.append("")
    lines += ["## Divergence {#divergence}", "",
              "A vector that exactly one listed implementation fails is where the specification "
              "or that implementation needs a second look.", ""]
    div = divergence(rows)
    if not div:
        lines += ["This view needs two implementations run on the same corpus release.", ""]
    for key, lone in div.items():
        corpus, release = key.split(" ")
        lines.append(f"### `{corpus}` `v{release}` {{#divergence-{corpus}-{release.replace('.', '-')}}}")
        lines.append("")
        if not lone:
            lines += ["Every listed implementation agrees on every vector.", ""]
            continue
        lines += ["| Vector | The one implementation that fails it |", "|---|---|"]
        lines += [f"| `{vid}` | [{esc(name)}](#impl-{name}) |" for vid, name in lone]
        lines.append("")
    lines += ["## Implementations {#implementations}", ""]
    for row in rows:
        lines += [f"### {esc(row.name)} {{#impl-{row.name}}}", "", esc(row.summary), "",
                  "| Field | Value |", "|---|---|",
                  f"| Tier | {tier_label(row)} |",
                  f"| Level | {row.level} |",
                  f"| Source | [{esc(row.repository)}]({row.repository}/tree/{row.commit}) at `{row.commit[:12]}` |",
                  f"| Version | {esc(row.version)} |",
                  f"| Language | {esc(row.language)} |",
                  f"| Build | {code(row.build) if row.build else 'none'} |",
                  f"| Verifier | {code(row.verifier)} |",
                  f"| JSON | [board/{row.name}.json](board/{row.name}.json) |",
                  f"| Badge | [board/{row.name}.badge.json](board/{row.name}.badge.json) |",
                  ""]
        lines += ["| Corpus | Release | Passed / scored | Disputed | Expected failures | Run | Signed record |",
                  "|---|---|---|---|---|---|---|"]
        for c, r in sorted(row.results.items()):
            xf = ", ".join(f"[`{x['id']}`]({x['link']})" for x in r.xfail) or "none"
            lines.append(f"| `{c}` | `v{r.release}` rev {r.suite_revision} | {r.scored_passed} / {r.scored_total} | "
                         f"{len(r.disputed)} | {xf} | [{r.run_started}]({r.run_url}) | "
                         f"[DSSE](board/{row.name}/{c}.dsse.json), [report](board/{row.name}/{c}.report.json) |")
        lines += ["", "Badge for a README:", "", "```markdown",
                  f"[![agent-evidence-vectors]"
                  f"(https://img.shields.io/endpoint?url={BASE_URL}board/{row.name}.badge.json)]"
                  f"({BASE_URL}board.html#impl-{row.name})",
                  "```", ""]
    return "\n".join(lines).rstrip("\n") + "\n"


def row_json(row: Row) -> dict:
    return {
        "name": row.name, "summary": row.summary, "tier": row.shown_tier, "claimedTier": row.claimed_tier,
        "relegated": row.relegated, "level": row.level,
        "implementation": {"repository": row.repository, "commit": row.commit, "version": row.version,
                           "language": row.language},
        "command": {"toolchain": row.toolchain, "build": row.build, "verifier": row.verifier},
        "page": f"{BASE_URL}board.html#impl-{row.name}",
        "results": [{
            "corpus": r.corpus, "release": r.release, "suiteRevision": r.suite_revision,
            "corpusDigest": r.corpus_digest, "passed": r.passed, "total": r.total,
            "scoredPassed": r.scored_passed, "scoredTotal": r.scored_total, "level": r.level,
            "disputed": r.disputed, "xfail": r.xfail, "run": {"url": r.run_url, "startedAt": r.run_started},
            "signer": r.signer,
            "record": {"url": f"{BASE_URL}board/{row.name}/{r.corpus}.dsse.json", "sha256": r.record_sha256},
            "report": {"url": f"{BASE_URL}board/{row.name}/{r.corpus}.report.json", "sha256": r.report_sha256},
        } for _, r in sorted(row.results.items())],
    }


def badge(row: Row) -> dict:
    """A shields.io endpoint document."""
    scored = sum(r.scored_passed for r in row.results.values())
    total = sum(r.scored_total for r in row.results.values())
    releases = sorted({r.release for r in row.results.values()}, key=_release_key)
    color = {"Tier 1": "brightgreen", "Tier 2": "yellow"}.get(row.level, "red")
    if row.shown_tier != "verified":
        color = {"Tier 1": "green", "Tier 2": "yellow"}.get(row.level, "red")
    message = f"{tier_label(row).split(' ')[0]} {row.level} {scored}/{total} v{releases[-1]}"
    return {"schemaVersion": 1, "label": "agent-evidence-vectors", "message": message, "color": color}


def public_files(root: Path, rows: list[Row]) -> dict[str, bytes]:
    """Files published under docs/: the index, one JSON twin and badge per row, and the signed bytes."""
    def dump(value: object) -> bytes:
        return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("ascii")
    files = {"board/index.json": dump({
        "predicateType": PREDICATE_TYPE,
        "policy": f"{BASE_URL}board-policy.html",
        "implementations": [row_json(r) for r in rows],
    })}
    for row in rows:
        files[f"board/{row.name}.json"] = dump(row_json(row))
        files[f"board/{row.name}.badge.json"] = dump(badge(row))
        for corpus in row.results:
            for kind in ("dsse", "report"):
                src = root / BOARD / "entries" / row.name / f"{corpus}.{kind}.json"
                files[f"board/{row.name}/{corpus}.{kind}.json"] = src.read_bytes()
    return files


def predicate_page() -> str:
    """The page the predicate type URI resolves to: a pointer at the policy section that defines it."""
    target = "../board-policy.html#run-record"
    return ("<!DOCTYPE html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\" />\n"
            "<title>Board run record v1</title>\n"
            f"<link rel=\"canonical\" href=\"{BASE_URL}board-policy.html#run-record\" />\n"
            f"<meta http-equiv=\"refresh\" content=\"0; url={target}\" />\n</head>\n<body>\n"
            f"<p><code>{PREDICATE_TYPE}</code> is defined in the "
            f"<a href=\"{target}\">board listing policy</a>.</p>\n</body>\n</html>\n")


def plan(root: Path, name: str) -> list[str]:
    """The runner inputs of one entry, as GITHUB_OUTPUT lines."""
    if not NAME.fullmatch(name):
        raise BoardError(f"entry name {name!r} is not valid")
    entry = load_entry(root / BOARD / "entries" / name / "entry.toml")
    for corpus in entry["corpora"]:
        if (entry["release"], corpus) not in load_pins(root):
            raise BoardError(f"{name}: release {entry['release']} of {corpus} is not pinned")
    owner_repo = entry["repository"].removeprefix("https://github.com/").rstrip("/")
    if not re.fullmatch(r"[A-Za-z0-9-]+/[A-Za-z0-9._-]+", owner_repo):
        raise BoardError(f"{name}: repository is not OWNER/NAME on GitHub")
    return [f"repository={owner_repo}", f"commit={entry['commit']}", f"toolchain={entry['toolchain']}",
            f"toolchain_version={entry.get('toolchain_version', '')}", f"build={entry['build']}",
            f"verifier={entry['verifier']}", f"release={entry['release']}", f"tier={entry['tier']}",
            f"corpora={json.dumps(entry['corpora'])}"]


def main(argv: list[str]) -> int:
    try:
        if argv[:1] == ["check"] and len(argv) == 1:
            rows = load_board(ROOT)
            for row in rows:
                cells = ", ".join(f"{c} {r.scored_passed}/{r.scored_total}" for c, r in sorted(row.results.items()))
                print(f"{row.name}: {tier_label(row)}, {row.level}, {cells}")
            print(f"board: {len(rows)} rows verified")
            return 0
        if argv[:1] == ["plan"] and len(argv) == 2:
            print("\n".join(plan(ROOT, argv[1])))
            return 0
    except BoardError as exc:
        print(f"board: {exc}", file=sys.stderr)
        return 1
    print(__doc__.split("\n\n")[0], file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
