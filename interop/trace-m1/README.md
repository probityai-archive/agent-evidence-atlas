# Independent M1 consumer

This original Probity reader checks signed native-result bytes, an explicit held report and its optional execution context. It preserves the native outcome and reason. It imports no REMORA runtime or reference verifier. The frozen producer source is [REMORA PR 822](https://github.com/darklordVirtual/REMORA-research/pull/822); INPUT-MANIFEST.json records the exact source and per-file digests.

Run from this directory:

```sh
uv sync --locked --group dev
uv run --locked python src/fetch_inputs.py
uv run --locked python src/replay.py --out results/replay-r1
```

For a fresh checkout, `bash scripts/qualify.sh` fetches the inputs and runs the controls, source checks and coverage gate. The downloaded third-party fixtures stay local and retain their upstream license. This repository distributes the original reader and controls.

The supported profile uses ASCII JSON, unique string keys, safe integers, bounded populations, canonical base64, explicit report selection and the fixture retention value. It rejects extra fields and unsupported claim upgrades. Signature verification also checks point admissibility using [libsodium's documented subgroup check](https://doc.libsodium.org/advanced/point-arithmetic). The ASCII serializer follows [RFC 8785's string rules](https://www.rfc-editor.org/rfc/rfc8785.html#section-3.2.2.2). This bounded profile is not general JCS or TRACE conformance.

A bound native result is a reported producer result. The reader does not establish its truth, workload identity, authority or effects. An unsigned external-evidence mapping cannot become a TRACE Trust Record or conformance level through this comparison. Our refusal codes remain separate from the producer's codes.
