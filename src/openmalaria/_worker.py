from __future__ import annotations

import argparse
import os
import pickle
from typing import Any

import pandas as pd

from ._openmalaria import OpenMalariaError as _NativeOpenMalariaError
from ._openmalaria import _run  # pyright: ignore[reportPrivateUsage]


def _run_direct(
    *,
    xml: str | None,
    path: str | None,
    resource_path: str,
    validate_only: bool,
    verbose: bool,
    progress: bool,
    seed: int | None,
) -> dict[str, Any]:
    raw = _run(
        xml=xml,
        path=path,
        resource_path=resource_path,
        validate_only=validate_only,
        verbose=verbose,
        progress=progress,
        seed=seed,
    )

    survey_df = pd.DataFrame(
        {
            "survey": raw.survey.survey,
            "column": raw.survey.column,
            "measure": raw.survey.measure,
            "value": raw.survey.value,
        }
    )

    continuous_df = None
    if raw.continuous.column_titles:
        continuous_df = pd.DataFrame(dict(enumerate(raw.continuous.columns)))
        continuous_df.columns = [
            title.strip() for title in raw.continuous.column_titles
        ]

    return {"survey": survey_df, "continuous": continuous_df}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--in", dest="infile", required=True)
    parser.add_argument("--out", dest="outfile", required=True)
    parser.add_argument("--cwd", dest="cwd", required=True)
    args = parser.parse_args()

    os.chdir(args.cwd)

    with open(args.infile, "rb") as f:
        job: dict[str, Any] = pickle.load(f)

    try:
        result = _run_direct(**job)
        outcome = {"ok": True, "result": result}
    except _NativeOpenMalariaError as e:
        outcome = {"ok": False, "error": str(e)}
    except Exception as e:  # noqa: BLE001
        outcome = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    with open(args.outfile, "wb") as f:
        pickle.dump(outcome, f)


if __name__ == "__main__":
    main()
