from __future__ import annotations

import os
import re
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

import openmalaria as om


def _read_expected_output(path: Path) -> pd.DataFrame:
    return pd.read_csv(
        path, sep="\t", header=None, names=["survey", "column", "measure", "value"]
    )


def _read_expected_ctsout(path: Path) -> pd.DataFrame:
    return pd.read_csv(path, sep="\t", skiprows=1)


def test_survey_schema_and_values(scenario1_result, expected_output1):
    survey = scenario1_result["survey"]

    assert list(survey.columns) == ["survey", "column", "measure", "value"]
    assert survey["survey"].dtype.kind == "i"
    assert survey["column"].dtype.kind == "i"
    assert survey["measure"].dtype.kind == "i"
    assert survey["value"].dtype.kind == "f"
    assert len(survey) > 0

    expected = _read_expected_output(expected_output1)
    assert survey.shape == expected.shape
    assert (
        survey[["survey", "column", "measure"]].to_numpy()
        == expected[["survey", "column", "measure"]].to_numpy()
    ).all()
    assert np.allclose(
        survey["value"].to_numpy(), expected["value"].to_numpy(), rtol=1e-5, atol=1e-5
    )


def test_continuous_schema_and_values(scenario1_result, expected_ctsout1):
    continuous = scenario1_result["continuous"]
    assert continuous is not None

    expected = _read_expected_ctsout(expected_ctsout1)
    assert list(continuous.columns) == list(expected.columns)
    assert continuous.shape == expected.shape
    assert np.allclose(
        continuous.to_numpy(dtype=float),
        expected.to_numpy(dtype=float),
        rtol=1e-6,
        atol=1e-6,
        equal_nan=True,
    )


def test_version():
    v = om.version()
    assert set(v.keys()) == {"program_version", "schema_version"}
    assert isinstance(v["program_version"], str) and v["program_version"]
    assert isinstance(v["schema_version"], int) and v["schema_version"] > 0


def test_core_commit():
    assert re.fullmatch(r"[0-9a-f]{40}", om.CORE_COMMIT)


def test_schema_version_matches_engine_and_packaged_xsd():
    assert om.SCHEMA_VERSION == om.version()["schema_version"]
    xsd = ET.parse(Path(om.SCHEMA_DIR) / "scenario_current.xsd").getroot()
    assert xsd.attrib["targetNamespace"] == (
        f"http://openmalaria.org/schema/scenario_{om.SCHEMA_VERSION}"
    )


def test_missing_scenario_raises(tmp_path):
    with pytest.raises(om.OpenMalariaError):
        om.run(path=str(tmp_path / "does_not_exist.xml"))


def test_xsd_error_message_includes_diagnostics(scenario1_path, resource_path):
    xml = re.sub(r'popSize="\d+"', 'popSize="abc"', scenario1_path.read_text())
    with pytest.raises(om.OpenMalariaError, match="abc"):
        om.run(xml=xml, resource_path=resource_path, validate_only=True)


def test_xml_and_path_both_given_raises():
    with pytest.raises(ValueError):
        om.run(xml="<x/>", path="dummy.xml")


def test_neither_xml_nor_path_raises():
    with pytest.raises(ValueError):
        om.run()


def test_validate_only_is_fast_and_empty(scenario1_path, resource_path):
    r = om.run(
        path=str(scenario1_path), resource_path=resource_path, validate_only=True
    )
    assert r["survey"].shape == (0, 4)
    assert r["continuous"] is None


def test_xml_matches_path(scenario1_path, resource_path):
    xml_content = scenario1_path.read_text()
    r = om.run(xml=xml_content, resource_path=resource_path)
    assert r["survey"].shape[0] > 0
    assert list(r["survey"].columns) == ["survey", "column", "measure", "value"]


