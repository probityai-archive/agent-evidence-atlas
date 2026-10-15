# Version ledger

Component releases, source tags and the documentation built from them

Draft. Site version 0.6-draft, 2026-10-01. Rebuilt on every change; the digests let a reader check that a page matches the version recorded here.

<a id="component-versions"></a>

## Component versions

These are publication records at the read time shown. The source column names the commit behind each release or tag, after peeling annotated tags. A repository can publish a harness and a case package at different versions.

| Component and artifact | Publication role | Version | Source commit | Read (UTC) | Scope |
|----|----|----|----|----|----|
| [Probity Admission](start.md#admission) / Python digest checker | Published release | [py-v0.1.0](https://github.com/probityai/agent-evidence-admission/releases/tag/py-v0.1.0) | [`0004d2333a84`](https://github.com/probityai/agent-evidence-admission/tree/0004d2333a841c95658d4a9c75232f0913ca7141) | 2026-10-15 | This release is the digest-check package. Admission policy and budget tasks retain their own source pins. |
| [Checkout composition reference](start.md#checkout-runner) / Composition CLI and Action | Source tag | [0.2.0](https://github.com/probityai/agent-checkout-runner/tree/v0.2.0) | [`297b5b182bb4`](https://github.com/probityai/agent-checkout-runner/tree/297b5b182bb40605b62586eccbf93a9c68a4aee1) | 2026-10-15 | A bounded synthetic composition reference. The source tag pins the CLI and Action, not a registry release or a merchant deployment. |
| [dsse](start.md#dsse) / Rust crate | Published release | [0.1.2](https://github.com/probityai/dsse/releases/tag/v0.1.2) | [`ec451793f5f5`](https://github.com/probityai/dsse/tree/ec451793f5f5b670ff4033721e424b1a80e52e3e) | 2026-10-15 | Signature verification checks bytes under caller-selected keys, not the truth of the payload. |
| [jcs-admit](start.md#jcs-admit) / Rust crate | Published release | [0.1.1](https://github.com/probityai/jcs-admit/releases/tag/v0.1.1) | [`33603fc8caf6`](https://github.com/probityai/jcs-admit/tree/33603fc8caf6f8469ea790f41ab74ae64d4f1658) | 2026-10-15 | Canonicalization and raw-input admission are separate from envelope verification. |
| [Probity Ratchet](start.md#ratchet) / Harness source | Source tag | [0.1.2](https://github.com/probityai/ratchet/tree/probity-ratchet-v0.1.2) | [`e2daf77f75e9`](https://github.com/probityai/ratchet/tree/e2daf77f75e92aa961cf184084335b67aaae7581) | 2026-10-15 | Annotated harness tag, peeled to its source commit. It is separate from the public case package. |
| [Probity Ratchet](start.md#ratchet) / Public case suite | Published release | [0.2.0](https://github.com/probityai/ratchet/releases/tag/probity-ratchet-cases-v0.2.0) | [`b6504260db8a`](https://github.com/probityai/ratchet/tree/b6504260db8af7d3746e9ac87740430dd988e8d9) | 2026-10-15 | The case package has its own release. All shipped splits are public. |
| [Probity Vectors](start.md#vectors) / Go verifier and Python harness | Published release | [0.18.1](https://github.com/probityai/agent-evidence-vectors/releases/tag/v0.18.1) | [`33d545104ff2`](https://github.com/probityai/agent-evidence-vectors/tree/33d545104ff2f8c124cff465c96c013eeb809156) | 2026-10-15 | The reviewed guide also carries a 0.18.0 install recipe. Select the version required by your result. |
| [Probity Vocabulary](start.md#vocabulary) / Vocabulary registry | Published release | [v0.4.0](https://github.com/probityai/agent-evidence-vocabulary/releases/tag/v0.4.0) | [`220a4f0a08b9`](https://github.com/probityai/agent-evidence-vocabulary/tree/220a4f0a08b90a555a430bb7d4334eb2617d05ba) | 2026-10-15 | Terms and crosswalks are versioned independently of executable packages. |

<a id="choose-the-pin-for-your-task"></a>

### Choose the pin for your task

- **Install or integrate:** use a component's [reviewed guide](start.md), then keep the exact package version or source commit its recipe selects. A guide can deliberately use an older release.
- **Repeat a tested installation:** use the recipe's recorded source, environment, command and retained output. A release number alone is not an install result.
- **Cite or replay a result:** retain the source and artifact digests in that result. [Lab records](lab.md), historical examples and citation snapshots do not move when a new release appears.

<a id="documentation-revisions"></a>

## Documentation revisions

A digest here is the SHA-256 of the artifact's source file in the site's repository, truncated to 16 hexadecimal characters for display. A change to the source changes the digest, and a change that alters what a page claims also gets a new version and a note.

| artifact | version | date | status | source SHA-256 (first 16) | note |
|----|----|----|----|----|----|
| [Home page](index.md) | 1.13 | 2026-10-15 | draft | `43db68137bee6879` `src/index.md` | The essay link carries its retitled name, Independent AI evaluators need evidence they can verify |
| Essay | 0.2 | 2026-09-27 | held | page not built in this repository yet | Held until it passes its release criteria |
| [Atlas](atlas.md) | 0.6-preview | 2026-10-14 | draft | `19d9ad2d6464bc5a` `data/atlas.toml` | Current releases read again (vocabulary v0.4.0, admission py-v0.1.0, dsse 0.1.2); admission and dsse limits quoted from their current READMEs; 25 star counts refreshed; the closed OWASP pull request removed from the contributions |
| Verifier demonstration | 0.1 | 2026-09-27 | held | page not built in this repository yet | Held until it passes its release criteria |
| [Experiments](experiments.md) | 0.4 | 2026-10-15 | draft | `9e216ec17d2fead0` `src/experiments.md` | Adds checkout composition and historical event references; retained experiments and Lab run bytes stay unchanged |
| Series plan | 0.1 | 2026-09-27 | held | page not built in this repository yet | Held until it passes its release criteria |
| [Claim ledger](claims.md) | 0.8.25 | 2026-10-15 | draft | `21e72b77c251e0fd` `CLAIMS.md` | Adds canonical component release identities and precise source, guide, install and historical pin roles |
| [Probity Open Evidence Lab](lab.md) | 0.1.11 | 2026-10-06 | draft | `c1fc9700bcf8794a` `src/lab.md` | Links the retained-run browser; existing retained records, artifacts and protocol remain unchanged |
| [Claim status](status.md) | 0.1 | 2026-10-13 | draft | `c88f8056051d6d8a` `src/status.md` | Generated from the Lab register and the open-cell data: verdict and operation-class totals, every record, and the open cells |
| [Task-grouped rates worked example](task-grouped-rates.md) | 0.1 | 2026-10-03 | draft | `92940ce8ee827ad0` `examples/task-grouped-rates/input.json` | Authored labels, paired task resampling, explicit weighting targets and unresolved outcomes |
| [Published robot controls companion](provael-task-controls.md) | 0.1 | 2026-10-03 | draft | `20b90c1ae59c399d` `examples/provael-task-controls/source-record.json` | Original publisher simulator labels, matched controls, corrected interpretation and exact paired task weights |
| [APS and PriorSeal pilot status](pilot.md) | 0.1.1 | 2026-10-01 | proposed | `e3026b2b60ceca12` `src/pilot.md` | Probity-owned proposal, merged technical replay, owner slots and acceptance gates; no formal pilot agreement |
| [Authored policy vocabulary finding](vocabulary-findings.md) | 0.1 | 2026-10-03 | draft | `20af3bbeb2180633` `src/vocabulary-findings.md` | Fixed action vocabulary raises the finite authored score; all default quality rows hold |
| [Authored tool-argument finding](tool-argument-findings.md) | 0.1 | 2026-10-03 | draft | `958f2a8c3268901a` `src/tool-argument-findings.md` | Preserves all native attempts, abstention failures and separate scoped-evidence publication/quality holds |
| [Project catalog](start.md) | 0.9 | 2026-10-15 | draft | `4c0508f4847ff68c` `data/catalog.json` | Refreshes reviewed source routes, adds Ratchet and public digest/case tasks, and reads release values from the existing Atlas records |
| [Automation guide](automation.md) | 0.1 | 2026-10-03 | draft | `375c2d92a75e7d34` `src/automation.md` | Catalog lookups, checked run records and result submissions |
| [Catalog maintenance guide](catalog.md) | 0.5 | 2026-10-15 | draft | `5151dce6311de2cf` `src/catalog.md` | Documents the shared release source, peeled tag identities and distinct recipe and citation pins |
| [Retained evidence decision walkthrough](replay-an-evidence-decision.md) | 0.4 | 2026-10-15 | draft | `42fe897cf7c5df85` `src/replay-an-evidence-decision.md` | The essay link carries its retitled name |
| [Retained-run browser](runs.md) | 0.1 | 2026-10-06 | draft | `6a2ac67797c7adf9` `src/runs.md` | Search, exact claim-result filters and complete static navigation over the existing Lab register; no aggregate run grade |
| [Published source routes](start.md) | 0.2 | 2026-10-15 | draft | `bb6f64daab1ac682` `data/catalog-sources.json` | Appends reviewed public README sources without replacing earlier source reviews |
| [Caller-declared APS and PriorSeal replay guide](replay-tools.md) | 0.1 | 2026-10-06 | draft | `8a4458c31bfb7496` `src/replay-tools.md` | Links one complete v2 procedure, explicit caller declarations, hashes of files read at invocation and actual process outputs; historical results stay unchanged |
| [Historical report and diagnostic retained record](runs.md) | 0.1 | 2026-10-06 | draft | `892a154384a1c6d9` `experiments/w3c-report-replay-2026-10-06/report.json` | Original historical report outputs and separate diagnostic controls with maintained data-only accounting; no new native or independent-operator claim |
| [Test outcomes and evidence conclusions](evidence-test-meaning.md) | 0.1 | 2026-10-06 | draft | `044d31da81f1f6c0` `src/evidence-test-meaning.md` | Worked hypothetical refund story with historical package pins, retained per-case data and a maintained Lab checking route |
| [Approved SQL illustration](approved-sql.md) | 0.1.0 | 2026-10-09 | illustration | `8a43f0b206be9201` `src/approved-sql.md` | Checked supplied-record comparison; native audit pair and independent reader remain separate contributions |
| [Request and effect join cases](request-effect-join.md) | 0.1 | 2026-10-09 | proposed | `65dd24d41527d3b5` `src/request-effect-join.md` | Selected producer contract and separate pre-dispatch, post-commit and target-coverage cases |
| [Synthetic authority, report and observation controls](authority-effect-cases.md) | 0.1.0 | 2026-10-09 | \[synthetic controls\]{.label .synthetic controls} | `1a237d760c9e90d7` `src/authority-effect-cases.md` | Authored supplied-record comparisons, source attribution and an installed-package gate; live effects, independent observation and outside operation remain separate |

[HTML view](versions.html) | [Agent guide](llms.txt)
