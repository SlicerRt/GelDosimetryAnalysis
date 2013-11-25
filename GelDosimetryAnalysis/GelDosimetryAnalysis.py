import os
import unittest
import numpy
from __main__ import vtk, qt, ctk, slicer
import GelDosimetryAnalysisLogic

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
      print("ERROR: There is no parent to GelDosimetryAnalysisSliceletWidget!")

#
# SliceletMainFrame
#   Handles the event when the slicelet is hidden (its window closed)
#
class SliceletMainFrame(qt.QFrame):
  def setSlicelet(self, slicelet):
    self.slicelet = slicelet

  def hideEvent(self, event):
    import gc
    refs = gc.get_referrers(self.slicelet)
    if len(refs) > 1:
      print('Stuck slicelet references (' + repr(len(refs)) + '):\n' + repr(refs))

    slicer.gelDosimetrySliceletInstance = None
    self.slicelet.parent = None
    self.slicelet = None
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
    # self.selfTestButton.setVisible(False) # TODO: Should be commented for testing so the button shows up

    # Initiate and group together all panels
    self.step0_layoutSelectionCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step1_loadDataCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step2_obiToPlanCtRegistrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step3_measuredDoseToObiRegistrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step4_doseCalibrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step5_doseComparisonCollapsibleButton = ctk.ctkCollapsibleButton()

    self.collapsibleButtonsGroup = qt.QButtonGroup()
    self.collapsibleButtonsGroup.addButton(self.step0_layoutSelectionCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.step1_loadDataCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.step2_obiToPlanCtRegistrationCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.step3_measuredDoseToObiRegistrationCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.step4_doseCalibrationCollapsibleButton)
    self.collapsibleButtonsGroup.addButton(self.step5_doseComparisonCollapsibleButton)

    self.step0_layoutSelectionCollapsibleButton.setProperty('collapsed', False)
    
    # Create module logic
    self.logic = GelDosimetryAnalysisLogic.GelDosimetryAnalysisLogic()

    # Set up constants
    self.obiMarkupsFiducialNodeName = "OBI fiducials"
    self.measuredMarkupsFiducialNodeName = "MEASURED fiducials"
    
    # Declare member variables (mainly for documentation)
    self.planCtVolumeNode = None
    self.planDoseVolumeNode = None
    self.obiVolumeNode = None
    self.obiMarkupsFiducialNode = None
    self.measuredMarkupsFiducialNode = None
    self.measuredVolumeNode = None
    self.calibrationVolumeNode = None
    
    # Get markups widget and logic
    try:
      slicer.modules.markups
      self.markupsWidget = slicer.modules.markups.widgetRepresentation()
      self.markupsWidgetLayout = self.markupsWidget.layout()
      self.markupsLogic = slicer.modules.markups.logic()
    except Exception, e:
      import traceback
      traceback.print_exc()
      print('ERROR: Unable to find Markups module!')
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
      print('ERROR: Failed to correctly reparent the Markups widget!')

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

    # Set up step panels
    self.setup_Step0_LayoutSelection()
    self.setup_Step1_LoadPlanningData()
    self.setup_Step2_ObiToPlanCtRegistration()
    self.setup_Step3_MeasuredToObiRegistration()
    self.setup_Step4_DoseCalibration()
    self.setup_Step5_DoseComparison()

    if widgetClass:
      self.widget = widgetClass(self.parent)
    self.parent.show()

  def __del__(self):
    self.cleanUp()
    
  # Clean up when slicelet is closed
  def cleanUp(self):
    print('Cleaning up')
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
      print('ERROR: Cleaning up failed!')

  # Disconnect all connections made to the slicelet to enable the garbage collector to destruct the slicelet object on quit
  def disconnect(self):
    self.selfTestButton.disconnect('clicked()', self.onSelfTestButtonClicked)
    self.step0_viewSelectorComboBox.disconnect('activated(int)', self.onViewSelect)
    self.step1_showDicomBrowserButton.disconnect('clicked()', self.logic.onDicomLoad)
    self.obiAdditionalLoadDataButton.disconnect('clicked()', self.logic.onDicomLoad)
    self.registerObiToPlanCtButton.disconnect('clicked()', self.onObiToPlanCTRegistration)
    self.step3_measuredDoseToObiRegistrationCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep3_MeasuredDoseToObiRegistrationSelected)
    self.step3A_obiFiducialSelectionCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep3A_ObiFiducialCollectionSelected)
    self.step3C_measuredFiducialSelectionCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep3C_ObiFiducialCollectionSelected)
    self.step3B_loadMeasuredDataButton.disconnect('clicked()', self.onLoadMeasuredData)
    self.step3D_registerMeasuredToObiButton.disconnect('clicked()', self.onMeasuredToObiRegistration)
    self.step4A_pddLoadDataButton.disconnect('clicked()', self.onLoadPddDataRead)
    self.step4A_loadCalibrationDataButton.disconnect('clicked()', self.onLoadCalibrationData)
    self.step4A_parseCalibrationVolumeButton.disconnect('clicked()', self.onParseCalibrationVolume)
    self.step4B_alignCalibrationCurvesButton.disconnect('clicked()', self.onAlignCalibrationCurves)
    self.step4B_computeDoseFromPddButton.disconnect('clicked()', self.onComputeDoseFromPdd)
    self.step4C_polynomialFittingAndCalibrationCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep4C_PolynomialFittingAndCalibrationSelected)
    self.step4C_showOpticalDensityVsDoseCurveButton.disconnect('clicked()', self.onShowOpticalDensityVsDoseCurve)
    self.step4C_fitPolynomialToOpticalDensityVsDoseCurveButton.disconnect('clicked()', self.onFitPolynomialToOpticalDensityVsDoseCurve)
    self.step4C_applyCalibrationButton.disconnect('clicked()', self.onApplyCalibration)
    self.step5_doseComparisonCollapsibleButton.disconnect('contentsCollapsed(bool)', self.onStep5_DoseComparisonSelected)
    self.step5A_referenceDoseUseMaximumDoseRadioButton.disconnect('toggled(bool)', self.onUseMaximumDoseRadioButtonToggled)
    self.step5A_computeGammaButton.disconnect('clicked()', self.onGammaDoseComparison)

  def setup_Step0_LayoutSelection(self):
    # Layout selection step
    self.step0_layoutSelectionCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step0_layoutSelectionCollapsibleButton.text = "Layout Selector"
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
    self.step0_layoutSelectionCollapsibleButtonLayout.addRow("Layout: ", self.step0_viewSelectorComboBox)
    self.step0_viewSelectorComboBox.connect('activated(int)', self.onViewSelect)

    # Add layout widget
    self.layoutWidget = slicer.qMRMLLayoutWidget()
    self.layoutWidget.setMRMLScene(slicer.mrmlScene)
    self.parent.layout().addWidget(self.layoutWidget,2)
    self.onViewSelect(0)

  def setup_Step1_LoadPlanningData(self):
    # Step 1: Load data panel
    self.step1_loadDataCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step1_loadDataCollapsibleButton.text = "1. Load planning data"
    self.sliceletPanelLayout.addWidget(self.step1_loadDataCollapsibleButton)
    self.step1_loadDataCollapsibleButtonLayout = qt.QFormLayout(self.step1_loadDataCollapsibleButton)
    self.step1_loadDataCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step1_loadDataCollapsibleButtonLayout.setSpacing(4)

    # Data loading button
    self.step1_showDicomBrowserButton = qt.QPushButton("Show DICOM browser")
    self.step1_showDicomBrowserButton.toolTip = "Load planning data (PlanCT, PlanDose)"
    self.step1_showDicomBrowserButton.name = "showDicomBrowserButton"
    self.step1_loadDataCollapsibleButtonLayout.addWidget(self.step1_showDicomBrowserButton)

    # Connections
    self.step1_showDicomBrowserButton.connect('clicked()', self.logic.onDicomLoad)

  def setup_Step2_ObiToPlanCtRegistration(self):
    # Step 2: OBI to PLANCT registration panel
    self.step2_obiToPlanCtRegistrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step2_obiToPlanCtRegistrationCollapsibleButton.text = "2. Register OBI to PLANCT"
    self.sliceletPanelLayout.addWidget(self.step2_obiToPlanCtRegistrationCollapsibleButton)
    self.step2_obiToPlanCtRegistrationCollapsibleButtonLayout = qt.QFormLayout(self.step2_obiToPlanCtRegistrationCollapsibleButton)
    self.step2_obiToPlanCtRegistrationCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step2_obiToPlanCtRegistrationCollapsibleButtonLayout.setSpacing(4)

    # OBI (on board imaging ~ CBCT) load button
    self.obiAdditionalLoadDataLabel = qt.QLabel("Load OBI data: ")
    self.obiAdditionalLoadDataButton = qt.QPushButton("Show DICOM browser")
    self.obiAdditionalLoadDataButton.toolTip = "Load on-board cone beam CT scan if not already loaded"
    self.obiAdditionalLoadDataButton.name = "obiAdditionalLoadDataButton"
    self.step2_obiToPlanCtRegistrationCollapsibleButtonLayout.addRow(self.obiAdditionalLoadDataLabel, self.obiAdditionalLoadDataButton)

    # PLANCT node selector
    self.planCTSelector = slicer.qMRMLNodeComboBox()
    self.planCTSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.planCTSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.planCTSelector.addEnabled = False
    self.planCTSelector.removeEnabled = False
    self.planCTSelector.setMRMLScene( slicer.mrmlScene )
    self.planCTSelector.setToolTip( "Pick the PLANCT volume for registration." )
    self.step2_obiToPlanCtRegistrationCollapsibleButtonLayout.addRow('PLANCT volume: ', self.planCTSelector)

    # PLANDOSE node selector
    self.planDoseSelector = slicer.qMRMLNodeComboBox()
    self.planDoseSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.planDoseSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.planDoseSelector.addEnabled = False
    self.planDoseSelector.removeEnabled = False
    self.planDoseSelector.setMRMLScene( slicer.mrmlScene )
    self.planDoseSelector.setToolTip( "Pick the PLANDOSE volume for registration." )
    self.step2_obiToPlanCtRegistrationCollapsibleButtonLayout.addRow('PLANDOSE volume: ', self.planDoseSelector)

    # OBI node selector
    self.obiSelector = slicer.qMRMLNodeComboBox()
    self.obiSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.obiSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.obiSelector.addEnabled = False
    self.obiSelector.removeEnabled = False
    self.obiSelector.setMRMLScene( slicer.mrmlScene )
    self.obiSelector.setToolTip( "Pick the OBI volume for registration." )
    self.step2_obiToPlanCtRegistrationCollapsibleButtonLayout.addRow('OBI volume: ', self.obiSelector)

    # OBI to PLANCT registration button
    self.registerObiToPlanCtButton = qt.QPushButton("Perform registration")
    self.registerObiToPlanCtButton.toolTip = "Register OBI volume to PLANCT volume"
    self.registerObiToPlanCtButton.name = "registerObiToPlanCtButton"
    self.step2_obiToPlanCtRegistrationCollapsibleButtonLayout.addRow('Register OBI to PLANCT: ', self.registerObiToPlanCtButton)

    # Connections
    self.obiAdditionalLoadDataButton.connect('clicked()', self.logic.onDicomLoad)
    self.registerObiToPlanCtButton.connect('clicked()', self.onObiToPlanCTRegistration)

  def setup_Step3_MeasuredToObiRegistration(self):
    # Step 3: Gel CT scan to cone beam CT registration panel
    self.step3_measuredDoseToObiRegistrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step3_measuredDoseToObiRegistrationCollapsibleButton.text = "3. Register MEASURED dose to OBI"
    self.sliceletPanelLayout.addWidget(self.step3_measuredDoseToObiRegistrationCollapsibleButton)
    self.step3_measuredDoseToObiRegistrationLayout = qt.QVBoxLayout(self.step3_measuredDoseToObiRegistrationCollapsibleButton)
    self.step3_measuredDoseToObiRegistrationLayout.setContentsMargins(12,4,4,4)
    self.step3_measuredDoseToObiRegistrationLayout.setSpacing(4)

    # Step 3/A): Select OBI fiducials on OBI volume
    self.step3A_obiFiducialSelectionCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step3A_obiFiducialSelectionCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step3A_obiFiducialSelectionCollapsibleButton.text = "3/A) Select OBI fiducial points"
    self.step3_measuredDoseToObiRegistrationLayout.addWidget(self.step3A_obiFiducialSelectionCollapsibleButton)

    # Step 3/B): Load MEASURED dose CT scan
    self.step3B_loadMeasuredDataCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step3B_loadMeasuredDataCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step3B_loadMeasuredDataCollapsibleButton.text = "3/B) Load MEASURED dose CT scan"
    loadMeasuredDataCollapsibleButtonLayout = qt.QFormLayout(self.step3B_loadMeasuredDataCollapsibleButton)
    loadMeasuredDataCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    loadMeasuredDataCollapsibleButtonLayout.setSpacing(4)
    self.step3_measuredDoseToObiRegistrationLayout.addWidget(self.step3B_loadMeasuredDataCollapsibleButton)

    self.step3B_loadMeasuredDataButton = qt.QPushButton("Load .vff File")
    self.step3B_loadMeasuredDataButton.toolTip = "Select CT scan of gel if not already loaded."
    self.step3B_loadMeasuredDataButton.name = "loadMeasuredDataButton"
    loadMeasuredDataCollapsibleButtonLayout.addRow('Load MEASURED dose volume: ', self.step3B_loadMeasuredDataButton)

    self.step3B_loadMeasuredDataStatusLabel = qt.QLabel()
    loadMeasuredDataCollapsibleButtonLayout.addRow(' ', self.step3B_loadMeasuredDataStatusLabel)

    # Step 3/C): Select MEASURED fiducials on MEASURED dose volume
    self.step3C_measuredFiducialSelectionCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step3C_measuredFiducialSelectionCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step3C_measuredFiducialSelectionCollapsibleButton.text = "3/C) Select MEASURED fiducial points"
    self.step3_measuredDoseToObiRegistrationLayout.addWidget(self.step3C_measuredFiducialSelectionCollapsibleButton)

    # Step 3/D): Perform registration
    self.step3D_measuredToObiRegistrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step3D_measuredToObiRegistrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step3D_measuredToObiRegistrationCollapsibleButton.text = "3/D) Perform registration"
    measuredToObiRegistrationCollapsibleButtonLayout = qt.QFormLayout(self.step3D_measuredToObiRegistrationCollapsibleButton)
    measuredToObiRegistrationCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    measuredToObiRegistrationCollapsibleButtonLayout.setSpacing(4)
    self.step3_measuredDoseToObiRegistrationLayout.addWidget(self.step3D_measuredToObiRegistrationCollapsibleButton)

    # MEASURED volume selector
    self.step3D_measuredVolumeSelector = slicer.qMRMLNodeComboBox()
    self.step3D_measuredVolumeSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.step3D_measuredVolumeSelector.addEnabled = False
    self.step3D_measuredVolumeSelector.removeEnabled = False
    self.step3D_measuredVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.step3D_measuredVolumeSelector.setToolTip( "MEASURED dose volume to be transformed" )
    self.step3D_measuredVolumeSelector.enabled = False # Don't let the user select another, use the one that was loaded (the combobox is there to indicate which volume is involved)
    measuredToObiRegistrationCollapsibleButtonLayout.addRow('MEASURED dose volume: ', self.step3D_measuredVolumeSelector)

    # Registration button - register MEASURED to OBI with fiducial registration
    self.step3D_registerMeasuredToObiButton = qt.QPushButton("Perform registration")
    self.step3D_registerMeasuredToObiButton.toolTip = "Perform fiducial registration between MEASURED dose and OBI"
    self.step3D_registerMeasuredToObiButton.name = "registerMeasuredToObiButton"
    measuredToObiRegistrationCollapsibleButtonLayout.addRow('Register MEASURED to OBI: ', self.step3D_registerMeasuredToObiButton)
    
    self.step3D_measuredToObiFiducialRegistrationErrorLabel = qt.QLabel('[Not yet performed]')
    measuredToObiRegistrationCollapsibleButtonLayout.addRow('Fiducial registration error: ', self.step3D_measuredToObiFiducialRegistrationErrorLabel)

    # Add substeps in a button group
    self.step3D_measuredToObiRegistrationCollapsibleButtonGroup = qt.QButtonGroup()
    self.step3D_measuredToObiRegistrationCollapsibleButtonGroup.addButton(self.step3A_obiFiducialSelectionCollapsibleButton)
    self.step3D_measuredToObiRegistrationCollapsibleButtonGroup.addButton(self.step3B_loadMeasuredDataCollapsibleButton)
    self.step3D_measuredToObiRegistrationCollapsibleButtonGroup.addButton(self.step3C_measuredFiducialSelectionCollapsibleButton)
    self.step3D_measuredToObiRegistrationCollapsibleButtonGroup.addButton(self.step3D_measuredToObiRegistrationCollapsibleButton)
    
    # Connections
    self.step3_measuredDoseToObiRegistrationCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep3_MeasuredDoseToObiRegistrationSelected)
    self.step3A_obiFiducialSelectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep3A_ObiFiducialCollectionSelected)
    self.step3C_measuredFiducialSelectionCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep3C_ObiFiducialCollectionSelected)
    self.step3B_loadMeasuredDataButton.connect('clicked()', self.onLoadMeasuredData)
    self.step3D_registerMeasuredToObiButton.connect('clicked()', self.onMeasuredToObiRegistration)

    # Open OBI fiducial selection panel when step is first opened
    self.step3A_obiFiducialSelectionCollapsibleButton.setProperty('collapsed', False)

  def setup_Step4_DoseCalibration(self):
    # Step 4: Apply dose calibration curve to CALIBRATION dose volume
    self.step4_doseCalibrationCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step4_doseCalibrationCollapsibleButton.text = "4. Apply dose calibration curve to MEASURED Dose"
    self.sliceletPanelLayout.addWidget(self.step4_doseCalibrationCollapsibleButton)
    self.step4_doseCalibrationCollapsibleButtonLayout = qt.QVBoxLayout(self.step4_doseCalibrationCollapsibleButton)
    self.step4_doseCalibrationCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step4_doseCalibrationCollapsibleButtonLayout.setSpacing(4)

    # Collapsible buttons for substeps
    self.step4A_prepareCalibrationDataCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step4A_prepareCalibrationDataCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step4B_alignPddAndExperimentalDataCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step4B_alignPddAndExperimentalDataCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step4C_polynomialFittingAndCalibrationCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step4C_polynomialFittingAndCalibrationCollapsibleButton.setProperty('collapsedHeight', 4)

    self.collapsibleButtonsGroupForCurveCalibration = qt.QButtonGroup()
    self.collapsibleButtonsGroupForCurveCalibration.addButton(self.step4A_prepareCalibrationDataCollapsibleButton)
    self.collapsibleButtonsGroupForCurveCalibration.addButton(self.step4B_alignPddAndExperimentalDataCollapsibleButton)
    self.collapsibleButtonsGroupForCurveCalibration.addButton(self.step4C_polynomialFittingAndCalibrationCollapsibleButton)

    # Step 4/A): prepare data for calibration
    self.step4A_prepareCalibrationDataCollapsibleButton.text = "4/A) Prepare data for calibration"
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout = qt.QFormLayout(self.step4A_prepareCalibrationDataCollapsibleButton)
    self.step4_doseCalibrationCollapsibleButtonLayout.addWidget(self.step4A_prepareCalibrationDataCollapsibleButton)
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout.setSpacing(4)

    # Load Pdd data
    self.step4A_pddLoadDataButton = qt.QPushButton("Load file")
    self.step4A_pddLoadDataButton.toolTip = "Load PDD data"
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout.addRow('Percent Depth Dose (PDD) data: ', self.step4A_pddLoadDataButton)
    # Add empty row
    self.step4A_pddLoadStatusLabel = qt.QLabel()
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout.addRow(' ', self.step4A_pddLoadStatusLabel)

    # Load CALIBRATION dose volume
    self.step4A_loadCalibrationDataButton = qt.QPushButton("Load .vff File")
    self.step4A_loadCalibrationDataButton.toolTip = "Select calibration CT scan of gel if not already loaded."
    self.step4A_loadCalibrationDataButton.name = "loadCalibrationDataButton"
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout.addRow('Load CALIBRATION dose volume: ', self.step4A_loadCalibrationDataButton)

    # Select CALIBRATION dose volume
    self.step4A_calibrationVolumeSelector = slicer.qMRMLNodeComboBox()
    self.step4A_calibrationVolumeSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.step4A_calibrationVolumeSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.step4A_calibrationVolumeSelector.addEnabled = False
    self.step4A_calibrationVolumeSelector.removeEnabled = False
    self.step4A_calibrationVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.step4A_calibrationVolumeSelector.setToolTip( "CALIBRATION dose volume for parsing" )
    self.step4A_calibrationVolumeSelector.enabled = False # Don't let the user select another, use the one that was loaded (the combobox is there to indicate which volume is involved)
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout.addRow('CALIBRATION dose volume: ', self.step4A_calibrationVolumeSelector)

    # Input parameters used for finding mean and standard deviation of centre of experimental volume
    self.step4A_radiusMmFromCentrePixelLineEdit = qt.QLineEdit()
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout.addRow('Averaging radius (mm): ', self.step4A_radiusMmFromCentrePixelLineEdit)

    # Parse/generate appropriate data arrays for analysis
    self.step4A_parseCalibrationVolumeButton = qt.QPushButton("Parse CALIBRATION dose volume")
    self.step4A_parseCalibrationVolumeButton.toolTip = "Parse CALIBRATION dose volume"
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout.addRow(self.step4A_parseCalibrationVolumeButton)
    self.step4A_parseCalibrationVolumeStatusLabel = qt.QLabel()
    self.step4A_prepareCalibrationDataCollapsibleButtonLayout.addRow(' ', self.step4A_parseCalibrationVolumeStatusLabel)

    # Step 4/B): Align Pdd data and CALIBRATION data
    self.step4B_alignPddAndExperimentalDataCollapsibleButton.text = "4/B) Align CALIBRATION data to PDD data"
    self.step4B_alignPddAndExperimentalDataCollapsibleButtonLayout = qt.QFormLayout(self.step4B_alignPddAndExperimentalDataCollapsibleButton)
    self.step4_doseCalibrationCollapsibleButtonLayout.addWidget(self.step4B_alignPddAndExperimentalDataCollapsibleButton)
    self.step4B_alignPddAndExperimentalDataCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step4B_alignPddAndExperimentalDataCollapsibleButtonLayout.setSpacing(4)

    # Align Pdd data and CALIBRATION data based on region of interest selected
    self.step4B_alignCalibrationCurvesButton = qt.QPushButton("Align and show plots")
    self.step4B_alignCalibrationCurvesButton.toolTip = "Align PDD data optical density values with experimental optical density values (coming from CALIBRATION)"
    self.step4B_alignPddAndExperimentalDataCollapsibleButtonLayout.addRow('Align curves: ', self.step4B_alignCalibrationCurvesButton)
    # Add empty row
    self.step4B_alignPddAndExperimentalDataCollapsibleButtonLayout.addRow(' ', None)

    # Input parameters for calculating dose information of CALIBRATION data based on PDD data
    self.step4B_rdfLineEdit = qt.QLineEdit()
    self.step4B_alignPddAndExperimentalDataCollapsibleButtonLayout.addRow('RDF: ', self.step4B_rdfLineEdit)
    self.step4B_monitorUnitsLineEdit = qt.QLineEdit()
    self.step4B_alignPddAndExperimentalDataCollapsibleButtonLayout.addRow("Electron MU's: ", self.step4B_monitorUnitsLineEdit)

    # Create dose information button
    self.step4B_computeDoseFromPddButton = qt.QPushButton("Compute dose from percent depth dose")
    self.step4B_computeDoseFromPddButton.toolTip = "Compute dose from PDD data based on RDF and MUs"
    self.step4B_alignPddAndExperimentalDataCollapsibleButtonLayout.addRow(self.step4B_computeDoseFromPddButton)

    self.step4B_computeDoseFromPddStatusLabel = qt.QLabel()
    self.step4B_alignPddAndExperimentalDataCollapsibleButtonLayout.addRow(' ', self.step4B_computeDoseFromPddStatusLabel)

    # Step 4/C): Fit polynomial and apply calibration
    self.step4C_polynomialFittingAndCalibrationCollapsibleButton.text = "4/C) Fit polynomial and apply calibration"
    self.step4C_polynomialFittingAndCalibrationCollapsibleButtonLayout = qt.QFormLayout(self.step4C_polynomialFittingAndCalibrationCollapsibleButton)
    self.step4_doseCalibrationCollapsibleButtonLayout.addWidget(self.step4C_polynomialFittingAndCalibrationCollapsibleButton)
    self.step4C_polynomialFittingAndCalibrationCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step4C_polynomialFittingAndCalibrationCollapsibleButtonLayout.setSpacing(4)

    # Show chart of optical density vs. dose curve.
    self.step4C_showOpticalDensityVsDoseCurveButton = qt.QPushButton("Show")
    self.step4C_showOpticalDensityVsDoseCurveButton.toolTip = "Show optical density Vs. Dose curve to determine the order of polynomial to fit."
    self.step4C_polynomialFittingAndCalibrationCollapsibleButtonLayout.addRow('Show optical density Vs. Dose curve: ', self.step4C_showOpticalDensityVsDoseCurveButton)

    # Find polynomial fit
    self.step4C_fitPolynomialToOpticalDensityVsDoseCurveButton = qt.QPushButton("Fit polynomial")
    self.step4C_fitPolynomialToOpticalDensityVsDoseCurveButton.toolTip = "Finds the line of best fit based on the data and polynomial order provided"
    self.step4C_polynomialFittingAndCalibrationCollapsibleButtonLayout.addRow(self.step4C_fitPolynomialToOpticalDensityVsDoseCurveButton)
    # Add empty row
    self.step4C_polynomialFittingAndCalibrationCollapsibleButtonLayout.addRow(' ', None)

    # MEASURED volume selector
    self.step4C_measuredVolumeSelector = slicer.qMRMLNodeComboBox()
    self.step4C_measuredVolumeSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.step4C_measuredVolumeSelector.addEnabled = False
    self.step4C_measuredVolumeSelector.removeEnabled = False
    self.step4C_measuredVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.step4C_measuredVolumeSelector.setToolTip( "MEASURED dose volume to calibrate" )
    self.step4C_measuredVolumeSelector.enabled = False # Don't let the user select another, use the one that was loaded (the combobox is there to indicate which volume is involved)
    self.step4C_polynomialFittingAndCalibrationCollapsibleButtonLayout.addRow('MEASURED dose volume: ', self.step4C_measuredVolumeSelector)

    # Apply calibration
    self.step4C_applyCalibrationButton = qt.QPushButton("Apply calibration")
    self.step4C_applyCalibrationButton.toolTip = "Apply fitted polynomial on MEASURED volume"
    self.step4C_polynomialFittingAndCalibrationCollapsibleButtonLayout.addRow(self.step4C_applyCalibrationButton)

    self.step4C_applyCalibrationStatusLabel = qt.QLabel()
    self.step4C_polynomialFittingAndCalibrationCollapsibleButtonLayout.addRow(' ', self.step4C_applyCalibrationStatusLabel)
    
    # Connections
    self.step4A_pddLoadDataButton.connect('clicked()', self.onLoadPddDataRead)
    self.step4A_loadCalibrationDataButton.connect('clicked()', self.onLoadCalibrationData)
    self.step4A_parseCalibrationVolumeButton.connect('clicked()', self.onParseCalibrationVolume)
    self.step4B_alignCalibrationCurvesButton.connect('clicked()', self.onAlignCalibrationCurves)
    self.step4B_computeDoseFromPddButton.connect('clicked()', self.onComputeDoseFromPdd)
    self.step4C_polynomialFittingAndCalibrationCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep4C_PolynomialFittingAndCalibrationSelected)
    self.step4C_showOpticalDensityVsDoseCurveButton.connect('clicked()', self.onShowOpticalDensityVsDoseCurve)
    self.step4C_fitPolynomialToOpticalDensityVsDoseCurveButton.connect('clicked()', self.onFitPolynomialToOpticalDensityVsDoseCurve)
    self.step4C_applyCalibrationButton.connect('clicked()', self.onApplyCalibration)

    # Open prepare calibratio data panel when step is first opened
    self.step4A_prepareCalibrationDataCollapsibleButton.setProperty('collapsed', False)
    
  def setup_Step5_DoseComparison(self):
    # Step 5: Dose comparison and analysis
    self.step5_doseComparisonCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step5_doseComparisonCollapsibleButton.text = "5. Perform dose comparison and analysis"
    self.sliceletPanelLayout.addWidget(self.step5_doseComparisonCollapsibleButton)
    self.step5_doseComparisonCollapsibleButtonLayout = qt.QFormLayout(self.step5_doseComparisonCollapsibleButton)
    self.step5_doseComparisonCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step5_doseComparisonCollapsibleButtonLayout.setSpacing(4)

    # Plan dose volume selector
    self.step5_planDoseSelector = slicer.qMRMLNodeComboBox()
    self.step5_planDoseSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.step5_planDoseSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.step5_planDoseSelector.addEnabled = False
    self.step5_planDoseSelector.removeEnabled = False
    self.step5_planDoseSelector.setMRMLScene( slicer.mrmlScene )
    self.step5_planDoseSelector.setToolTip( "Pick the PLANDOSE volume for comparison" )
    self.step5_doseComparisonCollapsibleButtonLayout.addRow('PLANDOSE volume: ', self.step5_planDoseSelector)

    # MEASURED dose volume selector
    self.step5_measuredDoseSelector = slicer.qMRMLNodeComboBox()
    self.step5_measuredDoseSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.step5_measuredDoseSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.step5_measuredDoseSelector.addEnabled = False
    self.step5_measuredDoseSelector.removeEnabled = False
    self.step5_measuredDoseSelector.setMRMLScene( slicer.mrmlScene )
    self.step5_measuredDoseSelector.setToolTip( "Pick the calibrated MEASURED optical CT volume for comparison." )
    self.step5_doseComparisonCollapsibleButtonLayout.addRow("MEASURED dose volume: ", self.step5_measuredDoseSelector)

    # Collapsible buttons for substeps
    self.step5A_gammaDoseComparisonCollapsibleButton = ctk.ctkCollapsibleButton()
    self.step5A_gammaDoseComparisonCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step5B_chiDoseComparisonCollapsibleButton = ctk.ctkCollapsibleButton() # TODO:
    self.step5B_chiDoseComparisonCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step5B_chiDoseComparisonCollapsibleButton.setVisible(False)
    self.step5C_doseDifferenceComparisonCollapsibleButton = ctk.ctkCollapsibleButton() # TODO:
    self.step5C_doseDifferenceComparisonCollapsibleButton.setProperty('collapsedHeight', 4)
    self.step5C_doseDifferenceComparisonCollapsibleButton.setVisible(False)

    self.collapsibleButtonsGroupForDoseComparisonAndAnalysis = qt.QButtonGroup()
    self.collapsibleButtonsGroupForDoseComparisonAndAnalysis.addButton(self.step5A_gammaDoseComparisonCollapsibleButton)
    self.collapsibleButtonsGroupForDoseComparisonAndAnalysis.addButton(self.step5B_chiDoseComparisonCollapsibleButton)
    self.collapsibleButtonsGroupForDoseComparisonAndAnalysis.addButton(self.step5C_doseDifferenceComparisonCollapsibleButton)

    # 5/A) Gamma dose comparison
    self.step5A_gammaDoseComparisonCollapsibleButton.text = "5/A) Gamma dose comparison"
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout = qt.QFormLayout(self.step5A_gammaDoseComparisonCollapsibleButton)
    self.step5_doseComparisonCollapsibleButtonLayout.addRow(self.step5A_gammaDoseComparisonCollapsibleButton)
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.setSpacing(4)

    self.step5A_dtaDistanceToleranceMmSpinBox = qt.QDoubleSpinBox()
    self.step5A_dtaDistanceToleranceMmSpinBox.setValue(3.0)
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.addRow('DTA distance tolerance (mm): ', self.step5A_dtaDistanceToleranceMmSpinBox)

    self.step5A_doseDifferenceTolerancePercentSpinBox = qt.QDoubleSpinBox()
    self.step5A_doseDifferenceTolerancePercentSpinBox.setValue(3.0)
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.addRow('Dose difference tolerance (%): ', self.step5A_doseDifferenceTolerancePercentSpinBox)

    self.step5A_referenceDoseLayout = qt.QGridLayout()
    self.step5A_referenceDoseLabel = qt.QLabel('Reference dose: ')
    self.step5A_referenceDoseLayout.addWidget(self.step5A_referenceDoseLabel, 0, 0, 2, 1)
    self.step5A_referenceDoseUseMaximumDoseRadioButton = qt.QRadioButton('Use maximum dose')
    self.step5A_referenceDoseLayout.addWidget(self.step5A_referenceDoseUseMaximumDoseRadioButton, 0, 1)
    self.step5A_referenceDoseUseCustomValueGyRadioButton = qt.QRadioButton('Use custom value (Gy)')
    self.step5A_referenceDoseLayout.addWidget(self.step5A_referenceDoseUseCustomValueGyRadioButton, 1, 1)
    self.step5A_referenceDoseCustomValueGySpinBox = qt.QDoubleSpinBox()
    self.step5A_referenceDoseCustomValueGySpinBox.setValue(5.0)
    self.step5A_referenceDoseCustomValueGySpinBox.setEnabled(False)
    self.step5A_referenceDoseLayout.addWidget(self.step5A_referenceDoseCustomValueGySpinBox, 1, 2)
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.addRow(self.step5A_referenceDoseLayout)

    self.step5A_analysisThresholdPercentSpinBox = qt.QDoubleSpinBox()
    self.step5A_analysisThresholdPercentSpinBox.setValue(0.0)
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.addRow('Analysis threshold (%): ', self.step5A_analysisThresholdPercentSpinBox)

    self.step5A_maximumGammaSpinBox = qt.QDoubleSpinBox()
    self.step5A_maximumGammaSpinBox.setValue(2.0)
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.addRow('Maximum gamma: ', self.step5A_maximumGammaSpinBox)

    self.step5_gammaVolumeSelector = slicer.qMRMLNodeComboBox()
    self.step5_gammaVolumeSelector.nodeTypes = ( ("vtkMRMLScalarVolumeNode"), "" )
    self.step5_gammaVolumeSelector.addAttribute( "vtkMRMLScalarVolumeNode", "LabelMap", 0 )
    self.step5_gammaVolumeSelector.addEnabled = True
    self.step5_gammaVolumeSelector.removeEnabled = False
    self.step5_gammaVolumeSelector.setMRMLScene( slicer.mrmlScene )
    self.step5_gammaVolumeSelector.setToolTip( "Select output gamma volume" )
    self.step5_gammaVolumeSelector.setProperty('baseName', 'GammaVolume')
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.addRow("Gamma volume: ", self.step5_gammaVolumeSelector)

    self.step5A_computeGammaButton = qt.QPushButton('Compute gamma')
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.addRow(self.step5A_computeGammaButton)

    self.step5A_gammaStatusLabel = qt.QLabel()
    self.step5A_gammaDoseComparisonCollapsibleButtonLayout.addRow(self.step5A_gammaStatusLabel)

    # 5/B) Chi dose comparison
    self.step5B_chiDoseComparisonCollapsibleButton.text = "5/B) Chi dose comparison"
    self.step5B_chiDoseComparisonCollapsibleButtonLayout = qt.QFormLayout(self.step5B_chiDoseComparisonCollapsibleButton)
    self.step5_doseComparisonCollapsibleButtonLayout.addRow(self.step5B_chiDoseComparisonCollapsibleButton)
    self.step5B_chiDoseComparisonCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step5B_chiDoseComparisonCollapsibleButtonLayout.setSpacing(4)

    # C) Dose difference comparison
    self.step5C_doseDifferenceComparisonCollapsibleButton.text = "5/C) Dose difference comparison"
    self.step5C_doseDifferenceComparisonCollapsibleButtonLayout = qt.QFormLayout(self.step5C_doseDifferenceComparisonCollapsibleButton)
    self.step5_doseComparisonCollapsibleButtonLayout.addRow(self.step5C_doseDifferenceComparisonCollapsibleButton)
    self.step5C_doseDifferenceComparisonCollapsibleButtonLayout.setContentsMargins(12,4,4,4)
    self.step5C_doseDifferenceComparisonCollapsibleButtonLayout.setSpacing(4)

    # Connections
    self.step5_doseComparisonCollapsibleButton.connect('contentsCollapsed(bool)', self.onStep5_DoseComparisonSelected)
    self.step5A_referenceDoseUseMaximumDoseRadioButton.connect('toggled(bool)', self.onUseMaximumDoseRadioButtonToggled)
    self.step5A_computeGammaButton.connect('clicked()', self.onGammaDoseComparison)

    # Open gamma dose comparison panel when step is first opened
    self.step5A_gammaDoseComparisonCollapsibleButton.setProperty('collapsed',False)
    self.step5A_referenceDoseUseMaximumDoseRadioButton.setChecked(True)

  #
  # Event handler functions
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

  def onLoadMeasuredData(self):
    slicer.app.ioManager().connect('newFileLoaded(qSlicerIO::IOProperties)', self.setMeasuredData)
    slicer.util.openAddDataDialog()
    slicer.app.ioManager().disconnect('newFileLoaded(qSlicerIO::IOProperties)', self.setMeasuredData)

  def setMeasuredData(self, params):
    # Assumes that two MRML nodes are created when loading a VFF file, and the first one is the volume (second is the display node)
    self.measuredVolumeNode = slicer.mrmlScene.GetNthNode( slicer.mrmlScene.GetNumberOfNodes()-2 )
    self.step3D_measuredVolumeSelector.setCurrentNode(self.measuredVolumeNode)
    self.step4C_measuredVolumeSelector.setCurrentNode(self.measuredVolumeNode)
    self.step5_measuredDoseSelector.setCurrentNode(self.measuredVolumeNode)

    self.step3B_loadMeasuredDataStatusLabel.setText('Volume loaded and set as MEASURED')

  def onStep3_MeasuredDoseToObiRegistrationSelected(self, collapsed):
    # Make sure the functions handling entering the fiducial selection panels are called when entering the outer panel
    if collapsed == False:
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      if self.step3A_obiFiducialSelectionCollapsibleButton.collapsed == False:
        if self.obiVolumeNode != None:
          selectionNode.SetReferenceActiveVolumeID(self.obiVolumeNode.GetID())
        else:
          selectionNode.SetReferenceActiveVolumeID(None)
        selectionNode.SetReferenceSecondaryVolumeID(None)
        appLogic.PropagateVolumeSelection() 
      elif self.step3C_measuredFiducialSelectionCollapsibleButton.collapsed == False:
        if self.measuredVolumeNode != None:
          selectionNode.SetReferenceActiveVolumeID(self.measuredVolumeNode.GetID())
        else:
          selectionNode.SetReferenceActiveVolumeID(None)
        selectionNode.SetReferenceSecondaryVolumeID(None)
        appLogic.PropagateVolumeSelection() 

  def onStep3A_ObiFiducialCollectionSelected(self, collapsed):
    # Add Markups widget
    if collapsed == False:
      # TODO: Clean up if possible. Did not work without double nesting (widget disappeared when switched to step 3/C)
      newLayout = qt.QFormLayout()
      newLayout.setMargin(0)
      newLayout.setSpacing(0)
      tempLayoutInner = qt.QVBoxLayout()
      tempLayoutInner.setMargin(0)
      tempLayoutInner.setSpacing(0)
      tempFrame = qt.QFrame()
      tempFrame.setLayout(tempLayoutInner)
      tempLayoutInner.addWidget(self.fiducialSelectionWidget)
      newLayout.addRow(tempFrame)
      self.step3A_obiFiducialSelectionCollapsibleButton.setLayout(newLayout)

      # Set annotation list node
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      selectionNode.SetActivePlaceNodeID(self.obiMarkupsFiducialNode.GetID())
      # interactionNode = appLogic.GetInteractionNode()
      # interactionNode.SwitchToSinglePlaceMode()

      # Select OBI fiducials node
      activeMarkupMrmlNodeCombobox = slicer.util.findChildren(widget=self.markupsWidgetClone, className='qMRMLNodeComboBox', name='activeMarkupMRMLNodeComboBox')[0]
      activeMarkupMrmlNodeCombobox.setCurrentNode(self.obiMarkupsFiducialNode)
      self.markupsWidget.onActiveMarkupMRMLNodeChanged(self.obiMarkupsFiducialNode)
      
      # Show only the OBI fiducials in the 3D view
      self.markupsLogic.SetAllMarkupsVisibility(self.obiMarkupsFiducialNode, True)
      self.markupsLogic.SetAllMarkupsVisibility(self.measuredMarkupsFiducialNode, False)

      # Automatically show OBI volume (show nothing if not present)
      if self.obiVolumeNode != None:
        selectionNode.SetReferenceActiveVolumeID(self.obiVolumeNode.GetID())
      else:
        selectionNode.SetReferenceActiveVolumeID(None)
      selectionNode.SetReferenceSecondaryVolumeID(None)
      appLogic.PropagateVolumeSelection() 
    else:
      # Delete temporary layout
      currentLayout = self.step3A_obiFiducialSelectionCollapsibleButton.layout()
      if currentLayout:
        currentLayout.deleteLater()

      # Show both fiducial lists in the 3D view
      self.markupsLogic.SetAllMarkupsVisibility(self.obiMarkupsFiducialNode, True)
      self.markupsLogic.SetAllMarkupsVisibility(self.measuredMarkupsFiducialNode, True)

  def onStep3C_ObiFiducialCollectionSelected(self, collapsed):
    # Add Markups widget
    if collapsed == False:
      # TODO: Clean up if possible. Did not work without double nesting
      newLayout = qt.QFormLayout()
      newLayout.setMargin(0)
      newLayout.setSpacing(0)
      tempLayoutInner = qt.QVBoxLayout()
      tempLayoutInner.setMargin(0)
      tempLayoutInner.setSpacing(0)
      tempFrame = qt.QFrame()
      tempFrame.setLayout(tempLayoutInner)
      tempLayoutInner.addWidget(self.fiducialSelectionWidget)
      newLayout.addWidget(tempFrame)
      self.step3C_measuredFiducialSelectionCollapsibleButton.setLayout(newLayout)

      # Set annotation list node
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      selectionNode.SetActivePlaceNodeID(self.measuredMarkupsFiducialNode.GetID())
      # interactionNode = appLogic.GetInteractionNode()
      # interactionNode.SwitchToSinglePlaceMode()

      # Select MEASURED fiducials node
      activeMarkupMrmlNodeCombobox = slicer.util.findChildren(widget=self.markupsWidgetClone, className='qMRMLNodeComboBox', name='activeMarkupMRMLNodeComboBox')[0]
      activeMarkupMrmlNodeCombobox.setCurrentNode(self.measuredMarkupsFiducialNode)
      self.markupsWidget.onActiveMarkupMRMLNodeChanged(self.measuredMarkupsFiducialNode)

      # Show only the OBI fiducials in the 3D view
      self.markupsLogic.SetAllMarkupsVisibility(self.measuredMarkupsFiducialNode, True)
      self.markupsLogic.SetAllMarkupsVisibility(self.obiMarkupsFiducialNode, False)

      # Automatically show MEASURED volume (show nothing if not present)
      if self.measuredVolumeNode != None:
        selectionNode.SetReferenceActiveVolumeID(self.measuredVolumeNode.GetID())
      else:
        selectionNode.SetReferenceActiveVolumeID(None)
      selectionNode.SetReferenceSecondaryVolumeID(None)
      appLogic.PropagateVolumeSelection() 
    else:
      # Delete temporary layout
      currentLayout = self.step3C_measuredFiducialSelectionCollapsibleButton.layout()
      if currentLayout:
        currentLayout.deleteLater()

      # Show both fiducial lists in the 3D view
      self.markupsLogic.SetAllMarkupsVisibility(self.obiMarkupsFiducialNode, True)
      self.markupsLogic.SetAllMarkupsVisibility(self.measuredMarkupsFiducialNode, True)

  def onObiToPlanCTRegistration(self):
    # Save selection for later
    self.planCtVolumeNode = self.planCTSelector.currentNode()
    self.planDoseVolumeNode = self.planDoseSelector.currentNode()
    self.obiVolumeNode = self.obiSelector.currentNode()

    # Start registration
    obiVolumeID = self.obiSelector.currentNodeID
    planCTVolumeID = self.planCTSelector.currentNodeID
    planDoseVolumeID = self.planDoseSelector.currentNodeID
    self.logic.registerObiToPlanCt(obiVolumeID, planCTVolumeID, planDoseVolumeID)

    # Show the two volumes for visual evaluation of the registration
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveVolumeID(planCTVolumeID)
    selectionNode.SetReferenceSecondaryVolumeID(obiVolumeID)
    appLogic.PropagateVolumeSelection() 
    # Set color to the OBI volume
    obiVolumeDisplayNode = self.obiVolumeNode.GetDisplayNode()
    colorNode = slicer.util.getNode('Iron')
    obiVolumeDisplayNode.SetAndObserveColorNodeID(colorNode.GetID())
    # Set transparency to the OBI volume
    compositeNodes = slicer.util.getNodes("vtkMRMLSliceCompositeNode*")
    for name in compositeNodes:
      if compositeNodes[name] != None:
        compositeNodes[name].SetForegroundOpacity(0.5)

  def onMeasuredToObiRegistration(self):
    errorRms = self.logic.registerObiToMeasured(self.obiMarkupsFiducialNode.GetID(), self.measuredMarkupsFiducialNode.GetID())
    
    # Show registration error on GUI
    self.step3D_measuredToObiFiducialRegistrationErrorLabel.setText(errorRms)

    # Apply transform to MEASURED volume
    obiToMeasuredTransformNode = slicer.util.getNode(self.logic.obiToMeasuredTransformName)
    self.measuredVolumeNode.SetAndObserveTransformNodeID(obiToMeasuredTransformNode.GetID())

    # Show both volumes in the 2D views
    appLogic = slicer.app.applicationLogic()
    selectionNode = appLogic.GetSelectionNode()
    selectionNode.SetReferenceActiveVolumeID(self.obiVolumeNode.GetID())
    selectionNode.SetReferenceSecondaryVolumeID(self.measuredVolumeNode.GetID())
    appLogic.PropagateVolumeSelection() 

  def onLoadPddDataRead(self):
    self.step4A_pddLoadStatusLabel.setText('')
    fileName = qt.QFileDialog.getOpenFileName(0, 'Open PDD data file', '', 'CSV with COMMA ( *.csv )')
    if fileName != None and fileName != '':
      success = self.logic.loadPdd(fileName)
      if success == True:
        self.step4A_pddLoadStatusLabel.setText('PDD loaded successfully')
        return
    self.step4A_pddLoadStatusLabel.setText('PDD loading failed!')

  def onLoadCalibrationData(self):
    slicer.app.ioManager().connect('newFileLoaded(qSlicerIO::IOProperties)', self.setCalibrationData)
    slicer.util.openAddDataDialog()
    slicer.app.ioManager().disconnect('newFileLoaded(qSlicerIO::IOProperties)', self.setCalibrationData)

  def setCalibrationData(self, params):
    # Assumes that two MRML nodes are created when loading a VFF file, and the first one is the volume (second is the display node)
    self.calibrationVolumeNode = slicer.mrmlScene.GetNthNode( slicer.mrmlScene.GetNumberOfNodes()-2 )
    self.step4A_calibrationVolumeSelector.setCurrentNode(self.calibrationVolumeNode)

    self.step4A_parseCalibrationVolumeStatusLabel.setText('Volume loaded and set as CALIBRATION')

  def onStep4C_PolynomialFittingAndCalibrationSelected(self, collapsed):
    if collapsed == False:
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      if self.measuredVolumeNode != None:
        selectionNode.SetReferenceActiveVolumeID(self.measuredVolumeNode.GetID())
      else:
        selectionNode.SetReferenceActiveVolumeID(None)
      selectionNode.SetReferenceSecondaryVolumeID(None)
      appLogic.PropagateVolumeSelection() 

  def onParseCalibrationVolume(self):
    radiusOfCentreCircleText = self.step4A_radiusMmFromCentrePixelLineEdit.text
    radiusOfCentreCircleFloat = float(radiusOfCentreCircleText)

    success = self.logic.getMeanOpticalDensityOfCentralCylinder(self.calibrationVolumeNode.GetID(), radiusOfCentreCircleFloat)
    if success == True:
      self.step4A_parseCalibrationVolumeStatusLabel.setText('Calibration volume parsed successfully')
      return
    self.step4A_parseCalibrationVolumeStatusLabel.setText('Calibration volume parsing failed!')

  def showCalibrationCurves(self):
    # Set up window to be used for displaying data
    self.calibrationCurveChartView = vtk.vtkContextView()
    self.calibrationCurveChartView.GetRenderer().SetBackground(1,1,1)
    self.calibrationCurveChart = vtk.vtkChartXY()
    self.calibrationCurveChartView.GetScene().AddItem(self.calibrationCurveChart)

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
    for rowIndex in xrange(0, calibrationNumberOfRows):
      self.calibrationCurveDataTable.SetValue(rowIndex, 0, self.logic.calibrationDataArray[rowIndex, 0])
      self.calibrationCurveDataTable.SetValue(rowIndex, 1, self.logic.calibrationDataArray[rowIndex, 1])
      # self.calibrationCurveDataTable.SetValue(rowIndex, 2, self.logic.calibrationDataArray[rowIndex, 2])

    calibrationMeanOpticalDensityLine = self.calibrationCurveChart.AddPlot(vtk.vtkChart.LINE)
    calibrationMeanOpticalDensityLine.SetInput(self.calibrationCurveDataTable, 0, 1)
    calibrationMeanOpticalDensityLine.SetColor(255, 0, 0, 255)
    calibrationMeanOpticalDensityLine.SetWidth(2.0)

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
    for pddDepthCounter in xrange(0, pddNumberOfRows):
      self.pddDataTable.SetValue(pddDepthCounter, 0, self.logic.pddDataArray[pddDepthCounter, 0])
      self.pddDataTable.SetValue(pddDepthCounter, 1, self.logic.pddDataArray[pddDepthCounter, 1])

    pddLine = self.calibrationCurveChart.AddPlot(vtk.vtkChart.LINE)
    pddLine.SetInput(self.pddDataTable, 0, 1)
    pddLine.SetColor(0, 0, 255, 255)
    pddLine.SetWidth(2.0)

    # Add aligned curve to the graph
    self.calibrationDataAlignedTable = vtk.vtkTable()
    calibrationDataAlignedNumberOfRows = self.logic.calibrationDataAlignedArray.shape[0]
    calibrationDataAlignedDepthArray = vtk.vtkDoubleArray()
    calibrationDataAlignedDepthArray.SetName("Depth (cm)")
    self.calibrationDataAlignedTable.AddColumn(calibrationDataAlignedDepthArray)
    calibrationDataAlignedValueArray = vtk.vtkDoubleArray()
    calibrationDataAlignedValueArray.SetName("Aligned calibration data")
    self.calibrationDataAlignedTable.AddColumn(calibrationDataAlignedValueArray)

    self.calibrationDataAlignedTable.SetNumberOfRows(calibrationDataAlignedNumberOfRows)
    for calibrationDataAlignedDepthCounter in xrange(0, calibrationDataAlignedNumberOfRows):
      self.calibrationDataAlignedTable.SetValue(calibrationDataAlignedDepthCounter, 0, self.logic.calibrationDataAlignedArray[calibrationDataAlignedDepthCounter, 0])
      self.calibrationDataAlignedTable.SetValue(calibrationDataAlignedDepthCounter, 1, self.logic.calibrationDataAlignedArray[calibrationDataAlignedDepthCounter, 1])

    calibrationDataAlignedLine = self.calibrationCurveChart.AddPlot(vtk.vtkChart.LINE)
    calibrationDataAlignedLine.SetInput(self.calibrationDataAlignedTable, 0, 1)
    calibrationDataAlignedLine.SetColor(0, 212, 0, 255)
    calibrationDataAlignedLine.SetWidth(2.0)

    # Show chart
    self.calibrationCurveChart.GetAxis(1).SetTitle('Depth (cm)')
    self.calibrationCurveChart.GetAxis(0).SetTitle('Percent Depth Dose / Optical Density')
    self.calibrationCurveChart.SetShowLegend(True)
    self.calibrationCurveChart.SetTitle('PDD vs Calibration data')
    self.calibrationCurveChartView.GetInteractor().Initialize()
    self.calibrationCurveChartView.GetRenderWindow().SetSize(800,550)
    self.calibrationCurveChartView.GetRenderWindow().Start()

  def onAlignCalibrationCurves(self):
    # Align PDD data and "experimental" (CALIBRATION) data. Allow for horizontal shift
    # and vertical scale (max PDD Y value/max CALIBRATION Y value).
    self.logic.alignPddToCalibration()

    # Show plots
    self.showCalibrationCurves()
    	
  def onComputeDoseFromPdd(self):
    rdfInputText = self.step4B_rdfLineEdit.text
    monitorUnitsInputText = self.step4B_monitorUnitsLineEdit.text
    rdfFloat = float(rdfInputText)
    monitorUnitsFloat = float(monitorUnitsInputText)

    # Calculate dose information: calculatedDose = (PddDose * MonitorUnits * RDF) / 10000
    if self.logic.computeDoseForMeasuredData(rdfFloat, monitorUnitsFloat) == True:
      self.step4B_computeDoseFromPddStatusLabel.setText('Dose successfully calculated from PDD')
    else:
      self.step4B_computeDoseFromPddStatusLabel.setText('Dose calculation from PDD failed!')

  def onShowOpticalDensityVsDoseCurve(self):
    # Create optical density vs dose function
    self.logic.createOpticalDensityVsDoseFunction()

    # Set up window to be used for displaying data
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
    for rowIndex in xrange(0, odVsDoseNumberOfRows):
      self.odVsDoseDataTable.SetValue(rowIndex, 0, self.logic.opticalDensityVsDoseFunction[rowIndex, 0])
      self.odVsDoseDataTable.SetValue(rowIndex, 1, self.logic.opticalDensityVsDoseFunction[rowIndex, 1])

    odVsDoseLinePoint = self.odVsDoseChart.AddPlot(vtk.vtkChart.POINTS)
    odVsDoseLinePoint.SetInput(self.odVsDoseDataTable, 0, 1)
    odVsDoseLinePoint.SetColor(0, 0, 255, 255)
    odVsDoseLinePoint.SetMarkerSize(10)
    odVsDoseLineInnerPoint = self.odVsDoseChart.AddPlot(vtk.vtkChart.POINTS)
    odVsDoseLineInnerPoint.SetInput(self.odVsDoseDataTable, 0, 1)
    odVsDoseLineInnerPoint.SetColor(255, 255, 255, 223)
    odVsDoseLineInnerPoint.SetMarkerSize(8)

    # Show chart
    self.odVsDoseChart.GetAxis(1).SetTitle('Optical density')
    self.odVsDoseChart.GetAxis(0).SetTitle('Dose (GY)')
    self.odVsDoseChart.SetTitle('Optical density VS dose')
    self.odVsDoseChartView.GetInteractor().Initialize()
    self.odVsDoseChartView.GetRenderWindow().SetSize(800,550)
    self.odVsDoseChartView.GetRenderWindow().Start()

  def onFitPolynomialToOpticalDensityVsDoseCurve(self):
    self.logic.fitCurveToOpticalDensityVsDoseFunctionArray()
    p = self.logic.calibrationPolynomialCoeffitients
    maxOrder = len(p) - 1

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
    for rowIndex in xrange(0, polynomialNumberOfRows):
      x = minPolynomial + (maxPolynomial-minPolynomial)*rowIndex/polynomialNumberOfRows
      self.polynomialTable.SetValue(rowIndex, 0, x)
      y = 0
      for order in xrange(0,maxOrder+1):
        y += p[order] * x ** (maxOrder-order)
      self.polynomialTable.SetValue(rowIndex, 1, y)

    polynomialLine = self.odVsDoseChart.AddPlot(vtk.vtkChart.LINE)
    polynomialLine.SetInput(self.polynomialTable, 0, 1)
    polynomialLine.SetColor(192, 0, 0, 255)
    polynomialLine.SetWidth(2)

  def onApplyCalibration(self):
    if self.logic.calibrate(self.measuredVolumeNode.GetID()) == True:
      self.step4C_applyCalibrationStatusLabel.setText('Calibration successfully performed')
    else:
      self.step4C_applyCalibrationStatusLabel.setText('Calibration failed!')

    # Set window/level options for the calibrated dose
    measuredVolumeDisplayNode = self.measuredVolumeNode.GetDisplayNode()
    odVsDoseNumberOfRows = self.logic.opticalDensityVsDoseFunction.shape[0]
    minDose = self.logic.opticalDensityVsDoseFunction[0, 1]
    maxDose = self.logic.opticalDensityVsDoseFunction[odVsDoseNumberOfRows-1, 1]
    minWindowLevel = minDose - (maxDose-minDose)*0.2
    maxWindowLevel = maxDose + (maxDose-minDose)*0.2
    measuredVolumeDisplayNode.AutoWindowLevelOff();
    measuredVolumeDisplayNode.SetWindowLevelMinMax(minWindowLevel, maxWindowLevel);

  def onStep5_DoseComparisonSelected(self, collapsed):
    # Set plan dose volume to selector
    if collapsed == False:
      self.step5_planDoseSelector.setCurrentNode(self.planDoseVolumeNode)

  def onUseMaximumDoseRadioButtonToggled(self, toggled):
    self.step5A_referenceDoseCustomValueGySpinBox.setEnabled(not toggled)

  def onGammaDoseComparison(self):
    try:
      slicer.modules.dosecomparison
      import vtkSlicerDoseComparisonModuleLogic

      self.gammaParameterSetNode = vtkSlicerDoseComparisonModuleLogic.vtkMRMLDoseComparisonNode()
      slicer.mrmlScene.AddNode(self.gammaParameterSetNode)
      self.gammaParameterSetNode.SetAndObserveReferenceDoseVolumeNode(self.step5_planDoseSelector.currentNode())
      self.gammaParameterSetNode.SetAndObserveCompareDoseVolumeNode(self.step5_measuredDoseSelector.currentNode())
      self.gammaParameterSetNode.SetAndObserveGammaVolumeNode(self.step5_gammaVolumeSelector.currentNode())
      self.gammaParameterSetNode.SetDtaDistanceToleranceMm(self.step5A_dtaDistanceToleranceMmSpinBox.value)
      self.gammaParameterSetNode.SetDoseDifferenceTolerancePercent(self.step5A_doseDifferenceTolerancePercentSpinBox.value)
      self.gammaParameterSetNode.SetUseMaximumDose(self.step5A_referenceDoseUseMaximumDoseRadioButton.isChecked())
      self.gammaParameterSetNode.SetReferenceDoseGy(self.step5A_referenceDoseCustomValueGySpinBox.value)
      self.gammaParameterSetNode.SetAnalysisThresholdPercent(self.step5A_analysisThresholdPercentSpinBox.value)
      self.gammaParameterSetNode.SetMaximumGamma(self.step5A_maximumGammaSpinBox.value)
      
      slicer.modules.dosecomparison.logic().SetAndObserveDoseComparisonNode(self.gammaParameterSetNode)
      slicer.modules.dosecomparison.logic().ComputeGammaDoseDifference()
      
      if self.gammaParameterSetNode.GetResultsValid():
        self.step5A_gammaStatusLabel.setText('Gamma dose comparison succeeded\nPass fraction: {0:.2f}%'.format(self.gammaParameterSetNode.GetPassFractionPercent()))
      else:
        self.step5A_gammaStatusLabel.setText('Gamma dose comparison failed!')

      # Show gamma volume
      appLogic = slicer.app.applicationLogic()
      selectionNode = appLogic.GetSelectionNode()
      selectionNode.SetReferenceActiveVolumeID(self.step5_gammaVolumeSelector.currentNodeID)
      selectionNode.SetReferenceSecondaryVolumeID(None)
      appLogic.PropagateVolumeSelection() 
      
    except Exception, e:
      import traceback
      traceback.print_exc()
      print('ERROR: Failed to perform gamma dose comparison!')

  #
  # Testing related functions
  #
  def onSelfTestButtonClicked(self):
    self.performSelfTestFromScratch()
    # self.performSelfTestFromSavedScene()

  def performSelfTestFromScratch(self):
    # 1. Load test data
    dicomWidget = slicer.modules.dicom.widgetRepresentation().self()
    # Plan CT
    dicomWidget.detailsPopup.offerLoadables('1.2.246.352.71.2.1706542068.2765222.20130515154841', 'Series')
    dicomWidget.detailsPopup.examineForLoading()
    dicomWidget.detailsPopup.loadCheckedLoadables()
    # OBI
    dicomWidget.detailsPopup.offerLoadables('1.2.246.352.61.2.5072632187121435903.9111181212989789573', 'Series')
    dicomWidget.detailsPopup.examineForLoading()
    dicomWidget.detailsPopup.loadCheckedLoadables()
    # Plan dose
    dicomWidget.detailsPopup.offerLoadables('1.2.246.352.71.2.1706542068.2765224.20130515154906', 'Series')
    dicomWidget.detailsPopup.examineForLoading()
    dicomWidget.detailsPopup.loadCheckedLoadables()
    slicer.app.processEvents()
    self.logic.delayDisplay('Wait for the slicelet to catch up', 300)

    # 2. Register
    self.step2_obiToPlanCtRegistrationCollapsibleButton.setChecked(True)
    planCTVolumeID = 'vtkMRMLScalarVolumeNode1'
    self.planCTSelector.setCurrentNodeID(planCTVolumeID)
    obiVolumeID = 'vtkMRMLScalarVolumeNode2'
    self.obiSelector.setCurrentNodeID(obiVolumeID)
    planDoseVolumeID = 'vtkMRMLScalarVolumeNode3'
    self.planDoseSelector.setCurrentNodeID(planDoseVolumeID)
    self.onObiToPlanCTRegistration()
    slicer.app.processEvents()

    # 3. Select fiducials
    self.step3_measuredDoseToObiRegistrationCollapsibleButton.setChecked(True)
    obiFiducialsNode = slicer.util.getNode(self.obiMarkupsFiducialNodeName)
    obiFiducialsNode.AddFiducial(90.1, 156.9, -23.7)
    obiFiducialsNode.AddFiducial(130.6, 77, -23.7)
    obiFiducialsNode.AddFiducial(162.45, 94.1, -23.7)
    obiFiducialsNode.AddFiducial(89.6, 156.9, 51.5)
    obiFiducialsNode.AddFiducial(114.9, 77.4, 51.5)
    obiFiducialsNode.AddFiducial(161.4, 92.6, 51.5)
    self.step3C_measuredFiducialSelectionCollapsibleButton.setChecked(True)
    measuredFiducialsNode = slicer.util.getNode(self.measuredMarkupsFiducialNodeName)
    measuredFiducialsNode.AddFiducial(-96.4, -29, 97.6)
    measuredFiducialsNode.AddFiducial(-15.3, -66.6, 97.6)
    measuredFiducialsNode.AddFiducial(-32.14, -98.73, 97.6)
    measuredFiducialsNode.AddFiducial(-96.14, -29.55, 21.56)
    measuredFiducialsNode.AddFiducial(-17.63, -51.3, 21.56)
    measuredFiducialsNode.AddFiducial(-31.36, -98.73, 21.56)

    # Load MEASURE Vff
    slicer.app.ioManager().connect('newFileLoaded(qSlicerIO::IOProperties)', self.setMeasuredData)
    slicer.util.loadNodeFromFile('d:/devel/_Images/RT/20130415_GelDosimetryData/Opt CT Data/051513-01_HR.vff', 'VffFile', {})
    slicer.app.ioManager().disconnect('newFileLoaded(qSlicerIO::IOProperties)', self.setMeasuredData)
    # Perform fiducial registration
    self.step3D_measuredToObiRegistrationCollapsibleButton.setChecked(True)
    self.onMeasuredToObiRegistration()
    
    # 4. Calibration
    self.step4_doseCalibrationCollapsibleButton.setChecked(True)
    self.logic.loadPdd('d:/devel/_Images/RT/20130415_GelDosimetryData/12MeV_6x6.csv')
    # Load CALIBRATION Vff
    slicer.app.ioManager().connect('newFileLoaded(qSlicerIO::IOProperties)', self.setCalibrationData)
    slicer.util.loadNodeFromFile('d:/devel/_Images/RT/20130415_GelDosimetryData/Opt CT Data/051513-e_HR.vff', 'VffFile', {})
    slicer.app.ioManager().disconnect('newFileLoaded(qSlicerIO::IOProperties)', self.setCalibrationData)

    # Parse calibration volume
    self.step4A_radiusMmFromCentrePixelLineEdit.setText('2.5')
    self.onParseCalibrationVolume()
    # Align calibration curves
    self.onAlignCalibrationCurves()
    # Generate dose information
    self.step4B_rdfLineEdit.setText('0.989')
    self.step4B_monitorUnitsLineEdit.setText('230')
    self.onComputeDoseFromPdd()
    # Show optical density VS dose curve
    self.step4C_polynomialFittingAndCalibrationCollapsibleButton.setChecked(True)
    self.onShowOpticalDensityVsDoseCurve()
    # Fit polynomial on OD VS dose curve
    self.onFitPolynomialToOpticalDensityVsDoseCurve()
    # Calibrate
    self.onApplyCalibration()

    # 5. Dose comparison
    slicer.app.processEvents()
    self.logic.delayDisplay('Wait for the slicelet to catch up', 300)
    self.step5_doseComparisonCollapsibleButton.setChecked(True)
    self.step5_gammaVolumeSelector.addNode()
    self.onGammaDoseComparison()

  def performSelfTestFromSavedScene(self):
    qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))
    # Load scene
    slicer.util.loadScene('c:/Slicer_Data/20131125_GelDosimetry_UpToStep_3D/2013-11-25-Scene.mrml')

    # Set member variables for the loaded scene
    self.planCtVolumeNode = slicer.util.getNode('7: ARIA RadOnc Images - Verification Plan Phantom')
    self.obiVolumeNode = slicer.util.getNode('0: Unknown')
    self.planDoseVolumeNode = slicer.util.getNode('33: RTDOSE: Eclipse Doses')

    self.measuredVolumeNode = slicer.util.getNode('051513-01_hr.vff')
    self.step3D_measuredVolumeSelector.setCurrentNode(self.measuredVolumeNode)
    self.step4C_measuredVolumeSelector.setCurrentNode(self.measuredVolumeNode)
    self.step5_measuredDoseSelector.setCurrentNode(self.measuredVolumeNode)

    self.calibrationVolumeNode = slicer.util.getNode('051513-02_hr.vff')
    self.step4A_calibrationVolumeSelector.setCurrentNode(self.calibrationVolumeNode)
    
    # Parse calibration volume
    self.step4A_radiusMmFromCentrePixelLineEdit.setText('2.5')
    self.onParseCalibrationVolume()

    # Calibration
    self.logic.loadPdd('d:/devel/_Images/RT/20130415_GelDosimetryData/12MeV_6x6.csv')

    self.onAlignCalibrationCurves()

    self.step4B_rdfLineEdit.setText('0.989')
    self.step4B_monitorUnitsLineEdit.setText('230')
    self.onComputeDoseFromPdd()

    self.onShowOpticalDensityVsDoseCurve()
    self.onFitPolynomialToOpticalDensityVsDoseCurve()

    slicer.app.processEvents()
    self.onApplyCalibration()

    self.step4_doseCalibrationCollapsibleButton.setChecked(True)
    self.step4C_polynomialFittingAndCalibrationCollapsibleButton.setChecked(True)

    # Dose comparison
    self.step5_doseComparisonCollapsibleButton.setChecked(True)
    self.step5_gammaVolumeSelector.addNode()
    self.onGammaDoseComparison()
    
    qt.QApplication.restoreOverrideCursor()

