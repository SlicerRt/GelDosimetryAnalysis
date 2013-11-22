project(vtkApplyPolynomialFunctionOnVolumeAlgo)

# --------------------------------------------------------------------------
# Sources

SET (ApplyPolynomialFunctionOnVolumeAlgo_SRCS
  vtkApplyPolynomialFunctionOnVolumeAlgo.cxx 
  vtkApplyPolynomialFunctionOnVolumeAlgo.h
  )

SET (ApplyPolynomialFunctionOnVolumeAlgo_INCLUDE_DIRS ${CMAKE_CURRENT_SOURCE_DIR} ${Slicer_Libs_INCLUDE_DIRS} CACHE INTERNAL "" FORCE)
  
# --------------------------------------------------------------------------
# Build the library

set(lib_name ${PROJECT_NAME})
SET (ApplyPolynomialFunctionOnVolumeAlgo_LIBS 
  vtkCommon
  vtkFiltering
  vtkImaging
  )

INCLUDE_DIRECTORIES( ${ApplyPolynomialFunctionOnVolumeAlgo_INCLUDE_DIRS} )
ADD_LIBRARY( ${lib_name} ${ApplyPolynomialFunctionOnVolumeAlgo_SRCS} )
TARGET_LINK_LIBRARIES( ${lib_name} ${ApplyPolynomialFunctionOnVolumeAlgo_LIBS})

# --------------------------------------------------------------------------
# Set external MS project 
SET (PLUSLIB_DEPENDENCIES ${PLUSLIB_DEPENDENCIES} vtkCalibrationAlgo CACHE INTERNAL "" FORCE)
LIST(REMOVE_DUPLICATES PLUSLIB_DEPENDENCIES)

# --------------------------------------------------------------------------
# Testing
#
# IF (BUILD_TESTING)
  # ADD_SUBDIRECTORY (Testing)
# ENDIF (BUILD_TESTING)
