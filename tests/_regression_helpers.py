from __future__ import annotations

import os
import shutil

import numpy as np
import pandas as pd
from conftest import CORE_TEST_DIR, EXPECTED_DIR, SCHEMA_FILE

import openmalaria as om

OM_BOXTEST_NAMES = [
    "1",
    "4",
    "5",
    "6",
    "9",
    "10",
    "11",
    "12",
    "2ITNs",
    "Cohort",
    "EffectiveDrug",
    "Empirical",
    "ESTS",
    "Genotypes",
    "IRS30",
    "KK_20150612",
    "LifeNet1",
    "LifeNet2",
    "Molineaux",
    "MolPairwise",
    "MSAT",
    "MSAT_HRP2",
    "NamawalaArabiensis",
    "NoInterv",
    "NoMPDLarviciding",
    "Penny",
    "Rach5IC",
    "SimpleMPDLarviciding",
    "SimpleMPDTest",
    "SubPopRemoval",
    "TrapTest",
    "TriggeredMSAT",
    "VecFullTest",
    "VecMonthly",
    "VecTest",
    "Vivax",
    "NonHumanHosts",
    "PEV",
    "BSV",
    "TBV",
    "DecisionTree5DayDielmo",
    "HetVecDailyEIR",
    "AvailabilityFilter",
    "GaussianCopulaGamma",
    "GaussianCopulaLognormal",
    "InfectionOrigin",
    "ModelNameNoOverrides",
    "ModelNameParamOverrides",
    "ModelNameModelOptionOverrides",
    "ModelNameManyOverrides",
    "ExactNv0",
]


def read_expected_output(path):
    return pd.read_csv(
        path, sep="\t", header=None, names=["survey", "column", "measure", "value"]
    )


def read_expected_ctsout(path):
    return pd.read_csv(path, sep="\t", skiprows=1)


def dedup_columns(names):
    seen = {}
    result = []
    for name in names:
        if name in seen:
            seen[name] += 1
            result.append(f"{name}.{seen[name]}")
        else:
            seen[name] = 0
            result.append(name)
    return result


def run_scenario(name: str, tmp_path):
    scenario_src = CORE_TEST_DIR / f"scenario{name}.xml"
    shutil.copy(SCHEMA_FILE, tmp_path / "scenario_current.xsd")
    scenario_path = tmp_path / f"scenario{name}.xml"
    shutil.copy(scenario_src, scenario_path)

    old_cwd = os.getcwd()
    os.chdir(tmp_path)
    try:
        return om.run(path=str(scenario_path), resource_path=str(CORE_TEST_DIR))
    finally:
        os.chdir(old_cwd)


def assert_matches_expected(result, name: str):
    expected_output = EXPECTED_DIR / f"output{name}.txt"
    expected_ctsout = EXPECTED_DIR / f"ctsout{name}.txt"

    survey = result["survey"]
    expected = read_expected_output(expected_output)
    assert survey.shape == expected.shape
    assert (
        survey[["survey", "column", "measure"]].to_numpy()
        == expected[["survey", "column", "measure"]].to_numpy()
    ).all()
    assert np.allclose(
        survey["value"].to_numpy(), expected["value"].to_numpy(), rtol=1e-5, atol=1e-5
    )

    continuous = result["continuous"]
    if continuous is not None and expected_ctsout.exists():
        expected_cts = read_expected_ctsout(expected_ctsout)
        assert dedup_columns(list(continuous.columns)) == list(expected_cts.columns)
        assert continuous.shape == expected_cts.shape
        assert np.allclose(
            continuous.to_numpy(dtype=float),
            expected_cts.to_numpy(dtype=float),
            rtol=1e-6,
            atol=1e-6,
            equal_nan=True,
        )


def assert_results_identical(result1, result2):
    survey1, survey2 = result1["survey"], result2["survey"]
    assert survey1.shape == survey2.shape
    assert (
        survey1[["survey", "column", "measure"]].to_numpy()
        == survey2[["survey", "column", "measure"]].to_numpy()
    ).all()
    assert (survey1["value"].to_numpy() == survey2["value"].to_numpy()).all()

    continuous1, continuous2 = result1["continuous"], result2["continuous"]
    assert (continuous1 is None) == (continuous2 is None)
    if continuous1 is not None:
        assert list(continuous1.columns) == list(continuous2.columns)
        assert continuous1.shape == continuous2.shape
        assert np.array_equal(
            continuous1.to_numpy(dtype=float),
            continuous2.to_numpy(dtype=float),
            equal_nan=True,
        )
