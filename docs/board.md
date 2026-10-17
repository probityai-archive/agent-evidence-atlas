# Conformance board

Implementations scored against agent-evidence-vectors, every row a signed record the build re-verifies

Every row below is backed by a signed run record. The site build re-verifies each record's signature, its report digest and its pinned corpus release before it renders the row, and stops on any record that does not verify. **Verified** rows were run by this board's own runner; **Community** rows were run and signed by their submitters. The [listing policy](board-policy.md) says how to join, what each tier and level means, and how disputes work.

Put the check in your own CI with the [agent-evidence-vectors Action](https://github.com/probityai/agent-evidence-vectors/blob/main/action.yml), then ask for a Verified run.

Pinned corpus releases: `v0.19.0`. Listed implementations: 0 (0 Verified, 0 Community).

No implementation is listed yet. The [listing policy](board-policy.md) says how to join.

<a id="divergence"></a>

## Divergence

A vector that exactly one listed implementation fails is where the specification or that implementation needs a second look.

This view needs two implementations run on the same corpus release.

<a id="implementations"></a>

## Implementations

<a id="impact"></a>

## Impact

Where the suite is already required or run outside this repository:

- [in-toto/attestation#588](https://github.com/in-toto/attestation/pull/588), the AI Agent Action predicate proposal, pins agent-evidence-vectors as its conformance suite.
- Five public repositories outside this organisation call the suite from their own CI workflows: agent-passport-system, AgentAvow, Rul1an/aee-checker, MoltyCel/moltrust-api and darklordVirtual/REMORA-research (GitHub code search, 2026-10-16).

<a id="machine-readable"></a>

## Machine-readable

- [board/index.json](board/index.json): every row, its level, digests and links to its signed records.
- `board/<name>.json` and `board/<name>.badge.json` for each implementation, listed with its row.

[HTML view](board.html) | [Agent guide](llms.txt)
