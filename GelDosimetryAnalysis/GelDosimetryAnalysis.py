import os
import unittest
import numpy
from __main__ import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging
import GelDosimetryAnalysisLogic
 
#
# Gel dosimetry analysis slicelet
#
# Streamlined workflow end-user application based on 3D Slicer and SlicerRT to support
# 3D gel-based radiation dosimetry.
#
# The all-caps terms correspond to data objects in the gel dosimetry data flow diagram
# https://subversion.assembla.com/svn/slicerrt/trunk/GelDosimetryAnalysis/doc/GelDosimetryAnalysis_DataFlow.png
#

#
# GelDosimetryAnalysisSliceletWidget
#
class GelDosimetryAnalysisSliceletWidget:
  def __init__(self, parent=None):
    try:
      parent
      self.parent = parent

    except Exception, e:
      import traceback
      traceback.print_exc()
      logging.error("There is no parent to GelDosimetryAnalysisSliceletWidget!")

#
# SliceletMainFrame
#   Handles the event when the slicelet is hidden (its window closed)
#
class SliceletMainFrame(qt.QFrame):
  def setSlicelet(self, slicelet):
    self.slicelet = slicelet

  def hideEvent(self, event):
    self.slicelet.disconnect()

    import gc
    refs = gc.get_referrers(self.slicelet)
    if len(refs) > 1:
      logging.debug('Stuck slicelet references (' + repr(len(refs)) + '):\n' + repr(refs))

    slicer.gelDosimetrySliceletInstance = None
    # self.slicelet.parent = None #TODO: Comment out these two lines because they cause a crash now when slicelet is closed
    # self.slicelet = None
    self.deleteLater()

