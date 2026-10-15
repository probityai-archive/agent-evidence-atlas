"""Package and Action controls must retain their actual task and source bindings."""
import re
from html.parser import HTMLParser
from pathlib import Path

import pytest

import discovery

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def public():
    return discovery.load_public(ROOT)


@pytest.fixture
def versions(public):
    return discovery.component_versions(public)


def test_only_actual_registry_packages_get_distribution_controls(versions):
    observed = {(row["component"], row.get("profile"), row["registry"], row["package"])
                for row in versions if "registry" in row}
    assert observed == {
        ("vectors", None, "pypi", "agent-evidence-vectors"),
        ("admission", "artifact-digest-check", "pypi", "agent-evidence-admission"),
        ("ratchet", "ratchet-cases", "pypi", "probity-ratchet-cases"),
        ("jcs-admit", None, "crates", "jcs-admit"),
        ("dsse", None, "crates", "dsse"),
    }


def test_tag_namespace_is_not_an_independently_authored_package_version(versions):
    row = next(row for row in versions if row["component"] == "admission")
    assert row["version"] == "py-v0.1.0"
    assert discovery.package_version(row) == "0.1.0"
    assert discovery.registry_links(row)["download"] == "https://pypi.org/project/agent-evidence-admission/0.1.0/#files"
    with pytest.raises(discovery.catalog.CatalogError, match="prefix does not match"):
        discovery.package_version({**row, "version_prefix": "different-"})


def test_downloads_keep_release_identity_while_live_badges_use_current_registry(versions):
    for row in versions:
        if "registry" not in row:
            continue
        links = discovery.registry_links(row)
        assert discovery.package_version(row) in links["download"]
        assert discovery.package_version(row) not in links["version_badge"]
        if row["registry"] == "pypi":
            assert links["statistics"] == "https://pepy.tech/projects/" + row["package"]
            assert "/pepy/dt/" in links["download_badge"]
            assert "mirrors" in links["download_badge"]
        else:
            assert links["download"].endswith("/download")
            assert "/crates/d/" in links["download_badge"]


@pytest.mark.parametrize("change, message", [
    ({"registry": "npm"}, "known registry"),
    ({"package": "../../foreign"}, "released package identity"),
    ({"kind": "source-tag"}, "released package identity"),
    ({"install_anchor": "install\" onclick=\"bad"}, "anchor is invalid"),
    ({"version_prefix": ""}, "prefix does not match"),
    ({"version": "not-a-package-version", "version_prefix": "not-"}, "exact package version"),
    ({"action_guide": "../README.md#install"}, "safe pinned source"),
    ({"action_guide": "https://foreign.example/README.md#install"}, "safe pinned source"),
    ({"action_guide": "README.md"}, "safe pinned source"),
    ({"workflow": "../ci.yml", "workflow_name": "CI"}, "named workflow"),
    ({"workflow": "ci.yml"}, "named workflow"),
    ({"workflow": "ci.yml", "workflow_name": "CI | product seal"}, "plain ASCII"),
])
def test_invalid_distribution_metadata_is_refused(versions, change, message):
    row = next(row for row in versions if row["component"] == "admission").copy()
    for field in ("display_name", "url", "source_url"):
        row.pop(field)
    row.update(change)
    with pytest.raises(discovery.catalog.CatalogError, match=message):
        discovery.check_component_version_fields(row)


@pytest.mark.parametrize("change, message", [
    ({"profile": "inspect-native-reader"}, "profile does not belong"),
    ({"profile": "unknown-profile"}, "profile does not belong"),
    ({"package": "probity-ratchet-cases"}, "package does not belong"),
])
def test_package_and_profile_cannot_move_to_an_unrelated_task(public, versions, change, message):
    row = next(row for row in versions if row["component"] == "admission")
    with pytest.raises(discovery.catalog.CatalogError, match=message):
        discovery.check_distribution_binding({**row, **change}, public)


def test_profile_distributions_do_not_promote_the_broader_component(public, versions):
    page = discovery.start_markdown(public, versions)
    admission = page.split("## Probity Admission {#admission}", 1)[1].split("\n## ", 1)[0]
    harness = page.split("## Probity Ratchet {#ratchet}", 1)[1].split("\n## ", 1)[0]
    assert "Draft." in admission and "pepy" not in admission
    assert "probity-ratchet-cases / recorded package release" not in harness
    for profile in ("artifact-digest-check", "ratchet-cases"):
        section = page.split("{#" + profile + "}", 1)[1].split("\n## ", 1)[0]
        assert "Download release files" in section and "Download statistics" in section


def test_action_buttons_retain_reviewed_guide_sources(public, versions):
    page = discovery.start_markdown(public, versions)
    assert "9e596fbff7bb29809d38319aebb56f2141923eb2/docs/guides/runner.md#run-the-suite-in-ci" in page
    assert "297b5b182bb40605b62586eccbf93a9c68a4aee1/README.md#run-it-in-your-own-ci" in page
    assert "Vectors ci workflow status" in page
    assert "Checkout runner run workflow status" in page
    assert "Windows" not in page
    assert "product passing" not in page


def test_action_guide_cannot_borrow_another_repository_or_missing_review(public, versions):
    import json
    sources = json.loads((ROOT / "data/catalog-sources.json").read_text())
    repositories = {row["id"]: row for row in public["repositories"]}
    row = next(row for row in versions if row["component"] == "vectors")
    assert "full_name" not in repositories[row["repository"]]
    discovery.check_action_source(row, repositories, sources)
    with pytest.raises(discovery.catalog.CatalogError, match="retained source review"):
        discovery.check_action_source(row, repositories, [])
    runner = next(row for row in versions if row["component"] == "checkout-runner")
    with pytest.raises(discovery.catalog.CatalogError, match="does not belong"):
        discovery.check_action_source({**row, "action_guide": runner["action_guide"]}, repositories, sources)


def test_a_workflow_filename_can_contain_periods(versions):
    row = next(row for row in versions if row["component"] == "vectors").copy()
    for field in ("display_name", "url", "source_url"):
        row.pop(field)
    row["workflow"] = "ci.qualified.yaml"
    discovery.check_component_version_fields(row)


def test_a_readme_refresh_does_not_move_a_reviewed_action_recipe(public, versions):
    row = next(row for row in versions if row["component"] == "vectors")
    changed = {**public, "repositories": [dict(record) for record in public["repositories"]]}
    for repository in changed["repositories"]:
        if repository["id"] == row["repository"]:
            repository["source"] = {**repository["source"], "commit": "a" * 40}
    markup = discovery.distribution_markup(row, changed)
    assert row["action_guide"] in markup
    assert "a" * 40 not in markup


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.images = []

    def handle_starttag(self, tag, attrs):
        row = dict(attrs)
        if tag == "a":
            self.links.append(row["href"])
        if tag == "img":
            self.images.append(row)


def test_badges_have_accessible_names_and_actions_survive_image_failure(public, versions):
    markup = "\n".join(discovery.distribution_markup(row, public) for row in versions)
    parser = Links()
    parser.feed(markup)
    assert len(parser.images) == 12
    assert all(row["alt"].strip() and row["height"] == "20" for row in parser.images)
    without_images = re.sub(r"<img[^>]+>", "", markup)
    fallback = Links()
    fallback.feed(without_images)
    assert fallback.links == parser.links
    for label in ("Install", "Download release files", "Registry release", "Download statistics", "Use pinned Action"):
        assert ">" + label + "</a>" in without_images
