from __future__ import annotations

import os
import pickle
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from . import _openmalaria
from .errors import OpenMalariaError
from .types import OMRunResult

__all__ = [
    "CORE_COMMIT",
    "MEASURE_CODES",
    "OMRunResult",
    "OpenMalariaError",
    "run",
    "version",
]

CORE_COMMIT: str = _openmalaria.CORE_COMMIT
MEASURE_CODES: dict[str, int] = _openmalaria.MEASURE_CODES


def run(
    *,
    xml: str | None = None,
    path: str | None = None,
    resource_path: str = "",
    validate_only: bool = False,
    verbose: bool = False,
    progress: bool = False,
    seed: int | None = None,
    schema_dir: str | None = None,
    tmp_dir: str | None = None,
    keep_tmp: bool = False,
) -> OMRunResult:
    if (xml is None) == (path is None):
        raise ValueError("exactly one of xml= or path= must be given")

    if schema_dir is None:
        worker_cwd = os.getcwd()
    else:
        worker_cwd = os.path.abspath(schema_dir)
        if path is not None:
            path = os.path.abspath(path)
        if resource_path:
            resource_path = os.path.abspath(resource_path)

    job = {
        "xml": xml,
        "path": path,
        "resource_path": resource_path,
        "validate_only": validate_only,
        "verbose": verbose,
        "progress": progress,
        "seed": seed,
    }

    tmp_path = tempfile.mkdtemp(prefix="openmalaria-run-", dir=tmp_dir)
    try:
        in_path = os.path.join(tmp_path, "in.pkl")
        out_path = os.path.join(tmp_path, "out.pkl")
        with open(in_path, "wb") as f:
            pickle.dump(job, f)

        package_dir = os.path.dirname(os.path.abspath(__file__))
        worker_launch_dir = os.path.dirname(package_dir)
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "openmalaria._worker",
                "--in",
                in_path,
                "--out",
                out_path,
                "--cwd",
                worker_cwd,
            ],
            cwd=worker_launch_dir,
            check=False,
        )

        if not os.path.exists(out_path):
            msg = (
                f"openmalaria worker subprocess exited with code {proc.returncode} "
                "before producing a result"
            )
            if keep_tmp:
                msg += f"; input/output pickles kept at {tmp_path}"
            raise OpenMalariaError(msg)

        with open(out_path, "rb") as f:
            outcome = pickle.load(f)
    finally:
        if not keep_tmp:
            shutil.rmtree(tmp_path)

    if keep_tmp:
        print(f"openmalaria: kept tmp files at {tmp_path}", file=sys.stderr)

    if not outcome["ok"]:
        raise OpenMalariaError(outcome["error"])
    return outcome["result"]


def version() -> dict[str, Any]:
    v = _openmalaria._version()  # pyright: ignore[reportPrivateUsage]
    return {"program_version": v.program_version, "schema_version": v.schema_version}
