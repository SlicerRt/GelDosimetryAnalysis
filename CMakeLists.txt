cmake_minimum_required(VERSION 2.8.9)

#-----------------------------------------------------------------------------
set(EXTENSION_NAME GelDosimetryAnalysis)

# ------------------------------------------------------------------------
set(GELDOSIMETRY_VERSION_MAJOR "0")
set(GELDOSIMETRY_VERSION_MINOR "2")
set(GELDOSIMETRY_VERSION_PATCH "2")
set(GELDOSIMETRY_VERSION ${GELDOSIMETRY_VERSION_MAJOR}.${GELDOSIMETRY_VERSION_MINOR}.${GELDOSIMETRY_VERSION_PATCH})


#-----------------------------------------------------------------------------
set(EXTENSION_HOMEPAGE "http://www.slicer.org/slicerWiki/index.php/Documentation/Nightly/Modules/GelDosimetry")
set(EXTENSION_CATEGORY "Radiotherapy")
set(EXTENSION_CONTRIBUTORS "Csaba Pinter (PerkLab, Queen's University), Jennifer Andrea (PerkLab, Queen's University), Mattea Welch (PerkLab, Queen's University)")
set(EXTENSION_DESCRIPTION "Slicelet covering the gel dosimetry analysis workflow used in commissioning new radiation techniques and to validate the accuracy of radiation treatment by enabling visual comparison of the planned dose to the delivered dose, where correspondence between the two dose distributions is achieved using embedded landmarks. Gel dosimetry is based on imaging chemical systems spatially fixed in gelatin, which exhibit a detectable change upon irradiation.")
set(EXTENSION_ICONURL "http://www.slicer.org/slicerWiki/images/f/f1/GelDosimetry_Logo_128x128.png")
set(EXTENSION_SCREENSHOTURLS "http://www.slicer.org/slicerWiki/images/8/83/GelDosimetrySlicelet_0.1_LandmarkRegistrationStep.png http://www.slicer.org/slicerWiki/images/6/68/GelDosimetrySlicelet_0.1_CalibrationCurvesAligned.png http://www.slicer.org/slicerWiki/images/5/51/GelDosimetrySlicelet_0.1_OdVsDoseCurve.png")

#-----------------------------------------------------------------------------
project(GelDosimetryAnalysis)
find_package(Slicer REQUIRED)
include(${Slicer_USE_FILE})

#-----------------------------------------------------------------------------
add_subdirectory(GelDosimetryAnalysisAlgo)
add_subdirectory(GelDosimetryAnalysis)

#-----------------------------------------------------------------------------
include(${Slicer_EXTENSION_CPACK})
