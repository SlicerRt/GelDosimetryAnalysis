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

#ifndef __qSlicerGelDosimetryAnalysisAlgoModuleWidget_h
#define __qSlicerGelDosimetryAnalysisAlgoModuleWidget_h

// SlicerQt includes
#include "qSlicerAbstractModuleWidget.h"

#include "qSlicerGelDosimetryAnalysisAlgoModuleExport.h"

class qSlicerGelDosimetryAnalysisAlgoModuleWidgetPrivate;

/// \ingroup Slicer_QtModules_ExtensionTemplate
class Q_SLICER_GELDOSIMETRYANALYSISALGO_EXPORT qSlicerGelDosimetryAnalysisAlgoModuleWidget :
  public qSlicerAbstractModuleWidget
{
  Q_OBJECT

  public:
    typedef qSlicerAbstractModuleWidget Superclass;
    qSlicerGelDosimetryAnalysisAlgoModuleWidget(QWidget *parent=0);
    virtual ~qSlicerGelDosimetryAnalysisAlgoModuleWidget();

  public slots:

  protected:
    QScopedPointer<qSlicerGelDosimetryAnalysisAlgoModuleWidgetPrivate> d_ptr;
    virtual void setup();

  private:
    Q_DECLARE_PRIVATE(qSlicerGelDosimetryAnalysisAlgoModuleWidget);
    Q_DISABLE_COPY(qSlicerGelDosimetryAnalysisAlgoModuleWidget);
};

#endif
