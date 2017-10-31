/*==============================================================================

  Program: 3D Slicer

  Portions (c) Copyright Brigham and Women's Hospital (BWH) All Rights Reserved.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

==============================================================================*/

// GelDosimetryAnalysisAlgo Logic includes
#include "vtkSlicerGelDosimetryAnalysisAlgoModuleLogic.h"
#include "vtkApplyPolynomialFunctionOnVolume.h"

// VTK includes
#include <vtkSmartPointer.h>
#include <vtkImageData.h>
#include <vtkDoubleArray.h>
#include <vtkObjectFactory.h>

// MRML includes
#include <vtkMRMLScalarVolumeNode.h>

//----------------------------------------------------------------------------
vtkStandardNewMacro(vtkSlicerGelDosimetryAnalysisAlgoModuleLogic);

//----------------------------------------------------------------------------
vtkSlicerGelDosimetryAnalysisAlgoModuleLogic::vtkSlicerGelDosimetryAnalysisAlgoModuleLogic()
{
}

//----------------------------------------------------------------------------
vtkSlicerGelDosimetryAnalysisAlgoModuleLogic::~vtkSlicerGelDosimetryAnalysisAlgoModuleLogic()
{
}

//---------------------------------------------------------------------------
void vtkSlicerGelDosimetryAnalysisAlgoModuleLogic::UpdateFromMRMLScene()
{
  if (!this->GetMRMLScene())
  {
    return;
  }
}

//---------------------------------------------------------------------------
bool vtkSlicerGelDosimetryAnalysisAlgoModuleLogic::ApplyPolynomialFunctionOnVolume(vtkMRMLScalarVolumeNode* volumeNode, vtkDoubleArray* polynomialCoefficients)
{
  if (!volumeNode || !volumeNode->GetImageData())
  {
    vtkErrorMacro("ApplyPolynomialFunctionOnVolume: Invalid input volume!");
    return false;
  }
  if (!polynomialCoefficients || polynomialCoefficients->GetNumberOfTuples() == 0)
  {
    vtkErrorMacro("ApplyPolynomialFunctionOnVolume: Invalid input polynomial coefficients!");
    return false;
  }

  vtkSmartPointer<vtkApplyPolynomialFunctionOnVolume> calibrator = vtkSmartPointer<vtkApplyPolynomialFunctionOnVolume>::New();
  calibrator->SetInputData(volumeNode->GetImageData());
  calibrator->SetPolynomialCoefficients(polynomialCoefficients);
  calibrator->Update();

  vtkSmartPointer<vtkImageData> newImageData = vtkSmartPointer<vtkImageData>::New();
  newImageData->DeepCopy(calibrator->GetOutput());

  volumeNode->SetAndObserveImageData(newImageData);
  volumeNode->Modified();

  return true;
}
