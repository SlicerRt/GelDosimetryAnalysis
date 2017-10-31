cmake_minimum_required(VERSION 2.8.9)

#-----------------------------------------------------------------------------
set(MODULE_NAME GelDosimetryAnalysis)

#-----------------------------------------------------------------------------
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}
  ${MODULE_NAME}Logic/__init__
  ${MODULE_NAME}Logic/${MODULE_NAME}Logic
  ${MODULE_NAME}Logic/LineProfileLogic
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  # WITH_GENERIC_TESTS # It fails because the generic test does not seem to add the module paths
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)
  set(GelDosimetryAnalysis_QTLOADABLEMODULES_LIB_DIRS "")
  set(SlicerRT_QTLOADABLEMODULES_LIB_DIRS "")
  if(CMAKE_CONFIGURATION_TYPES)
    foreach(config ${CMAKE_CONFIGURATION_TYPES})
      list(APPEND GelDosimetryAnalysis_QTLOADABLEMODULES_LIB_DIRS "${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR}/${config}")
      list(APPEND SlicerRT_QTLOADABLEMODULES_LIB_DIRS "${SlicerRT_DIR}/inner-build/${Slicer_QTLOADABLEMODULES_LIB_DIR}/${config}")
    endforeach()
  else()
    set(GelDosimetryAnalysis_QTLOADABLEMODULES_LIB_DIRS "${CMAKE_BINARY_DIR}/${Slicer_QTLOADABLEMODULES_LIB_DIR}")
    set(SlicerRT_QTLOADABLEMODULES_LIB_DIRS "${SlicerRT_DIR}/inner-build/${Slicer_QTLOADABLEMODULES_LIB_DIR}")
  endif()
  # Register the unittest subclass in the main script as a ctest.
  # Note that the test will also be available at runtime.
  slicer_add_python_unittest(
    SCRIPT ${MODULE_NAME}.py
    SLICER_ARGS --additional-module-paths
      ${CMAKE_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}
      ${CMAKE_BINARY_DIR}/${Slicer_QTSCRIPTEDMODULES_LIB_DIR}/GelDosimetryAnalysisLogic
      ${GelDosimetryAnalysis_QTLOADABLEMODULES_LIB_DIRS}
      # ${SlicerRT_LIBRARY_PATHS_LAUNCHER_BUILD} # The variable CMAKE_CFG_INTDIR does not contain anything
      ${SlicerRT_QTLOADABLEMODULES_LIB_DIRS}
      ${SlicerRT_PYTHONPATH_LAUNCHER_BUILD}
    )

  # Additional build-time testing
  add_subdirectory(Testing)
endif()

