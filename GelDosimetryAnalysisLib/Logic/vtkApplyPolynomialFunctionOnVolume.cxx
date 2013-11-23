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

#include "vtkApplyPolynomialFunctionOnVolume.h"

// VTK includes
#include <vtkObjectFactory.h>
#include <vtkSmartPointer.h>
#include <vtkImageData.h>
#include "vtkImageProgressIterator.h"

//----------------------------------------------------------------------------
vtkStandardNewMacro(vtkApplyPolynomialFunctionOnVolume);

//----------------------------------------------------------------------------
vtkApplyPolynomialFunctionOnVolume::vtkApplyPolynomialFunctionOnVolume()
{
  this->PolynomialCoefficients = NULL;
}

//----------------------------------------------------------------------------
vtkApplyPolynomialFunctionOnVolume::~vtkApplyPolynomialFunctionOnVolume()
{
  this->SetPolynomialCoefficients(NULL);
}

//----------------------------------------------------------------------------
void vtkApplyPolynomialFunctionOnVolume::PrintSelf(ostream& os, vtkIndent indent)
{
  this->Superclass::PrintSelf(os,indent);

  os << indent << "PolynomialCoefficients: " << this->GetPolynomialCoefficients() << "\n";
}

//----------------------------------------------------------------------------
template <class T>
void vtkApplyPolynomialFunctionOnVolumeExecute1(vtkApplyPolynomialFunctionOnVolume *self,
                               vtkImageData *inData,
                               vtkImageData *outData,
                               int outExt[6], int id, T *)
{
  switch (outData->GetScalarType())
  {
    vtkTemplateMacro(
      vtkApplyPolynomialFunctionOnVolumeExecute(self, inData,
      outData, outExt, id, 
      static_cast<T *>(0), 
      static_cast<VTK_TT *>(0)));
  default:
    vtkGenericWarningMacro("Execute: Unknown input ScalarType");
    return;
  }
}

//----------------------------------------------------------------------------
// This method is passed a input and output data, and executes the filter
// algorithm to fill the output from the input.
// It just executes a switch statement to call the correct function for
// the datas data types.
void vtkApplyPolynomialFunctionOnVolume::ThreadedExecute(vtkImageData *inData, 
                                          vtkImageData *outData,
                                          int outExt[6], int id)
{
  // Check Single component
  int numberOfScalarComponents;
  numberOfScalarComponents = inData->GetNumberOfScalarComponents();
  if (numberOfScalarComponents != 1)
  {
    vtkErrorMacro("ThreadedExecute: Input has " << numberOfScalarComponents << " instead of 1 scalar component.");
    return;
  }

  // Validate input coefficients
  if (this->PolynomialCoefficients == NULL || this->PolynomialCoefficients->GetNumberOfTuples() < 1)
  {
    vtkErrorMacro("ThreadedExecute Invalid input polynomial coefficiets");
    return;
  }

  switch (inData->GetScalarType())
  {
    vtkTemplateMacro(
      vtkApplyPolynomialFunctionOnVolumeExecute1(this, 
      inData, 
      outData, 
      outExt, 
      id,
      static_cast<VTK_TT *>(0)));
    default:
      vtkErrorMacro("ThreadedExecute: Unknown input ScalarType");
      return;
  }
}

//----------------------------------------------------------------------------
// This templated function executes the filter for any type of data.
template <class IT, class OT>
void vtkApplyPolynomialFunctionOnVolumeExecute(vtkApplyPolynomialFunctionOnVolume *self,
                              vtkImageData *inData,
                              vtkImageData *outData, 
                              int outExt[6], int id, IT *, OT *)
{
  vtkImageIterator<IT> inIt(inData, outExt);
  vtkImageProgressIterator<OT> outIt(outData, outExt, self, id);
  double inValue = 0;

  // Convert input coefficients into vector for faster access
  std::vector<double> coefficients;
  coefficients.resize(self->GetPolynomialCoefficients()->GetNumberOfTuples());
  for (int coeffIndex = 0; coeffIndex < self->GetPolynomialCoefficients()->GetNumberOfTuples(); ++coeffIndex)
  {
    coefficients[coeffIndex] = self->GetPolynomialCoefficients()->GetValue(coeffIndex);
  }

  // Loop through output pixels
  while (!outIt.IsAtEnd())
  {
    IT* inSI = inIt.BeginSpan();
    OT* outSI = outIt.BeginSpan();
    OT* outSIEnd = outIt.EndSpan();
    while (outSI != outSIEnd)
    {
      // Apply polynomial on voxel
      inValue = (double)(*inSI);

      int maxOrder = coefficients.size() - 1;
      OT calibratedValue = 0;
      for (int order=0; order < maxOrder+1; ++order)
      {
        calibratedValue += coefficients[order] * pow(inValue, maxOrder-order);
        *outSI = static_cast<OT>(calibratedValue);
      }
      ++inSI;
      ++outSI;
    }
    inIt.NextSpan();
    outIt.NextSpan();
  }
}
