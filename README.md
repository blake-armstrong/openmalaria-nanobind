# openmalaria-nanobind

Minimal Python bindings for
[OpenMalaria](https://github.com/OpenMalaria-Org/openmalaria), built with
[nanobind](https://github.com/wjakob/nanobind). Runs a scenario in a fresh
subprocess per call and returns pandas DataFrames directly. **Bypasses the need
to read an XML from the disk, and writing results to the disk.**

NOTE: This is **NOT** a *workflow*. This repo provides a small and concise way
to connect the OpenMalaria C++ code to Python as a library call. This repo does
not add additional functionality to OpenMalaria. It is just an environment that
provides a consistent way to run OpenMalaria through Python, handle exceptions,
and provide small typings for returned information.

Published on PyPI as `openmalaria` and imported as `import openmalaria`.
Analysis helpers built on top of `run()` (survey reshaping, age groups, rates)
live separately in
[openmalaria-python](https://github.com/blake-armstrong/openmalaria-python)
(`pip install openmalaria-tools`, `import openmalaria_tools`). Everything in
this repo is intended as a candidate for upstreaming (see
[Upstreaming](#upstreaming)).

## Install

This repo depends on the
[openmalaria](https://github.com/blake-armstrong/openmalaria) C++ core as a git
submodule (`core/`), which is not python-aware. The `OM_BUILD_PYTHON` CMake flag
is built from a local patch here (see `patches/`)

```sh
git submodule update --init
git -C core apply ../patches/0001-add-python-bindings-hook.patch
pip install .
```

(editable, for development: `pip install -e .`)

With [uv](https://docs.astral.sh/uv/):

```sh
git submodule update --init
git -C core apply ../patches/0001-add-python-bindings-hook.patch
uv venv
uv pip install .
```

(editable: `uv pip install -e .`)

If `core/CMakeLists.txt` changes upstream in a way that conflicts with the
patch, re-run `git -C core apply` after resolving and update the patch file
(`git -C core diff > patches/0001-add-python-bindings-hook.patch`).

## Usage

```python
import openmalaria as om

result = om.run(path="scenario.xml")
result["survey"]  # pd.DataFrame: survey, column, measure, value
result["continuous"]  # pd.DataFrame (one row per timestep) or None
```

Or pass scenario XML content directly instead of a file path:

```python
result = om.run(xml=scenario_xml_string, resource_path="/path/to/resources")
```

The package ships the `scenario_current.xsd` its engine was compiled against,
in `om.SCHEMA_DIR`, and the worker subprocess runs from that directory, so a
scenario whose `xsi:schemaLocation` names `scenario_current.xsd` validates
against the matching schema without any setup. Pass
`schema_dir=<dir containing the XSD>` to validate against a different copy.
The package also ships the resource files the core reads at run time
(`densities.csv`, `autoRegressionParameters.csv`) in `om.RESOURCE_DIR`, and
`run()` uses that directory when `resource_path=` is not given. Pass
`resource_path=<dir>` to use your own copies.
Relative `path=`/`resource_path=` are resolved against the caller's working
directory, and an empty `resource_path=""` means the caller's working directory.

`om.run()` also accepts `validate_only=True` (parse/validate the scenario and
stop before any timestep evolution. This acts as a cheap sanity check,
equivalent to the CLI's `--validate-only`), `seed=<int>` (override the
scenario's `@iseed`), and `verbose=True`/`progress=True` (equivalent to the CLI
flags of the same name).

Each `run()` exchanges its input/output with the worker subprocess via pickle
files in a temporary directory, which is deleted afterwards by default.
`tmp_dir=<path>` controls where that directory is created (defaults to the
system temp dir), and `keep_tmp=True` skips deletion and prints the kept
directory's path to stderr, for inspecting `in.pkl`/`out.pkl` after a run.

### `survey` DataFrame schema

Mirrors `output.txt`'s own row schema exactly: `survey` (1-based survey number),
`column` (encodes age-group/cohort/species/genotype/drug the same way
`output.txt` does), `measure` (the OutMeasure id), `value`.

### `continuous` DataFrame schema

One row per reported timestep, one column per enabled `monitoring/continuous`
metric (column names taken from the scenario's own metric titles). `None` if the
scenario has no `<continuous>` monitoring configured.

## Version info

```python
>>> om.version()
{'program_version': 'schema-50.0', 'schema_version': 50}
```

Equivalent to the CLI's `openMalaria --version`.

```python
>>> om.SCHEMA_VERSION
50
```

The scenario schema version this engine reads, the same number `om.version()`
reports and the one in `om.SCHEMA_DIR`'s XSD namespace. Downstream packages
should read it from here rather than hard-coding it.

```python
>>> om.CORE_COMMIT
'90582271b6b2aa497991d58fba547314b1c369f1'
```

The commit of the `core` submodule the extension was built from, captured at
build time. It is `'unknown'` if git was unavailable; pass
`-C cmake.define.OM_CORE_COMMIT=<sha>` to set it explicitly.

## IMPORTANT: one subprocess per run()

OpenMalaria's C++ core keeps several pieces of state as process-global statics
that `init()` functions populate but never clear. This works for the CLI (always
exactly one process per scenario), but not for a library function callers might
invoke repeatedly in one long-lived process. Verified examples:

- `util::CommandLine::resourcePath` -- a 2nd call with `resource_path` set
  throws outright ("--resource-path (or -p) may only be given once").
- `util::CommandLine::options` -- boolean CLI flags (`verbose`, `progress`, ...)
  leak silently across calls; once set, stuck on for the rest of the process.
- `interventions::InterventionManager` -- append-only; throws on a 2nd run
  reusing any `<component id="...">` name, and silently duplicates/accumulates
  timed and continuous deployments otherwise.
- `Transmission::PerHostAnophParams::params` -- append-only per mosquito
  species; a 2nd run's species indices land on the *first* run's leftover
  entries, silently using the wrong entomological parameters.
- `mon::Continuous::toReport` -- append-only; a 2nd run's `continuous` DataFrame
  would include the first run's columns mixed into its own.
- `mon::internal::runtime.conditions` -- push_back-only, never cleared.

It would be ideal to fix the underlying issues with OpenMalaria, but I am not an
admin there. So instead, a work around is to launch
`python -m openmalaria._worker` fresh for every call, so there's never a second
call in the same still-alive process for any of the above to leak across.

It costs a process-spawn + reimport per `run()` call

## Tests

```sh
uv run pytest
```

`tests/test_rerun_consistency.py` and
`test_repeated_calls_in_same_process_succeed` guard the one-subprocess-per-run()
isolation above: every box-test scenario is run twice in the same process and
must match `core/test/expected` both times.

## Linting and type checking

```sh
uv run ruff format --check
uv run ruff check
uv run basedpyright
```

`src/openmalaria/_openmalaria.pyi` is generated from the compiled module;
regenerate it after changing `bindings/src/bindings.cpp`:

```sh
uv run --with nanobind python -m nanobind.stubgen -q -P \
  -p bindings/stubgen_patterns.txt \
  -m openmalaria._openmalaria \
  -o src/openmalaria/_openmalaria.pyi
```

## Limitations

**No checkpoint/resume support.** Checkpointing (`-c`/`--checkpoint-file` on the
CLI) remains a CLI-only feature; `om.run()` exposes no checkpoint parameters.

**CPU-core pinning is the caller's responsibility.** OpenMalaria's simulation
engine has no internal threading (no OpenMP, no `std::thread` anywhere in the
C++ core), so single-core execution is achieved externally:
`mpirun --bind-to core -np N python script.py`, or
`os.sched_setaffinity(0, {core_id})` (Linux) at the start of a worker process.

## Upstreaming

If OpenMalaria adopts Python bindings, this repo maps onto upstream as:

- `patches/0001-add-python-bindings-hook.patch` becomes a real `OM_BUILD_PYTHON`
  CMake option in upstream's `CMakeLists.txt`.
- `bindings/` (the nanobind C++ and its CMake) becomes an upstream `python/`
  directory, and `src/openmalaria/` its Python package.
- The `core/` submodule and patch step disappear.
- The subprocess isolation in `run()`/`_worker.py` stays until the
  process-global statics listed above are cleared between runs in the C++ core;
  after that, `run()` can call `_run()` directly.
