# Choose a component

Start with the task you need.

Vectors tests how a verifier behaves. Verify checks a supplied claim against evidence bytes.

A published release, a reviewed guide and a tested installation are different pins. Use the exact recipe and source named by the result you reproduce. The [version ledger](versions.md#component-versions) records release and source roles.

| Task | Project |
|----|----|
| Check artifact digests or evaluate admission policies | [Probity Admission](#admission) |
| Run an APS refund example with safe retries | [Probity APS refund example](#aps-refund-retries) |
| Check an artifact against a document's named digest | [Probity artifact digest check](#artifact-digest-check) |
| Choose a tool or inspect recorded claims and retained runs | [Probity Atlas](#atlas) |
| Run a checkout composition and replay its retained claims | [Checkout composition reference](#checkout-runner) |
| Sign and verify DSSE envelopes in Rust | [dsse](#dsse) |
| Read selected retained Inspect execution profiles | [Probity native Inspect reader](#inspect-native-reader) |
| Reject duplicate JSON keys and canonicalize in Rust | [jcs-admit](#jcs-admit) |
| Check published MintID trace records | [Probity MintID trace reader](#mintid-trace-records-v2) |
| Record file actions or check native delegation evidence | [Probity Observer](#observer) |
| Check an agent guard against replay and regression cases | [Probity Ratchet](#ratchet) |
| Test an agent on public fault and benign cases | [Probity Ratchet public cases](#ratchet-cases) |
| Test a verifier against conformance cases | [Probity Vectors](#vectors) |
| Install a pinned verifier and check an evidence claim | [Probity Verify](#verify) |
| Use shared definitions for agent evidence claims | [Probity Vocabulary](#vocabulary) |
| Check a selected run against retained witness anchors | [Probity witnessed run selection](#witnessed-run-selection) |

<a id="admission"></a>

## Probity Admission

Component ID: `admission`.

Provides a Python artifact-digest checker, admission policies for OPA, Kyverno and policy-controller, and a pre-call budget reservation API.

Draft. [Reviewed guide and source](https://github.com/probityai/agent-evidence-admission/blob/c8f34fe857a969a5a503e0792466b76797d66355/README.md)

Python digest checker: published release [py-v0.1.0](https://github.com/probityai/agent-evidence-admission/releases/tag/py-v0.1.0), source [`0004d2333a84`](https://github.com/probityai/agent-evidence-admission/tree/0004d2333a841c95658d4a9c75232f0913ca7141), read 2026-10-15. This release is the digest-check package. Admission policy and budget tasks retain their own source pins.

<a id="aps-refund-retries"></a>

## Probity APS refund example

Profile ID: `aps-refund-retries`. Component ID: `observer`.

Runs a local APS refund example that ties retries to approved actions and retains records for a separate reader.

Prototype. [Reviewed guide and source](https://github.com/probityai/agent-evidence-observer/blob/753932b42b00ab8257396112c529f840396f0ce7/docs/APS-REFUND-RETRIES.md)

<a id="artifact-digest-check"></a>

## Probity artifact digest check

Profile ID: `artifact-digest-check`. Component ID: `admission`.

Checks an artifact against digests named by a TEA document, CycloneDX SBOM or VEX, or in-toto statement.

Released. [Reviewed guide and source](https://github.com/probityai/agent-evidence-admission/blob/c8f34fe857a969a5a503e0792466b76797d66355/python/README.md)

<a id="atlas"></a>

## Probity Atlas

Component ID: `atlas`.

Provides task-based project navigation, agent assurance documentation and an Open Evidence Lab run register.

Draft. [Reviewed guide and source](https://github.com/probityai/agent-evidence-atlas/blob/ec67f0375e008cb7befc19a31762490b5cbbe520/README.md)

<a id="checkout-runner"></a>

## Checkout composition reference

Component ID: `checkout-runner`.

Runs a bounded synthetic checkout and refund composition as a CLI or Action, with separate decisions, attempts, effects and observations for offline replay.

Released. [Reviewed guide and source](https://github.com/probityai/agent-checkout-runner/blob/297b5b182bb40605b62586eccbf93a9c68a4aee1/README.md)

Composition CLI and Action: source tag [0.2.0](https://github.com/probityai/agent-checkout-runner/tree/v0.2.0), source [`297b5b182bb4`](https://github.com/probityai/agent-checkout-runner/tree/297b5b182bb40605b62586eccbf93a9c68a4aee1), read 2026-10-15. A bounded synthetic composition reference. The source tag pins the CLI and Action, not a registry release or a merchant deployment.

<a id="dsse"></a>

## dsse

Component ID: `dsse`.

Signs and verifies DSSE envelopes with explicit threshold and key handling.

Released. [Reviewed guide and source](https://github.com/probityai/dsse/blob/8549e5e54080b5f8c864f8b3eba8f57af8bd9c51/README.md)

Rust crate: published release [0.1.2](https://github.com/probityai/dsse/releases/tag/v0.1.2), source [`ec451793f5f5`](https://github.com/probityai/dsse/tree/ec451793f5f5b670ff4033721e424b1a80e52e3e), read 2026-10-15. Signature verification checks bytes under caller-selected keys, not the truth of the payload.

<a id="inspect-native-reader"></a>

## Probity native Inspect reader

Profile ID: `inspect-native-reader`. Component ID: `observer`.

Reads selected retained Inspect execution profiles offline, preserving errors and unstarted attempts. Inspect accepted the catalog entry, and the live Inspect extensions catalog lists it as of October 14, 2026.

Prototype. [Reviewed guide and source](https://github.com/probityai/agent-evidence-observer/blob/71ac0b2126473316655184235000647a6dd0f5cf/docs/NATIVE-CONSUMER-CI.md)

<a id="jcs-admit"></a>

## jcs-admit

Component ID: `jcs-admit`.

Checks raw JSON input before producing its RFC 8785 canonical form.

Released. [Reviewed guide and source](https://github.com/probityai/jcs-admit/blob/0a058d7b676fb452929337c528b893c7f2121062/README.md)

Rust crate: published release [0.1.1](https://github.com/probityai/jcs-admit/releases/tag/v0.1.1), source [`33603fc8caf6`](https://github.com/probityai/jcs-admit/tree/33603fc8caf6f8469ea790f41ab74ae64d4f1658), read 2026-10-15. Canonicalization and raw-input admission are separate from envelope verification.

<a id="mintid-trace-records-v2"></a>

## Probity MintID trace reader

Profile ID: `mintid-trace-records-v2`. Component ID: `jcs-admit`.

Reads published MintID trace records after raw JSON admission and checks source-bound evidence and actor attribution.

Prototype. [Reviewed guide and source](https://github.com/probityai/jcs-admit/blob/fb32a68aa2772e51cee32bc14835075d88af3953/interop/mintid-trace-records-v2/README.md)

<a id="observer"></a>

## Probity Observer

Component ID: `observer`.

Records brokered file actions with signed packets and history, and reads selected native delegation evidence offline.

Prototype. [Reviewed guide and source](https://github.com/probityai/agent-evidence-observer/blob/f9fd4a13fb31da5f990fd8da82472ed4cedb5f97/README.md)

<a id="ratchet"></a>

## Probity Ratchet

Component ID: `ratchet`.

Provides a source-tagged agent guard harness, signed admission records and public regression cases.

Released. [Reviewed guide and source](https://github.com/probityai/ratchet/blob/b2800b26ec6cf60fee8e95682660846f674f97c2/README.md)

Harness source: source tag [0.1.2](https://github.com/probityai/ratchet/tree/probity-ratchet-v0.1.2), source [`e2daf77f75e9`](https://github.com/probityai/ratchet/tree/e2daf77f75e92aa961cf184084335b67aaae7581), read 2026-10-15. Annotated harness tag, peeled to its source commit. It is separate from the public case package.

Public case suite: published release [0.2.0](https://github.com/probityai/ratchet/releases/tag/probity-ratchet-cases-v0.2.0), source [`b6504260db8a`](https://github.com/probityai/ratchet/tree/b6504260db8af7d3746e9ac87740430dd988e8d9), read 2026-10-15. The case package has its own release. All shipped splits are public.

<a id="ratchet-cases"></a>

## Probity Ratchet public cases

Profile ID: `ratchet-cases`. Component ID: `ratchet`.

Grades agent tasks in a simulated company on final state, with declared tool faults, traps and benign cases. All shipped splits are public.

Released. [Reviewed guide and source](https://github.com/probityai/ratchet/blob/b6504260db8af7d3746e9ac87740430dd988e8d9/probity-ratchet-cases/README.md)

<a id="vectors"></a>

## Probity Vectors

Component ID: `vectors`.

Provides conformance cases and reference verifiers for selected agent evidence formats.

Released. [Reviewed guide and source](https://github.com/probityai/agent-evidence-vectors/blob/9e596fbff7bb29809d38319aebb56f2141923eb2/README.md)

Go verifier and Python harness: published release [0.18.1](https://github.com/probityai/agent-evidence-vectors/releases/tag/v0.18.1), source [`33d545104ff2`](https://github.com/probityai/agent-evidence-vectors/tree/33d545104ff2f8c124cff465c96c013eeb809156), read 2026-10-15. The reviewed guide also carries a 0.18.0 install recipe. Select the version required by your result.

<a id="verify"></a>

## Probity Verify

Component ID: `verify`.

Checks supplied evidence bytes through claim-specific offline adapters. Its README links to source-pinned installation and checked task recipes.

Unreleased. [Reviewed guide and source](https://github.com/probityai/probity-verify/blob/2ecdbafc0c6cc0f26461ffe913fe342e7de090a6/README.md)

<a id="vocabulary"></a>

## Probity Vocabulary

Component ID: `vocabulary`.

Defines versioned terms and crosswalks for claims about agent execution.

Released. [Reviewed guide and source](https://github.com/probityai/agent-evidence-vocabulary/blob/220a4f0a08b90a555a430bb7d4334eb2617d05ba/README.md)

Vocabulary registry: published release [v0.4.0](https://github.com/probityai/agent-evidence-vocabulary/releases/tag/v0.4.0), source [`220a4f0a08b9`](https://github.com/probityai/agent-evidence-vocabulary/tree/220a4f0a08b90a555a430bb7d4334eb2617d05ba), read 2026-10-15. Terms and crosswalks are versioned independently of executable packages.

<a id="witnessed-run-selection"></a>

## Probity witnessed run selection

Profile ID: `witnessed-run-selection`. Component ID: `observer`.

Checks a supplied run against consumer-retained witness anchors, plan and control pins, and execution closure.

Prototype. [Reviewed guide and source](https://github.com/probityai/agent-evidence-observer/blob/d53776c7b783abbce42a3422f56ed390dfedd2f2/docs/WITNESSED-RUN-SELECTION.md)

<a id="run-and-share-a-check"></a>

## Run and share a check

The [Open Evidence Lab](lab.md) holds replayable runs and accepts new results and corrections. For scripted lookups, use the [automation guide](automation.md).

For a combined CLI and Action example, use the [checkout composition reference](experiments.md#checkout-composition). It keeps decisions, attempts, effects and observations separate in a replayable synthetic bundle.

[HTML view](start.html) | [Agent guide](llms.txt)
