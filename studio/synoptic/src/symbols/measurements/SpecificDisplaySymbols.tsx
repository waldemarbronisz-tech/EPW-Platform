import React from 'react';
import { MeasurementDisplaySymbol } from './MeasurementDisplaySymbol';
import type { SymbolProps } from '../SymbolRenderer';

export const VoltageDisplaySymbol: React.FC<SymbolProps> = (props) => {
  const customProps = {
    ...props,
    obj: {
      ...props.obj,
      text: props.obj.text || 'VOLTAGE',
      editor: {
        ...props.obj.editor,
        unit: props.obj.editor?.unit || 'V'
      }
    }
  };
  return <MeasurementDisplaySymbol {...customProps} />;
};

export const CurrentDisplaySymbol: React.FC<SymbolProps> = (props) => {
  const customProps = {
    ...props,
    obj: {
      ...props.obj,
      text: props.obj.text || 'CURRENT',
      editor: {
        ...props.obj.editor,
        unit: props.obj.editor?.unit || 'A'
      }
    }
  };
  return <MeasurementDisplaySymbol {...customProps} />;
};

export const TemperatureDisplaySymbol: React.FC<SymbolProps> = (props) => {
  const customProps = {
    ...props,
    obj: {
      ...props.obj,
      text: props.obj.text || 'TEMP',
      editor: {
        ...props.obj.editor,
        unit: props.obj.editor?.unit || '°C'
      }
    }
  };
  return <MeasurementDisplaySymbol {...customProps} />;
};
