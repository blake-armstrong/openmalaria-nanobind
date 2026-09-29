list (REMOVE_ITEM CMAKE_MODULE_PATH "${CMAKE_SOURCE_DIR}/cmake")

find_package (Python 3.9 COMPONENTS Interpreter Development.Module REQUIRED)

execute_process (
  COMMAND "${Python_EXECUTABLE}" -m nanobind --cmake_dir
  OUTPUT_STRIP_TRAILING_WHITESPACE
  OUTPUT_VARIABLE NB_DIR
)
list (APPEND CMAKE_PREFIX_PATH "${NB_DIR}")
find_package (nanobind CONFIG REQUIRED)

set_target_properties (model schema contrib PROPERTIES POSITION_INDEPENDENT_CODE ON)

nanobind_add_module (_openmalaria src/bindings.cpp)

if (NOT DEFINED OM_CORE_COMMIT)
  set (OM_CORE_COMMIT "unknown")
  find_package (Git QUIET)
  if (GIT_FOUND)
    execute_process (
      COMMAND "${GIT_EXECUTABLE}" -c safe.directory=* rev-parse HEAD
      WORKING_DIRECTORY "${CMAKE_SOURCE_DIR}"
      OUTPUT_VARIABLE _om_core_commit
      OUTPUT_STRIP_TRAILING_WHITESPACE
      RESULT_VARIABLE _om_git_result
      ERROR_QUIET
    )
    if (_om_git_result EQUAL 0)
      set (OM_CORE_COMMIT "${_om_core_commit}")
    endif ()
  endif ()
endif ()
message (STATUS "OpenMalaria core commit: ${OM_CORE_COMMIT}")

target_compile_definitions (_openmalaria PRIVATE OM_CORE_COMMIT="${OM_CORE_COMMIT}")

target_include_directories (_openmalaria PRIVATE
  ${CMAKE_SOURCE_DIR}/model
  ${CMAKE_BINARY_DIR}
  ${CMAKE_BINARY_DIR}/model
)

target_link_libraries (_openmalaria PRIVATE
  model
  schema
  contrib
  ${GSL_LIBRARIES}
  ${XERCESC_LIBRARIES}
  ${Z_LIBRARIES}
  ${PTHREAD_LIBRARIES}
)

add_dependencies (_openmalaria inlined_xsd)

install (TARGETS _openmalaria LIBRARY DESTINATION openmalaria)
install (FILES "${CMAKE_BINARY_DIR}/schema/scenario_current.xsd"
  DESTINATION openmalaria/schema)