#
# GelDosimetryAnalysisSlicelet
#
class GelDosimetryAnalysisSlicelet(object):
  def __init__(self, parent, widgetClass=None):
    # Set up main frame
    self.parent = parent
    self.parent.setLayout(qt.QHBoxLayout())

    self.layout = self.parent.layout()
    self.layout.setMargin(0)
    self.layout.setSpacing(0)

    self.sliceletPanel = qt.QFrame(self.parent)
    self.sliceletPanelLayout = qt.QVBoxLayout(self.sliceletPanel)
    self.sliceletPanelLayout.setMargin(4)
    self.sliceletPanelLayout.setSpacing(0)
    self.layout.addWidget(self.sliceletPanel,1)

    # For testing only
    self.selfTestButton = qt.QPushButton("Run self-test")
    self.sliceletPanelLayout.addWidget(self.selfTestButton)
    self.selfTestButton.connect('clicked()', self.onSelfTestButtonClicked)
    #self.selfTestButton.setVisible(False) # TODO_ForTesting: Should be commented out for testing so the button shows up

    # Initiate and group together all panels
    self.step0_layoutSelectionCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step1_loadDataCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step2_registrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step3_doseCalibrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step4_doseComparisonCollapsibleButton = ctk.ctkCollapsibleButton()
    self.stepT1_lineProfileCollapsibleButton = ctk.ctkCollapsibleButton()

    self.collapsibleButtonsGroup = qt.QButtonGroup()
    self.collapsibleButtonsGroup.addButton(self.step0_layoutSelectionCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.step1_loadDataCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.step2_registrationCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.step3_doseCalibrationCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.step4_doseComparisonCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.stepT1_lineProfileCollapsibleButton)

    self.step0_layoutSelectionCollapsibleButton.setProperty('collapsed', False)
    
    # Create module logic
    self.logic = GelDosimetryAnalysisLogic.GelDosimetryAnalysisLogic()

    # Set up constants
    self.obiMarkupsFiducialNodeName = "OBI fiducials"
    self.measuredMarkupsFiducialNodeName = "MEASURED fiducials"
    self.gammaScalarBarColorTableName = "GammaScalarBarColorTable"
    self.numberOfGammaLabels = 9
	
    # Declare member variables (selected at certain steps and then from then on for the workflow)
    self.mode = None
    self.planCtVolumeNode = None
    self.planDoseVolumeNode = None
    self.planStructuresNode = None
    self.obiVolumeNode = None
    self.measuredVolumeNode = None
    self.calibrationVolumeNode = None

    self.obiMarkupsFiducialNode = None
    self.measuredMarkupsFiducialNode = None
    self.calibratedMeasuredVolumeNode = None
    self.maskContourNode = None
    self.gammaVolumeNode = None

    self.gammaScalarBarWidget = None
    
    # Get markups widget and logic
    try:
      slicer.modules.markups
      self.markupsWidget = slicer.modules.markups.widgetRepresentation()
      self.markupsWidgetLayout = self.markupsWidget.layout()
      self.markupsLogic = slicer.modules.markups.logic()
    except Exception, e:
      import traceback
      traceback.print_exc()
      logging.error('Unable to find Markups module!')
    # Build re-usable markups widget
    self.markupsWidgetClone = qt.QFrame()
    self.markupsWidgetClone.setLayout(self.markupsWidgetLayout)
    self.fiducialSelectionWidget = qt.QFrame()
    self.fiducialSelectionLayout = qt.QFormLayout()
    self.fiducialSelectionLayout.setMargin(0)
    self.fiducialSelectionLayout.setSpacing(0)
    self.fiducialSelectionWidget.setLayout(self.fiducialSelectionLayout)
    self.fiducialSelectionButton = slicer.qSlicerMouseModeToolBar()
    self.fiducialSelectionButton.setApplicationLogic(slicer.app.applicationLogic())
    self.fiducialSelectionButton.setMRMLScene(slicer.app.mrmlScene())
    self.fiducialSelectionButton.setPersistence(1)
    self.fiducialSelectionLayout.addRow(self.markupsWidgetClone)
    self.fiducialSelectionLayout.addRow('Select fiducials: ', self.fiducialSelectionButton)

    # Make temporary changes in the Markups UI
    try:
      advancedCollapsibleButton = slicer.util.findChildren(widget=self.markupsWidgetClone, className='ctkCollapsibleGroupBox', name='advancedCollapsibleButton')[0]
      advancedCollapsibleButton.setVisible(False)
      activeMarkupMRMLNodeComboBox = slicer.util.findChildren(widget=self.markupsWidgetClone, className='qMRMLNodeComboBox', name='activeMarkupMRMLNodeComboBox')[0]
      activeMarkupMRMLNodeComboBox.setEnabled(False)
    except Exception, e:
      import traceback
      traceback.print_exc()
      logging.error('Failed to correctly reparent the Markups widget!')

    # Create or get fiducial nodes
    self.obiMarkupsFiducialNode = slicer.util.getNode(self.obiMarkupsFiducialNodeName)
    if self.obiMarkupsFiducialNode == None:
      obiFiducialsNodeId = self.markupsLogic.AddNewFiducialNode(self.obiMarkupsFiducialNodeName)
      self.obiMarkupsFiducialNode = slicer.mrmlScene.GetNodeByID(obiFiducialsNodeId)
    self.measuredMarkupsFiducialNode = slicer.util.getNode(self.measuredMarkupsFiducialNodeName)
    if self.measuredMarkupsFiducialNode == None:
      measuredFiducialsNodeId = self.markupsLogic.AddNewFiducialNode(self.measuredMarkupsFiducialNodeName)
      self.measuredMarkupsFiducialNode = slicer.mrmlScene.GetNodeByID(measuredFiducialsNodeId)
    measuredFiducialsDisplayNode = self.measuredMarkupsFiducialNode.GetDisplayNode()
    measuredFiducialsDisplayNode.SetSelectedColor(0, 0.9, 0)

    # Turn on slice intersections in 2D viewers
    compositeNodes = slicer.util.getNodes("vtkMRMLSliceCompositeNode*")
    for compositeNode in compositeNodes.values():
      compositeNode.SetSliceIntersectionVisibility(1)

    # Set up step panels
    self.setup_Step0_LayoutSelection()    
    self.setup_Step1_LoadData()
    self.setup_Step2_Registration()
    self.setup_step3_DoseCalibration()
    self.setup_Step4_DoseComparison()
    self.setup_StepT1_lineProfileCollapsibleButton()

    if widgetClass:
      self.widget = widgetClass(self.parent)
    self.parent.show()

  def __del__(self):
    self.cleanUp()
    
  # Clean up when slicelet is closed
  def cleanUp(self):
    logging.debug('Cleaning up')
    # Show the previously hidden advanced panel in the Markups module UI
    try:
      advancedCollapsibleButton = slicer.util.findChildren(widget=self.markupsWidgetClone, className='ctkCollapsibleGroupBox', name='advancedCollapsibleButton')[0]
      advancedCollapsibleButton.setVisible(True)
      activeMarkupMRMLNodeComboBox = slicer.util.findChildren(widget=self.markupsWidgetClone, className='qMRMLNodeComboBox', name='activeMarkupMRMLNodeComboBox')[0]
      activeMarkupMRMLNodeComboBox.setEnabled(True)

      # Return the Markups widget ownership to the Markups module
      self.markupsWidget.setLayout(self.markupsWidgetLayout)
    except Exception, e:
      import traceback
      traceback.print_exc()
      logging.error('Cleaning up failed!')

  # Disconnect all connections made to the slicelet to enable the garbage collector to destruct the slicelet object on quit
  def disconnect(self):
    self.selfTestButton.disconnect('clicked()', self.onSelfTestButtonClicked)
    self.step0_viewSelectorComboBox.disconnect('activated(int)', self.onViewSelect)
    self.step0_clinicalModeRadioButton.disconnect('toggled(bool)', self.onClinicalModeSelect)
    self.step0_preclinicalModeRadioButton.disconnect('toggled(bool)', self.onPreclinicalModeSelect)
    self.step1_showDicomBrowserButton.disconnect('clicked()', self.logic.onDicomLoad)
    self.step2_1_registerObiToPlanCtButton.disconnect('clicked()', self.onObiToPlanCTRegistration)
    self.step2_2_measuredDoseToObiRegistrationCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep2_2_MeasuredDoseToObiRegistrationSelected)
    self.step2_2_1_obiFiducialSelectionCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep2_2_1_ObiFiducialCollectionSelected)
    self.step2_2_2_measuredFiducialSelectionCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep2_2_2_ObiFiducialCollectionSelected)
    self.step1_loadNonDicomDataButton.disconnect('clicked()', self.onLoadNonDicomData)
    self.step2_2_3_registerMeasuredToObiButton.disconnect('clicked()', self.onMeasuredToObiRegistration)
    self.step3_1_pddLoadDataButton.disconnect('clicked()', self.onLoadPddDataRead)
    self.step3_1_alignCalibrationCurvesButton.disconnect('clicked()', self.onAlignCalibrationCurves)
    self.step3_1_xTranslationSpinBox.disconnect('valueChanged(double)', self.onAdjustAlignmentValueChanged)
    self.step3_1_yScaleSpinBox.disconnect('valueChanged(double)', self.onAdjustAlignmentValueChanged)
    self.step3_1_yTranslationSpinBox.disconnect('valueChanged(double)', self.onAdjustAlignmentValueChanged)
    self.step3_1_computeDoseFromPddButton.disconnect('clicked()', self.onComputeDoseFromPdd)
    self.step3_1_calibrationRoutineCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep3_1_CalibrationRoutineSelected)
    self.step3_1_showOpticalDensityVsDoseCurveButton.disconnect('clicked()', self.onShowOpticalDensityVsDoseCurve)
    self.step3_1_removeSelectedPointsFromOpticalDensityVsDoseCurveButton.disconnect('clicked()', self.onRemoveSelectedPointsFromOpticalDensityVsDoseCurve)
    self.step3_1_fitPolynomialToOpticalDensityVsDoseCurveButton.disconnect('clicked()', self.onFitPolynomialToOpticalDensityVsDoseCurve)
    self.step3_2_exportCalibrationToCSV.disconnect('clicked()', self.onExportCalibration)
    self.step3_2_applyCalibrationButton.disconnect('clicked()', self.onApplyCalibration)
    self.step4_doseComparisonCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep4_DoseComparisonSelected)
    self.step4_maskContourSelector.disconnect('currentNodeChanged(vtkMRMLNode*)', self.onStep4_MaskContourSelectionChanged)
    self.step4_1_referenceDoseUseMaximumDoseRadioButton.disconnect('toggled(bool)', self.onUseMaximumDoseRadioButtonToggled)
    self.step4_1_computeGammaButton.disconnect('clicked()', self.onGammaDoseComparison)
    self.step4_1_showGammaReportButton.disconnect('clicked()', self.onShowGammaReport)
    self.stepT1_lineProfileCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStepT1_LineProfileSelected)
    self.stepT1_createLineProfileButton.disconnect('clicked(bool)', self.onCreateLineProfileButton)
    self.stepT1_inputRulerSelector.disconnect("currentNodeChanged(vtkMRMLNode*)", self.onSelectLineProfileParameters)
    self.stepT1_exportLineProfilesToCSV.disconnect('clicked()', self.onExportLineProfiles)

  def setup_Step0_LayoutSelection(self):
    # Layout selection step
    self.step0_layoutSelectionCollapsibleButton.setProperty('collapsedHeight', 4)
    #TODO: Change back if there are more modes
    self.step0_layoutSelectionCollapsibleButton.text = "Layout selector"
    # self.step0_layoutSelectionCollapsibleButton.text = "Layout and mode selector"
    self.sliceletPanelLayout.addWidget(self.step0_layoutSelectionCollapsibleButton)
    self.step0_layoutSelectionCollapsibleButtonLayout = qt.QFormLayout(self.step0_layoutSelectionCollapsibleButton)
    self.step0_layoutSelectionCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step0_layoutSelectionCollapsibleButtonLayout.setSpacing(4)

    self.step0_viewSelectorComboBox = qt.QComboBox(self.step0_layoutSelectionCollapsibleButton)
    self.step0_viewSelectorComboBox.addItem("Four-up 3D + 3x2D view")
    self.step0_viewSelectorComboBox.addItem("Conventional 3D + 3x2D view")
    self.step0_viewSelectorComboBox.addItem("3D-only view")
    self.step0_viewSelectorComboBox.addItem("Axial slice only view")
    self.step0_viewSelectorComboBox.addItem("Double 3D view")
    self.step0_viewSelectorComboBox.addItem("Four-up plus plot view")
    self.step0_viewSelectorComboBox.addItem("Plot only view")
    self.step0_layoutSelectionCollapsibleButtonLayout.addRow("Layout: ", self.step0_viewSelectorComboBox)
    self.step0_viewSelectorComboBox.connect('activated(int)', self.onViewSelect)
    
    # Mode Selector: Radio-buttons
    self.step0_modeSelectorLayout = qt.QGridLayout()
    self.step0_modeSelectorLabel = qt.QLabel('Select mode: ')
    self.step0_modeSelectorLayout.addWidget(self.step0_modeSelectorLabel, 0, 0, 1, 1)
    self.step0_clinicalModeRadioButton = qt.QRadioButton('Clinical optical readout')
    self.step0_clinicalModeRadioButton.setChecked(True)
    self.step0_modeSelectorLayout.addWidget(self.step0_clinicalModeRadioButton, 0, 1)
    self.step0_preclinicalModeRadioButton = qt.QRadioButton('Preclinical MRI readout')
    self.step0_modeSelectorLayout.addWidget(self.step0_preclinicalModeRadioButton, 0, 2)
    #TODO: Uncomment when preclinical mode works #601
    # self.step0_layoutSelectionCollapsibleButtonLayout.addRow(self.step0_modeSelectorLayout)
    self.step0_clinicalModeRadioButton.connect('toggled(bool)', self.onClinicalModeSelect)
    self.step0_preclinicalModeRadioButton.connect('toggled(bool)', self.onPreclinicalModeSelect)
    
    # Add layout widget
    self.layoutWidget = slicer.qMRMLLayoutWidget()
    self.layoutWidget.setMRMLScene(slicer.mrmlScene)
    self.parent.layout().addWidget(self.layoutWidget,2)
    self.onViewSelect(0)

  def setup_Step1_LoadData(self):
    # Step 1: Load data panel
    self.step1_loadDataCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step1_loadDataCollapsibleButton.text = "1. Load data"
    self.sliceletPanelLayout.addWidget(self.step1_loadDataCollapsibleButton)
    self.step1_loadDataCollapsibleButtonLayout = qt.QFormLayout(self.step1_loadDataCollapsibleButton)
    self.step1_loadDataCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step1_loadDataCollapsibleButtonLayout.setSpacing(4)

    # Load data label
    self.step1_LoadDataLabel = qt.QLabel("Load all DICOM data involved in the workflow.\nNote: Can return to this step later if more data needs to be loaded")
    self.step1_LoadDataLabel.wordWrap = True
    self.step1_loadDataCollapsibleButtonLayout.addRow(self.step1_LoadDataLabel)

    # Load DICOM data button
    self.step1_showDicomBrowserButton = qt.QPushButton("Load DICOM data")
    self.step1_showDicomBrowserButton.toolTip = "Load planning data (CT, dose, structures)"
    self.step1_showDicomBrowserButton.name = "showDicomBrowserButton"
    self.step1_loadDataCollapsibleButtonLayout.addRow(self.step1_showDicomBrowserButton)

    # Load non-DICOM data button
    self.step1_loadNonDicomDataButton = qt.QPushButton("Load non-DICOM data from file")
    self.step1_loadNonDicomDataButton.toolTip = "Load optical CT files from VFF, NRRD, etc."
    self.step1_loadNonDicomDataButton.name = "loadNonDicomDataButton"
    self.step1_loadDataCollapsibleButtonLayout.addRow(self.step1_loadNonDicomDataButton)
    
    # Add empty row
    self.step1_loadDataCollapsibleButtonLayout.addRow(' ', None)
    
    # Assign data label
    self.step1_AssignDataLabel = qt.QLabel("Assign loaded data to roles.\nNote: If this selection is changed later then all the following steps need to be performed again")
    self.step1_AssignDataLabel.wordWrap = True
    self.step1_loadDataCollapsibleButtonLayout.addRow(self.step1_AssignDataLabel)

    # PLANCT node selector
    self.planCTSelector = slicer.qMRMLNodeComboBox()
    self.planCTSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.planCTSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.planCTSelector.addEnabled = False
    self.planCTSelector.removeEnabled = False
    self.planCTSelector.setMRMLScene( slicer.mrmlScene )
    self.planCTSelector.setToolTip( "Pick the planning CT volume" )
    self.step1_loadDataCollapsibleButtonLayout.addRow('Planning CT volume: ', self.planCTSelector)

    # PLANDOSE node selector
    self.planDoseSelector = slicer.qMRMLNodeComboBox()
    self.planDoseSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.planDoseSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.planDoseSelector.addEnabled = False
    self.planDoseSelector.removeEnabled = False
    self.planDoseSelector.setMRMLScene( slicer.mrmlScene )
    self.planDoseSelector.setToolTip( "Pick the planning dose volume." )
    self.step1_loadDataCollapsibleButtonLayout.addRow('Plan dose volume: ', self.planDoseSelector)

    # PLANSTRUCTURES node selector
    self.planStructuresSelector = slicer.qMRMLNodeComboBox()
    self.planStructuresSelector.nodeTypes = ( ("vtkMRMLSubjectHierarchyNode"), "" )
    self.planStructuresSelector.addAttribute( "vtkMRMLSubjectHierarchyNode", "DicomRtImport.ContourHierarchy", 1 )
    self.planStructuresSelector.noneEnabled = True
    self.planStructuresSelector.addEnabled = False
    self.planStructuresSelector.removeEnabled = False
    self.planStructuresSelector.setMRMLScene( slicer.mrmlScene )
    self.planStructuresSelector.setToolTip( "Pick the planning structure set." )
    self.step1_loadDataCollapsibleButtonLayout.addRow('Structures: ', self.planStructuresSelector)

    # OBI node selector
    self.obiSelector = slicer.qMRMLNodeComboBox()
    self.obiSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.obiSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.obiSelector.addEnabled = False
    self.obiSelector.removeEnabled = False
    self.obiSelector.setMRMLScene( slicer.mrmlScene )
    self.obiSelector.setToolTip( "Pick the OBI volume." )
    self.step1_loadDataCollapsibleButtonLayout.addRow('OBI volume: ', self.obiSelector)

    # MEASURED node selector
    self.measuredVolumeSelector = slicer.qMRMLNodeComboBox()
    self.measuredVolumeSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.measuredVolumeSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.measuredVolumeSelector.addEnabled = False
    self.measuredVolumeSelector.removeEnabled = False
    self.measuredVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.measuredVolumeSelector.setToolTip( "Pick the measured gel dosimeter volume." )
    self.step1_loadDataCollapsibleButtonLayout.addRow('Measured gel dosimeter volume: ', self.measuredVolumeSelector)

    # CALIBRATION node selector
    self.calibrationVolumeSelector = slicer.qMRMLNodeComboBox()
    self.calibrationVolumeSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.calibrationVolumeSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.calibrationVolumeSelector.noneEnabled = True
    self.calibrationVolumeSelector.addEnabled = False
    self.calibrationVolumeSelector.removeEnabled = False
    self.calibrationVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.calibrationVolumeSelector.setToolTip( "Pick the calibration gel dosimeter volume for registration.\nNote: Only needed if calibration function is not entered, but calculated based on calibration gel volume and PDD data" )
    self.step1_loadDataCollapsibleButtonLayout.addRow('Calibration gel volume (optional): ', self.calibrationVolumeSelector)

    # Connections
    self.step1_showDicomBrowserButton.connect('clicked()', self.logic.onDicomLoad)
    self.step1_loadNonDicomDataButton.connect('clicked()', self.onLoadNonDicomData)
    self.step1_loadDataCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep1_LoadDataCollapsed)

  def setup_Step2_Registration(self):
    # Step 2: Registration step
    self.step2_registrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step2_registrationCollapsibleButton.text = "2. Registration"
    self.sliceletPanelLayout.addWidget(self.step2_registrationCollapsibleButton)
    self.step2_registrationCollapsibleButtonLayout = qt.QFormLayout(self.step2_registrationCollapsibleButton)
    self.step2_registrationCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step2_registrationCollapsibleButtonLayout.setSpacing(4)

    # Step 2.1: OBI to PLANCT registration panel    
    self.step2_1_obiToPlanCtRegistrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step2_1_obiToPlanCtRegistrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step2_1_obiToPlanCtRegistrationCollapsibleButton.text = "2.1. Register OBI to planning CT"
    self.step2_registrationCollapsibleButtonLayout.addWidget(self.step2_1_obiToPlanCtRegistrationCollapsibleButton)
    self.step2_1_obiToPlanCtRegistrationLayout = qt.QFormLayout(self.step2_1_obiToPlanCtRegistrationCollapsibleButton)
    self.step2_1_obiToPlanCtRegistrationLayout.setContentsMargins(12,4,4,4)
    self.step2_1_obiToPlanCtRegistrationLayout.setSpacing(4)

    # Registration label
    self.step2_1_registrationLabel = qt.QLabel("Automatically register the OBI volume to the planning CT.\nIt should take several seconds.")
    self.step2_1_registrationLabel.wordWrap = True
    self.step2_1_obiToPlanCtRegistrationLayout.addRow(self.step2_1_registrationLabel)

    # OBI to PLANCT registration button
    self.step2_1_registerObiToPlanCtButton = qt.QPushButton("Perform registration")
    self.step2_1_registerObiToPlanCtButton.toolTip = "Register OBI volume to planning CT volume"
    self.step2_1_registerObiToPlanCtButton.name = "step2_1_registerObiToPlanCtButton"
    self.step2_1_obiToPlanCtRegistrationLayout.addRow(self.step2_1_registerObiToPlanCtButton)

    # Step 2.2: Gel CT scan to cone beam CT registration panel
    self.step2_2_measuredDoseToObiRegistrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step2_2_measuredDoseToObiRegistrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step2_2_measuredDoseToObiRegistrationCollapsibleButton.text = "2.2. Register gel dosimeter volume to OBI"
    self.step2_registrationCollapsibleButtonLayout.addWidget(self.step2_2_measuredDoseToObiRegistrationCollapsibleButton)
    self.step2_2_measuredDoseToObiRegistrationLayout = qt.QVBoxLayout(self.step2_2_measuredDoseToObiRegistrationCollapsibleButton)
    self.step2_2_measuredDoseToObiRegistrationLayout.setContentsMargins(12,4,4,4)
    self.step2_2_measuredDoseToObiRegistrationLayout.setSpacing(4)

    # Step 2.2.1: Select OBI fiducials on OBI volume
    self.step2_2_1_obiFiducialSelectionCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step2_2_1_obiFiducialSelectionCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step2_2_1_obiFiducialSelectionCollapsibleButton.text = "2.2.1 Select OBI fiducial points"
    self.step2_2_measuredDoseToObiRegistrationLayout.addWidget(self.step2_2_1_obiFiducialSelectionCollapsibleButton)

    # Step 2.2.2: Select MEASURED fiducials on MEASURED dose volume
    self.step2_2_2_measuredFiducialSelectionCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step2_2_2_measuredFiducialSelectionCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step2_2_2_measuredFiducialSelectionCollapsibleButton.text = "2.2.2 Select measured gel dosimeter fiducial points"
    self.step2_2_measuredDoseToObiRegistrationLayout.addWidget(self.step2_2_2_measuredFiducialSelectionCollapsibleButton)

    # Step 2.2.3: Perform registration
    self.step2_2_3_measuredToObiRegistrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step2_2_3_measuredToObiRegistrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step2_2_3_measuredToObiRegistrationCollapsibleButton.text = "2.2.3 Perform registration"
    measuredToObiRegistrationCollapsibleButtonLayout = qt.QFormLayout(self.step2_2_3_measuredToObiRegistrationCollapsibleButton)
    measuredToObiRegistrationCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    measuredToObiRegistrationCollapsibleButtonLayout.setSpacing(4)
    self.step2_2_measuredDoseToObiRegistrationLayout.addWidget(self.step2_2_3_measuredToObiRegistrationCollapsibleButton)

    # Registration button - register MEASURED to OBI with fiducial registration
    self.step2_2_3_registerMeasuredToObiButton = qt.QPushButton("Register gel volume to OBI")
    self.step2_2_3_registerMeasuredToObiButton.toolTip = "Perform fiducial registration between measured gel dosimeter volume and OBI"
    self.step2_2_3_registerMeasuredToObiButton.name = "registerMeasuredToObiButton"
    measuredToObiRegistrationCollapsibleButtonLayout.addRow(self.step2_2_3_registerMeasuredToObiButton)

    # Fiducial error label
    self.step2_2_3_measuredToObiFiducialRegistrationErrorLabel = qt.QLabel('[Not yet performed]')
    measuredToObiRegistrationCollapsibleButtonLayout.addRow('Fiducial registration error: ', self.step2_2_3_measuredToObiFiducialRegistrationErrorLabel)

    # Add empty row
    measuredToObiRegistrationCollapsibleButtonLayout.addRow(' ', None)

    # Note label about fiducial error
    self.step2_2_3_NoteLabel = qt.QLabel("Note: Typical registration error is < 3mm")
    measuredToObiRegistrationCollapsibleButtonLayout.addRow(self.step2_2_3_NoteLabel)
    
    # Add substeps in button groups
    self.step2_2_registrationCollapsibleButtonGroup = qt.QButtonGroup()
    self.step2_2_registrationCollapsibleButtonGroup.addButton(self.step2_1_obiToPlanCtRegistrationCollapsibleButton)
    self.step2_2_registrationCollapsibleButtonGroup.addButton(self.step2_2_measuredDoseToObiRegistrationCollapsibleButton)

    self.step2_2_measuredToObiRegistrationCollapsibleButtonGroup = qt.QButtonGroup()
    self.step2_2_measuredToObiRegistrationCollapsibleButtonGroup.addButton(self.step2_2_1_obiFiducialSelectionCollapsibleButton)
    self.step2_2_measuredToObiRegistrationCollapsibleButtonGroup.addButton(self.step2_2_2_measuredFiducialSelectionCollapsibleButton)
    self.step2_2_measuredToObiRegistrationCollapsibleButtonGroup.addButton(self.step2_2_3_measuredToObiRegistrationCollapsibleButton)

    # Connections
    self.step2_1_registerObiToPlanCtButton.connect('clicked()', self.onObiToPlanCTRegistration)
    self.step2_2_measuredDoseToObiRegistrationCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep2_2_MeasuredDoseToObiRegistrationSelected)
    self.step2_2_1_obiFiducialSelectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep2_2_1_ObiFiducialCollectionSelected)
    self.step2_2_2_measuredFiducialSelectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep2_2_2_ObiFiducialCollectionSelected)
    self.step2_2_3_registerMeasuredToObiButton.connect('clicked()', self.onMeasuredToObiRegistration)

    # Open first panels when steps are first opened
    self.step2_2_1_obiFiducialSelectionCollapsibleButton.setProperty('collapsed', False)
    self.step2_1_obiToPlanCtRegistrationCollapsibleButton.setProperty('collapsed', False)

  def setup_step3_DoseCalibration(self):
    # Step 3: Calibration step
    self.step3_doseCalibrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step3_doseCalibrationCollapsibleButton.text = "3. Dose calibration"
    self.sliceletPanelLayout.addWidget(self.step3_doseCalibrationCollapsibleButton)
    self.step3_doseCalibrationCollapsibleButtonLayout = qt.QVBoxLayout(self.step3_doseCalibrationCollapsibleButton)
    self.step3_doseCalibrationCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step3_doseCalibrationCollapsibleButtonLayout.setSpacing(4)
    
    # Step 3.1: Calibration routine (optional)
    self.step3_1_calibrationRoutineCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step3_1_calibrationRoutineCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step3_1_calibrationRoutineCollapsibleButton.text = "3.1. Perform calibration routine (optional)"
    self.step3_doseCalibrationCollapsibleButtonLayout.addWidget(self.step3_1_calibrationRoutineCollapsibleButton)
    self.step3_1_calibrationRoutineLayout = qt.QFormLayout(self.step3_1_calibrationRoutineCollapsibleButton)
    self.step3_1_calibrationRoutineLayout.setContentsMargins(12,4,4,4)
    self.step3_1_calibrationRoutineLayout.setSpacing(4)

    # Load Pdd data
    self.step3_1_pddLoadDataButton = qt.QPushButton("Load reference percent depth dose (PDD) data from CSV file")
    self.step3_1_pddLoadDataButton.toolTip = "Load PDD data file from CSV"
    self.step3_1_calibrationRoutineLayout.addRow(self.step3_1_pddLoadDataButton)

    # Relative dose factor
    self.step3_1_rdfLineEdit = qt.QLineEdit()
    self.step3_1_calibrationRoutineLayout.addRow('Relative dose factor (RDF): ', self.step3_1_rdfLineEdit)

    # Empty row
    self.step3_1_calibrationRoutineLayout.addRow(' ', None)

    # Monitor units
    self.step3_1_monitorUnitsLineEdit = qt.QLineEdit()
    self.step3_1_calibrationRoutineLayout.addRow("Delivered monitor units (MU's): ", self.step3_1_monitorUnitsLineEdit)

    # Averaging radius
    self.step3_1_radiusMmFromCentrePixelLineEdit = qt.QLineEdit()
    self.step3_1_radiusMmFromCentrePixelLineEdit.toolTip = "Radius of the cylinder that is extracted around central axis to get optical density values per depth"
    self.step3_1_calibrationRoutineLayout.addRow('Averaging radius (mm): ', self.step3_1_radiusMmFromCentrePixelLineEdit)

    # Align Pdd data and CALIBRATION data based on region of interest selected
    self.step3_1_alignCalibrationCurvesButton = qt.QPushButton("Plot reference and gel PDD data")
    self.step3_1_alignCalibrationCurvesButton.toolTip = "Align PDD data optical density values with experimental optical density values (coming from calibration gel volume)"
    self.step3_1_calibrationRoutineLayout.addRow(self.step3_1_alignCalibrationCurvesButton)

    # Controls to adjust alignment
    self.step3_1_adjustAlignmentControlsLayout = qt.QHBoxLayout(self.step3_1_calibrationRoutineCollapsibleButton)
    self.step3_1_adjustAlignmentLabel = qt.QLabel('Manual adjustment: ')
    self.step3_1_xTranslationLabel = qt.QLabel('  X shift:')
    self.step3_1_xTranslationSpinBox = qt.QDoubleSpinBox()
    self.step3_1_xTranslationSpinBox.decimals = 2
    self.step3_1_xTranslationSpinBox.singleStep = 0.01
    self.step3_1_xTranslationSpinBox.value = 0
    self.step3_1_xTranslationSpinBox.minimum = -10.0
    self.step3_1_xTranslationSpinBox.maximumWidth = 48
    self.step3_1_yScaleLabel = qt.QLabel('  Y scale:')
    self.step3_1_yScaleSpinBox = qt.QDoubleSpinBox()
    self.step3_1_yScaleSpinBox.decimals = 3
    self.step3_1_yScaleSpinBox.singleStep = 0.25
    self.step3_1_yScaleSpinBox.value = 1
    self.step3_1_yScaleSpinBox.minimum = 0
    self.step3_1_yScaleSpinBox.maximum = 1000
    self.step3_1_yScaleSpinBox.maximumWidth = 60
    self.step3_1_yTranslationLabel = qt.QLabel('  Y shift:')
    self.step3_1_yTranslationSpinBox = qt.QDoubleSpinBox()
    self.step3_1_yTranslationSpinBox.decimals = 2
    self.step3_1_yTranslationSpinBox.singleStep = 0.1
    self.step3_1_yTranslationSpinBox.value = 0
    self.step3_1_yTranslationSpinBox.minimum = -99.9
    self.step3_1_yTranslationSpinBox.maximumWidth = 48
    self.step3_1_adjustAlignmentControlsLayout.addWidget(self.step3_1_adjustAlignmentLabel)
    self.step3_1_adjustAlignmentControlsLayout.addWidget(self.step3_1_xTranslationLabel)
    self.step3_1_adjustAlignmentControlsLayout.addWidget(self.step3_1_xTranslationSpinBox)
    self.step3_1_adjustAlignmentControlsLayout.addWidget(self.step3_1_yScaleLabel)
    self.step3_1_adjustAlignmentControlsLayout.addWidget(self.step3_1_yScaleSpinBox)
    self.step3_1_adjustAlignmentControlsLayout.addWidget(self.step3_1_yTranslationLabel)
    self.step3_1_adjustAlignmentControlsLayout.addWidget(self.step3_1_yTranslationSpinBox)
    self.step3_1_calibrationRoutineLayout.addRow(self.step3_1_adjustAlignmentControlsLayout)

    # Add empty row
    self.step3_1_calibrationRoutineLayout.addRow(' ', None)

    # Create dose information button
    self.step3_1_computeDoseFromPddButton = qt.QPushButton("Calculate dose from reference PDD")
    self.step3_1_computeDoseFromPddButton.toolTip = "Compute dose from PDD data based on RDF and MUs"
    self.step3_1_calibrationRoutineLayout.addRow(self.step3_1_computeDoseFromPddButton)

    # Empty row
    self.step3_1_calibrationRoutineLayout.addRow(' ', None)

    # Show chart of optical density vs. dose curve and remove selected points
    self.step3_1_odVsDoseCurveControlsLayout = qt.QHBoxLayout(self.step3_1_calibrationRoutineCollapsibleButton)
    self.step3_1_showOpticalDensityVsDoseCurveButton = qt.QPushButton("Plot optical density vs dose")
    self.step3_1_showOpticalDensityVsDoseCurveButton.toolTip = "Show optical density vs. Dose curve to determine the order of polynomial to fit."
    self.step3_1_removeSelectedPointsFromOpticalDensityVsDoseCurveButton = qt.QPushButton("Optional: Remove selected points from plot")
    self.step3_1_removeSelectedPointsFromOpticalDensityVsDoseCurveButton.toolTip = "Removes the selected points (typically outliers) from the OD vs Dose curve so that they are omitted during polynomial fitting.\nTo select points, hold down the right mouse button and draw a selection rectangle in the chart view."
    self.step3_1_helpLabel = qt.QLabel()
    self.step3_1_helpLabel.pixmap = qt.QPixmap(':Icons/Help.png')
    self.step3_1_helpLabel.maximumWidth = 24
    self.step3_1_helpLabel.toolTip = "To select points in the plot, hold down the right mouse button and draw a selection rectangle in the chart view."
    self.step3_1_odVsDoseCurveControlsLayout.addWidget(self.step3_1_showOpticalDensityVsDoseCurveButton)
    self.step3_1_odVsDoseCurveControlsLayout.addWidget(self.step3_1_removeSelectedPointsFromOpticalDensityVsDoseCurveButton)
    self.step3_1_odVsDoseCurveControlsLayout.addWidget(self.step3_1_helpLabel)
    self.step3_1_calibrationRoutineLayout.addRow(self.step3_1_odVsDoseCurveControlsLayout)
    
    # Add empty row
    self.step3_1_calibrationRoutineLayout.addRow(' ', None)

    # Find polynomial fit
    self.step3_1_selectOrderOfPolynomialFitButton = qt.QComboBox()
    self.step3_1_selectOrderOfPolynomialFitButton.addItem('1')
    self.step3_1_selectOrderOfPolynomialFitButton.addItem('2')
    self.step3_1_selectOrderOfPolynomialFitButton.addItem('3')
    self.step3_1_selectOrderOfPolynomialFitButton.addItem('4')
    self.step3_1_calibrationRoutineLayout.addRow('Fit with what order polynomial function:', self.step3_1_selectOrderOfPolynomialFitButton)
    
    self.step3_1_fitPolynomialToOpticalDensityVsDoseCurveButton = qt.QPushButton("Fit data and determine calibration function")
    self.step3_1_fitPolynomialToOpticalDensityVsDoseCurveButton.toolTip = "Finds the line of best fit based on the data and polynomial order provided"
    self.step3_1_calibrationRoutineLayout.addRow(self.step3_1_fitPolynomialToOpticalDensityVsDoseCurveButton)

    self.step3_1_fitPolynomialResidualsLabel = qt.QLabel()
    self.step3_1_calibrationRoutineLayout.addRow(self.step3_1_fitPolynomialResidualsLabel)

    # Step 3.2: Apply calibration
    self.step3_2_applyCalibrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step3_2_applyCalibrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step3_2_applyCalibrationCollapsibleButton.text = "3.2. Apply calibration"
    self.step3_doseCalibrationCollapsibleButtonLayout.addWidget(self.step3_2_applyCalibrationCollapsibleButton)
    self.step3_2_applyCalibrationLayout = qt.QFormLayout(self.step3_2_applyCalibrationCollapsibleButton)
    self.step3_2_applyCalibrationLayout.setContentsMargins(12,4,4,4)
    self.step3_2_applyCalibrationLayout.setSpacing(4)

    # Calibration function label
    self.step3_2_calibrationFunctionLabel = qt.QLabel("Calibration function:\n(either determined from step 3.1., or can be manually input/altered)")
    self.step3_2_calibrationFunctionLabel.wordWrap = True
    self.step3_2_applyCalibrationLayout.addRow(self.step3_2_calibrationFunctionLabel)

    # Dose calibration function input fields
    self.step3_2_calibrationFunctionLayout = qt.QHBoxLayout(self.step3_1_calibrationRoutineCollapsibleButton)
    self.step3_2_doseLabel = qt.QLabel('Dose: ')
    self.step3_2_doseLabel0LineEdit = qt.QLineEdit()
    self.step3_2_doseLabel0LineEdit.maximumWidth = 32
    self.step3_2_doseLabel0Label = qt.QLabel(' OD<span style=" font-size:8pt; vertical-align:super;">0</span> + ')
    self.step3_2_doseLabel1LineEdit = qt.QLineEdit()
    self.step3_2_doseLabel1LineEdit.maximumWidth = 32
    self.step3_2_doseLabel1Label = qt.QLabel(' OD<span style=" font-size:8pt; vertical-align:super;">1</span> + ')
    self.step3_2_doseLabel2LineEdit = qt.QLineEdit()
    self.step3_2_doseLabel2LineEdit.maximumWidth = 32
    self.step3_2_doseLabel2Label = qt.QLabel(' OD<span style=" font-size:8pt; vertical-align:super;">2</span> + ')
    self.step3_2_doseLabel3LineEdit = qt.QLineEdit()
    self.step3_2_doseLabel3LineEdit.maximumWidth = 32
    self.step3_2_doseLabel3Label = qt.QLabel(' OD<span style=" font-size:8pt; vertical-align:super;">3</span> + ')
    self.step3_2_doseLabel4LineEdit = qt.QLineEdit()
    self.step3_2_doseLabel4LineEdit.maximumWidth = 32
    self.step3_2_doseLabel4Label = qt.QLabel(' OD<span style=" font-size:8pt; vertical-align:super;">4</span>')
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel0LineEdit)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel0Label)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel1LineEdit)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel1Label)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel2LineEdit)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel2Label)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel3LineEdit)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel3Label)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel4LineEdit)
    self.step3_2_calibrationFunctionLayout.addWidget(self.step3_2_doseLabel4Label)
    self.step3_2_applyCalibrationLayout.addRow(self.step3_2_calibrationFunctionLayout)

    # Export calibration polynomial coefficients to CSV
    self.step3_2_exportCalibrationToCSV = qt.QPushButton("Optional: Export calibration points to a CSV file")
    self.step3_2_exportCalibrationToCSV.toolTip = "Export optical density to dose calibration plot points (if points were removed, those are not exported).\nIf polynomial fitting has been done, export the coefficients as well."
    self.step3_2_applyCalibrationLayout.addRow(self.step3_2_exportCalibrationToCSV)
    
    # Empty row
    self.step3_1_calibrationRoutineLayout.addRow(' ', None)

    # Apply calibration button
    self.step3_2_applyCalibrationButton = qt.QPushButton("Apply calibration")
    self.step3_2_applyCalibrationButton.toolTip = "Apply fitted polynomial on MEASURED volume"
    self.step3_2_applyCalibrationLayout.addRow(self.step3_2_applyCalibrationButton)

    self.step3_2_applyCalibrationStatusLabel = qt.QLabel()
    self.step3_2_applyCalibrationLayout.addRow(' ', self.step3_2_applyCalibrationStatusLabel)

    # Add substeps in a button group
    self.step3_calibrationCollapsibleButtonGroup = qt.QButtonGroup()
    self.step3_calibrationCollapsibleButtonGroup.addButton(self.step3_1_calibrationRoutineCollapsibleButton)
    self.step3_calibrationCollapsibleButtonGroup.addButton(self.step3_2_applyCalibrationCollapsibleButton)

    # Connections
    self.step3_1_pddLoadDataButton.connect('clicked()', self.onLoadPddDataRead)
    self.step3_1_alignCalibrationCurvesButton.connect('clicked()', self.onAlignCalibrationCurves)
    self.step3_1_xTranslationSpinBox.connect('valueChanged(double)', self.onAdjustAlignmentValueChanged)
    self.step3_1_yScaleSpinBox.connect('valueChanged(double)', self.onAdjustAlignmentValueChanged)
    self.step3_1_yTranslationSpinBox.connect('valueChanged(double)', self.onAdjustAlignmentValueChanged)
    self.step3_1_computeDoseFromPddButton.connect('clicked()', self.onComputeDoseFromPdd)
    self.step3_1_calibrationRoutineCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep3_1_CalibrationRoutineSelected)
    self.step3_1_showOpticalDensityVsDoseCurveButton.connect('clicked()', self.onShowOpticalDensityVsDoseCurve)
    self.step3_1_removeSelectedPointsFromOpticalDensityVsDoseCurveButton.connect('clicked()', self.onRemoveSelectedPointsFromOpticalDensityVsDoseCurve)
    self.step3_1_fitPolynomialToOpticalDensityVsDoseCurveButton.connect('clicked()', self.onFitPolynomialToOpticalDensityVsDoseCurve)
    self.step3_2_exportCalibrationToCSV.connect('clicked()', self.onExportCalibration)
    self.step3_2_applyCalibrationButton.connect('clicked()', self.onApplyCalibration)

    # Open prepare calibration data panel when step is first opened
    self.step3_1_calibrationRoutineCollapsibleButton.setProperty('collapsed', False)
    
  def setup_Step4_DoseComparison(self):
    # Step 4: Dose comparison and analysis
    self.step4_doseComparisonCollapsibleButton.setProperty('collapsedHeight', 4)
    # self.step4_doseComparisonCollapsibleButton.text = "4. 3D dose comparison"
    self.step4_doseComparisonCollapsibleButton.text = "4. 3D gamma dose comparison" #TODO: Switch to line above when more dose comparisons are added
    self.sliceletPanelLayout.addWidget(self.step4_doseComparisonCollapsibleButton)
    self.step4_doseComparisonCollapsibleButtonLayout = qt.QFormLayout(self.step4_doseComparisonCollapsibleButton)
    self.step4_doseComparisonCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step4_doseComparisonCollapsibleButtonLayout.setSpacing(4)

    # Mask contour selector
    self.step4_maskContourSelector = slicer.qMRMLNodeComboBox()
    self.step4_maskContourSelector.nodeTypes = ( ("vtkMRMLContourNode"), "" )
    self.step4_maskContourSelector.addEnabled = False
    self.step4_maskContourSelector.removeEnabled = False
    self.step4_maskContourSelector.noneEnabled = True
    self.step4_maskContourSelector.setMRMLScene( slicer.mrmlScene )
    self.step4_maskContourSelector.setToolTip( "Pick the mask contour that determines the considered region for comparison." )
    self.step4_doseComparisonCollapsibleButtonLayout.addRow("Mask contour: ", self.step4_maskContourSelector)

    # Collapsible buttons for substeps
    self.step4_1_gammaDoseComparisonCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step4_1_gammaDoseComparisonCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step4_1_gammaDoseComparisonCollapsibleButton.setVisible(False) # TODO
    self.step4_2_chiDoseComparisonCollapsibleButton = ctk.ctkCollapsibleButton() #TODO:
    self.step4_2_chiDoseComparisonCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step4_2_chiDoseComparisonCollapsibleButton.setVisible(False) # TODO
    self.step4_3_doseDifferenceComparisonCollapsibleButton = ctk.ctkCollapsibleButton() #TODO:
    self.step4_3_doseDifferenceComparisonCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step4_3_doseDifferenceComparisonCollapsibleButton.setVisible(False) # TODO

    self.collapsibleButtonsGroupForDoseComparisonAndAnalysis = qt.QButtonGroup()
    self.collapsibleButtonsGroupForDoseComparisonAndAnalysis.addButton(self.step4_1_gammaDoseComparisonCollapsibleButton)
    self.collapsibleButtonsGroupForDoseComparisonAndAnalysis.addButton(self.step4_2_chiDoseComparisonCollapsibleButton)
    self.collapsibleButtonsGroupForDoseComparisonAndAnalysis.addButton(self.step4_3_doseDifferenceComparisonCollapsibleButton)

    # 4.1. Gamma dose comparison
    self.step4_1_gammaDoseComparisonCollapsibleButton.text = "4.1. Gamma dose comparison"
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout = qt.QFormLayout(self.step4_1_gammaDoseComparisonCollapsibleButton)
    self.step4_doseComparisonCollapsibleButtonLayout.addRow(self.step4_1_gammaDoseComparisonCollapsibleButton)
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.setSpacing(4)

    # Temporarily assign main layout to 4.1. gamma layout until more dose comparisons are added
    #TODO: Remove when more dose comparisons are added
    self.step4_1_gammaDoseComparisonCollapsibleButton = self.step4_doseComparisonCollapsibleButton
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout = self.step4_doseComparisonCollapsibleButtonLayout

    # DTA
    self.step4_1_dtaDistanceToleranceMmSpinBox = qt.QDoubleSpinBox()
    self.step4_1_dtaDistanceToleranceMmSpinBox.setValue(3.0)
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow('Distance-to-agreement criteria (mm): ', self.step4_1_dtaDistanceToleranceMmSpinBox)

    # Dose difference tolerance criteria
    self.step4_1_doseDifferenceToleranceLayout = qt.QHBoxLayout(self.step4_1_gammaDoseComparisonCollapsibleButton)
    self.step4_1_doseDifferenceToleranceLabelBefore = qt.QLabel('Dose difference criteria is ')
    self.step4_1_doseDifferenceTolerancePercentSpinBox = qt.QDoubleSpinBox()
    self.step4_1_doseDifferenceTolerancePercentSpinBox.setValue(3.0)
    self.step4_1_doseDifferenceToleranceLabelAfter = qt.QLabel('% of:  ')
    self.step4_1_doseDifferenceToleranceLayout.addWidget(self.step4_1_doseDifferenceToleranceLabelBefore)
    self.step4_1_doseDifferenceToleranceLayout.addWidget(self.step4_1_doseDifferenceTolerancePercentSpinBox)
    self.step4_1_doseDifferenceToleranceLayout.addWidget(self.step4_1_doseDifferenceToleranceLabelAfter)

    self.step4_1_referenceDoseLayout = qt.QVBoxLayout()
    self.step4_1_referenceDoseUseMaximumDoseRadioButton = qt.QRadioButton('the maximum dose\n(calculated from plan dose volume)')
    self.step4_1_referenceDoseUseCustomValueLayout = qt.QHBoxLayout(self.step4_1_gammaDoseComparisonCollapsibleButton)
    self.step4_1_referenceDoseUseCustomValueGyRadioButton = qt.QRadioButton('a custom dose value (cGy):')
    self.step4_1_referenceDoseCustomValueCGySpinBox = qt.QDoubleSpinBox()
    self.step4_1_referenceDoseCustomValueCGySpinBox.value = 5.0
    self.step4_1_referenceDoseCustomValueCGySpinBox.maximum = 99999
    self.step4_1_referenceDoseCustomValueCGySpinBox.maximumWidth = 48
    self.step4_1_referenceDoseCustomValueCGySpinBox.enabled = False
    self.step4_1_referenceDoseUseCustomValueLayout.addWidget(self.step4_1_referenceDoseUseCustomValueGyRadioButton)
    self.step4_1_referenceDoseUseCustomValueLayout.addWidget(self.step4_1_referenceDoseCustomValueCGySpinBox)
    self.step4_1_referenceDoseUseCustomValueLayout.addStretch(1) 
    self.step4_1_referenceDoseLayout.addWidget(self.step4_1_referenceDoseUseMaximumDoseRadioButton)
    self.step4_1_referenceDoseLayout.addLayout(self.step4_1_referenceDoseUseCustomValueLayout)
    self.step4_1_doseDifferenceToleranceLayout.addLayout(self.step4_1_referenceDoseLayout)

    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow(self.step4_1_doseDifferenceToleranceLayout)

    # Analysis threshold
    self.step4_1_analysisThresholdLayout = qt.QHBoxLayout(self.step4_1_gammaDoseComparisonCollapsibleButton)
    self.step4_1_analysisThresholdLabelBefore = qt.QLabel('Do not calculate gamma values for voxels below ')
    self.step4_1_analysisThresholdPercentSpinBox = qt.QDoubleSpinBox()
    self.step4_1_analysisThresholdPercentSpinBox.value = 0.0
    self.step4_1_analysisThresholdPercentSpinBox.maximumWidth = 48
    self.step4_1_analysisThresholdLabelAfter = qt.QLabel('% of the maximum dose,')
    self.step4_1_analysisThresholdLabelAfter.wordWrap = True
    self.step4_1_analysisThresholdLayout.addWidget(self.step4_1_analysisThresholdLabelBefore)
    self.step4_1_analysisThresholdLayout.addWidget(self.step4_1_analysisThresholdPercentSpinBox)
    self.step4_1_analysisThresholdLayout.addWidget(self.step4_1_analysisThresholdLabelAfter)
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow(self.step4_1_analysisThresholdLayout)
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow(qt.QLabel('                                            or the custom dose value (depending on selection above).'))

    # Use linear interpolation
    self.step4_1_useLinearInterpolationCheckBox = qt.QCheckBox()
    self.step4_1_useLinearInterpolationCheckBox.checked = True
    self.step4_1_useLinearInterpolationCheckBox.setToolTip('Flag determining whether linear interpolation is used when resampling the compare dose volume to reference grid. Nearest neighbour is used if unchecked.')
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow('Use linear interpolation: ', self.step4_1_useLinearInterpolationCheckBox)

    # Maximum gamma
    self.step4_1_maximumGammaSpinBox = qt.QDoubleSpinBox()
    self.step4_1_maximumGammaSpinBox.setValue(2.0)
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow('Upper bound for gamma calculation: ', self.step4_1_maximumGammaSpinBox)

    # Gamma volume selector
    self.step4_1_gammaVolumeSelectorLayout = qt.QHBoxLayout(self.step4_1_gammaDoseComparisonCollapsibleButton)
    self.step4_1_gammaVolumeSelector = slicer.qMRMLNodeComboBox()
    self.step4_1_gammaVolumeSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.step4_1_gammaVolumeSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.step4_1_gammaVolumeSelector.addEnabled = True
    self.step4_1_gammaVolumeSelector.removeEnabled = False
    self.step4_1_gammaVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.step4_1_gammaVolumeSelector.setToolTip( "Select output gamma volume" )
    self.step4_1_gammaVolumeSelector.setProperty('baseName', 'GammaVolume')
    self.step4_1_helpLabel = qt.QLabel()
    self.step4_1_helpLabel.pixmap = qt.QPixmap(':Icons/Help.png')
    self.step4_1_helpLabel.maximumWidth = 24
    self.step4_1_helpLabel.toolTip = "A gamma volume must be selected to contain the output. You can create a new volume by selecting 'Create new Volume'"
    self.step4_1_gammaVolumeSelectorLayout.addWidget(self.step4_1_gammaVolumeSelector)
    self.step4_1_gammaVolumeSelectorLayout.addWidget(self.step4_1_helpLabel)
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow("Gamma volume: ", self.step4_1_gammaVolumeSelectorLayout)

    self.step4_1_computeGammaButton = qt.QPushButton('Calculate gamma volume')
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow(self.step4_1_computeGammaButton)

    self.step4_1_gammaStatusLabel = qt.QLabel()
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow(self.step4_1_gammaStatusLabel)

    self.step4_1_showGammaReportButton = qt.QPushButton('Show report')
    self.step4_1_showGammaReportButton.enabled = False
    self.step4_1_gammaDoseComparisonCollapsibleButtonLayout.addRow(self.step4_1_showGammaReportButton)

    # 4.2. Chi dose comparison
    self.step4_2_chiDoseComparisonCollapsibleButton.text = "4.2. Chi dose comparison"
    self.step4_2_chiDoseComparisonCollapsibleButtonLayout = qt.QFormLayout(self.step4_2_chiDoseComparisonCollapsibleButton)
    self.step4_doseComparisonCollapsibleButtonLayout.addRow(self.step4_2_chiDoseComparisonCollapsibleButton)
    self.step4_2_chiDoseComparisonCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step4_2_chiDoseComparisonCollapsibleButtonLayout.setSpacing(4)

    # 4.3. Dose difference comparison
    self.step4_3_doseDifferenceComparisonCollapsibleButton.text = "4.3. Dose difference comparison"
    self.step4_3_doseDifferenceComparisonCollapsibleButtonLayout = qt.QFormLayout(self.step4_3_doseDifferenceComparisonCollapsibleButton)
    self.step4_doseComparisonCollapsibleButtonLayout.addRow(self.step4_3_doseDifferenceComparisonCollapsibleButton)
    self.step4_3_doseDifferenceComparisonCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step4_3_doseDifferenceComparisonCollapsibleButtonLayout.setSpacing(4)

    # Scalar bar
    self.gammaScalarBarWidget = vtk.vtkScalarBarWidget()

    # Connections
    self.step4_doseComparisonCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep4_DoseComparisonSelected)
    self.step4_maskContourSelector.connect('currentNodeChanged(vtkMRMLNode*)', self.onStep4_MaskContourSelectionChanged)
    self.step4_1_referenceDoseUseMaximumDoseRadioButton.connect('toggled(bool)', self.onUseMaximumDoseRadioButtonToggled)
    self.step4_1_computeGammaButton.connect('clicked()', self.onGammaDoseComparison)
    self.step4_1_showGammaReportButton.connect('clicked()', self.onShowGammaReport)

    # Open gamma dose comparison panel when step is first opened
    #self.step4_1_gammaDoseComparisonCollapsibleButton.setProperty('collapsed',False) #TODO: Uncomment when adding more dose comparisons
    self.step4_1_referenceDoseUseMaximumDoseRadioButton.setChecked(True)

  def setup_StepT1_lineProfileCollapsibleButton(self):
    # Step T1: Line profile tool
    self.stepT1_lineProfileCollapsibleButton.setProperty('collapsedHeight', 4)
    self.stepT1_lineProfileCollapsibleButton.text = "Tool: Line profile"
    self.sliceletPanelLayout.addWidget(self.stepT1_lineProfileCollapsibleButton)
    self.stepT1_lineProfileCollapsibleButtonLayout = qt.QFormLayout(self.stepT1_lineProfileCollapsibleButton)
    self.stepT1_lineProfileCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.stepT1_lineProfileCollapsibleButtonLayout.setSpacing(4)
    
    # Ruler creator
    self.stepT1_rulerCreationButton = slicer.qSlicerMouseModeToolBar()
    self.stepT1_rulerCreationButton.setApplicationLogic(slicer.app.applicationLogic())
    self.stepT1_rulerCreationButton.setMRMLScene(slicer.app.mrmlScene())
    self.stepT1_rulerCreationButton.setToolTip( "Create ruler (line segment) for line profile" )
    self.stepT1_lineProfileCollapsibleButtonLayout.addRow("Create ruler: ", self.stepT1_rulerCreationButton)

    # Input ruler selector
    self.stepT1_inputRulerSelector = slicer.qMRMLNodeComboBox()
    self.stepT1_inputRulerSelector.nodeTypes = ( ("vtkMRMLAnnotationRulerNode"), "" )
    self.stepT1_inputRulerSelector.selectNodeUponCreation = True
    self.stepT1_inputRulerSelector.addEnabled = False
    self.stepT1_inputRulerSelector.removeEnabled = False
    self.stepT1_inputRulerSelector.noneEnabled = False
    self.stepT1_inputRulerSelector.showHidden = False
    self.stepT1_inputRulerSelector.showChildNodeTypes = False
    self.stepT1_inputRulerSelector.setMRMLScene( slicer.mrmlScene )
    self.stepT1_inputRulerSelector.setToolTip( "Pick the ruler that defines the sampling line." )
    self.stepT1_lineProfileCollapsibleButtonLayout.addRow("Input ruler: ", self.stepT1_inputRulerSelector)

    # Line sampling resolution in mm
    self.stepT1_lineResolutionMmSliderWidget = ctk.ctkSliderWidget()
    self.stepT1_lineResolutionMmSliderWidget.decimals = 1
    self.stepT1_lineResolutionMmSliderWidget.singleStep = 0.1
    self.stepT1_lineResolutionMmSliderWidget.minimum = 0.1
    self.stepT1_lineResolutionMmSliderWidget.maximum = 2
    self.stepT1_lineResolutionMmSliderWidget.value = 0.5
    self.stepT1_lineResolutionMmSliderWidget.setToolTip("Sampling density along the line in mm")
    self.stepT1_lineProfileCollapsibleButtonLayout.addRow("Line resolution (mm): ", self.stepT1_lineResolutionMmSliderWidget)

    # Create line profile button
    self.stepT1_createLineProfileButton = qt.QPushButton("Create line profile")
    self.stepT1_createLineProfileButton.toolTip = "Compute and show line profile"
    self.stepT1_createLineProfileButton.enabled = False
    self.stepT1_lineProfileCollapsibleButtonLayout.addRow(self.stepT1_createLineProfileButton)
    self.onSelectLineProfileParameters()

    # Export line profiles to CSV button
    self.stepT1_exportLineProfilesToCSV = qt.QPushButton("Export line profiles to CSV")
    self.stepT1_exportLineProfilesToCSV.toolTip = "Export calculated line profiles to CSV"
    self.stepT1_lineProfileCollapsibleButtonLayout.addRow(self.stepT1_exportLineProfilesToCSV)

    # Hint label
    self.stepT1_lineProfileCollapsibleButtonLayout.addRow(' ', None)
    self.stepT1_lineProfileHintLabel = qt.QLabel("Hint: Full screen plot view is available in the layout selector tab (top one)")
    self.stepT1_lineProfileCollapsibleButtonLayout.addRow(self.stepT1_lineProfileHintLabel)

    # Connections
    self.stepT1_lineProfileCollapsibleButton.connect('contentsCollapsed(bool)', self.onStepT1_LineProfileSelected)
    self.stepT1_createLineProfileButton.connect('clicked(bool)', self.onCreateLineProfileButton)
    self.stepT1_inputRulerSelector.connect("currentNodeChanged(vtkMRMLNode*)", self.onSelectLineProfileParameters)
    self.stepT1_exportLineProfilesToCSV.connect('clicked()', self.onExportLineProfiles)

  #
  # -----------------------
  # Event handler functions
  # -----------------------
  #
  def onViewSelect(self, layoutIndex):
    if layoutIndex == 0:
       self.layoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)
    elif layoutIndex == 1:
       self.layoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutConventionalView)
    elif layoutIndex == 2:
       self.layoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
    elif layoutIndex == 3:
       self.layoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutTabbedSliceView)
    elif layoutIndex == 4:
       self.layoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutDual3DView)
    elif layoutIndex == 5:
       self.layoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpQuantitativeView)
    elif layoutIndex == 6:
       self.layoutWidget.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUpQuantitativeView)

  def onClinicalModeSelect(self, toggled):
    if self.step0_clinicalModeRadioButton.isChecked() == True:
      self.mode = 'Clinical'
            
      # Step 3.1. Label for plot visibility
      self.step3_1_showOpticalDensityVsDoseCurveButton.setText("Plot optical density vs dose")
      self.step3_1_showOpticalDensityVsDoseCurveButton.toolTip = "Show optical density vs. Dose curve to determine the order of polynomial to fit."
  
  def onPreclinicalModeSelect(self, toggled):
    if self.step0_preclinicalModeRadioButton.isChecked() == True:
      self.mode = 'Preclinical'
            
      # Step 3.1. Label for plot visibility
      self.step3_1_showOpticalDensityVsDoseCurveButton.setText("Plot R1 vs dose")
      self.step3_1_showOpticalDensityVsDoseCurveButton.toolTip = "Show Relaxation Rates vs. Dose curve to determine the order of polynomial to fit."
    
  def onLoadNonDicomData(self):
    slicer.util.openAddDataDialog()

  def onStep1_LoadDataCollapsed(self, collapsed):
    # Save selections to member variables when switching away from load data step
    if collapsed == True:
      self.planCtVolumeNode = self.planCTSelector.currentNode()
      self.planDoseVolumeNode = self.planDoseSelector.currentNode()
      self.obiVolumeNode = self.obiSelector.currentNode()
      self.planStructuresNode = self.planStructuresSelector.currentNode()
      self.measuredVolumeNode = self.measuredVolumeSelector.currentNode()
      self.calibrationVolumeNode = self.calibrationVolumeSelector.currentNode()

  def onStep2_2_MeasuredDoseToObiRegistrationSelected(self, collapsed):
    # Make sure the functions handling entering the fiducial selection panels are called when entering the outer panel
    if collapsed == False:
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      if self.step2_2_1_obiFiducialSelectionCollapsibleButton.collapsed == False:
        if self.obiVolumeNode != None:
          selectionNode.SetActiveVolumeID(self.obiVolumeNode.GetID())
        else:
          selectionNode.SetActiveVolumeID(None)
        selectionNode.SetSecondaryVolumeID(None)
        appLogic.PropagateVolumeSelection() 
      elif self.step2_2_2_measuredFiducialSelectionCollapsibleButton.collapsed == False:
        if self.measuredVolumeNode != None:
          selectionNode.SetActiveVolumeID(self.measuredVolumeNode.GetID())
        else:
          selectionNode.SetActiveVolumeID(None)
        selectionNode.SetSecondaryVolumeID(None)
        appLogic.PropagateVolumeSelection() 

  def onStep2_2_1_ObiFiducialCollectionSelected(self, collapsed):
    # Add Markups widget
    if collapsed == False:
      #TODO: Clean up if possible. Did not work without double nesting (widget disappeared when switched to next step)
      newLayout = qt.QFormLayout()
      newLayout.setMargin(0)
      newLayout.setSpacing(0)
      tempLayoutInner = qt.QVBoxLayout()
      tempLayoutInner.setMargin(0)
      tempLayoutInner.setSpacing(0)
      
      # Create instructions label
      fiducialSelectLabel = qt.QLabel("Scroll to the image plane where the OBI fiducials are located, then click the 'Select fiducials' button below. Next, select the fiducial points in the displayed image plane. The fiducial points will populate the table below.")
      fiducialSelectLabel.wordWrap = True
      newLayout.addRow(fiducialSelectLabel)
      
      # Create frame for markups widget
      tempFrame = qt.QFrame()
      tempFrame.setLayout(tempLayoutInner)
      tempLayoutInner.addWidget(self.fiducialSelectionWidget)
      newLayout.addRow(tempFrame)
      self.step2_2_1_obiFiducialSelectionCollapsibleButton.setLayout(newLayout)

      # Set annotation list node
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      selectionNode.SetActivePlaceNodeID(self.obiMarkupsFiducialNode.GetID())
      # interactionNode = appLogic.GetInteractionNode()
      # interactionNode.SwitchToSinglePlaceMode()
      # Switch to place fiducial mode
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")

      # Select OBI fiducials node
      activeMarkupMrmlNodeCombobox = slicer.util.findChildren(widget=self.markupsWidgetClone, className='qMRMLNodeComboBox', name='activeMarkupMRMLNodeComboBox')[0]
      activeMarkupMrmlNodeCombobox.setCurrentNode(self.obiMarkupsFiducialNode)
      self.markupsWidget.onActiveMarkupMRMLNodeChanged(self.obiMarkupsFiducialNode)
      
      # Show only the OBI fiducials in the 3D view
      self.markupsLogic.SetAllMarkupsVisibility(self.obiMarkupsFiducialNode, True)
      self.markupsLogic.SetAllMarkupsVisibility(self.measuredMarkupsFiducialNode, False)

      # Automatically show OBI volume (show nothing if not present)
      if self.obiVolumeNode != None:
        selectionNode.SetActiveVolumeID(self.obiVolumeNode.GetID())
      else:
        selectionNode.SetActiveVolumeID(None)
      selectionNode.SetSecondaryVolumeID(None)
      appLogic.PropagateVolumeSelection() 
    else:
      # Delete temporary layout
      currentLayout = self.step2_2_1_obiFiducialSelectionCollapsibleButton.layout()
      if currentLayout:
        currentLayout.deleteLater()

      # Show both fiducial lists in the 3D view
      self.markupsLogic.SetAllMarkupsVisibility(self.obiMarkupsFiducialNode, True)
      self.markupsLogic.SetAllMarkupsVisibility(self.measuredMarkupsFiducialNode, True)

  def onStep2_2_2_ObiFiducialCollectionSelected(self, collapsed):
    # Add Markups widget
    if collapsed == False:
      #TODO: Clean up if possible. Did not work without double nesting
      newLayout = qt.QFormLayout()
      newLayout.setMargin(0)
      newLayout.setSpacing(0)
      tempLayoutInner = qt.QVBoxLayout()
      tempLayoutInner.setMargin(0)
      tempLayoutInner.setSpacing(0)

      # Create instructions label
      fiducialSelectLabel = qt.QLabel("Scroll to the image plane where the gel dosimeter fiducials are located, then click the 'Select fiducials' button below. Next, select the fiducial points in the displayed image plane. The fiducial points will populate the table below.")
      fiducialSelectLabel.wordWrap = True
      newLayout.addRow(fiducialSelectLabel)
      
      # Create frame for markups widget
      tempFrame = qt.QFrame()
      tempFrame.setLayout(tempLayoutInner)
      tempLayoutInner.addWidget(self.fiducialSelectionWidget)
      newLayout.addWidget(tempFrame)
      self.step2_2_2_measuredFiducialSelectionCollapsibleButton.setLayout(newLayout)

      # Set annotation list node
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      selectionNode.SetActivePlaceNodeID(self.measuredMarkupsFiducialNode.GetID())
      # interactionNode = appLogic.GetInteractionNode()
      # interactionNode.SwitchToSinglePlaceMode()
      # Switch to place fiducial mode
      selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLMarkupsFiducialNode")

      # Select MEASURED fiducials node
      activeMarkupMrmlNodeCombobox = slicer.util.findChildren(widget=self.markupsWidgetClone, className='qMRMLNodeComboBox', name='activeMarkupMRMLNodeComboBox')[0]
      activeMarkupMrmlNodeCombobox.setCurrentNode(self.measuredMarkupsFiducialNode)
      self.markupsWidget.onActiveMarkupMRMLNodeChanged(self.measuredMarkupsFiducialNode)

      # Show only the OBI fiducials in the 3D view
      self.markupsLogic.SetAllMarkupsVisibility(self.measuredMarkupsFiducialNode, True)
      self.markupsLogic.SetAllMarkupsVisibility(self.obiMarkupsFiducialNode, False)

      # Automatically show MEASURED volume (show nothing if not present)
      if self.measuredVolumeNode != None:
        selectionNode.SetActiveVolumeID(self.measuredVolumeNode.GetID())
      else:
        selectionNode.SetActiveVolumeID(None)
      selectionNode.SetSecondaryVolumeID(None)
      appLogic.PropagateVolumeSelection() 
    else:
      # Delete temporary layout
      currentLayout = self.step2_2_2_measuredFiducialSelectionCollapsibleButton.layout()
      if currentLayout:
        currentLayout.deleteLater()

      # Show both fiducial lists in the 3D view
      self.markupsLogic.SetAllMarkupsVisibility(self.obiMarkupsFiducialNode, True)
      self.markupsLogic.SetAllMarkupsVisibility(self.measuredMarkupsFiducialNode, True)

  def onObiToPlanCTRegistration(self):
    # Start registration
    obiVolumeID = self.obiVolumeNode.GetID()
    planCTVolumeID = self.planCtVolumeNode.GetID()
    planDoseVolumeID = self.planDoseVolumeNode.GetID()
    planStructuresID = self.planStructuresSelector.currentNodeID
    self.logic.registerObiToPlanCt(obiVolumeID, planCTVolumeID, planDoseVolumeID, planStructuresID)

    # Show the two volumes for visual evaluation of the registration
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetActiveVolumeID(planCTVolumeID)
    selectionNode.SetSecondaryVolumeID(obiVolumeID)
    appLogic.PropagateVolumeSelection() 
    # Set color to the OBI volume
    obiVolumeDisplayNode = self.obiVolumeNode.GetDisplayNode()
    colorNode = slicer.util.getNode('Green')
    obiVolumeDisplayNode.SetAndObserveColorNodeID(colorNode.GetID())
    # Set transparency to the OBI volume
    compositeNodes = slicer.util.getNodes("vtkMRMLSliceCompositeNode*")
    for compositeNode in compositeNodes.values():
      compositeNode.SetForegroundOpacity(0.5)
    # Hide structures for sake of speed
    if self.planStructuresNode != None:
      self.planStructuresNode.SetDisplayVisibilityForBranch(0)
    # Hide beam models
    beamModelsParent = slicer.util.getNode('*_BeamModels_SubjectHierarchy')
    if beamModelsParent != None:
      beamModelsParent.SetDisplayVisibilityForBranch(0)

  def onMeasuredToObiRegistration(self):
    errorRms = self.logic.registerObiToMeasured(self.obiMarkupsFiducialNode.GetID(), self.measuredMarkupsFiducialNode.GetID())
    
    # Show registration error on GUI
    self.step2_2_3_measuredToObiFiducialRegistrationErrorLabel.setText(errorRms)

    # Apply transform to MEASURED volume
    obiToMeasuredTransformNode = slicer.util.getNode(self.logic.obiToMeasuredTransformName)
    self.measuredVolumeNode.SetAndObserveTransformNodeID(obiToMeasuredTransformNode.GetID())

    # Show both volumes in the 2D views
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetActiveVolumeID(self.obiVolumeNode.GetID())
    selectionNode.SetSecondaryVolumeID(self.measuredVolumeNode.GetID())
    appLogic.PropagateVolumeSelection() 

  def onLoadPddDataRead(self):
    fileName = qt.QFileDialog.getOpenFileName(0, 'Open PDD data file', '', 'CSV with COMMA ( *.csv )')
    if fileName != None and fileName != '':
      success = self.logic.loadPdd(fileName)
      if success == True:
        self.logic.delayDisplay('PDD loaded successfully')
        return
    slicer.util.errorDisplay('PDD loading failed!')

  def onStep3_1_CalibrationRoutineSelected(self, collapsed):
    if collapsed == False:
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      if self.measuredVolumeNode != None:
        selectionNode.SetActiveVolumeID(self.measuredVolumeNode.GetID())
      else:
        selectionNode.SetActiveVolumeID(None)
      selectionNode.SetSecondaryVolumeID(None)
      appLogic.PropagateVolumeSelection() 

  def parseCalibrationVolume(self):
    radiusOfCentreCircleText = self.step3_1_radiusMmFromCentrePixelLineEdit.text
    radiusOfCentreCircleFloat = 0
    if radiusOfCentreCircleText.isnumeric():
      radiusOfCentreCircleFloat = float(radiusOfCentreCircleText)
    else:
      slicer.util.errorDisplay('Invalid averaging radius!')
      return False

    success = self.logic.getMeanOpticalDensityOfCentralCylinder(self.calibrationVolumeNode.GetID(), radiusOfCentreCircleFloat)
    if success == True:
      self.logic.delayDisplay('Calibration volume parsed successfully')
    slicer.util.errorDisplay('Calibration volume parsing failed!')
    return success

  def createCalibrationCurvesWindow(self):
    # Set up window to be used for displaying data
    self.calibrationCurveChartView = vtk.vtkContextView()
    self.calibrationCurveChartView.GetRenderer().SetBackground(1,1,1)
    self.calibrationCurveChart = vtk.vtkChartXY()
    self.calibrationCurveChartView.GetScene().AddItem(self.calibrationCurveChart)
    
  def showCalibrationCurves(self):
    # Create CALIBRATION mean optical density plot
    self.calibrationCurveDataTable = vtk.vtkTable()
    calibrationNumberOfRows = self.logic.calibrationDataArray.shape[0]

    calibrationDepthArray = vtk.vtkDoubleArray()
    calibrationDepthArray.SetName("Depth (cm)")
    self.calibrationCurveDataTable.AddColumn(calibrationDepthArray)
    calibrationMeanOpticalDensityArray = vtk.vtkDoubleArray()
    calibrationMeanOpticalDensityArray.SetName("Calibration data (mean optical density)")
    self.calibrationCurveDataTable.AddColumn(calibrationMeanOpticalDensityArray)

    self.calibrationCurveDataTable.SetNumberOfRows(calibrationNumberOfRows)
    for rowIndex in xrange(calibrationNumberOfRows):
      self.calibrationCurveDataTable.SetValue(rowIndex, 0, self.logic.calibrationDataArray[rowIndex, 0])
      self.calibrationCurveDataTable.SetValue(rowIndex, 1, self.logic.calibrationDataArray[rowIndex, 1])
      # self.calibrationCurveDataTable.SetValue(rowIndex, 2, self.logic.calibrationDataArray[rowIndex, 2])

    if hasattr(self, 'calibrationMeanOpticalDensityLine'):
      self.calibrationCurveChart.RemovePlotInstance(self.calibrationMeanOpticalDensityLine)
    self.calibrationMeanOpticalDensityLine = self.calibrationCurveChart.AddPlot(vtk.vtkChart.LINE)
    self.calibrationMeanOpticalDensityLine.SetInputData(self.calibrationCurveDataTable, 0, 1)
    self.calibrationMeanOpticalDensityLine.SetColor(255, 0, 0, 255)
    self.calibrationMeanOpticalDensityLine.SetWidth(2.0)

    # Create Pdd plot
    self.pddDataTable = vtk.vtkTable()
    pddNumberOfRows = self.logic.pddDataArray.shape[0]
    pddDepthArray = vtk.vtkDoubleArray()
    pddDepthArray.SetName("Depth (cm)")
    self.pddDataTable.AddColumn(pddDepthArray)
    pddValueArray = vtk.vtkDoubleArray()
    pddValueArray.SetName("PDD (percent depth dose)")
    self.pddDataTable.AddColumn(pddValueArray)

    self.pddDataTable.SetNumberOfRows(pddNumberOfRows)
    for pddDepthCounter in xrange(pddNumberOfRows):
      self.pddDataTable.SetValue(pddDepthCounter, 0, self.logic.pddDataArray[pddDepthCounter, 0])
      self.pddDataTable.SetValue(pddDepthCounter, 1, self.logic.pddDataArray[pddDepthCounter, 1])

    if hasattr(self, 'pddLine'):
      self.calibrationCurveChart.RemovePlotInstance(self.pddLine)
    self.pddLine = self.calibrationCurveChart.AddPlot(vtk.vtkChart.LINE)
    self.pddLine.SetInputData(self.pddDataTable, 0, 1)
    self.pddLine.SetColor(0, 0, 255, 255)
    self.pddLine.SetWidth(2.0)

    # Add aligned curve to the graph
    self.calibrationDataAlignedTable = vtk.vtkTable()
    calibrationDataAlignedNumberOfRows = self.logic.calibrationDataAlignedToDisplayArray.shape[0]
    calibrationDataAlignedDepthArray = vtk.vtkDoubleArray()
    calibrationDataAlignedDepthArray.SetName("Depth (cm)")
    self.calibrationDataAlignedTable.AddColumn(calibrationDataAlignedDepthArray)
    calibrationDataAlignedValueArray = vtk.vtkDoubleArray()
    calibrationDataAlignedValueArray.SetName("Aligned calibration data")
    self.calibrationDataAlignedTable.AddColumn(calibrationDataAlignedValueArray)

    self.calibrationDataAlignedTable.SetNumberOfRows(calibrationDataAlignedNumberOfRows)
    for calibrationDataAlignedDepthCounter in xrange(calibrationDataAlignedNumberOfRows):
      self.calibrationDataAlignedTable.SetValue(calibrationDataAlignedDepthCounter, 0, self.logic.calibrationDataAlignedToDisplayArray[calibrationDataAlignedDepthCounter, 0])
      self.calibrationDataAlignedTable.SetValue(calibrationDataAlignedDepthCounter, 1, self.logic.calibrationDataAlignedToDisplayArray[calibrationDataAlignedDepthCounter, 1])

    if hasattr(self, 'calibrationDataAlignedLine'):
      self.calibrationCurveChart.RemovePlotInstance(self.calibrationDataAlignedLine)
    self.calibrationDataAlignedLine = self.calibrationCurveChart.AddPlot(vtk.vtkChart.LINE)
    self.calibrationDataAlignedLine.SetInputData(self.calibrationDataAlignedTable, 0, 1)
    self.calibrationDataAlignedLine.SetColor(0, 212, 0, 255)
    self.calibrationDataAlignedLine.SetWidth(2.0)

    # Show chart
    self.calibrationCurveChart.GetAxis(1).SetTitle('Depth (cm) - select region using right mouse button to be considered for calibration')
    self.calibrationCurveChart.GetAxis(0).SetTitle('Percent Depth Dose / Optical Density')
    self.calibrationCurveChart.SetShowLegend(True)
    self.calibrationCurveChart.SetTitle('PDD vs Calibration data')
    self.calibrationCurveChartView.GetInteractor().Initialize()
    self.calibrationCurveChartView.GetRenderWindow().SetSize(800,550)
    self.calibrationCurveChartView.GetRenderWindow().SetWindowName('PDD vs Calibration data chart')
    self.calibrationCurveChartView.GetRenderWindow().Start()

  def onAlignCalibrationCurves(self):
    # Parse calibration volume (average optical densities along central cylinder)
    success = self.parseCalibrationVolume()
    if not success:
      return
    
    # Align PDD data and "experimental" (CALIBRATION) data. Allow for horizontal shift
    # and vertical scale (max PDD Y value/max CALIBRATION Y value).
    result = self.logic.alignPddToCalibration()
    
    # Set alignment results to manual controls
    self.step3_1_xTranslationSpinBox.blockSignals(True)
    self.step3_1_xTranslationSpinBox.setValue(result[1])
    self.step3_1_xTranslationSpinBox.blockSignals(False)
    self.step3_1_yScaleSpinBox.blockSignals(True)
    self.step3_1_yScaleSpinBox.setValue(result[2])
    self.step3_1_yScaleSpinBox.blockSignals(False)
    self.step3_1_yTranslationSpinBox.blockSignals(True)
    self.step3_1_yTranslationSpinBox.setValue(result[3])
    self.step3_1_yTranslationSpinBox.blockSignals(False)

    # Show plots
    self.createCalibrationCurvesWindow()
    self.showCalibrationCurves()

  def onAdjustAlignmentValueChanged(self, value):
    self.logic.createAlignedCalibrationArray(self.step3_1_xTranslationSpinBox.value, self.step3_1_yScaleSpinBox.value, self.step3_1_yTranslationSpinBox.value)
    self.showCalibrationCurves()

  def onComputeDoseFromPdd(self):
    rdfInputText = self.step3_1_rdfLineEdit.text
    monitorUnitsInputText = self.step3_1_monitorUnitsLineEdit.text
    rdfFloat = 0
    monitorUnitsFloat = 0
    if monitorUnitsInputText.isnumeric() and rdfInputText.isnumeric():
      monitorUnitsFloat = float(monitorUnitsInputText)
      rdfFloat = float(rdfInputText)
    else:
      slicer.util.errorDisplay('Invalid monitor units or RDF!')
      return

    # Calculate dose information: calculatedDose = (PddDose * MonitorUnits * RDF) / 10000
    if self.logic.computeDoseForMeasuredData(rdfFloat, monitorUnitsFloat) == True:
      self.logic.delayDisplay('Dose successfully calculated from PDD')
    else:
      slicer.util.errorDisplay('Dose calculation from PDD failed!')

  def onShowOpticalDensityVsDoseCurve(self):
    # Get selection from PDD vs Calibration chart
    selection = self.pddLine.GetSelection()
    if selection != None and selection.GetNumberOfTuples() > 0:
      pddRangeMin = self.pddDataTable.GetValue(selection.GetValue(0), 0)
      pddRangeMax = self.pddDataTable.GetValue(selection.GetValue(selection.GetNumberOfTuples()-1), 0)
    else:
      pddRangeMin = -1000
      pddRangeMax = 1000
    logging.info('Selected Pdd range: {0} - {1}'.format(pddRangeMin,pddRangeMax))

    # Create optical density vs dose function
    self.logic.createOpticalDensityVsDoseFunction(pddRangeMin, pddRangeMax)

    self.odVsDoseChartView = vtk.vtkContextView()
    self.odVsDoseChartView.GetRenderer().SetBackground(1,1,1)
    self.odVsDoseChart = vtk.vtkChartXY()
    self.odVsDoseChartView.GetScene().AddItem(self.odVsDoseChart)

    # Create optical density vs dose plot
    self.odVsDoseDataTable = vtk.vtkTable()
    odVsDoseNumberOfRows = self.logic.opticalDensityVsDoseFunction.shape[0]

    opticalDensityArray = vtk.vtkDoubleArray()
    opticalDensityArray.SetName("Optical density")
    self.odVsDoseDataTable.AddColumn(opticalDensityArray)
    doseArray = vtk.vtkDoubleArray()
    doseArray.SetName("Dose (GY)")
    self.odVsDoseDataTable.AddColumn(doseArray)

    self.odVsDoseDataTable.SetNumberOfRows(odVsDoseNumberOfRows)
    for rowIndex in xrange(odVsDoseNumberOfRows):
      self.odVsDoseDataTable.SetValue(rowIndex, 0, self.logic.opticalDensityVsDoseFunction[rowIndex, 0])
      self.odVsDoseDataTable.SetValue(rowIndex, 1, self.logic.opticalDensityVsDoseFunction[rowIndex, 1])

    self.odVsDoseLinePoint = self.odVsDoseChart.AddPlot(vtk.vtkChart.POINTS)
    self.odVsDoseLinePoint.SetInputData(self.odVsDoseDataTable, 0, 1)
    self.odVsDoseLinePoint.SetColor(0, 0, 255, 255)
    self.odVsDoseLinePoint.SetMarkerSize(10)
    self.odVsDoseLineInnerPoint = self.odVsDoseChart.AddPlot(vtk.vtkChart.POINTS)
    self.odVsDoseLineInnerPoint.SetInputData(self.odVsDoseDataTable, 0, 1)
    self.odVsDoseLineInnerPoint.SetColor(255, 255, 255, 223)
    self.odVsDoseLineInnerPoint.SetMarkerSize(8)

    # Show chart
    self.odVsDoseChart.GetAxis(1).SetTitle('Optical density')
    self.odVsDoseChart.GetAxis(0).SetTitle('Dose (GY)')
    self.odVsDoseChart.SetTitle('Optical density vs Dose')
    self.odVsDoseChartView.GetInteractor().Initialize()
    self.odVsDoseChartView.GetRenderWindow().SetSize(800,550)
    self.odVsDoseChartView.GetRenderWindow().SetWindowName('Optical density vs Dose chart')
    self.odVsDoseChartView.GetRenderWindow().Start()

  def onRemoveSelectedPointsFromOpticalDensityVsDoseCurve(self):
    outlierSelection = self.odVsDoseLineInnerPoint.GetSelection()
    if outlierSelection == None:
      outlierSelection = self.odVsDoseLinePoint.GetSelection()
    if outlierSelection != None and outlierSelection.GetNumberOfTuples() > 0:
      # Get outlier indices in descending order
      outlierIndices = []
      for outlierSelectionIndex in xrange(outlierSelection.GetNumberOfTuples()):
        outlierIndex = outlierSelection.GetValue(outlierSelectionIndex)
        outlierIndices.append(outlierIndex)
      outlierIndices.sort()
      outlierIndices.reverse()
      for outlierIndex in outlierIndices:
        self.odVsDoseDataTable.RemoveRow(outlierIndex)
        self.logic.opticalDensityVsDoseFunction = numpy.delete(self.logic.opticalDensityVsDoseFunction, outlierIndex, 0)

      # De-select former points
      emptySelectionArray = vtk.vtkIdTypeArray()
      self.odVsDoseLinePoint.SetSelection(emptySelectionArray)
      self.odVsDoseLineInnerPoint.SetSelection(emptySelectionArray)
      if hasattr(self, 'polynomialLine') and self.polynomialLine != None:
        self.polynomialLine.SetSelection(emptySelectionArray)
      # Update chart view
      self.odVsDoseDataTable.Modified()
      self.odVsDoseChartView.Render()
    
  def onFitPolynomialToOpticalDensityVsDoseCurve(self):
    orderSelectionComboboxCurrentIndex = self.step3_1_selectOrderOfPolynomialFitButton.currentIndex
    maxOrder = int(self.step3_1_selectOrderOfPolynomialFitButton.itemText(orderSelectionComboboxCurrentIndex))
    residuals = self.logic.fitCurveToOpticalDensityVsDoseFunctionArray(maxOrder)
    p = self.logic.calibrationPolynomialCoefficients

    # Clear line edits
    for order in xrange(5):
      exec("self.step3_2_doseLabel{0}LineEdit.text = ''".format(order))
    # Show polynomial on GUI (highest order first in the coefficients list)
    for orderIndex in xrange(maxOrder+1):
      order = maxOrder-orderIndex
      exec("self.step3_2_doseLabel{0}LineEdit.text = {1}".format(order,p[orderIndex]))
    # Show residuals
    self.step3_1_fitPolynomialResidualsLabel.text = "Residuals of the least-squares fit of the polynomial: {0:.3f}".format(residuals[0])

    # Compute points to display for the fitted polynomial
    odVsDoseNumberOfRows = self.logic.opticalDensityVsDoseFunction.shape[0]
    minOd = self.logic.opticalDensityVsDoseFunction[0, 0]
    maxOd = self.logic.opticalDensityVsDoseFunction[odVsDoseNumberOfRows-1, 0]
    minPolynomial = minOd - (maxOd-minOd)*0.2
    maxPolynomial = maxOd + (maxOd-minOd)*0.2

    # Create table to display polynomial
    self.polynomialTable = vtk.vtkTable()
    polynomialXArray = vtk.vtkDoubleArray()
    polynomialXArray.SetName("X")
    self.polynomialTable.AddColumn(polynomialXArray)
    polynomialYArray = vtk.vtkDoubleArray()
    polynomialYArray.SetName("Y")
    self.polynomialTable.AddColumn(polynomialYArray)
    # The displayed polynomial is 4 times as dense as the OD VS dose curve
    polynomialNumberOfRows = odVsDoseNumberOfRows * 4
    self.polynomialTable.SetNumberOfRows(polynomialNumberOfRows)
    for rowIndex in xrange(polynomialNumberOfRows):
      x = minPolynomial + (maxPolynomial-minPolynomial)*rowIndex/polynomialNumberOfRows
      self.polynomialTable.SetValue(rowIndex, 0, x)
      y = 0
      # Highest order first in the coefficients list
      for orderIndex in xrange(maxOrder+1):
        y += p[orderIndex] * x ** (maxOrder-orderIndex)
      self.polynomialTable.SetValue(rowIndex, 1, y)

    if hasattr(self, 'polynomialLine') and self.polynomialLine != None:
      self.odVsDoseChart.RemovePlotInstance(self.polynomialLine)

    self.polynomialLine = self.odVsDoseChart.AddPlot(vtk.vtkChart.LINE)
    self.polynomialLine.SetInputData(self.polynomialTable, 0, 1)
    self.polynomialLine.SetColor(192, 0, 0, 255)
    self.polynomialLine.SetWidth(2)

  def setCalibrationFunctionCoefficientsToLogic(self):
    # Determine the number of orders based on the input fields
    maxOrder = 0
    for order in xrange(5):
      exec("lineEditText = self.step3_2_doseLabel{0}LineEdit.text".format(order))
      if lineEditText.numeric() and float(lineEditText) != 0:
        maxOrder = order
    # Initialize all coefficients to zero in the coefficients list
    self.logic.calibrationPolynomialCoefficients = [0]*(maxOrder+1)
    for order in xrange(maxOrder+1):
      exec("lineEditText = self.step3_2_doseLabel{0}LineEdit.text".format(order))
      if lineEditText.numeric():
        self.logic.calibrationPolynomialCoefficients[maxOrder-order] = float(lineEditText)

  def onExportCalibration(self):
    # Set calibration polynomial coefficients from input fields to logic
    self.setCalibrationFunctionCoefficientsToLogic()
    
    # Export
    result = self.logic.exportCalibrationToCSV()
    qt.QMessageBox.information(None, 'Calibration values exported', result)

  def onApplyCalibration(self):
    # Set calibration polynomial coefficients from input fields to logic
    self.setCalibrationFunctionCoefficientsToLogic()

    # Perform calibration
    self.calibratedMeasuredVolumeNode = self.logic.calibrate(self.measuredVolumeNode.GetID())
    if self.calibratedMeasuredVolumeNode != None:
      self.step3_2_applyCalibrationStatusLabel.setText('Calibration successfully performed')
    else:
      self.step3_2_applyCalibrationStatusLabel.setText('Calibration failed!')
      return

    # Show calibrated volume
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetActiveVolumeID(self.calibratedMeasuredVolumeNode.GetID())
    selectionNode.SetSecondaryVolumeID(self.planDoseVolumeNode.GetID())
    appLogic.PropagateVolumeSelection() 

    # Set window/level options for the calibrated dose
    calibratedVolumeDisplayNode = self.calibratedMeasuredVolumeNode.GetDisplayNode()
    odVsDoseNumberOfRows = self.logic.opticalDensityVsDoseFunction.shape[0]
    minDose = self.logic.opticalDensityVsDoseFunction[0, 1]
    maxDose = self.logic.opticalDensityVsDoseFunction[odVsDoseNumberOfRows-1, 1]
    minWindowLevel = minDose - (maxDose-minDose)*0.2
    maxWindowLevel = maxDose + (maxDose-minDose)*0.2
    calibratedVolumeDisplayNode.AutoWindowLevelOff();
    calibratedVolumeDisplayNode.SetWindowLevelMinMax(minWindowLevel, maxWindowLevel);

    # Set calibrated dose to dose comparison step input
    self.step4_measuredDoseSelector.setCurrentNode(self.calibratedMeasuredVolumeNode)

  def onStep4_DoseComparisonSelected(self, collapsed):
    # Set plan dose volume to selector
    if collapsed == False:
      gammaScalarBarColorTable = slicer.util.getNode(self.gammaScalarBarColorTableName)
      if gammaScalarBarColorTable != None:
        self.gammaScalarBarWidget.SetEnabled(1)
        self.gammaScalarBarWidget.Render()
    else:
      self.gammaScalarBarWidget.SetEnabled(0)
      self.gammaScalarBarWidget.Render()

  def onStep4_MaskContourSelectionChanged(self, node):
    # Use subject hierarchy to properly toggle visibility, slice intersections and all
    from vtkSlicerSubjectHierarchyModuleMRML import vtkMRMLSubjectHierarchyNode
    # Hide previously selected mask contour
    if self.maskContourNode != None:
      maskContourShNode = vtkMRMLSubjectHierarchyNode.GetAssociatedSubjectHierarchyNode(self.maskContourNode)
      maskContourShNode.SetDisplayVisibilityForBranch(0)
    # Set new mask contour
    self.maskContourNode = node
    # Show new mask contour
    if self.maskContourNode != None:
      maskContourShNode = vtkMRMLSubjectHierarchyNode.GetAssociatedSubjectHierarchyNode(self.maskContourNode)
      maskContourShNode.SetDisplayVisibilityForBranch(1)

  def onUseMaximumDoseRadioButtonToggled(self, toggled):
    self.step4_1_referenceDoseCustomValueCGySpinBox.setEnabled(not toggled)

  def onGammaDoseComparison(self):
    try:
      slicer.modules.dosecomparison
      import vtkSlicerDoseComparisonModuleLogic

      if self.step4_1_gammaVolumeSelector.currentNode() == None:
        qt.QMessageBox.warning(None, 'Warning', 'Gamma volume not selected. If there is no suitable output gamma volume, create one.')
        return
      else:
        self.gammaVolumeNode = self.step4_1_gammaVolumeSelector.currentNode()

      self.gammaParameterSetNode = vtkSlicerDoseComparisonModuleLogic.vtkMRMLDoseComparisonNode()
      slicer.mrmlScene.AddNode(self.gammaParameterSetNode)
      self.gammaParameterSetNode.SetAndObserveCompareDoseVolumeNode(self.step4_measuredDoseSelector.currentNode())
      self.gammaParameterSetNode.SetAndObserveMaskContourNode(self.maskContourNode)
      self.gammaParameterSetNode.SetAndObserveGammaVolumeNode(self.gammaVolumeNode)
      self.gammaParameterSetNode.SetDtaDistanceToleranceMm(self.step4_1_dtaDistanceToleranceMmSpinBox.value)
      self.gammaParameterSetNode.SetDoseDifferenceTolerancePercent(self.step4_1_doseDifferenceTolerancePercentSpinBox.value)
      self.gammaParameterSetNode.SetUseMaximumDose(self.step4_1_referenceDoseUseMaximumDoseRadioButton.isChecked())
      self.gammaParameterSetNode.SetUseLinearInterpolation(self.step4_1_useLinearInterpolationCheckBox.isChecked())
      self.gammaParameterSetNode.SetReferenceDoseGy(self.step4_1_referenceDoseCustomValueCGySpinBox.value)
      self.gammaParameterSetNode.SetAnalysisThresholdPercent(self.step4_1_analysisThresholdPercentSpinBox.value)
      self.gammaParameterSetNode.SetMaximumGamma(self.step4_1_maximumGammaSpinBox.value)

      qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))
      slicer.modules.dosecomparison.logic().SetAndObserveDoseComparisonNode(self.gammaParameterSetNode)
      slicer.modules.dosecomparison.logic().ComputeGammaDoseDifference()
      qt.QApplication.restoreOverrideCursor()

      if self.gammaParameterSetNode.GetResultsValid():
        self.step4_1_gammaStatusLabel.setText('Gamma dose comparison succeeded\nPass fraction: {0:.2f}%'.format(self.gammaParameterSetNode.GetPassFractionPercent()))
        self.step4_1_showGammaReportButton.enabled = True
        self.gammaReport = self.gammaParameterSetNode.GetReportString()
      else:
        self.step4_1_gammaStatusLabel.setText('Gamma dose comparison failed!')
        self.step4_1_showGammaReportButton.enabled = False

      # Show gamma volume
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      selectionNode.SetActiveVolumeID(self.step4_1_gammaVolumeSelector.currentNodeID)
      selectionNode.SetSecondaryVolumeID(None)
      appLogic.PropagateVolumeSelection()

      # Show contour (use subject hierarchy to properly toggle visibility, slice intersections and all)
      from vtkSlicerSubjectHierarchyModuleMRML import vtkMRMLSubjectHierarchyNode
      maskContourShNode = vtkMRMLSubjectHierarchyNode.GetAssociatedSubjectHierarchyNode(self.maskContourNode)
      maskContourShNode.SetDisplayVisibilityForBranch(1)
      
      # Show gamma slice in 3D view
      layoutManager = self.layoutWidget.layoutManager()
      sliceViewerNames = layoutManager.sliceViewNames()
      sliceViewerWidgetRed = layoutManager.sliceWidget(sliceViewerNames[0])
      sliceLogicRed = sliceViewerWidgetRed.sliceLogic()
      sliceLogicRed.StartSliceNodeInteraction(slicer.vtkMRMLSliceNode.SliceVisibleFlag)
      sliceLogicRed.GetSliceNode().SetSliceVisible(1)
      sliceLogicRed.EndSliceNodeInteraction()

      # Set gamma window/level
      maximumGamma = self.step4_1_maximumGammaSpinBox.value
      gammaDisplayNode = self.gammaVolumeNode.GetDisplayNode()
      gammaDisplayNode.AutoWindowLevelOff()
      gammaDisplayNode.SetWindowLevel(maximumGamma/2, maximumGamma/2)
      gammaDisplayNode.ApplyThresholdOn()
      gammaDisplayNode.AutoThresholdOff()
      gammaDisplayNode.SetLowerThreshold(0.001)

      # Create scalar bar
      import vtkSlicerColorsModuleVTKWidgets
      gammaScalarBarActor = vtkSlicerColorsModuleVTKWidgets.vtkSlicerScalarBarActor()
      gammaScalarBarActor.SetOrientationToVertical()
      gammaScalarBarActor.SetNumberOfLabels(self.numberOfGammaLabels)
      gammaScalarBarTitleTextProps = gammaScalarBarActor.GetTitleTextProperty()
      gammaScalarBarTitleTextProps.SetFontSize(8)
      gammaScalarBarActor.SetTitleTextProperty(gammaScalarBarTitleTextProps)
      gammaScalarBarActor.SetTitle('gamma')
      gammaScalarBarActor.SetLabelFormat('%.8s')
      gammaScalarBarActor.SetPosition(0.1, 0.1)
      gammaScalarBarActor.SetWidth(0.1)
      gammaScalarBarActor.SetHeight(0.8)
      
      # Add scalar bar
      layoutManager = self.layoutWidget.layoutManager()
      sliceViewerNames = layoutManager.sliceViewNames()
      sliceViewerWidgetRed = layoutManager.sliceWidget(sliceViewerNames[0])
      sliceViewRed = sliceViewerWidgetRed.sliceView()
      sliceViewerWidgetRedInteractorStyle = sliceViewerWidgetRed.interactorStyle()
      self.gammaScalarBarWidget.SetInteractor(sliceViewerWidgetRedInteractorStyle.GetInteractor())

      # Setup scalar bar colors and labels
      gammaColorTable = slicer.util.getNode('Gamma_Color*')
      if gammaColorTable != None:
        gammaScalarBarColorTable = slicer.util.getNode(self.gammaScalarBarColorTableName)
        if gammaScalarBarColorTable == None:
          gammaScalarBarColorTable = slicer.vtkMRMLColorTableNode()
          gammaScalarBarColorTable.SetName(self.gammaScalarBarColorTableName)
          gammaScalarBarColorTable.SetTypeToUser()
          gammaScalarBarColorTable.SetAttribute('Category','GelDosimetry')
          gammaScalarBarColorTable.HideFromEditorsOn()
          slicer.mrmlScene.AddNode(gammaScalarBarColorTable)
        gammaScalarBarColorTable.SetNumberOfColors(self.numberOfGammaLabels)
        gammaScalarBarColorTableLookupTable = gammaScalarBarColorTable.GetLookupTable()
        gammaScalarBarColorTableLookupTable.SetTableRange(0,self.numberOfGammaLabels-1)
        gammaLookupTable = gammaColorTable.GetLookupTable()
        for colorIndex in xrange(self.numberOfGammaLabels):
          interpolatedColor = [0]*3
          gammaLookupTable.GetColor(256*colorIndex/(self.numberOfGammaLabels-1), interpolatedColor)
          colorName = '{0:.2f}'.format(maximumGamma*colorIndex/(self.numberOfGammaLabels-1))
          gammaScalarBarColorTableLookupTable.SetAnnotation(colorIndex, colorName)
          gammaScalarBarColorTable.AddColor(colorName, interpolatedColor[0], interpolatedColor[1], interpolatedColor[2])
          # logging.debug('Name: ' + colorName + '  Color' + repr(interpolatedColor)) #TODO remove
        gammaScalarBarActor.UseAnnotationAsLabelOn()
        gammaScalarBarActor.SetLookupTable(gammaScalarBarColorTableLookupTable)
        self.gammaScalarBarWidget.SetScalarBarActor(gammaScalarBarActor)
        self.gammaScalarBarWidget.SetEnabled(1)
        self.gammaScalarBarWidget.Render()
      else:
        logging.error('Unable to find gamma color table!')

      # Center 3D view
      layoutManager = self.layoutWidget.layoutManager()
      threeDWidget = layoutManager.threeDWidget(0)
      if threeDWidget != None and threeDWidget.threeDView() != None:
        threeDWidget.threeDView().resetFocalPoint()
      
    except Exception, e:
      import traceback
      traceback.print_exc()
      logging.error('Failed to perform gamma dose comparison!')

  def onShowGammaReport(self):
    if hasattr(self,"gammaReport"):
      qt.QMessageBox.information(None, 'Gamma computation report', self.gammaReport)
    else:
      qt.QMessageBox.information(None, 'Gamma computation report missing', 'No report available!')
    
  def onStepT1_LineProfileSelected(self, collapsed):
    # Change to quantitative view on enter, change back on leave
    if collapsed == False:
      self.currentLayoutIndex = self.step0_viewSelectorComboBox.currentIndex
      self.onViewSelect(5)
    else:
      self.onViewSelect(self.currentLayoutIndex)

    # Show dose volumes
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    if self.planDoseVolumeNode:
      selectionNode.SetActiveVolumeID(self.planDoseVolumeNode.GetID())
    if self.calibratedMeasuredVolumeNode:
      selectionNode.SetSecondaryVolumeID(self.calibratedMeasuredVolumeNode.GetID())
    appLogic = slicer.app.applicationLogic()
    appLogic.PropagateVolumeSelection()

    # Switch to place ruler mode
    selectionNode.SetReferenceActivePlaceNodeClassName("vtkMRMLAnnotationRulerNode")

  def onCreateLineProfileButton(self):
    # Create array nodes for the results
    if not hasattr(self, 'planDoseLineProfileArrayNode'):
      self.planDoseLineProfileArrayNode = slicer.vtkMRMLDoubleArrayNode()
      slicer.mrmlScene.AddNode(self.planDoseLineProfileArrayNode)
    if not hasattr(self, 'calibratedMeasuredDoseLineProfileArrayNode'):
      self.calibratedMeasuredDoseLineProfileArrayNode = slicer.vtkMRMLDoubleArrayNode()
      slicer.mrmlScene.AddNode(self.calibratedMeasuredDoseLineProfileArrayNode)
    if self.gammaVolumeNode and not hasattr(self, 'gammaLineProfileArrayNode'):
      self.gammaLineProfileArrayNode = slicer.vtkMRMLDoubleArrayNode()
      slicer.mrmlScene.AddNode(self.gammaLineProfileArrayNode)

    lineProfileLogic = GelDosimetryAnalysisLogic.LineProfileLogic()
    lineResolutionMm = float(self.stepT1_lineResolutionMmSliderWidget.value)
    selectedRuler = self.stepT1_inputRulerSelector.currentNode()
    rulerLengthMm = lineProfileLogic.computeRulerLength(selectedRuler)
    numberOfLineSamples = int( (rulerLengthMm / lineResolutionMm) + 0.5 )

    # Get number of samples based on selected sampling density
    if self.planDoseVolumeNode:
      lineProfileLogic.run(self.planDoseVolumeNode, selectedRuler, self.planDoseLineProfileArrayNode, numberOfLineSamples)
    if self.calibratedMeasuredVolumeNode:
      lineProfileLogic.run(self.calibratedMeasuredVolumeNode, selectedRuler, self.calibratedMeasuredDoseLineProfileArrayNode, numberOfLineSamples)
    if self.gammaVolumeNode:
      lineProfileLogic.run(self.gammaVolumeNode, selectedRuler, self.gammaLineProfileArrayNode, numberOfLineSamples)

  def onSelectLineProfileParameters(self):
    self.stepT1_createLineProfileButton.enabled = self.planDoseVolumeNode and self.measuredVolumeNode and self.stepT1_inputRulerSelector.currentNode()

  def onExportLineProfiles(self):
    import csv
    import os

    self.outputDir = slicer.app.temporaryPath + '/GelDosimetry'
    if not os.access(self.outputDir, os.F_OK):
      os.mkdir(self.outputDir)
    if not hasattr(self, 'planDoseLineProfileArrayNode') and not hasattr(self, 'calibratedMeasuredDoseLineProfileArrayNode'):
      return 'Dose line profiles not computed yet!\nClick Create line profile\n'

    # Assemble file name for calibration curve points file
    from time import gmtime, strftime
    fileName = self.outputDir + '/' + strftime("%Y%m%d_%H%M%S_", gmtime()) + 'LineProfiles.csv'

    # Write calibration curve points CSV file
    with open(fileName, 'w') as fp:
      csvWriter = csv.writer(fp, delimiter=',', lineterminator='\n')

      planDoseLineProfileArray = self.planDoseLineProfileArrayNode.GetArray()
      calibratedDoseLineProfileArray = self.calibratedMeasuredDoseLineProfileArrayNode.GetArray()
      gammaLineProfileArray = None
      if hasattr(self, 'gammaLineProfileArrayNode'):
        data = [['PlanDose','CalibratedMeasuredDose','Gamma']]
        gammaLineProfileArray = self.gammaLineProfileArrayNode.GetArray()
      else:
        data = [['PlanDose','CalibratedMeasuredDose']]

      numOfSamples = planDoseLineProfileArray.GetNumberOfTuples()
      for index in xrange(numOfSamples):
        planDoseSample = planDoseLineProfileArray.GetTuple(index)[1]
        calibratedDoseSample = calibratedDoseLineProfileArray.GetTuple(index)[1]
        if gammaLineProfileArray:
          gammaSample = gammaLineProfileArray.GetTuple(index)[1]
          samples = [planDoseSample, calibratedDoseSample, gammaSample]
        else:
          samples = [planDoseSample, calibratedDoseSample]
        data.append(samples)
      csvWriter.writerows(data)

    message = 'Dose line profiles saved in file\n' + fileName + '\n\n'
    qt.QMessageBox.information(None, 'Line profiles values exported', message)

  #
  # -------------------------
  # Testing related functions
  # -------------------------
  #
  def onSelfTestButtonClicked(self):
    # TODO_ForTesting: Choose the testing method here
    self.performSelfTestFromScratch()
    # self.performSelfTestFromSavedScene()

  def performSelfTestFromScratch(self):
    # 1. Load test data
    planCtSeriesInstanceUid = '1.2.246.352.71.2.1706542068.3448830.20131009141316'
    obiSeriesInstanceUid = '1.2.246.352.61.2.5257103442752107062.11507227178299854732'
    planDoseSeriesInstanceUid = '1.2.246.352.71.2.876365306.7756.20140123124241'
    structureSetSeriesInstanceUid = '1.2.246.352.71.2.876365306.7755.20140122163851'
    seriesUIDList = [planCtSeriesInstanceUid, obiSeriesInstanceUid, planDoseSeriesInstanceUid, structureSetSeriesInstanceUid]
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
    dicomWidget.detailsPopup.offerLoadables(seriesUIDList, 'SeriesUIDList')
    dicomWidget.detailsPopup.examineForLoading()
    dicomWidget.detailsPopup.loadCheckedLoadables()

    slicer.app.processEvents()
    self.logic.delayDisplay('Wait for the slicelet to catch up', 300)

    # 2. Register
    self.step2_registrationCollapsibleButton.setChecked(True)
    planCTVolumeID = 'vtkMRMLScalarVolumeNode1'
    self.planCTSelector.setCurrentNodeID(planCTVolumeID)
    obiVolumeID = 'vtkMRMLScalarVolumeNode2'
    self.obiSelector.setCurrentNodeID(obiVolumeID)
    planDoseVolumeID = 'vtkMRMLScalarVolumeNode3'
    self.planDoseSelector.setCurrentNodeID(planDoseVolumeID)
    structureSetID = 'vtkMRMLSubjectHierarchyNode6'
    self.planStructuresSelector.setCurrentNodeID(structureSetID)
    self.onObiToPlanCTRegistration()
    slicer.app.processEvents()

    # 3. Select fiducials
    self.step2_2_measuredDoseToObiRegistrationCollapsibleButton.setChecked(True)
    obiFiducialsNode = slicer.util.getNode(self.obiMarkupsFiducialNodeName)
    obiFiducialsNode.AddFiducial(76.4, 132.1, -44.8)
    obiFiducialsNode.AddFiducial(173, 118.4, -44.8)
    obiFiducialsNode.AddFiducial(154.9, 163.5, -44.8)
    obiFiducialsNode.AddFiducial(77.4, 133.6, 23.9)
    obiFiducialsNode.AddFiducial(172.6, 118.9, 23.9)
    obiFiducialsNode.AddFiducial(166.5, 151.3, 23.9)
    self.step2_2_2_measuredFiducialSelectionCollapsibleButton.setChecked(True)
    measuredFiducialsNode = slicer.util.getNode(self.measuredMarkupsFiducialNodeName)
    measuredFiducialsNode.AddFiducial(-92.25, -25.9, 26.2)
    measuredFiducialsNode.AddFiducial(-31.9, -100.8, 26.2)
    measuredFiducialsNode.AddFiducial(-15, -55.2, 26.2)
    measuredFiducialsNode.AddFiducial(-92, -26.7, 94)
    measuredFiducialsNode.AddFiducial(-32.7, -101, 94)
    measuredFiducialsNode.AddFiducial(-15, -73.6, 94)

    # Load MEASURE Vff
    slicer.app.ioManager().connect('newFileLoaded(qSlicerIO::IOProperties)', self.setMeasuredData)
    slicer.util.loadNodeFromFile('d:/devel/_Images/RT/20140123_GelDosimetry_StructureSetIncluded/VFFs/LCV01_HR_plan.vff', 'VffFile', {})
    slicer.app.ioManager().disconnect('newFileLoaded(qSlicerIO::IOProperties)', self.setMeasuredData)
    # Perform fiducial registration
    self.step2_2_3_measuredToObiRegistrationCollapsibleButton.setChecked(True)
    self.onMeasuredToObiRegistration()

    # 4. Calibration
    self.step3_doseCalibrationCollapsibleButton.setChecked(True)
    self.logic.loadPdd('d:/devel/_Images/RT/20140123_GelDosimetry_StructureSetIncluded/12MeV.csv')
    # Load CALIBRATION Vff
    slicer.app.ioManager().connect('newFileLoaded(qSlicerIO::IOProperties)', self.setCalibrationData)
    slicer.util.loadNodeFromFile('d:/devel/_Images/RT/20140123_GelDosimetry_StructureSetIncluded/VFFs/LCV02_HR_calib.vff', 'VffFile', {})
    slicer.app.ioManager().disconnect('newFileLoaded(qSlicerIO::IOProperties)', self.setCalibrationData)

    # Parse calibration volume
    self.step3_1_radiusMmFromCentrePixelLineEdit.setText('5')
    self.onParseCalibrationVolume()
    # Align calibration curves
    self.onAlignCalibrationCurves()
    self.step3_1_xTranslationSpinBox.setValue(1)
    self.step3_1_yScaleSpinBox.setValue(1.162)
    self.step3_1_yTranslationSpinBox.setValue(1.28)

    # Generate dose information
    self.step3_doseCalibrationCollapsibleButton.setChecked(True)
    self.step3_1_rdfLineEdit.setText('0.989')
    self.step3_1_monitorUnitsLineEdit.setText('1850')
    self.onComputeDoseFromPdd()
    # Show optical density VS dose curve
    self.step3_1_calibrationRoutineCollapsibleButton.setChecked(True)
    self.onShowOpticalDensityVsDoseCurve()
    # Fit polynomial on OD VS dose curve
    self.onFitPolynomialToOpticalDensityVsDoseCurve()
    # Calibrate
    self.onApplyCalibration()

    # 5. Dose comparison
    slicer.app.processEvents()
    self.logic.delayDisplay('Wait for the slicelet to catch up', 300)
    self.step4_doseComparisonCollapsibleButton.setChecked(True)
    self.step4_1_gammaVolumeSelector.addNode()
    maskContourNodeID = 'vtkMRMLContourNode7'
    self.step4_maskContourSelector.setCurrentNodeID(maskContourNodeID)
    # self.onGammaDoseComparison() # Uncomment if needed, takes a lot of time (~10s)

  def performSelfTestFromSavedScene(self):
    # Set variables. Only this section needs to be changed when testing new dataset
    scenePath = 'c:/Slicer_Data/20140820_GelDosimetry_StructureSetIncluded/2014-08-20-Scene.mrml'
    planCtVolumeNodeName = '*ARIA RadOnc Images - Verification Plan Phantom'
    obiVolumeNodeName = '0: Unknown'
    planDoseVolumeNodeName = '53: RTDOSE: Eclipse Doses: '
    planStructuresNodeName = '52: RTSTRUCT: CT_1_AllStructures_SubjectHierarchy'
    measuredVolumeNodeName = 'lcv01_hr.vff'
    calibrationVolumeNodeName = 'lcv02_hr.vff'
    radiusMmFromCentrePixelMm = '5'
    pddFileName = 'd:/devel/_Images/RT/20140123_GelDosimetry_StructureSetIncluded/12MeV.csv'
    rdf = '0.989'
    monitorUnits = '1850'
    maskContourNodeID = 'vtkMRMLContourNode7'
    xTranslationSpinBoxValue = 1
    yScaleSpinBoxValue = 1.162
    yTranslationSpinBoxValue = 1.28
    
    # Start test
    qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))

    # Load scene
    slicer.util.loadScene(scenePath)

    # Set member variables for the loaded scene
    self.mode = 'Clinical'
    self.planCtVolumeNode = slicer.util.getNode(planCtVolumeNodeName)
    self.obiVolumeNode = slicer.util.getNode(obiVolumeNodeName)
    self.planDoseVolumeNode = slicer.util.getNode(planDoseVolumeNodeName)
    self.planStructuresNode = slicer.util.getNode(planStructuresNodeName)
    self.planStructuresNode.SetDisplayVisibilityForBranch(0)
    self.measuredVolumeNode = slicer.util.getNode(measuredVolumeNodeName)
    self.calibrationVolumeNode = slicer.util.getNode(calibrationVolumeNodeName)

    # Parse calibration volume
    self.step3_1_radiusMmFromCentrePixelLineEdit.setText(radiusMmFromCentrePixelMm)
    self.onParseCalibrationVolume()

    # Calibration
    self.logic.loadPdd(pddFileName)

    self.onAlignCalibrationCurves()
    self.step3_1_xTranslationSpinBox.setValue(xTranslationSpinBoxValue)
    self.step3_1_yScaleSpinBox.setValue(yScaleSpinBoxValue)
    self.step3_1_yTranslationSpinBox.setValue(yTranslationSpinBoxValue)

    self.step3_1_rdfLineEdit.setText(rdf)
    self.step3_1_monitorUnitsLineEdit.setText(monitorUnits)
    self.onComputeDoseFromPdd()

    self.onShowOpticalDensityVsDoseCurve()
    self.onFitPolynomialToOpticalDensityVsDoseCurve()

    slicer.app.processEvents()
    self.onApplyCalibration()

    self.step3_doseCalibrationCollapsibleButton.setChecked(True)
    self.step3_1_calibrationRoutineCollapsibleButton.setChecked(True)

    # Dose comparison
    self.step4_doseComparisonCollapsibleButton.setChecked(True)
    self.step4_1_gammaVolumeSelector.addNode()
    self.step4_maskContourSelector.setCurrentNodeID(maskContourNodeID)
    self.onGammaDoseComparison() #TODO: Uncomment if needed, takes a lot of time (~10s)
    
    qt.QApplication.restoreOverrideCursor()