def test_packaged_schema_is_used_by_default(
    scenario1_path, resource_path, tmp_path, monkeypatch
):
    monkeypatch.chdir(tmp_path)
    r = om.run(
        path=str(scenario1_path), resource_path=resource_path, validate_only=True
    )
    assert r["survey"].shape == (0, 4)
    assert os.getcwd() == str(tmp_path)


def test_schema_dir_overrides_packaged_schema(scenario1_path, resource_path, tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    with pytest.raises(om.OpenMalariaError):
        om.run(
            path=str(scenario1_path),
            resource_path=resource_path,
            schema_dir=str(empty),
            validate_only=True,
        )

    custom = tmp_path / "custom"
    custom.mkdir()
    shutil.copy(Path(om.SCHEMA_DIR) / "scenario_current.xsd", custom)
    r = om.run(
        path=str(scenario1_path),
        resource_path=resource_path,
        schema_dir=str(custom),
        validate_only=True,
    )
    assert r["survey"].shape == (0, 4)


def test_relative_paths_resolve_against_caller_cwd(
    scenario1_path, resource_path, monkeypatch
):
    monkeypatch.chdir(scenario1_path.parent.parent)
    relative = os.path.join(scenario1_path.parent.name, scenario1_path.name)

    r = om.run(path=relative, resource_path=resource_path, validate_only=True)
    assert r["survey"].shape == (0, 4)


def test_empty_resource_path_is_caller_cwd(
    scenario1_result, resource_path, monkeypatch
):
    monkeypatch.chdir(resource_path)
    r = om.run(path="scenario1.xml", resource_path="")
    assert r["survey"].equals(scenario1_result["survey"])


def test_packaged_resources_present():
    assert sorted(os.listdir(om.RESOURCE_DIR)) == [
        "autoRegressionParameters.csv",
        "densities.csv",
    ]


def test_default_resource_path_is_packaged(
    scenario1_path, scenario1_result, tmp_path, monkeypatch
):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    r = om.run(path=str(scenario1_path))
    assert r["survey"].equals(scenario1_result["survey"])


def test_repeated_calls_in_same_process_succeed(scenario1_path, resource_path):
    r1 = om.run(path=str(scenario1_path), resource_path=resource_path)
    r2 = om.run(path=str(scenario1_path), resource_path=resource_path)
    assert (r1["survey"]["value"].to_numpy() == r2["survey"]["value"].to_numpy()).all()


def test_tmp_dir_is_used_and_cleaned_up_by_default(
    scenario1_path, resource_path, tmp_path
):
    custom_tmp = tmp_path / "custom_tmp"
    custom_tmp.mkdir()

    om.run(
        path=str(scenario1_path), resource_path=resource_path, tmp_dir=str(custom_tmp)
    )

    assert list(custom_tmp.iterdir()) == []


def test_keep_tmp_preserves_pickle_files_under_tmp_dir(
    scenario1_path, resource_path, tmp_path
):
    custom_tmp = tmp_path / "custom_tmp"
    custom_tmp.mkdir()

    om.run(
        path=str(scenario1_path),
        resource_path=resource_path,
        tmp_dir=str(custom_tmp),
        keep_tmp=True,
    )

    entries = list(custom_tmp.iterdir())
    assert len(entries) == 1
    run_dir = entries[0]
    assert run_dir.name.startswith("openmalaria-run-")
    assert (run_dir / "in.pkl").exists()
    assert (run_dir / "out.pkl").exists()


def test_keep_tmp_prints_kept_path_on_stderr(scenario1_path, resource_path, capsys):
    om.run(path=str(scenario1_path), resource_path=resource_path, keep_tmp=True)

    captured = capsys.readouterr()
    assert "openmalaria: kept tmp files at " in captured.err
    kept_path = captured.err.strip().rsplit(" at ", 1)[1]
    assert os.path.isdir(kept_path)
    assert os.path.exists(os.path.join(kept_path, "in.pkl"))
    assert os.path.exists(os.path.join(kept_path, "out.pkl"))
    shutil.rmtree(kept_path)
