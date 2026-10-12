# Check a signed result and its selected report

Independent consumer of REMORA's public M1 fixtures.

A signed result can identify a report without proving that the reported action happened. This reader checks that distinction against [REMORA's published mapping fixtures](https://github.com/darklordVirtual/REMORA-research/pull/822).

Probity wrote and operated the reader separately from REMORA. It imports no REMORA runtime or reference verifier. Its author had read the producer protocol and expected cases; this is a comparison against known answers.

The retained run agrees with all 12 expected decisions: three results bind to their selected reports and nine inputs are refused. A bound `CONTRADICTED` result keeps its native outcome and reason. The reader preserves report identity, commitment, sequence and explicit selection. Its refusal codes remain separate from REMORA's codes.

[Inspect the retained result](interop/trace-m1/retained/public-report.json) or [read the qualification record](interop/trace-m1/retained/QUALIFICATION.json). The qualification passed 118 controls and the coverage gate for every production module. The controls include changed report selection, Boolean sequences, unsupported fields, invalid signing points and unsupported claim upgrades.

To run the [original reader and controls](https://github.com/probityai/agent-evidence-atlas/tree/main/interop/trace-m1), use a fresh checkout:

``` sh
cd interop/trace-m1
bash scripts/qualify.sh
```

The fetcher checks each input's digest against a manifest that names the producer commit. Third-party fixtures stay local under their upstream license. The public report omits producer expected mappings and declared context bodies.

This checks a bounded synthetic population. A verified signature does not establish workload identity, authority, effects or the truth of the native result. An unsigned external-evidence mapping does not become a TRACE Trust Record or conformance level. The supported ASCII JSON profile is narrower than general JCS.

[Find other retained runs](runs.md) or [bring an evidence question to the Lab](lab.md).

[HTML view](trace-m1-consumer.html) | [Agent guide](llms.txt)
