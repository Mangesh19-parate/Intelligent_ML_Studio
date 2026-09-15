/// <reference types="vite/client" />

declare module 'react-plotly.js' {
  import * as React from 'react';
  interface PlotParams {
    data: any[];
    layout?: any;
    config?: any;
    frames?: any[];
    style?: React.CSSProperties;
    useResizeHandler?: boolean;
    className?: string;
    onInitialized?: (figure: any, graphDiv: HTMLElement) => void;
    onUpdate?: (figure: any, graphDiv: HTMLElement) => void;
    onPurge?: (figure: any, graphDiv: HTMLElement) => void;
    onError?: (err: Error) => void;
  }
  const Plot: React.ComponentType<PlotParams>;
  export default Plot;
}
