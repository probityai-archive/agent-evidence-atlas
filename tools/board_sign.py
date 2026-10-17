#!/usr/bin/env python3
"""Sign one harness report as a board run record (a DSSE envelope over an in-toto Statement).

    python3 tools/board_sign.py --entry board/entries/NAME/entry.toml --corpus CORPUS \
        --report report.json --run-url URL --started-at 2026-10-17T00:00:00Z \
        --key-env BOARD_RUNNER_KEY --keyid KEYID --out CORPUS.dsse.json

The private key is a 64-character hex Ed25519 seed read from the named environment
variable, never from an argument or a file. The record is checked with the same
code the board build runs before it is written, so a record this tool writes is a
record the build accepts, and a report the pins reject is never signed.

The board runner signs Verified records in the sign job of
.github/workflows/board-run.yml, which never executes the implementation under test.
A Community submitter runs the same tool with their own key, declared in entry.toml.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

sys.path.insert(0, str(Path(__file__).resolve().parent))
import board  # noqa: E402


def statement(entry: dict, corpus: str, report: dict, report_raw: bytes, pin: board.Pin,
              run_url: str, started_at: str) -> dict:
    return {
        "_type": board.STATEMENT_TYPE,
        "subject": [{"name": f"{corpus}.report.json", "digest": {"sha256": hashlib.sha256(report_raw).hexdigest()}}],
        "predicateType": board.PREDICATE_TYPE,
        "predicate": {
            "entry": entry["name"],
            "tier": entry["tier"],
            "implementation": {"repository": entry["repository"], "commit": entry["commit"], "version": entry["version"]},
            "command": {"toolchain": entry["toolchain"], "build": entry["build"], "verifier": entry["verifier"]},
            "corpus": {"name": corpus, "release": pin.release, "suiteRevision": pin.suite_revision,
                       "corpusDigest": pin.corpus_digest, "manifestSha256": pin.manifest_sha256},
            "totals": {k: report["totals"][k] for k in board.TOTAL_KEYS},
            "run": {"url": run_url, "startedAt": started_at},
        },
    }


def sign(payload: bytes, seed_hex: str, keyid: str) -> dict:
    key = Ed25519PrivateKey.from_private_bytes(bytes.fromhex(seed_hex))
    sig = key.sign(board.pae(board.PAYLOAD_TYPE, payload))
    return {"payloadType": board.PAYLOAD_TYPE, "payload": base64.b64encode(payload).decode("ascii"),
            "signatures": [{"keyid": keyid, "sig": base64.b64encode(sig).decode("ascii")}]}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--entry", type=Path, required=True)
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--report", type=Path, required=True)
    ap.add_argument("--run-url", required=True)
    ap.add_argument("--started-at", required=True)
    ap.add_argument("--key-env", required=True)
    ap.add_argument("--keyid", required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--root", type=Path, default=board.ROOT, help="board repository root (pins, keys)")
    args = ap.parse_args(argv)
    seed = os.environ.get(args.key_env, "")
    if not board.HEX64.fullmatch(seed):
        print(f"board_sign: ${args.key_env} must hold a 64-character lowercase hex Ed25519 seed", file=sys.stderr)
        return 2
    try:
        entry = board.load_entry(args.entry.resolve())
        if args.corpus not in entry["corpora"]:
            raise board.BoardError(f"{entry['name']} does not list corpus {args.corpus}")
        pins = board.load_pins(args.root)
        pin = pins.get((entry["release"], args.corpus))
        if pin is None:
            raise board.BoardError(f"release {entry['release']} of {args.corpus} is not pinned")
        report_raw = args.report.read_bytes()
        report = json.loads(report_raw)
        payload = json.dumps(statement(entry, args.corpus, report, report_raw, pin, args.run_url, args.started_at),
                             sort_keys=True, separators=(",", ":")).encode("utf-8")
        envelope = sign(payload, seed, args.keyid)
        # Prove the record with the build's own verifier before writing it.
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / entry["name"]
            probe.mkdir()
            shutil.copyfile(args.entry, probe / "entry.toml")
            (probe / f"{args.corpus}.report.json").write_bytes(report_raw)
            (probe / f"{args.corpus}.dsse.json").write_text(json.dumps(envelope, indent=2) + "\n", encoding="ascii")
            board.verify_corpus(entry, args.corpus, probe, pins, board.load_runner_keys(args.root),
                                board.load_disputes(args.root))
    except (board.BoardError, OSError, ValueError, KeyError) as exc:
        print(f"board_sign: refused: {exc}", file=sys.stderr)
        return 1
    args.out.write_text(json.dumps(envelope, indent=2) + "\n", encoding="ascii")
    print(f"board_sign: wrote {args.out} ({entry['name']} {args.corpus} {report['totals']['pass']}/{report['totals']['vectors']})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
