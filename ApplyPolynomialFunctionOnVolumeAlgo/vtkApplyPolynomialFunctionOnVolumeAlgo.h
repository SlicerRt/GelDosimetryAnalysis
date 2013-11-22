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

// .NAME vtkApplyPolynomialFunctionOnVolumeAlgo - Applies polynomial function on image data
// .SECTION Description


#ifndef __vtkApplyPolynomialFunctionOnVolumeAlgo_h
#define __vtkApplyPolynomialFunctionOnVolumeAlgo_h

// VTK includes
#include <vtkImageData.h>
#include <vtkDoubleArray.h>

/// \ingroup GelDosimetryAnalysis
class vtkApplyPolynomialFunctionOnVolumeAlgo : public vtkObject
{
public:

  static vtkApplyPolynomialFunctionOnVolumeAlgo *New();
  vtkTypeMacro(vtkApplyPolynomialFunctionOnVolumeAlgo, vtkObject );

  /// Run algorithm
  virtual void Update();

  /// Set input image data
  vtkSetObjectMacro(InputImageData, vtkImageData);
  /// Get input image data
  vtkGetObjectMacro(InputImageData, vtkImageData);

  /// Set polynomial coefficients
  vtkSetObjectMacro(PolynomialCoefficients, vtkDoubleArray);
  /// Get polynomial coefficients
  vtkGetObjectMacro(PolynomialCoefficients, vtkDoubleArray);

  /// Set output image data
  vtkGetObjectMacro(OutputImageData, vtkImageData);

protected:
  /// Set output image data
  vtkSetObjectMacro(OutputImageData, vtkImageData);

protected:
  vtkImageData* InputImageData;
  vtkImageData* OutputImageData;

  /// Coefficients of the polynomial to apply. They are expected to be in
  /// decreasing order, see p(x) = p[0] * x**deg + ... + p[deg]
  vtkDoubleArray* PolynomialCoefficients;

protected:
  vtkApplyPolynomialFunctionOnVolumeAlgo();
  virtual ~vtkApplyPolynomialFunctionOnVolumeAlgo();

private:
  vtkApplyPolynomialFunctionOnVolumeAlgo(const vtkApplyPolynomialFunctionOnVolumeAlgo&); // Not implemented
  void operator=(const vtkApplyPolynomialFunctionOnVolumeAlgo&);               // Not implemented
};

#endif 