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

// .NAME vtkSlicerGelDosimetryAnalysisAlgoModuleLogic - slicer logic class for volumes manipulation
// .SECTION Description
// This class manages the logic associated with reading, saving,
// and changing propertied of the volumes

#ifndef __vtkSlicerGelDosimetryAnalysisAlgoModuleLogic_h
#define __vtkSlicerGelDosimetryAnalysisAlgoModuleLogic_h

// Slicer includes
#include "vtkSlicerModuleLogic.h"

// GelDosimetryAnalysisAlgo Module Logic
#include "vtkSlicerGelDosimetryAnalysisAlgoModuleLogicExport.h"

class vtkMRMLScalarVolumeNode;
class vtkDoubleArray;

class VTK_SLICER_GELDOSIMETRYANALYSISALGO_MODULE_LOGIC_EXPORT vtkSlicerGelDosimetryAnalysisAlgoModuleLogic : public vtkSlicerModuleLogic
{
public:
  /// Constructor
  static vtkSlicerGelDosimetryAnalysisAlgoModuleLogic* New();
  vtkTypeMacro(vtkSlicerGelDosimetryAnalysisAlgoModuleLogic, vtkSlicerModuleLogic);
  void PrintSelf(ostream& os, vtkIndent indent);

  /// Apply polynomial function on volume. The input volume's image data will be overwritten
  /// \return Success flag
  bool ApplyPolynomialFunctionOnVolume(vtkMRMLScalarVolumeNode* volumeNode, vtkDoubleArray* polynomialCoefficients);

protected:
  vtkSlicerGelDosimetryAnalysisAlgoModuleLogic();
  virtual ~vtkSlicerGelDosimetryAnalysisAlgoModuleLogic();

  virtual void SetMRMLSceneInternal(vtkMRMLScene* newScene);
  virtual void UpdateFromMRMLScene();
  
private:
  vtkSlicerGelDosimetryAnalysisAlgoModuleLogic(const vtkSlicerGelDosimetryAnalysisAlgoModuleLogic&); // Not implemented
  void operator=(const vtkSlicerGelDosimetryAnalysisAlgoModuleLogic&);            // Not implemented
};

#endif
