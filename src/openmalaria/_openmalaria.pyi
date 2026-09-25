from typing import Annotated

import numpy
from numpy.typing import NDArray


class SurveyData:
    @property
    def survey(self) -> Annotated[NDArray[numpy.int32], dict(shape=(None,))]: ...

    @property
    def column(self) -> Annotated[NDArray[numpy.int32], dict(shape=(None,))]: ...

    @property
    def measure(self) -> Annotated[NDArray[numpy.int32], dict(shape=(None,))]: ...

    @property
    def value(self) -> Annotated[NDArray[numpy.float64], dict(shape=(None,))]: ...

class ContinuousData:
    @property
    def column_titles(self) -> list[str]: ...

    @property
    def columns(self) -> list[Annotated[NDArray[numpy.float64], dict(shape=(None,))]]: ...

class RawRunResult:
    @property
    def survey(self) -> SurveyData: ...

    @property
    def continuous(self) -> ContinuousData: ...

class VersionInfo:
    @property
    def program_version(self) -> str: ...

    @property
    def schema_version(self) -> int: ...

def _run(xml: str | None = None, path: str | None = None, resource_path: str = '', validate_only: bool = False, verbose: bool = False, progress: bool = False, seed: int | None = None) -> RawRunResult: ...

def _version() -> VersionInfo: ...

MEASURE_CODES: dict[str, int]

class OpenMalariaError(Exception):
    pass