#
# GelDosimetryAnalysis
#
class GelDosimetryAnalysis(ScriptedLoadableModule):
  """Uses ScriptedLoadableModule base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """ 

  def __init__(self, parent):
    ScriptedLoadableModule.__init__(self, parent) 
    parent.title = "Gel Dosimetry Analysis"
    parent.categories = ["Slicelets"]
    parent.dependencies = ["GelDosimetryAnalysisAlgo", "DicomRtImportExport", "BRAINSFit", "BRAINSResample", "DoseComparison"]
    parent.contributors = ["Csaba Pinter (Queen's University), Mattea Welch (Queen's University), Jennifer Andrea (Queen's University), Kevin Alexander (Kingston General Hospital)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = "Slicelet for gel dosimetry analysis"
    parent.acknowledgementText = """
    This file was originally developed by Mattea Welch, Jennifer Andrea, and Csaba Pinter (Queen's University). Funding was provided by NSERC-USRA, OCAIRO, Cancer Care Ontario and Queen's University
    """

#
# GelDosimetryAnalysisWidget
#
class GelDosimetryAnalysisWidget(ScriptedLoadableModuleWidget):
  """Uses ScriptedLoadableModuleWidget base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setup(self):
    self.developerMode = True
    ScriptedLoadableModuleWidget.setup(self) 

    # Show slicelet button
    launchSliceletButton = qt.QPushButton("Show slicelet")
    launchSliceletButton.toolTip = "Launch the slicelet"
    self.layout.addWidget(launchSliceletButton)
    launchSliceletButton.connect('clicked()', self.onShowSliceletButtonClicked)

    # Add vertical spacer
    self.layout.addStretch(1) 

  def onShowSliceletButtonClicked(self):
    mainFrame = SliceletMainFrame()
    mainFrame.setMinimumWidth(1200)
    mainFrame.connect('destroyed()', self.onSliceletClosed)
    slicelet = GelDosimetryAnalysisSlicelet(mainFrame)
    mainFrame.setSlicelet(slicelet)

    # Make the slicelet reachable from the Slicer python interactor for testing
    # TODO_ForTesting: Should be uncommented for testing
    slicer.gelDosimetrySliceletInstance = slicelet

  def onSliceletClosed(self):
    logging.debug('Slicelet closed')

# ---------------------------------------------------------------------------
class GelDosimetryAnalysisTest(ScriptedLoadableModuleTest):
  """
  This is the test case for your scripted module.
  Uses ScriptedLoadableModuleTest base class, available at:
  https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
  """

  def setUp(self):
    """ Do whatever is needed to reset the state - typically a scene clear will be enough.
    """
    slicer.mrmlScene.Clear(0)

  def runTest(self):
    """Run as few or as many tests as needed here.
    """
    self.setUp()

#
# Main
#
if __name__ == "__main__":
  #TODO: access and parse command line arguments
  #   Example: SlicerRt/src/BatchProcessing
  #   Ideally handle --xml

  import sys
  logging.debug( sys.argv )

  mainFrame = qt.QFrame()
  slicelet = GelDosimetryAnalysisSlicelet(mainFrame)
