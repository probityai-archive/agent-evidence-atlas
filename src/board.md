---
title: "Conformance board"
subtitle: "Implementations scored against agent-evidence-vectors, every row a signed record the build re-verifies"
description: "Verified and Community rows of agent evidence verifiers, scored against pinned agent-evidence-vectors releases, with a divergence view, a JSON twin and a badge per implementation."
---

Every row below is backed by a signed run record. The site build re-verifies each record's
signature, its report digest and its pinned corpus release before it renders the row, and stops on
any record that does not verify. **Verified** rows were run by this board's own runner;
**Community** rows were run and signed by their submitters. The [listing policy](board-policy.html)
says how to join, what each tier and level means, and how disputes work.

Put the check in your own CI with the
[agent-evidence-vectors Action](https://github.com/probityai/agent-evidence-vectors/blob/main/action.yml),
then ask for a Verified run.

<!-- conformance-board -->

## Impact {#impact}

Where the suite is already required or run outside this repository:

- [in-toto/attestation#588](https://github.com/in-toto/attestation/pull/588), the AI Agent Action
  predicate proposal, pins agent-evidence-vectors as its conformance suite.
- Five public repositories outside this organisation call the suite from their own CI workflows:
  agent-passport-system, AgentAvow, Rul1an/aee-checker, MoltyCel/moltrust-api and
  darklordVirtual/REMORA-research (GitHub code search, 2026-10-16).

## Machine-readable {#machine-readable}

- [board/index.json](board/index.json): every row, its level, digests and links to its signed records.
- `board/<name>.json` and `board/<name>.badge.json` for each implementation, listed with its row.
