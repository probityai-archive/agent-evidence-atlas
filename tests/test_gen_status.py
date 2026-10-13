"""Pin the claim status page's verdict mapping, operation-class rule and freshness check."""
import importlib.util
import json
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("gen_status", ROOT / "tools/gen_status.py")
gen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gen)


def record(rid, results, roles):
    return {"id": rid, "evidenceClaim": "public-fixture-check", "reviewState": "retained", "roles": roles,
            "limits": [], "claimResults": [{"claim": f"c{i}", "result": r} for i, r in enumerate(results)],
            "report": f"../experiments/{rid}/report.json", "provenance": f"../experiments/{rid}/provenance.json",
            "contract": "https://github.com/example/tool/blob/0123456789abcdef/README.md"}


def open_cells():
    return {"cell": [{"mechanism": "mech:a", "mechanism_title": "A", "property": "prop:x", "property_title": "X",
                      "property_question": "is x so", "words": "a cannot show x", "url": "https://example.org/a",
                      "basis": "states the limit", "excerpt": "cannot show x"},
                     {"mechanism": "mech:b", "mechanism_title": "B", "property": "prop:x", "property_title": "X",
                      "property_question": "is x so", "words": "b cannot show x", "url": "https://example.org/b",
                      "basis": "states the scope", "excerpt": "b does y"}],
            "start": [{"rank": 1, "mechanism": "mech:b", "property": "prop:x", "passing_case": "a passing case shows x"}]}


@pytest.mark.parametrize("result, verdict", [
    ("pass", "ESTABLISHED"), ("fail", "CONTRADICTED"),
    ("not-exercised", "NOT_ESTABLISHED"), ("out-of-scope", "NOT_ESTABLISHED")])
def test_verdict_mapping(result, verdict):
    assert gen.verdict(result) == verdict


def test_unknown_result_is_refused():
    with pytest.raises(ValueError):
        gen.verdict("passed")


@pytest.mark.parametrize("roles, expected", [
    ({"runner": "Probity-owned GitHub Actions", "independentOperation": "not-established"}, "Probity-operated"),
    ({"fixtureOperator": "Probity"}, "Probity-operated"),
    ({"atlasOperator": "Probity", "independentOperation": "Probity operated the reader separately; not independent of Probity"}, "Probity-operated"),
    ({"fixtureOperator": "same-operator-fixture", "atlasReplay": "author-produced", "independentOperation": "not-established"}, "author-operated"),
    ({"runner": "a producer's agent under its author's mandate"}, "author-operated"),
    ({"runner": "Probity-owned GitHub Actions", "independentOperation": "established"}, "independently operated"),
    ({"historicalRunner": "outside lab", "independentOperator": "established"}, "independently operated"),
])
def test_operation_class_rule(roles, expected):
    assert gen.operation_class(roles) == expected


def test_record_without_operator_role_is_refused():
    with pytest.raises(ValueError):
        gen.operation_class({"readerAuthor": "Probity", "independentEffectCustody": "not-established"})


def test_totals_count_each_result_under_its_record_class():
    register = {"records": [
        record("p-run", ["pass", "fail", "not-exercised", "out-of-scope"], {"runner": "Probity CI"}),
        record("a-run", ["pass", "pass"], {"fixtureOperator": "same-operator-fixture"})]}
    page = gen.render(register, open_cells())
    assert "| ESTABLISHED (`pass`) | 1 | 2 | 0 | **3** |" in page
    assert "| CONTRADICTED (`fail`) | 1 | 0 | 0 | **1** |" in page
    assert "| NOT_ESTABLISHED, out of scope (`out-of-scope`) | 1 | 0 | 0 | **1** |" in page
    assert "| records | 1 | 1 | 0 | **2** |" in page
    assert "| 1 | 1 | 2 (1 out of scope) | Probity-operated |" in page
    assert "no record here was independently operated" in page


def test_start_cells_lead_and_are_not_repeated():
    page = gen.render({"records": [record("p-run", ["pass"], {"runner": "Probity CI"})]}, open_cells())
    start, rest = page.split("## Every open cell", 1)
    assert "**B x X**" in start and "a passing case shows x" in start
    assert "b cannot show x" not in rest and "a cannot show x" in rest


def test_start_entry_must_name_an_open_cell():
    cells = open_cells()
    cells["start"][0]["mechanism"] = "mech:missing"
    with pytest.raises(ValueError):
        gen.render({"records": [record("p-run", ["pass"], {"runner": "Probity CI"})]}, cells)


def test_committed_page_matches_its_data():
    register = json.loads((ROOT / "data/lab-register.json").read_text(encoding="utf-8"))
    cells = tomllib.loads((ROOT / "data/open-cells.toml").read_text(encoding="utf-8"))
    assert (ROOT / "src/status.md").read_text(encoding="utf-8") == gen.render(register, cells)
