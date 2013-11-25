import os
import time
from __main__ import vtk, qt, ctk, slicer
from math import *
import numpy
from vtk.util import numpy_support

#
# GelDosimetryAnalysisLogic
#
class GelDosimetryAnalysisLogic:
  """This class should implement all the actual
  computation done by your module.  The interface
  should be such that other python code can import
  this class and make use of the functionality without
  requiring an instance of the Widget
  """

  def __init__(self):
    # Define constants
    self.obiToPlanTransformName = 'obiToPlanTransform'
    self.obiToMeasuredTransformName = "obiToMeasuredTransform"
    self.orderOfFittedPolynomial = 3

    # Declare member variables (mainly for documentation)
    self.pddDataArray = None
    self.calculatedDose = None # Computed from Pdd usinf RDF and Electron MUs
    self.calibrationDataArray = None
    self.calibrationDataAlignedArray = None # Calibration array registered (X shift and Y scale) to the Pdd curve
    self.opticalDensityVsDoseFunction = None
    self.calibrationPolynomialCoeffitients = None

    # Set logic instance to the global variable that supplies it to the calibration curve alignment minimizer function
    global gelDosimetryLogicInstanceGlobal
    gelDosimetryLogicInstanceGlobal = self

  # ---------------------------------------------------------------------------
  # Show and select DICOM browser
  def onDicomLoad(self):
    slicer.modules.dicom.widgetRepresentation()
    slicer.modules.DICOMWidget.enter()

  # ---------------------------------------------------------------------------
  # Use BRAINS registration to register PlanCT to OBI volume
  def registerObiToPlanCt(self, obiVolumeID, planCtVolumeID):
    try:
      qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))
      parametersRigid = {}
      parametersRigid["fixedVolume"] = planCtVolumeID
      parametersRigid["movingVolume"] = obiVolumeID
      parametersRigid["useRigid"] = True
      parametersRigid["initializeTransformMode"] = "useMomentsAlign"
      #parametersRigid["backgroundFillValue"] = -1000.0

      # Set output transform
      obiToPlanTransformNode = slicer.util.getNode(self.obiToPlanTransformName)
      if obiToPlanTransformNode == None:
        obiToPlanTransformNode = slicer.vtkMRMLLinearTransformNode()
        slicer.mrmlScene.AddNode(obiToPlanTransformNode)
        obiToPlanTransformNode.SetName(self.obiToPlanTransformName)
      # parametersRigid["outputTransform"] = obiToPlanTransformNode.GetID()
      parametersRigid["linearTransform"] = obiToPlanTransformNode.GetID()

      # Runs the brainsfit registration
      brainsFit = slicer.modules.brainsfit
      cliBrainsFitRigidNode = None
      cliBrainsFitRigidNode = slicer.cli.run(brainsFit, None, parametersRigid)

      waitCount = 0
      while cliBrainsFitRigidNode.GetStatusString() != 'Completed' and waitCount < 200:
        self.delayDisplay( "Register OBI to PlanCT using rigid registration... %d" % waitCount )
        waitCount += 1
      self.delayDisplay("Register OBI to PlanCT using rigid registration finished")
      qt.QApplication.restoreOverrideCursor()
      
      # Invert output transform (planToObi) to get the desired obiToPlan transform
      obiToPlanTransformNode.GetMatrixTransformToParent().Invert()

      # Apply transform to plan CT
      planCtVolumeNode = slicer.mrmlScene.GetNodeByID(planCtVolumeID)
      planCtVolumeNode.SetAndObserveTransformNodeID(obiToPlanTransformNode.GetID())
      # The output transform was automatically applied to the moving image (the OBI), undo that
      obiVolumeNode = slicer.mrmlScene.GetNodeByID(obiVolumeID)
      obiVolumeNode.SetAndObserveTransformNodeID(None)
      
    except Exception, e:
      import traceback
      traceback.print_exc()
    
  # ---------------------------------------------------------------------------
  def registerObiToMeasured(self, obiFiducialListID, measuredFiducialListID):
    try:
      qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))
      parametersFiducial = {}
      parametersFiducial["fixedLandmarks"] = obiFiducialListID
      parametersFiducial["movingLandmarks"] = measuredFiducialListID
      
      # Create linear transform which will store the registration transform
      obiToMeasuredTransformNode = slicer.util.getNode(self.obiToMeasuredTransformName)
      if obiToMeasuredTransformNode == None:
        obiToMeasuredTransformNode = slicer.vtkMRMLLinearTransformNode()
        slicer.mrmlScene.AddNode(obiToMeasuredTransformNode)
        obiToMeasuredTransformNode.SetName(self.obiToMeasuredTransformName)
      parametersFiducial["saveTransform"] = obiToMeasuredTransformNode.GetID()
      parametersFiducial["transformType"] = "Rigid"

      # Run fiducial registration
      fiducialRegistration = slicer.modules.fiducialregistration
      cliFiducialRegistrationRigidNode = None
      cliFiducialRegistrationRigidNode = slicer.cli.run(fiducialRegistration, None, parametersFiducial)

      waitCount = 0
      while cliFiducialRegistrationRigidNode.GetStatusString() != 'Completed' and waitCount < 200:
        self.delayDisplay( "Register MEASURED to OBI using fiducial registration... %d" % waitCount )
        waitCount += 1
      self.delayDisplay("Register MEASURED to OBI using fiducial registration finished")
      qt.QApplication.restoreOverrideCursor()
      
      # Apply transform to MEASURED fiducials
      measuredFiducialsNode = slicer.mrmlScene.GetNodeByID(measuredFiducialListID)
      measuredFiducialsNode.SetAndObserveTransformNodeID(obiToMeasuredTransformNode.GetID())

      return cliFiducialRegistrationRigidNode.GetParameterAsString('rms')
    except Exception, e:
      import traceback
      traceback.print_exc()

  # ---------------------------------------------------------------------------
  def loadPdd(self, fileName):
    if fileName == None or fileName == '':
      print('ERROR: Empty PDD file name!')
      return False

    readFile = open(fileName, 'r')
    lines = readFile.readlines()
    doseTable = numpy.zeros([len(lines), 2]) # 2 columns

    rowCounter = 0
    for line in lines:
      firstValue, endOfLine = line.partition(',')[::2]
      if endOfLine == '':
        print "ERROR: File formatted incorrectly!"
        return False
      valueOne = float(firstValue)
      doseTable[rowCounter, 1] = valueOne
      secondValue, lineEnd = endOfLine.partition('\n')[::2]
      if (secondValue == ''):
        print "ERROR: Two values are required per line in the file!"
        return False
      valueTwo = float(secondValue)
      doseTable[rowCounter, 0] = secondValue
      # print('PDD row ' + rowCounter + ': ' + firstValue + ', ' + secondValue) # For testing
      rowCounter += 1

    print("Pdd data successfully loaded from file '" + fileName + "'")
    self.pddDataArray = doseTable
    return True

  # ---------------------------------------------------------------------------
  def getMeanOpticalDensityOfCentralCylinder(self, calibrationVolumeNodeID, centralRadiusMm):
    # Format of output array: the following values are provided for each slice:
    #   depth (cm), mean optical density on the slice at depth, std.dev. of optical density
    qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))

    calibrationVolume = slicer.util.getNode(calibrationVolumeNodeID)
    calibrationVolumeImageData = calibrationVolume.GetImageData()
    
    # Get image properties needed for the calculation
    calibrationVolumeSliceThicknessCm = calibrationVolume.GetSpacing()[2] / 10.0
    if calibrationVolume.GetSpacing()[0] != calibrationVolume.GetSpacing()[1]:
      print('WARNING! Image data X and Y spacing differ! This is not supported, the mean optical density data may be skewed!')
    calibrationVolumeInPlaneSpacing = calibrationVolume.GetSpacing()[0]

    centralRadiusPixel = int(numpy.ceil(centralRadiusMm / calibrationVolumeInPlaneSpacing))
    if centralRadiusPixel != centralRadiusMm / calibrationVolumeInPlaneSpacing:
      print('Central radius has been rounded up to {0} (original radius is {1}mm = {2}px)'.format(centralRadiusPixel, centralRadiusMm, centralRadiusMm / calibrationVolumeInPlaneSpacing))

    numberOfSlices = calibrationVolumeImageData.GetExtent()[5] - calibrationVolumeImageData.GetExtent()[4] + 1
    centerXCoordinate = (calibrationVolumeImageData.GetExtent()[1] - calibrationVolumeImageData.GetExtent()[0])/2
    centerYCoordinate = (calibrationVolumeImageData.GetExtent()[3] - calibrationVolumeImageData.GetExtent()[2])/2

    # Get image data in numpy array
    calibrationVolumeImageDataAsScalars = calibrationVolumeImageData.GetPointData().GetScalars()
    numpyImageDataArray = numpy_support.vtk_to_numpy(calibrationVolumeImageDataAsScalars)
    numpyImageDataArray = numpy.reshape(numpyImageDataArray, (calibrationVolumeImageData.GetExtent()[1]+1, calibrationVolumeImageData.GetExtent()[3]+1, calibrationVolumeImageData.GetExtent()[5]+1), 'F')
    
    opticalDensityOfCentralCylinderTable = numpy.zeros((numberOfSlices, 3))
    sliceNumber = 0
    z = calibrationVolumeImageData.GetExtent()[5]
    zMin = calibrationVolumeImageData.GetExtent()[4]
    while z  >= zMin:
      totalPixels = 0
      totalOpticalDensity = 0
      listOfOpticalDensities = []
      meanOpticalDensity = 0

      for y in xrange(centerYCoordinate - centralRadiusPixel, centerYCoordinate + centralRadiusPixel):
        for x in xrange(centerXCoordinate - centralRadiusPixel, centerXCoordinate + centralRadiusPixel):
          distanceOfX = abs(x - centerXCoordinate)
          distanceOfY = abs(y - centerYCoordinate)
          if ((distanceOfX + distanceOfY) <= centralRadiusPixel) or ((pow(distanceOfX, 2) + pow(distanceOfY, 2)) <= pow(centralRadiusPixel, 2)):
            currentOpticalDensity = numpyImageDataArray[x, y, z]
            listOfOpticalDensities.append(currentOpticalDensity)
            totalOpticalDensity = totalOpticalDensity + currentOpticalDensity
            totalPixels+=1
      
      meanOpticalDensity = totalOpticalDensity / totalPixels
      standardDeviationOpticalDensity	= 0
      for currentOpticalDensityValue in xrange(0, totalPixels):
        standardDeviationOpticalDensity += pow((listOfOpticalDensities[currentOpticalDensityValue] - meanOpticalDensity), 2)
      standardDeviationOpticalDensity = sqrt(standardDeviationOpticalDensity / totalPixels)
      opticalDensityOfCentralCylinderTable[sliceNumber, 0] = sliceNumber * calibrationVolumeSliceThicknessCm
      opticalDensityOfCentralCylinderTable[sliceNumber, 1] = meanOpticalDensity
      opticalDensityOfCentralCylinderTable[sliceNumber, 2] = standardDeviationOpticalDensity
      # print('Slice (cm): ' + repr(sliceNumber*calibrationVolumeSliceThicknessCm))
      # print('  Mean: ' + repr(meanOpticalDensity) + '  StdDev: ' + repr(standardDeviationOpticalDensity))
      sliceNumber += 1
      z -= 1

    qt.QApplication.restoreOverrideCursor()
    print('CALIBRATION data has been successfully parsed with averaging radius {0}mm ({1}px)'.format(centralRadiusMm, centralRadiusPixel))
    self.calibrationDataArray = opticalDensityOfCentralCylinderTable
    return True

  # ---------------------------------------------------------------------------
  def alignPddToCalibration(self):
    qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))
    error = -1.0

    # Check the input arrays
    if self.pddDataArray.size == 0 or self.calibrationDataArray.size == 0:
      print('ERROR: Pdd or calibration data is empty!')
      return error

    # Discard values of 0 from both ends of the data (it is considered invalid)
    self.calibrationDataCleanedArray = self.calibrationDataArray
    calibrationCleanedNumberOfRows = self.calibrationDataCleanedArray.shape[0]
    while self.calibrationDataCleanedArray[0,1] == 0:
      self.calibrationDataCleanedArray = numpy.delete(self.calibrationDataCleanedArray, 0, 0)
    calibrationCleanedNumberOfRows = self.calibrationDataCleanedArray.shape[0]
    while self.calibrationDataCleanedArray[calibrationCleanedNumberOfRows-1,1] == 0:
      self.calibrationDataCleanedArray = numpy.delete(self.calibrationDataCleanedArray, calibrationCleanedNumberOfRows-1, 0)
      calibrationCleanedNumberOfRows = self.calibrationDataCleanedArray.shape[0]

    # Remove outliers from calibration array
    self.calibrationDataCleanedArray = self.removeOutliersFromArray(self.calibrationDataCleanedArray, 5, 10, 0.0075)

    # Do initial scaling of the calibration array based on the maximum values
    maxPdd = self.findMaxValueInArray(self.pddDataArray)
    maxCalibration = self.findMaxValueInArray(self.calibrationDataCleanedArray)
    initialScaling = maxPdd / maxCalibration
    calibrationCleanedNumberOfRows = self.calibrationDataCleanedArray.shape[0]
    self.calibrationDataPreprocessedArray = numpy.zeros(self.calibrationDataCleanedArray.shape)
    for calibrationRowIndex in xrange(0, calibrationCleanedNumberOfRows):
      self.calibrationDataPreprocessedArray[calibrationRowIndex, 0] = self.calibrationDataCleanedArray[calibrationRowIndex, 0]
      self.calibrationDataPreprocessedArray[calibrationRowIndex, 1] = self.calibrationDataCleanedArray[calibrationRowIndex, 1] * initialScaling
    # print('Initial scaling was performed with scaling factor {0:.4f}'.format(initialScaling))

    # Create the working structures
    self.minimizer = vtk.vtkAmoebaMinimizer()
    self.minimizer.SetFunction(curveAlignmentCalibrationFunction)
    self.minimizer.SetParameterValue("xTrans",0)
    self.minimizer.SetParameterScale("xTrans",5)
    self.minimizer.SetParameterValue("yScale",1)
    self.minimizer.SetParameterScale("yScale",0.1)
    self.minimizer.SetMaxIterations(20)

    self.minimizer.Minimize()
    error = self.minimizer.GetFunctionValue()
    xTrans = self.minimizer.GetParameterValue("xTrans")
    yScale = self.minimizer.GetParameterValue("yScale")

    # Create aligned array
    self.calibrationDataAlignedArray = numpy.zeros([self.pddDataArray.shape[0], 2])
    interpolator = vtk.vtkPiecewiseFunction()
    self.populateInterpolatorForParameters(interpolator, xTrans, yScale)
    range = interpolator.GetRange()
    sumSquaredDifference = 0.0
    calibrationAlignedRowIndex = -1
    pddNumberOfRows = self.pddDataArray.shape[0]
    for pddRowIndex in xrange(0, pddNumberOfRows):
      pddCurrentDepth = self.pddDataArray[pddRowIndex, 0]
      if pddCurrentDepth > range[0] and pddCurrentDepth < range[1]:
        calibrationAlignedRowIndex += 1
        self.calibrationDataAlignedArray[calibrationAlignedRowIndex, 0] = pddCurrentDepth
        self.calibrationDataAlignedArray[calibrationAlignedRowIndex, 1] = interpolator.GetValue(pddCurrentDepth)
      else:
        # If the Pdd depth value is out of range then delete the last row (it will never be set, but we need to remove the zeros from the end)
        self.calibrationDataAlignedArray = numpy.delete(self.calibrationDataAlignedArray, self.calibrationDataAlignedArray.shape[0]-1, 0)

    qt.QApplication.restoreOverrideCursor()
    print('CALIBRATION successfully aligned with PDD with error={0:.2f} and parameters xTrans={1:.2f}, yScale={2:.2f}'.format(error, xTrans, yScale))
    return error

  # ---------------------------------------------------------------------------
  def removeOutliersFromArray(self, arrayToClean, outlierThreshold, maxNumberOfOutlierIterations, minimumMeanDifferenceInFractionOfMaxValueThreshold):
    # Removes outliers starting from the two ends of a function stored in an array
    # The input array has to have two columns, the first column containing the X values, the second the Y values
    # Parameters:
    #   outlierThreshold: Multiplier of mean of differences. If a value is more than this much different
    #     to its neighbor than it is an outlier
    #   minimumMeanDifferenceInFractionOfMaxValueThreshold: The array is considered not to contain outliers
    #     if the mean differences are less than the maximum value multiplied by this value
    numberOfFoundOutliers = -1
    numberOfIterations = 0

    # Compute average difference between two adjacent points. Go from both ends of the curve,
    # and throw away points that have a difference bigger than the computed average multiplied by N.
    # Do this until no points are thrown away in an iteration OR there are no points left (error)
    # OR the average difference is small enough
    numberOfRows = arrayToClean.shape[0]
    while numberOfIterations < maxNumberOfOutlierIterations and numberOfFoundOutliers != 0 and numberOfRows > 0:
      maxValue = self.findMaxValueInArray(arrayToClean)
      meanDifference = self.computeMeanDifferenceOfNeighborsForArray(arrayToClean)
      # print('Outlier removel iteration {0}: MeanDifference={1:.2f} (fraction of max value: {2:.4f})'.format(numberOfIterations, meanDifference, meanDifference/maxValue))
      # print('  Difference at egdges: first={0:.2f}  last={1:.2f}'.format(abs(arrayToClean[0,1] - arrayToClean[1,1]), abs(arrayToClean[numberOfRows-1,1] - arrayToClean[numberOfRows-2,1])))
      if meanDifference < maxValue * minimumMeanDifferenceInFractionOfMaxValueThreshold:
        # print('  MaxValue: {0:.2f} ({1:.4f}), finishing outlier search'.format(maxValue,maxValue*minimumMeanDifferenceInFractionOfMaxValueThreshold))
        break
      numberOfFoundOutliers = 0
      # Remove outliers from the beginning
      while abs(arrayToClean[0,1] - arrayToClean[1,1]) > meanDifference * outlierThreshold:
        # print('  Deleted first: {0:.2f},{0:.2f}  difference={0:.2f}'.format(arrayToClean[0,0], arrayToClean[0,1], abs(arrayToClean[0,1] - arrayToClean[1,1])))
        arrayToClean = numpy.delete(arrayToClean, 0, 0)
        numberOfFoundOutliers += 1
      # Remove outliers from the end        
      numberOfRows = arrayToClean.shape[0]
      while abs(arrayToClean[numberOfRows-1,1] - arrayToClean[numberOfRows-2,1]) > meanDifference * outlierThreshold:
        # print('  Deleted last: {0:.2f},{0:.2f}  difference={0:.2f}'.format(arrayToClean[numberOfRows-1,0], arrayToClean[numberOfRows-1,1], abs(arrayToClean[numberOfRows-1,1] - arrayToClean[numberOfRows-2,1])))
        arrayToClean = numpy.delete(arrayToClean, numberOfRows-1, 0)
        numberOfRows = arrayToClean.shape[0]
        numberOfFoundOutliers += 1
      numberOfRows = arrayToClean.shape[0]
      numberOfIterations += 1

    return arrayToClean

  # ---------------------------------------------------------------------------
  def computeMeanDifferenceOfNeighborsForArray(self, array):
    numberOfValues = array.shape[0]
    sumDifferences = 0
    for index in xrange(0, numberOfValues-1):
      sumDifferences += abs(array[index, 1] - array[index+1, 1])
    return sumDifferences / (numberOfValues-1)

  # ---------------------------------------------------------------------------
  def findMaxValueInArray(self, array):
    numberOfValues = array.shape[0]
    maximumValue = -1
    for index in xrange(0, numberOfValues):
      if array[index, 1] > maximumValue:
        maximumValue = array[index, 1]
    return maximumValue

  # ---------------------------------------------------------------------------
  def populateInterpolatorForParameters(self, interpolator, xTrans, yScale):
    calibrationNumberOfRows = self.calibrationDataPreprocessedArray.shape[0]
    for calibrationRowIndex in xrange(0, calibrationNumberOfRows):
      xTranslated = self.calibrationDataPreprocessedArray[calibrationRowIndex, 0] + xTrans
      yScaled = self.calibrationDataPreprocessedArray[calibrationRowIndex, 1] * yScale
      interpolator.AddPoint(xTranslated, yScaled)

  # ---------------------------------------------------------------------------
  def doseGenerationForMeasuredData(self, rdf, monitorUnits):
    self.calculatedDose = numpy.zeros(self.pddDataArray.shape)
    pddNumberOfRows = self.pddDataArray.shape[0]
    for pddRowIndex in xrange(0, pddNumberOfRows):
      self.calculatedDose[pddRowIndex, 0] = self.pddDataArray[pddRowIndex, 0]
      self.calculatedDose[pddRowIndex, 1] = self.pddDataArray[pddRowIndex, 1] * rdf * monitorUnits / 10000.0

  # ---------------------------------------------------------------------------
  def createOpticalDensityVsDoseFunction(self):
    # Create interpolator for aligned calibration function to allow getting the values for the
    # depths present in the calculated dose function
    interpolator = vtk.vtkPiecewiseFunction()
    calibrationAlignedNumberOfRows = self.calibrationDataAlignedArray.shape[0]
    for calibrationRowIndex in xrange(0, calibrationAlignedNumberOfRows):
      currendDose = self.calibrationDataAlignedArray[calibrationRowIndex, 0]
      currentOpticalDensity = self.calibrationDataAlignedArray[calibrationRowIndex, 1]
      interpolator.AddPoint(currendDose, currentOpticalDensity)

    # Get the optical density and the dose values from the aligned calibration function and the calculated dose
    self.opticalDensityVsDoseFunction = numpy.zeros(self.calculatedDose.shape)
    doseNumberOfRows = self.calculatedDose.shape[0]
    for doseRowIndex in xrange(0, doseNumberOfRows):
      # Reverse the function so that smallest dose comes first (which decreases with depth)
      currentDepth = self.calculatedDose[doseRowIndex, 0]
      self.opticalDensityVsDoseFunction[doseNumberOfRows-doseRowIndex-1, 0] = interpolator.GetValue(currentDepth)
      self.opticalDensityVsDoseFunction[doseNumberOfRows-doseRowIndex-1, 1] = self.calculatedDose[doseRowIndex, 1]

    # Make sure it is a function - remove points where the optical density (the X axis values) does not increase
    while True:
      pointsToDelete = []
      numberOfRows = self.opticalDensityVsDoseFunction.shape[0]
      for rowIndex in xrange(0, numberOfRows-1):
        if self.opticalDensityVsDoseFunction[rowIndex, 0] >= self.opticalDensityVsDoseFunction[rowIndex+1, 0]:
          pointsToDelete.append(rowIndex)
          # print('n={0:3} P(n)={1:6.2f} <= P(n+1)={2:6.2f}'.format(rowIndex,self.opticalDensityVsDoseFunction[rowIndex, 0],self.opticalDensityVsDoseFunction[rowIndex+1, 0]))
      if len(pointsToDelete) == 0:
        break
      pointsToDelete.reverse() # It's easier to delete the point with the biggest index first so the other indices remain valid
      for pointIndex in xrange(0, len(pointsToDelete)):
        self.opticalDensityVsDoseFunction = numpy.delete(self.opticalDensityVsDoseFunction, pointsToDelete[pointIndex], 0)

    # Remove outliers
    self.opticalDensityVsDoseFunction = self.removeOutliersFromArray(self.opticalDensityVsDoseFunction, 3, 1, 0.005)

  # ---------------------------------------------------------------------------
  def fitCurveToOpticalDensityVsDoseFunctionArray(self):
    # Fit polynomial on the cleaned OD vs dose function array
    odVsDoseNumberOfRows = self.opticalDensityVsDoseFunction.shape[0]
    opticalDensityData = numpy.zeros((odVsDoseNumberOfRows))
    doseData = numpy.zeros((odVsDoseNumberOfRows))
    for rowIndex in xrange(0, odVsDoseNumberOfRows):
      opticalDensityData[rowIndex] = self.opticalDensityVsDoseFunction[rowIndex, 0]
      doseData[rowIndex] = self.opticalDensityVsDoseFunction[rowIndex, 1]
    self.calibrationPolynomialCoeffitients = numpy.polyfit(opticalDensityData, doseData, self.orderOfFittedPolynomial)
    print('Coefficients of the fitted polynomial: ' + repr(self.calibrationPolynomialCoeffitients.tolist()))
    
    # Decrease max order if the coefficients are negligible (for faster calibration)
    epsilon = 0.00001
    while abs(self.calibrationPolynomialCoeffitients[0]) < epsilon:
      self.calibrationPolynomialCoeffitients = numpy.delete(self.calibrationPolynomialCoeffitients, 0, 0)
    print('Coefficients of the fitted polynomial after reduction: ' + repr(self.calibrationPolynomialCoeffitients.tolist()))

  # ---------------------------------------------------------------------------
  def calibrate(self, measuredVolumeID):
    qt.QApplication.setOverrideCursor(qt.QCursor(qt.Qt.BusyCursor))
    import time
    start = time.time()

    measuredVolume = slicer.util.getNode(measuredVolumeID)
    coefficients = numpy_support.numpy_to_vtk(self.calibrationPolynomialCoeffitients)
    
    import vtkSlicerGelDosimetryAnalysisAlgoModuleLogic
    if slicer.modules.geldosimetryanalysisalgo.logic().ApplyPolynomialFunctionOnVolume(measuredVolume, coefficients) == False:
      print('ERROR: Calibration failed!')
      return False

    end = time.time()
    qt.QApplication.restoreOverrideCursor()
    print('Calibration of MEASURED volume is successful (time: {0})'.format(end - start))
    return True

  # ---------------------------------------------------------------------------
  # Utility functions
  # ---------------------------------------------------------------------------
  def delayDisplay(self,message,msec=1000):
    """This utility method displays a small dialog and waits.
    This does two things: 1) it lets the event loop catch up
    to the state of the test so that rendering and widget updates
    have all taken place before the test continues and 2) it
    shows the user/developer/tester the state of the test
    so that we'll know when it breaks.
    """
    print(message)
    self.info = qt.QDialog()
    self.infoLayout = qt.QVBoxLayout()
    self.info.setLayout(self.infoLayout)
    self.label = qt.QLabel(message,self.info)
    self.infoLayout.addWidget(self.label)
    qt.QTimer.singleShot(msec, self.info.close)
    self.info.exec_()

