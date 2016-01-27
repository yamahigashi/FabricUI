//
// Copyright (c) 2010-2016, Fabric Software Inc. All rights reserved.
//

#pragma once

#include "BaseViewItem.h"

class QComboBox;

class ComboBoxViewItem : public BaseViewItem
{
  Q_OBJECT

public:
  
  static BaseViewItem *CreateItem(
    QString const &name,
    QVariant const &value,
    ItemMetadata* metaData
    );
  static const int Priority;

  ComboBoxViewItem(QString const &name, QVariant const &v, ItemMetadata* metadata, bool isString );
  ~ComboBoxViewItem();

  virtual void metadataChanged( );

  virtual QWidget *getWidget() /*override*/;
  
  virtual void onModelValueChanged( QVariant const &value ) /*override*/;

  void deleteMe() { delete this; }

private:

  QComboBox* m_comboBox;
  bool m_isString;

private slots:
  void entrySelected(int index);
};
