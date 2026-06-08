import React, { useState, useCallback, useEffect } from 'react';
import type { TraceOptions, Preset } from '../types';

interface ParamPanelProps {
  presets: Preset[];
  activePreset: string;
  onSelectPreset: (name: string) => void;
  options: TraceOptions;
  onChangeOptions: (opts: TraceOptions) => void;
  onSavePreset: (name: string, options: TraceOptions) => void;
  onDeletePreset: (name: string) => void;
  livePreview: boolean;
  onToggleLivePreview: () => void;
  outputFormat: 'svg' | 'pdf' | 'png';
  onChangeOutputFormat: (f: 'svg' | 'pdf' | 'png') => void;
  optimizeLevel: number;
  onChangeOptimizeLevel: (v: number) => void;
}

export const ParamPanel: React.FC<ParamPanelProps> = ({
  presets,
  activePreset,
  onSelectPreset,
  options,
  onChangeOptions,
  onSavePreset,
  onDeletePreset,
  livePreview,
  onToggleLivePreview,
  outputFormat,
  onChangeOutputFormat,
  optimizeLevel,
  onChangeOptimizeLevel,
}) => {
  const [presetName, setPresetName] = useState('');
  const [showSave, setShowSave] = useState(false);

  useEffect(() => {
    const preset = presets.find((p) => p.name === activePreset);
    if (preset) {
      onChangeOptions({ ...preset.options });
    }
  }, [activePreset, presets]);

  const update = useCallback(
    <K extends keyof TraceOptions>(key: K, value: TraceOptions[K]) => {
      onChangeOptions({ ...options, [key]: value });
    },
    [options, onChangeOptions]
  );

  const handleSave = useCallback(() => {
    if (presetName.trim()) {
      onSavePreset(presetName.trim(), options);
      setPresetName('');
      setShowSave(false);
    }
  }, [presetName, options, onSavePreset]);

  const currentPreset = presets.find((p) => p.name === activePreset);

  return (
    <div className="param-panel">
      <div className="param-section">
        <label className="param-label">Preset</label>
        <div className="param-preset-row">
          <select
            className="param-select"
            value={activePreset}
            onChange={(e) => onSelectPreset(e.target.value)}
          >
            {presets.map((p) => (
              <option key={p.name} value={p.name}>
                {p.displayName} {p.isBuiltin ? '(Built-in)' : '(Custom)'}
              </option>
            ))}
          </select>
          <button className="btn btn-sm" onClick={() => setShowSave((s) => !s)}>
            Save
          </button>
          {currentPreset && !currentPreset.isBuiltin && (
            <button className="btn btn-sm btn-danger" onClick={() => onDeletePreset(currentPreset.name)}>
              Del
            </button>
          )}
        </div>
        {showSave && (
          <div className="param-save-row">
            <input
              className="param-input"
              placeholder="Preset name"
              value={presetName}
              onChange={(e) => setPresetName(e.target.value)}
            />
            <button className="btn btn-sm btn-primary" onClick={handleSave}>
              OK
            </button>
          </div>
        )}
      </div>

      <div className="param-section">
        <label className="param-label">Color Mode</label>
        <select
          className="param-select"
          value={options.colormode}
          onChange={(e) => update('colormode', e.target.value as TraceOptions['colormode'])}
        >
          <option value="color">Color</option>
          <option value="binary">Binary</option>
        </select>
      </div>

      <div className="param-section">
        <label className="param-label">Hierarchical</label>
        <select
          className="param-select"
          value={options.hierarchical}
          onChange={(e) => update('hierarchical', e.target.value as TraceOptions['hierarchical'])}
        >
          <option value="stacked">Stacked</option>
          <option value="cutout">Cutout</option>
        </select>
      </div>

      <div className="param-section">
        <label className="param-label">Mode</label>
        <select
          className="param-select"
          value={options.mode}
          onChange={(e) => update('mode', e.target.value as TraceOptions['mode'])}
        >
          <option value="spline">Spline</option>
          <option value="polygon">Polygon</option>
          <option value="pixel">Pixel</option>
          <option value="none">None</option>
        </select>
      </div>

      <div className="param-section">
        <Slider label="Filter Speckle" value={options.filter_speckle} min={0} max={20} step={1} onChange={(v) => update('filter_speckle', v)} />
        <Slider label="Color Precision" value={options.color_precision} min={1} max={16} step={1} onChange={(v) => update('color_precision', v)} />
        <Slider label="Layer Difference" value={options.layer_difference} min={1} max={64} step={1} onChange={(v) => update('layer_difference', v)} />
        <Slider label="Corner Threshold" value={options.corner_threshold} min={0} max={180} step={1} onChange={(v) => update('corner_threshold', v)} />
        <Slider label="Length Threshold" value={options.length_threshold} min={0} max={20} step={0.5} onChange={(v) => update('length_threshold', v)} />
        <Slider label="Max Iterations" value={options.max_iterations} min={1} max={50} step={1} onChange={(v) => update('max_iterations', v)} />
        <Slider label="Splice Threshold" value={options.splice_threshold} min={0} max={180} step={1} onChange={(v) => update('splice_threshold', v)} />
        <Slider label="Path Precision" value={options.path_precision} min={1} max={16} step={1} onChange={(v) => update('path_precision', v)} />
      </div>

      <div className="param-section">
        <label className="param-label">Preprocessing</label>
        <div className="param-check-row">
          <input
            id="denoise"
            type="checkbox"
            checked={options.denoise}
            onChange={(e) => update('denoise', e.target.checked)}
          />
          <label htmlFor="denoise">Denoise</label>
        </div>
        <div className="param-check-row">
          <input
            id="posterize"
            type="checkbox"
            checked={options.posterize !== null}
            onChange={(e) => update('posterize', e.target.checked ? 4 : null)}
          />
          <label htmlFor="posterize">Posterize</label>
          {options.posterize !== null && (
            <input
              className="param-input param-input-sm"
              type="number"
              min={2}
              max={32}
              value={options.posterize}
              onChange={(e) => update('posterize', parseInt(e.target.value, 10))}
            />
          )}
        </div>
        <div className="param-check-row">
          <input
            id="maxside"
            type="checkbox"
            checked={options.max_input_side !== null}
            onChange={(e) => update('max_input_side', e.target.checked ? 2048 : null)}
          />
          <label htmlFor="maxside">Max Input Side</label>
          {options.max_input_side !== null && (
            <input
              className="param-input param-input-sm"
              type="number"
              min={256}
              max={8192}
              step={128}
              value={options.max_input_side}
              onChange={(e) => update('max_input_side', parseInt(e.target.value, 10))}
            />
          )}
        </div>
      </div>

      <div className="param-section">
        <label className="param-label">Export</label>
        <div className="param-segmented">
          {(['svg', 'pdf', 'png'] as const).map((f) => (
            <button
              key={f}
              className={`param-segment ${outputFormat === f ? 'active' : ''}`}
              onClick={() => onChangeOutputFormat(f)}
            >
              {f.toUpperCase()}
            </button>
          ))}
        </div>
        <Slider label="Optimize Level" value={optimizeLevel} min={0} max={3} step={1} onChange={onChangeOptimizeLevel} />
      </div>

      <div className="param-section">
        <div className="param-check-row">
          <input id="livepreview" type="checkbox" checked={livePreview} onChange={onToggleLivePreview} />
          <label htmlFor="livepreview">Live Preview</label>
        </div>
      </div>
    </div>
  );
};

const Slider: React.FC<{
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}> = ({ label, value, min, max, step, onChange }) => {
  return (
    <div className="slider-row">
      <div className="slider-header">
        <span className="slider-label">{label}</span>
        <span className="slider-value">{value}</span>
      </div>
      <input
        className="slider-input"
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
      />
    </div>
  );
};
