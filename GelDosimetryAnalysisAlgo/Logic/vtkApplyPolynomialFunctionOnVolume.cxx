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
// The switch statement in Execute will call this method with
// the appropriate input type (IT). Note that this example assumes
// that the output data type is the same as the input data type.
// This is not always the case.
template <class IT>
void vtkApplyPolynomialFunctionOnVolumeExecute(vtkApplyPolynomialFunctionOnVolume *self,
                                               vtkImageData* input,
                                               vtkImageData* output,
                                               IT* inPtr, IT* outPtr)
{
  int dims[3];
  input->GetDimensions(dims);
  if (input->GetScalarType() != output->GetScalarType())
  {
    vtkGenericWarningMacro(<< "Execute: input ScalarType, " << input->GetScalarType()
      << ", must match out ScalarType " << output->GetScalarType());
    return;
  }

  int size = dims[0]*dims[1]*dims[2];

  double inValue = 0;

  // Convert input coefficients into vector for faster access
  std::vector<double> coefficients;
  coefficients.resize(self->GetPolynomialCoefficients()->GetNumberOfTuples());
  for (int coeffIndex = 0; coeffIndex < self->GetPolynomialCoefficients()->GetNumberOfTuples(); ++coeffIndex)
  {
    coefficients[coeffIndex] = self->GetPolynomialCoefficients()->GetValue(coeffIndex);
  }

  // Apply polynomial on volume voxels
  for(int i=0; i<size; i++)
  {
    inValue = inPtr[i];

    int maxOrder = coefficients.size() - 1;
    IT calibratedValue = 0;
    for (int order=0; order < maxOrder+1; ++order)
    {
      calibratedValue += coefficients[order] * pow(inValue, maxOrder-order);
    }
    outPtr[i] = calibratedValue;
  }
}

//----------------------------------------------------------------------------
// This method is passed a input and output data, and executes the filter
// algorithm to fill the output from the input.
// It just executes a switch statement to call the correct function for
// the datas data types.
void vtkApplyPolynomialFunctionOnVolume::SimpleExecute(vtkImageData *inData, vtkImageData *outData)
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

  void* inPtr = inData->GetScalarPointer();
  void* outPtr = outData->GetScalarPointer();

  switch(outData->GetScalarType())
  {
    // This is simply a #define for a big case list. It handles all
    // data types VTK supports.
    vtkTemplateMacro(
      vtkApplyPolynomialFunctionOnVolumeExecute(this,
      inData, outData,
      static_cast<VTK_TT *>(inPtr),
      static_cast<VTK_TT *>(outPtr)));
  default:
    vtkGenericWarningMacro("Execute: Unknown input ScalarType");
    return;
  }
}
