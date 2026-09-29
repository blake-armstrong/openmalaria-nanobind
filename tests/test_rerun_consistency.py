from __future__ import annotations

import pytest
from _regression_helpers import (
    OM_BOXTEST_NAMES,
    assert_matches_expected,
    assert_results_identical,
    run_scenario,
)


@pytest.mark.parametrize("name", OM_BOXTEST_NAMES)
def test_two_runs_in_same_process_match_and_are_consistent(name):
    result1 = run_scenario(name)
    result2 = run_scenario(name)

    assert_matches_expected(result1, name)
    assert_matches_expected(result2, name)
    assert_results_identical(result1, result2)
