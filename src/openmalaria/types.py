from __future__ import annotations

from typing import TypedDict

import pandas as pd


class OMRunResult(TypedDict):
    """The dict openmalaria.run() itself returns."""

    survey: pd.DataFrame
    continuous: pd.DataFrame | None
