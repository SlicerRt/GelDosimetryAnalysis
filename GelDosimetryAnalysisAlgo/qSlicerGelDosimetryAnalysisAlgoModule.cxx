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

// Qt includes
#include <QtPlugin>

// GelDosimetryAnalysisAlgo includes
#include "qSlicerGelDosimetryAnalysisAlgoModule.h"
#include "qSlicerGelDosimetryAnalysisAlgoModuleWidget.h"

// GelDosimetryAnalysisAlgo logic includes
#include "vtkSlicerGelDosimetryAnalysisAlgoModuleLogic.h"

//-----------------------------------------------------------------------------
Q_EXPORT_PLUGIN2(qSlicerGelDosimetryAnalysisAlgoModule, qSlicerGelDosimetryAnalysisAlgoModule);

//-----------------------------------------------------------------------------
/// \ingroup Slicer_QtModules_ExtensionTemplate
class qSlicerGelDosimetryAnalysisAlgoModulePrivate
{
public:
  qSlicerGelDosimetryAnalysisAlgoModulePrivate();
};

//-----------------------------------------------------------------------------
// qSlicerGelDosimetryAnalysisAlgoModulePrivate methods

//-----------------------------------------------------------------------------
qSlicerGelDosimetryAnalysisAlgoModulePrivate
::qSlicerGelDosimetryAnalysisAlgoModulePrivate()
{
}

//-----------------------------------------------------------------------------
// qSlicerGelDosimetryAnalysisAlgoModule methods

//-----------------------------------------------------------------------------
qSlicerGelDosimetryAnalysisAlgoModule
::qSlicerGelDosimetryAnalysisAlgoModule(QObject* _parent)
  : Superclass(_parent)
  , d_ptr(new qSlicerGelDosimetryAnalysisAlgoModulePrivate)
{
}

//-----------------------------------------------------------------------------
qSlicerGelDosimetryAnalysisAlgoModule::~qSlicerGelDosimetryAnalysisAlgoModule()
{
}

//-----------------------------------------------------------------------------
QString qSlicerGelDosimetryAnalysisAlgoModule::helpText()const
{
  return "This hidden module provides C++ algorithms for the Gel Dosimetry Analysis slicelet";
}

//-----------------------------------------------------------------------------
QString qSlicerGelDosimetryAnalysisAlgoModule::acknowledgementText()const
{
  return "This work is part of SparKit project, funded by Cancer Care Ontario (CCO)'s ACRU program and Ontario Consortium for Adaptive Interventions in Radiation Oncology (OCAIRO).";
}

//-----------------------------------------------------------------------------
QStringList qSlicerGelDosimetryAnalysisAlgoModule::contributors()const
{
  QStringList moduleContributors;
  moduleContributors << QString("Csaba Pinter (Queen's)");
  return moduleContributors;
}

//-----------------------------------------------------------------------------
QStringList qSlicerGelDosimetryAnalysisAlgoModule::categories() const
{
  return QStringList() << "Slicelets";
}

//-----------------------------------------------------------------------------
QStringList qSlicerGelDosimetryAnalysisAlgoModule::dependencies() const
{
  return QStringList();
}

//-----------------------------------------------------------------------------
void qSlicerGelDosimetryAnalysisAlgoModule::setup()
{
  this->Superclass::setup();
}

//-----------------------------------------------------------------------------
qSlicerAbstractModuleRepresentation * qSlicerGelDosimetryAnalysisAlgoModule
::createWidgetRepresentation()
{
  return new qSlicerGelDosimetryAnalysisAlgoModuleWidget;
}

//-----------------------------------------------------------------------------
vtkMRMLAbstractLogic* qSlicerGelDosimetryAnalysisAlgoModule::createLogic()
{
  return vtkSlicerGelDosimetryAnalysisAlgoModuleLogic::New();
}
