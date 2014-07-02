/*==============================================================================

  Program: 3D Slicer

  Copyright (c) Kitware Inc.

  See COPYRIGHT.txt
  or http://www.slicer.org/copyright/copyright.txt for details.

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS,
  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
  See the License for the specific language governing permissions and
  limitations under the License.

  This file was originally developed by Csaba Pinter, PerkLab, Queen's University
  and was supported through the Applied Cancer Research Unit program of Cancer Care
  Ontario with funds provided by the Ontario Ministry of Health and Long-Term Care

==============================================================================*/

// .NAME vtkApplyPolynomialFunctionOnVolume - Applies polynomial function on image data
// .SECTION Description

#ifndef __vtkApplyPolynomialFunctionOnVolume_h
#define __vtkApplyPolynomialFunctionOnVolume_h

#include "vtkSlicerGelDosimetryAnalysisAlgoModuleLogicExport.h"

// VTK includes
#include <vtkSimpleImageToImageFilter.h>
#include <vtkDoubleArray.h>

class vtkImageData;

/// \ingroup GelDosimetryAnalysis
class VTK_SLICER_GELDOSIMETRYANALYSISALGO_MODULE_LOGIC_EXPORT vtkApplyPolynomialFunctionOnVolume : public vtkSimpleImageToImageFilter
{
public:
  static vtkApplyPolynomialFunctionOnVolume *New();
  vtkTypeMacro(vtkApplyPolynomialFunctionOnVolume, vtkSimpleImageToImageFilter);
  void PrintSelf(ostream& os, vtkIndent indent);

  /// Set polynomial coefficients
  vtkSetObjectMacro(PolynomialCoefficients, vtkDoubleArray);
  /// Get polynomial coefficients
  vtkGetObjectMacro(PolynomialCoefficients, vtkDoubleArray);

protected:
  /// Execute function applying the polynomial to the input image
  virtual void SimpleExecute(vtkImageData *inData, vtkImageData *outData);

protected:
  /// Coefficients of the polynomial to apply. They are expected to be in
  /// decreasing order, as in p(x) = p[0] * x**deg + ... + p[deg]
  vtkDoubleArray* PolynomialCoefficients;

protected:
  vtkApplyPolynomialFunctionOnVolume();
  virtual ~vtkApplyPolynomialFunctionOnVolume();

private:
  vtkApplyPolynomialFunctionOnVolume(const vtkApplyPolynomialFunctionOnVolume&); // Not implemented
  void operator=(const vtkApplyPolynomialFunctionOnVolume&);               // Not implemented
};

#endif 