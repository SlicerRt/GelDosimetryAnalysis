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

#include "vtkApplyPolynomialFunctionOnVolumeAlgo.h"

// VTK includes
#include <vtkObjectFactory.h>
#include <vtkSmartPointer.h>

//----------------------------------------------------------------------------
vtkStandardNewMacro(vtkApplyPolynomialFunctionOnVolumeAlgo);

//----------------------------------------------------------------------------
vtkApplyPolynomialFunctionOnVolumeAlgo::vtkApplyPolynomialFunctionOnVolumeAlgo()
{
  this->InputImageData = NULL;
  this->PolynomialCoefficients = NULL;

  this->OutputImageData = NULL;
  vtkSmartPointer<vtkImageData> outputImageData = vtkSmartPointer<vtkImageData>::New();
  this->SetOutputImageData(outputImageData);
}

//----------------------------------------------------------------------------
vtkApplyPolynomialFunctionOnVolumeAlgo::~vtkApplyPolynomialFunctionOnVolumeAlgo()
{
  this->SetInputImageData(NULL);
  this->SetPolynomialCoefficients(NULL);
  this->SetOutputImageData(NULL);
}

//----------------------------------------------------------------------------
void vtkApplyPolynomialFunctionOnVolumeAlgo::Update()
{
  if (!this->InputImageData || !this->OutputImageData)
  {
    vtkErrorMacro("Update: Input image data and output image data have to be initialized!");
    return;
  }

  //this->OutputImageData->ShallowCopy(decimator->GetOutput());
} 