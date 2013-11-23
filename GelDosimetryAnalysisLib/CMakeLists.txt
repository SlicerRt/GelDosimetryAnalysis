#-----------------------------------------------------------------------------
set(MODULE_NAME GelDosimetryAnalysisLib)

#-----------------------------------------------------------------------------
add_subdirectory(Logic)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  __init__
  GelDosimetryAnalysisLogic
  )

set(MODULE_PYTHON_RESOURCES
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  WITH_SUBDIR
  )

#-----------------------------------------------------------------------------
# if(BUILD_TESTING)
  # add_subdirectory(Testing)
# endif()