#
# Function to minimize for the calibration curve alignment
#
def curveAlignmentCalibrationFunction():
  # Get logic instance
  global gelDosimetryLogicInstanceGlobal
  logic = gelDosimetryLogicInstanceGlobal

  # Transform experimental calibration curve with the current values provided by the minimizer and
  # create piecewise function from the transformed calibration curve to be able to compare with the Pdd
  xTrans = logic.minimizer.GetParameterValue("xTrans")
  yScale = logic.minimizer.GetParameterValue("yScale")
  interpolator = vtk.vtkPiecewiseFunction()
  logic.populateInterpolatorForParameters(interpolator, xTrans, yScale)
  interpolatorRange = interpolator.GetRange()
  # Compute similarity between the Pdd and the transformed calibration curve
  pddNumberOfRows = logic.pddDataArray.shape[0]
  sumSquaredDifference = 0.0
  for pddRowIndex in xrange(0, pddNumberOfRows):
    pddCurrentDepth = logic.pddDataArray[pddRowIndex, 0]
    pddCurrentDose = logic.pddDataArray[pddRowIndex, 1]
    difference = pddCurrentDose - interpolator.GetValue(pddCurrentDepth)
    if pddCurrentDepth < interpolatorRange[0] or pddCurrentDepth > interpolatorRange[1]:
      pass # Don't count the parts outside the range of the actual transformed calibration curve
    else:
      sumSquaredDifference += difference ** 2

  # print('Iteration: {0:2}  xTrans: {1:6.2f}  yScale: {2:6.2f}  error: {3:.2f}'.format(logic.minimizer.GetIterations(), xTrans, yScale, sumSquaredDifference))
  logic.minimizer.SetFunctionValue(sumSquaredDifference)

# Global variable holding the logic instance for the calibration curve minimizer function
gelDosimetryLogicInstanceGlobal = None

# Notes:
# Code snippet to reload logic
# GelDosimetryAnalysisLogic = reload(GelDosimetryAnalysisLogic)
