from __future__ import annotations

import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
CORE_DIR = REPO_ROOT / "core"
CORE_TEST_DIR = CORE_DIR / "test"
RESOURCE_DIR = CORE_TEST_DIR
EXPECTED_DIR = CORE_TEST_DIR / "expected"


@pytest.fixture(scope="session")
def resource_path() -> str:
    return str(RESOURCE_DIR)


@pytest.fixture
def scenario1_path(tmp_path: Path) -> Path:
    dest = tmp_path / "scenario1.xml"
    shutil.copy(CORE_TEST_DIR / "scenario1.xml", dest)
    return dest


@pytest.fixture(scope="session")
def scenario1_result(resource_path):
    import openmalaria as om

    return om.run(
        path=str(CORE_TEST_DIR / "scenario1.xml"), resource_path=resource_path
    )


@pytest.fixture
def expected_output1() -> Path:
    return EXPECTED_DIR / "output1.txt"


@pytest.fixture
def expected_ctsout1() -> Path:
    return EXPECTED_DIR / "ctsout1.txt"
