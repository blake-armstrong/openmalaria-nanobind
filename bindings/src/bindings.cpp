/* This file is part of OpenMalaria.
 *
 * Copyright (C) 2005-2026 Swiss Tropical and Public Health Institute
 * Copyright (C) 2005-2015 Liverpool School Of Tropical Medicine
 * Copyright (C) 2020-2026 University of Basel
 * Copyright (C) 2025-2026 The Kids Research Institute Australia
 *
 * OpenMalaria is free software; you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation; either version 2 of the License, or (at
 * your option) any later version.
 *
 * This program is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with this program; if not, write to the Free Software
 * Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301,
 * USA.
 */

// nanobind extension module

#include <nanobind/nanobind.h>
#include <nanobind/ndarray.h>
#include <nanobind/stl/optional.h>
#include <nanobind/stl/string.h>
#include <nanobind/stl/vector.h>

#include "Simulator.h"
#include "mon/OutMeasures.h"
#include "schema/scenario.h"
#include "util/CommandLine.h"
#include "util/DocumentLoader.h"
#include "util/errors.h"
#include "util/version.h"

#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

namespace nb = nanobind;
using namespace nb::literals;

namespace {

struct OpenMalariaError : std::runtime_error {
  OpenMalariaError(const std::string &msg, int code)
      : std::runtime_error(code != 0 ? msg + " (error code " +
                                           std::to_string(code) + ")"
                                     : msg) {}
};

template <typename T>
nb::ndarray<T, nb::numpy, nb::ndim<1>> vector_to_ndarray(std::vector<T> v) {
  auto *owned = new std::vector<T>(std::move(v));
  nb::capsule owner(
      owned, [](void *p) noexcept { delete static_cast<std::vector<T> *>(p); });
  return nb::ndarray<T, nb::numpy, nb::ndim<1>>(owned->data(), {owned->size()},
                                                owner);
}

struct SurveyData {
  nb::ndarray<int, nb::numpy, nb::ndim<1>> survey;
  nb::ndarray<int, nb::numpy, nb::ndim<1>> column;
  nb::ndarray<int, nb::numpy, nb::ndim<1>> measure;
  nb::ndarray<double, nb::numpy, nb::ndim<1>> value;
};

struct ContinuousData {
  std::vector<std::string> column_titles;
  std::vector<nb::ndarray<double, nb::numpy, nb::ndim<1>>> columns;
};

struct RawRunResult {
  SurveyData survey;
  ContinuousData continuous;
};

struct VersionInfo {
  std::string program_version;
  int schema_version;
};

SurveyData convertSurvey(std::vector<OM::mon::SurveyRow> &rows) {
  std::vector<int> survey, column, measure;
  std::vector<double> value;
  survey.reserve(rows.size());
  column.reserve(rows.size());
  measure.reserve(rows.size());
  value.reserve(rows.size());
  for (const auto &r : rows) {
    survey.push_back(r.survey);
    column.push_back(r.column);
    measure.push_back(r.measure);
    value.push_back(r.value);
  }
  return SurveyData{
      vector_to_ndarray(std::move(survey)),
      vector_to_ndarray(std::move(column)),
      vector_to_ndarray(std::move(measure)),
      vector_to_ndarray(std::move(value)),
  };
}

ContinuousData convertContinuous(OM::mon::Continuous::CapturedData &captured) {
  ContinuousData result;
  result.column_titles = std::move(captured.columnTitles);
  result.columns.reserve(captured.columns.size());
  for (auto &col : captured.columns)
    result.columns.push_back(vector_to_ndarray(std::move(col)));
  return result;
}

RawRunResult run_impl(std::optional<std::string> xml,
                      std::optional<std::string> path,
                      std::string resource_path, bool validate_only,
                      bool verbose, bool progress, std::optional<int> seed) {
  if (xml.has_value() == path.has_value())
    throw std::invalid_argument("exactly one of xml= or path= must be given");

  std::vector<std::string> args = {"openmalaria"};
  if (!resource_path.empty()) {
    args.push_back("--resource-path");
    args.push_back(resource_path);
  }
  if (validate_only)
    args.push_back("--validate-only");
  if (verbose)
    args.push_back("--verbose");
  if (progress)
    args.push_back("--progress");

  std::vector<char *> argv;
  argv.reserve(args.size());
  for (auto &a : args)
    argv.push_back(a.data());

  try {
    OM::util::CommandLine::parse(static_cast<int>(argv.size()), argv.data());

    OM::Simulator::RunConfig config;
    config.outputMode = OM::Simulator::OutputMode::CaptureInMemory;
    config.seedOverride = seed;
    config.scenario.isPath = path.has_value();
    if (path)
      config.scenario.path = *path;
    else
      config.scenario.xml = *xml;

    OM::Simulator::RunResult result = OM::Simulator::run(config);

    RawRunResult raw;
    raw.survey = convertSurvey(result.surveyRows);
    raw.continuous = convertContinuous(result.continuous);
    return raw;
  } catch (const OM::util::base_exception &e) {
    throw OpenMalariaError(e.message(), e.getCode());
  } catch (const xsd::cxx::tree::exception<char> &e) {
    std::ostringstream message;
    message << "XSD error: " << e.what() << '\n' << e;
    throw OpenMalariaError(message.str(), -1);
  }
}

VersionInfo version_impl() {
  return VersionInfo{OM::util::semantic_version, OM::util::SCHEMA_VERSION};
}

nb::dict measure_codes_impl() {
  nb::dict codes;
  for (const auto &def : OM::mon::defs)
    codes[def.name] = def.outId;
  return codes;
}

void register_core_bindings(nb::module_ &m) {
  nb::class_<SurveyData>(m, "SurveyData")
      .def_ro("survey", &SurveyData::survey, nb::rv_policy::copy)
      .def_ro("column", &SurveyData::column, nb::rv_policy::copy)
      .def_ro("measure", &SurveyData::measure, nb::rv_policy::copy)
      .def_ro("value", &SurveyData::value, nb::rv_policy::copy);

  nb::class_<ContinuousData>(m, "ContinuousData")
      .def_ro("column_titles", &ContinuousData::column_titles)
      .def_ro("columns", &ContinuousData::columns, nb::rv_policy::copy);

  nb::class_<RawRunResult>(m, "RawRunResult")
      .def_ro("survey", &RawRunResult::survey)
      .def_ro("continuous", &RawRunResult::continuous);

  nb::class_<VersionInfo>(m, "VersionInfo")
      .def_ro("program_version", &VersionInfo::program_version)
      .def_ro("schema_version", &VersionInfo::schema_version);

  m.def("_run", &run_impl, "xml"_a = nb::none(), "path"_a = nb::none(),
        "resource_path"_a = "", "validate_only"_a = false, "verbose"_a = false,
        "progress"_a = false, "seed"_a = nb::none());

  m.def("_version", &version_impl);

  m.attr("MEASURE_CODES") = measure_codes_impl();

  m.attr("CORE_COMMIT") = OM_CORE_COMMIT;

  m.attr("SCHEMA_VERSION") = OM::util::SCHEMA_VERSION;
}

void register_error_bindings(nb::module_ &m) {
  nb::exception<OpenMalariaError>(m, "OpenMalariaError");
}

} // namespace

NB_MODULE(_openmalaria, m) {
  register_core_bindings(m);
  register_error_bindings(m);
}
