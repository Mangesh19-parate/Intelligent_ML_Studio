import React, { useState, useMemo } from 'react';
import Plot from 'react-plotly.js';
import {
  BarChart2,
  PieChart as PieIcon,
  ScatterChart,
  LineChart,
  Layers,
  Sparkles,
  Sliders,
  Filter,
  Grid,
  Info,
} from 'lucide-react';

export const InteractiveEDAStudio = ({ edaReport }) => {
  const [analysisType, setAnalysisType] = useState('UNIVARIATE'); // 'UNIVARIATE' | 'BIVARIATE' | 'MULTIVARIATE'

  // Univariate controls
  const [uniColumn, setUniColumn] = useState('');
  const [uniChartType, setUniChartType] = useState('HISTO'); // 'HISTO' | 'KDE' | 'BOX' | 'COUNT' | 'PIE'
  const [numBins, setNumBins] = useState(25);

  // Bivariate controls
  const [bivX, setBivX] = useState('');
  const [bivY, setBivY] = useState('');
  const [bivChartType, setBivChartType] = useState('SCATTER'); // 'SCATTER' | 'LINE' | 'BAR' | 'BOX' | 'HEATMAP'
  const [colorHue, setColorHue] = useState('');

  // Multivariate controls
  const [multiColumns, setMultiColumns] = useState([]);
  const [multiHue, setMultiHue] = useState('');

  const sampleData = useMemo(() => edaReport?.sample_records || [], [edaReport]);
  const columnsMeta = useMemo(() => edaReport?.columns_metadata || [], [edaReport]);

  const numericCols = useMemo(() => columnsMeta.filter((c) => c.is_numeric).map((c) => c.name), [columnsMeta]);
  const categoricalCols = useMemo(() => columnsMeta.filter((c) => !c.is_numeric).map((c) => c.name), [columnsMeta]);

  // Set default selected columns if empty
  React.useEffect(() => {
    if (columnsMeta.length > 0) {
      if (!uniColumn) {
        setUniColumn(numericCols[0] || columnsMeta[0].name);
      }
      if (!bivX) {
        setBivX(numericCols[0] || columnsMeta[0].name);
      }
      if (!bivY) {
        setBivY(numericCols[1] || numericCols[0] || columnsMeta[0].name);
      }
      if (multiColumns.length === 0 && numericCols.length >= 2) {
        setMultiColumns(numericCols.slice(0, 3));
      }
    }
  }, [columnsMeta, numericCols]);

  const activeUniMeta = columnsMeta.find((c) => c.name === uniColumn);
  const isUniNumeric = activeUniMeta ? activeUniMeta.is_numeric : true;

  // Auto-switch univariate chart type based on column type
  React.useEffect(() => {
    if (activeUniMeta) {
      if (activeUniMeta.is_numeric && (uniChartType === 'COUNT' || uniChartType === 'PIE')) {
        setUniChartType('HISTO');
      } else if (!activeUniMeta.is_numeric && (uniChartType === 'HISTO' || uniChartType === 'KDE' || uniChartType === 'BOX')) {
        setUniChartType('COUNT');
      }
    }
  }, [uniColumn]);

  // Generate Univariate Plot Data
  const renderUnivariatePlot = () => {
    if (!uniColumn || sampleData.length === 0) {
      return <div className="text-center py-12 text-xs text-[var(--color-text-muted)]">No data available to plot.</div>;
    }

    const rawValues = sampleData.map((d) => d[uniColumn]).filter((v) => v !== null && v !== undefined);

    let plotData = [];
    let layout = {
      title: `${uniColumn} — ${uniChartType} Analysis`,
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: '#94a3b8', size: 11 },
      margin: { l: 50, r: 30, t: 50, b: 50 },
      autosize: true,
      colorway: ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899'],
    };

    if (isUniNumeric) {
      const numValues = rawValues.map(Number).filter((v) => !isNaN(v));
      if (uniChartType === 'HISTO') {
        plotData = [
          {
            x: numValues,
            type: 'histogram',
            nbinsx: numBins,
            marker: { color: '#3b82f6', line: { color: '#1e40af', width: 1 } },
            opacity: 0.8,
            name: uniColumn,
          },
        ];
        layout.xaxis = { title: uniColumn, gridcolor: '#334155' };
        layout.yaxis = { title: 'Frequency', gridcolor: '#334155' };
      } else if (uniChartType === 'KDE') {
        plotData = [
          {
            x: numValues,
            type: 'histogram',
            histnorm: 'probability density',
            nbinsx: numBins,
            marker: { color: '#60a5fa', opacity: 0.4 },
            name: 'Density Histogram',
          },
        ];
        layout.xaxis = { title: uniColumn, gridcolor: '#334155' };
        layout.yaxis = { title: 'Density', gridcolor: '#334155' };
      } else if (uniChartType === 'BOX') {
        plotData = [
          {
            y: numValues,
            type: 'box',
            name: uniColumn,
            boxpoints: 'outliers',
            marker: { color: '#8b5cf6' },
          },
        ];
        layout.yaxis = { title: uniColumn, gridcolor: '#334155' };
      }
    } else {
      // Categorical values
      const counts = {};
      rawValues.forEach((v) => {
        const key = String(v);
        counts[key] = (counts[key] || 0) + 1;
      });
      const labels = Object.keys(counts);
      const values = Object.values(counts);

      if (uniChartType === 'PIE') {
        plotData = [
          {
            labels,
            values,
            type: 'pie',
            hole: 0.4,
            textinfo: 'label+percent',
            marker: { colors: ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ec4899', '#06b6d4', '#f97316'] },
          },
        ];
      } else {
        // COUNT
        plotData = [
          {
            x: labels,
            y: values,
            type: 'bar',
            marker: { color: '#8b5cf6' },
            name: uniColumn,
          },
        ];
        layout.xaxis = { title: uniColumn, gridcolor: '#334155' };
        layout.yaxis = { title: 'Count', gridcolor: '#334155' };
      }
    }

    return (
      <div className="w-full h-[400px]">
        <Plot data={plotData} layout={layout} useResizeHandler style={{ width: '100%', height: '100%' }} config={{ responsive: true }} />
      </div>
    );
  };

  // Generate Bivariate Plot Data
  const renderBivariatePlot = () => {
    if (!bivX || !bivY || sampleData.length === 0) {
      return <div className="text-center py-12 text-xs text-[var(--color-text-muted)]">Select variables to plot.</div>;
    }

    const isXNum = numericCols.includes(bivX);
    const isYNum = numericCols.includes(bivY);

    let plotData = [];
    let layout = {
      title: `${bivY} vs ${bivX}`,
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: '#94a3b8', size: 11 },
      margin: { l: 60, r: 30, t: 50, b: 60 },
      autosize: true,
      xaxis: { title: bivX, gridcolor: '#334155' },
      yaxis: { title: bivY, gridcolor: '#334155' },
    };

    if (isXNum && isYNum) {
      // Numerical - Numerical (Scatter / Line)
      if (bivChartType === 'LINE') {
        const sorted = [...sampleData].sort((a, b) => (Number(a[bivX]) || 0) - (Number(b[bivX]) || 0));
        plotData = [
          {
            x: sorted.map((d) => d[bivX]),
            y: sorted.map((d) => d[bivY]),
            type: 'scatter',
            mode: 'lines+markers',
            line: { color: '#3b82f6', width: 2 },
            marker: { size: 5 },
            name: `${bivY} vs ${bivX}`,
          },
        ];
      } else {
        // SCATTER
        if (colorHue && colorHue !== 'NONE') {
          // Group by hue
          const groups = {};
          sampleData.forEach((d) => {
            const h = String(d[colorHue] ?? 'Unknown');
            if (!groups[h]) groups[h] = { x: [], y: [] };
            groups[h].x.push(d[bivX]);
            groups[h].y.push(d[bivY]);
          });
          plotData = Object.keys(groups).map((h) => ({
            x: groups[h].x,
            y: groups[h].y,
            type: 'scatter',
            mode: 'markers',
            name: h,
            marker: { size: 6, opacity: 0.7 },
          }));
        } else {
          plotData = [
            {
              x: sampleData.map((d) => d[bivX]),
              y: sampleData.map((d) => d[bivY]),
              type: 'scatter',
              mode: 'markers',
              marker: { color: '#3b82f6', size: 6, opacity: 0.7 },
              name: 'Observations',
            },
          ];
        }
      }
    } else if (isXNum !== isYNum) {
      // Numerical - Categorical (Grouped Box / Bar)
      const numCol = isXNum ? bivX : bivY;
      const catCol = isXNum ? bivY : bivX;

      const groups = {};
      sampleData.forEach((d) => {
        const cVal = String(d[catCol] ?? 'Missing');
        const nVal = Number(d[numCol]);
        if (!isNaN(nVal)) {
          if (!groups[cVal]) groups[cVal] = [];
          groups[cVal].push(nVal);
        }
      });

      if (bivChartType === 'BOX') {
        plotData = Object.keys(groups).map((cat) => ({
          y: groups[cat],
          type: 'box',
          name: cat,
          boxpoints: 'outliers',
        }));
      } else {
        // Grouped Bar (Mean ± Std)
        const categories = Object.keys(groups);
        const means = categories.map((cat) => {
          const arr = groups[cat];
          return arr.reduce((a, b) => a + b, 0) / arr.length;
        });
        plotData = [
          {
            x: categories,
            y: means,
            type: 'bar',
            marker: { color: '#8b5cf6' },
            name: `Mean ${numCol}`,
          },
        ];
      }
    } else {
      // Categorical - Categorical (Contingency Crosstab Heatmap)
      const matrix = {};
      const xCats = new Set();
      const yCats = new Set();

      sampleData.forEach((d) => {
        const xVal = String(d[bivX] ?? 'N/A');
        const yVal = String(d[bivY] ?? 'N/A');
        xCats.add(xVal);
        yCats.add(yVal);
        const k = `${xVal}___${yVal}`;
        matrix[k] = (matrix[k] || 0) + 1;
      });

      const xArr = Array.from(xCats).slice(0, 10);
      const yArr = Array.from(yCats).slice(0, 10);
      const zValues = yArr.map((y) => xArr.map((x) => matrix[`${x}___${y}`] || 0));

      plotData = [
        {
          x: xArr,
          y: yArr,
          z: zValues,
          type: 'heatmap',
          colorscale: 'Blues',
          hoverongaps: false,
        },
      ];
    }

    return (
      <div className="w-full h-[400px]">
        <Plot data={plotData} layout={layout} useResizeHandler style={{ width: '100%', height: '100%' }} config={{ responsive: true }} />
      </div>
    );
  };

  // Generate Multivariate Plot Data (Scatter Matrix / Pair Plot)
  const renderMultivariatePlot = () => {
    if (multiColumns.length < 2 || sampleData.length === 0) {
      return (
        <div className="text-center py-12 text-xs text-[var(--color-text-muted)]">
          Select at least 2 numerical features for pair plot matrix analysis.
        </div>
      );
    }

    const dimensions = multiColumns.map((col) => ({
      label: col,
      values: sampleData.map((d) => Number(d[col]) || 0),
    }));

    let markerConfig = { size: 3, color: '#3b82f6', opacity: 0.6 };
    if (multiHue && multiHue !== 'NONE') {
      const hueValues = sampleData.map((d) => {
        const val = String(d[multiHue]);
        let hash = 0;
        for (let i = 0; i < val.length; i++) hash = val.charCodeAt(i) + ((hash << 5) - hash);
        return Math.abs(hash % 10);
      });
      markerConfig = {
        size: 4,
        color: hueValues,
        colorscale: 'Portland',
        opacity: 0.7,
      };
    }

    const plotData = [
      {
        type: 'splom',
        dimensions,
        marker: markerConfig,
      },
    ];

    const layout = {
      title: `Pairwise Scatter Matrix (${multiColumns.join(', ')})`,
      paper_bgcolor: 'transparent',
      plot_bgcolor: 'transparent',
      font: { color: '#94a3b8', size: 10 },
      margin: { l: 50, r: 30, t: 50, b: 50 },
      autosize: true,
    };

    return (
      <div className="w-full h-[500px]">
        <Plot data={plotData} layout={layout} useResizeHandler style={{ width: '100%', height: '100%' }} config={{ responsive: true }} />
      </div>
    );
  };

  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-2xl p-6 shadow-sm space-y-6">
      {/* Header & Mode Switcher */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-[var(--color-border)]">
        <div>
          <h2 className="text-base font-bold text-[var(--color-text)] flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-[var(--color-accent)]" />
            <span>Exploratory Data Analysis (EDA) Studio</span>
          </h2>
          <p className="text-xs text-[var(--color-text-muted)] mt-0.5">
            Interactive univariate distributions, bivariate correlations, and multivariate pair plot matrices
          </p>
        </div>

        {/* Mode Selector Tabs */}
        <div className="flex items-center p-1 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl">
          <button
            onClick={() => setAnalysisType('UNIVARIATE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              analysisType === 'UNIVARIATE'
                ? 'bg-[var(--color-accent)] text-white shadow-xs'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            Univariate
          </button>
          <button
            onClick={() => setAnalysisType('BIVARIATE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              analysisType === 'BIVARIATE'
                ? 'bg-[var(--color-accent)] text-white shadow-xs'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            Bivariate
          </button>
          <button
            onClick={() => setAnalysisType('MULTIVARIATE')}
            className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer ${
              analysisType === 'MULTIVARIATE'
                ? 'bg-[var(--color-accent)] text-white shadow-xs'
                : 'text-[var(--color-text-muted)] hover:text-[var(--color-text)]'
            }`}
          >
            Multivariate
          </button>
        </div>
      </div>

      {/* 1. UNIVARIATE CONTROLS & PLOT */}
      {analysisType === 'UNIVARIATE' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-4 p-4 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl text-xs">
            <div className="flex items-center gap-2">
              <label className="font-semibold text-[var(--color-text-muted)]">Feature:</label>
              <select
                value={uniColumn}
                onChange={(e) => setUniColumn(e.target.value)}
                className="px-3 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg font-bold text-[var(--color-text)] focus:outline-none cursor-pointer"
              >
                {columnsMeta.map((c) => (
                  <option key={c.name} value={c.name}>
                    {c.name} ({c.type})
                  </option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="font-semibold text-[var(--color-text-muted)]">Chart Type:</label>
              {isUniNumeric ? (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setUniChartType('HISTO')}
                    className={`px-2.5 py-1 rounded text-xs font-bold ${uniChartType === 'HISTO' ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-surface)] text-[var(--color-text-muted)]'}`}
                  >
                    Histogram
                  </button>
                  <button
                    onClick={() => setUniChartType('KDE')}
                    className={`px-2.5 py-1 rounded text-xs font-bold ${uniChartType === 'KDE' ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-surface)] text-[var(--color-text-muted)]'}`}
                  >
                    Density (KDE)
                  </button>
                  <button
                    onClick={() => setUniChartType('BOX')}
                    className={`px-2.5 py-1 rounded text-xs font-bold ${uniChartType === 'BOX' ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-surface)] text-[var(--color-text-muted)]'}`}
                  >
                    Box Plot
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setUniChartType('COUNT')}
                    className={`px-2.5 py-1 rounded text-xs font-bold ${uniChartType === 'COUNT' ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-surface)] text-[var(--color-text-muted)]'}`}
                  >
                    Countplot (Bar)
                  </button>
                  <button
                    onClick={() => setUniChartType('PIE')}
                    className={`px-2.5 py-1 rounded text-xs font-bold ${uniChartType === 'PIE' ? 'bg-[var(--color-accent)] text-white' : 'bg-[var(--color-surface)] text-[var(--color-text-muted)]'}`}
                  >
                    Pie Chart
                  </button>
                </div>
              )}
            </div>

            {isUniNumeric && uniChartType === 'HISTO' && (
              <div className="flex items-center gap-2">
                <label className="font-semibold text-[var(--color-text-muted)]">Bins ({numBins}):</label>
                <input
                  type="range"
                  min="5"
                  max="50"
                  value={numBins}
                  onChange={(e) => setNumBins(Number(e.target.value))}
                  className="cursor-pointer"
                />
              </div>
            )}
          </div>

          {renderUnivariatePlot()}
        </div>
      )}

      {/* 2. BIVARIATE CONTROLS & PLOT */}
      {analysisType === 'BIVARIATE' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-4 p-4 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl text-xs">
            <div className="flex items-center gap-2">
              <label className="font-semibold text-[var(--color-text-muted)]">X-Axis:</label>
              <select
                value={bivX}
                onChange={(e) => setBivX(e.target.value)}
                className="px-3 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg font-bold text-[var(--color-text)] focus:outline-none cursor-pointer"
              >
                {columnsMeta.map((c) => (
                  <option key={c.name} value={c.name}>{c.name} ({c.type})</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="font-semibold text-[var(--color-text-muted)]">Y-Axis:</label>
              <select
                value={bivY}
                onChange={(e) => setBivY(e.target.value)}
                className="px-3 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg font-bold text-[var(--color-text)] focus:outline-none cursor-pointer"
              >
                {columnsMeta.map((c) => (
                  <option key={c.name} value={c.name}>{c.name} ({c.type})</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="font-semibold text-[var(--color-text-muted)]">Plot Type:</label>
              <select
                value={bivChartType}
                onChange={(e) => setBivChartType(e.target.value)}
                className="px-3 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg font-bold text-[var(--color-text)] focus:outline-none cursor-pointer"
              >
                <option value="SCATTER">Scatter Plot</option>
                <option value="LINE">Line Plot (Trend)</option>
                <option value="BOX">Grouped Box Plot</option>
                <option value="BAR">Grouped Bar Plot</option>
                <option value="HEATMAP">Contingency Heatmap</option>
              </select>
            </div>

            <div className="flex items-center gap-2">
              <label className="font-semibold text-[var(--color-text-muted)]">Color Hue (Class):</label>
              <select
                value={colorHue}
                onChange={(e) => setColorHue(e.target.value)}
                className="px-3 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg font-bold text-[var(--color-text)] focus:outline-none cursor-pointer"
              >
                <option value="NONE">None</option>
                {categoricalCols.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {renderBivariatePlot()}
        </div>
      )}

      {/* 3. MULTIVARIATE CONTROLS & PAIR PLOT */}
      {analysisType === 'MULTIVARIATE' && (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center justify-between gap-4 p-4 bg-[var(--color-surface-hover)] border border-[var(--color-border)] rounded-xl text-xs">
            <div className="space-y-1">
              <label className="font-semibold text-[var(--color-text-muted)] block">
                Select Numerical Features for Pair Matrix (2–5 columns):
              </label>
              <div className="flex items-center gap-2 flex-wrap">
                {numericCols.map((col) => {
                  const isChecked = multiColumns.includes(col);
                  return (
                    <button
                      key={col}
                      onClick={() => {
                        if (isChecked) {
                          setMultiColumns(multiColumns.filter((c) => c !== col));
                        } else {
                          if (multiColumns.length < 5) setMultiColumns([...multiColumns, col]);
                        }
                      }}
                      className={`px-2.5 py-1 rounded-md text-xs font-bold transition-all cursor-pointer ${
                        isChecked
                          ? 'bg-[var(--color-accent)] text-white'
                          : 'bg-[var(--color-surface)] text-[var(--color-text-muted)] border border-[var(--color-border)]'
                      }`}
                    >
                      {col}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="flex items-center gap-2">
              <label className="font-semibold text-[var(--color-text-muted)]">Hue / Class:</label>
              <select
                value={multiHue}
                onChange={(e) => setMultiHue(e.target.value)}
                className="px-3 py-1.5 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg font-bold text-[var(--color-text)] focus:outline-none cursor-pointer"
              >
                <option value="NONE">None</option>
                {categoricalCols.map((c) => (
                  <option key={c} value={c}>{c}</option>
                ))}
              </select>
            </div>
          </div>

          {renderMultivariatePlot()}
        </div>
      )}
    </div>
  );
};

export default InteractiveEDAStudio;