#
# GelDosimetryAnalysis
#
class GelDosimetryAnalysis:
  def __init__(self, parent):
    parent.title = "Gel Dosimetry Analysis"
    parent.categories = ["Slicelets"]
    parent.dependencies = ["GelDosimetryAnalysisAlgo", "DicomRtImport", "BRAINSFit", "BRAINSResample", "DoseComparison"]
    parent.contributors = ["Mattea Welch (Queen's University), Jennifer Andrea (Queen's University), Csaba Pinter (Queen's University)"] # replace with "Firstname Lastname (Org)"
    parent.helpText = "Slicelet for gel dosimetry analysis"
    parent.acknowledgementText = """
    This file was originally developed by Mattea Welch, Jennifer Andrea, and Csaba Pinter (Queen's University). Funding was provided by NSERC-USRA, OCAIRO, Cancer Care Ontario and Queen's University
    """
    self.parent = parent

#
# GelDosimetryAnalysisWidget
#
class GelDosimetryAnalysisWidget:
  def __init__(self, parent = None):
    if not parent:
      self.parent = slicer.qMRMLWidget()
      self.parent.setLayout(qt.QVBoxLayout())
      self.parent.setMRMLScene(slicer.mrmlScene)
    else:
      self.parent = parent
    self.layout = self.parent.layout()
    if not parent:
      self.setup()
      self.parent.show()

  def setup(self):
    # Reload panel
    reloadCollapsibleButton = ctk.ctkCollapsibleButton()
    reloadCollapsibleButton.text = "Reload"
    self.layout.addWidget(reloadCollapsibleButton)
    reloadFormLayout = qt.QFormLayout(reloadCollapsibleButton)

    # Reload button
    self.reloadButton = qt.QPushButton("Reload")
    self.reloadButton.toolTip = "Reload this module."
    self.reloadButton.name = "GelDosimetryAnalysis Reload"
    reloadFormLayout.addWidget(self.reloadButton)
    self.reloadButton.connect('clicked()', self.onReload)

    # Show slicelet button
    launchSliceletButton = qt.QPushButton("Show slicelet")
    launchSliceletButton.toolTip = "Launch the slicelet"
    reloadFormLayout.addWidget(launchSliceletButton)
    launchSliceletButton.connect('clicked()', self.onShowSliceletButtonClicked)

  def onReload(self,moduleName="GelDosimetryAnalysis"):
    """Generic reload method for any scripted module.
    ModuleWizard will subsitute correct default moduleName.
    """
    import imp, sys, os, slicer

    widgetName = moduleName + "Widget"

    # Reload the source code
    # - set source file path
    # - load the module to the global space
    filePath = eval('slicer.modules.%s.path' % moduleName.lower())
    p = os.path.dirname(filePath)
    if not sys.path.__contains__(p):
      sys.path.insert(0,p)
    fp = open(filePath, "r")
    globals()[moduleName] = imp.load_module(
        moduleName, fp, filePath, ('.py', 'r', imp.PY_SOURCE))
    fp.close()

    # Rebuild the widget
    # - find and hide the existing widget
    # - create a new widget in the existing parent
    parent = slicer.util.findChildren(name='%s Reload' % moduleName)[0].parent().parent()
    for child in parent.children():
      try:
        child.hide()
      except AttributeError:
        pass
    # Remove spacer items
    item = parent.layout().itemAt(0)
    while item:
      parent.layout().removeItem(item)
      item = parent.layout().itemAt(0)
    # Create new widget inside existing parent
    globals()[widgetName.lower()] = eval(
        'globals()["%s"].%s(parent)' % (moduleName, widgetName))
    globals()[widgetName.lower()].setup()

  def onShowSliceletButtonClicked(self):
    mainFrame = SliceletMainFrame()
    mainFrame.setMinimumWidth(1200)
    mainFrame.connect('destroyed()', self.onSliceletClosed)
    slicelet = GelDosimetryAnalysisSlicelet(mainFrame)
    mainFrame.setSlicelet(slicelet)

    # Make the slicelet reachable from the Slicer python interactor for testing
    # slicer.gelDosimetrySliceletInstance = slicelet

  def onSliceletClosed(self):
    print('Slicelet closed')

# ---------------------------------------------------------------------------
class GelDosimetryAnalysisTest(unittest.TestCase):
  """
  This is the test case for your scripted module.
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
  # TODO: need a way to access and parse command line arguments
  # TODO: ideally command line args should handle --xml

  import sys
  print( sys.argv )

  mainFrame = qt.QFrame()
  slicelet = GelDosimetryAnalysisSlicelet(mainFrame)
