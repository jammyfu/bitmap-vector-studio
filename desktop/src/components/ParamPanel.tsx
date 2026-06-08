import React, { useState, useCallback, useEffect, useRef } from 'react';
import { useInvoke } from '../hooks/useInvoke';
import type { TraceOptions, Preset } from '../types';

interface ParamPanelProps {
  inputPath?: string;
  options: TraceOptions;
  onChangeOptions: (opts: TraceOptions) => void;
  livePreview: boolean;
  onToggleLivePreview: () => void;
  outputFormat: 'svg' | 'pdf' | 'png';
  onChangeOutputFormat: (f: 'svg' | 'pdf' | 'png') => void;
  optimizeLevel: number;
  onChangeOptimizeLevel: (v: number) => void;
  onPreviewResult?: (svgPath: string) => void;
  onToast?: (message: string, type?: 'success' | 'error') => void;
}

export const ParamPanel: React.FC<ParamPanelProps> = ({
  inputPath,
  options,
  onChangeOptions,
  livePreview,
  onToggleLivePreview,
  outputFormat,
  onChangeOutputFormat,
  optimizeLevel,
  onChangeOptimizeLevel,
  onPreviewResult,
  onToast,
}) => {
  const [presets, setPresets] = useState<Preset[]>([]);
  const [activePreset, setActivePreset] = useState<string>('default');
  const [presetName, setPresetName] = useState('');
  const [showSave, setShowSave] = useState(false);
  const [isRecommending, setIsRecommending] = useState(false);
  const livePreviewTimeout = useRef<ReturnType<typeof setTimeout> | null>(null);

  const { call: callGetPresets, loading: loadingPresets } = useInvoke<Record<string, never>, string>('get_presets');
  const { call: callSavePreset, loading: savingPreset } = useInvoke<{ name: string; options: string; description: string }, void>('save_preset');
  const { call: callDeletePreset } = useInvoke<{ name: string }, void>('delete_preset');
  const { call: callRecommend } = useInvoke<{ inputPath: string }, string>('recommend_preset');
  const { call: callConvert } = useInvoke<{ inputPath: string; options: string }, string>('convert_image');

  // Load presets from backend on mount
  useEffect(() => {
    async function load() {
      const result = await callGetPresets();
      if (result) {
        try {
          const parsed = JSON.parse(result) as { presets?: Preset[] };
          if (parsed.presets) {
            setPresets(parsed.presets);
          } else if (Array.isArray(parsed)) {
            setPresets(parsed);
          }
        } catch {
          onToast?.('Failed to parse presets', 'error');
        }
      }
    }
    load();
  }, [callGetPresets, onToast]);

  // Apply preset when activePreset changes
  useEffect(() => {
    const preset = presets.find((p) => p.name === activePreset);
    if (preset) {
      onChangeOptions({ ...preset.options });
    }
  }, [activePreset, presets, onChangeOptions]);

  // Live preview debounce
  useEffect(() => {
    if (!livePreview || !inputPath) return;
    if (livePreviewTimeout.current) {
      clearTimeout(livePreviewTimeout.current);
    }
    livePreviewTimeout.current = setTimeout(async () => {
      try {
        const result = await callConvert({ inputPath, options: JSON.stringify(options) });
        if (result) {
          const parsed = JSON.parse(result) as { outputPath?: string };
          if (parsed.outputPath) {
            onPreviewResult?.(parsed.outputPath);
          }
        }
      } catch (err) {
        // Silently ignore live preview errors
      }
    }, 600);
    return () => {
      if (livePreviewTimeout.current) clearTimeout(livePreviewTimeout.current);
    };
  }, [options, livePreview, inputPath, callConvert, onPreviewResult]);

  const update = useCallback(
    <K extends keyof TraceOptions>(key: K, value: TraceOptions[K]) => {
      onChangeOptions({ ...options, [key]: value });
    },
    [options, onChangeOptions]
  );

  const handleSave = useCallback(async () => {
    if (!presetName.trim()) return;
    const result = await callSavePreset({
      name: presetName.trim(),
      options: JSON.stringify(options),
      description: '',
    });
    if (result !== null) {
      onToast?.('Preset saved', 'success');
      setPresetName('');
      setShowSave(false);
      // Refresh presets
      const refreshed = await callGetPresets();
      if (refreshed) {
        try {
          const parsed = JSON.parse(refreshed) as { presets?: Preset[] };
          if (parsed.presets) setPresets(parsed.presets);
          else if (Array.isArray(parsed)) setPresets(parsed);
        } catch { /* ignore */ }
      }
    } else {
      onToast?.('Failed to save preset', 'error');
    }
  }, [presetName, options, callSavePreset, callGetPresets, onToast]);

  const handleDelete = useCallback(async (name: string) => {
    const result = await callDeletePreset({ name });
    if (result !== null) {
      onToast?.('Preset deleted', 'success');
      setPresets((prev) => prev.filter((p) => p.name !== name));
      if (activePreset === name) setActivePreset('default');
    } else {
      onToast?.('Failed to delete preset', 'error');
    }
  }, [callDeletePreset, activePreset, onToast]);

  const handleRecommend = useCallback(async () => {
    if (!inputPath) {
      onToast?.('Please select an image first', 'error');
      return;
    }
    setIsRecommending(true);
    const result = await callRecommend({ inputPath });
    setIsRecommending(false);
    if (result) {
      try {
        const parsed = JSON.parse(result) as { preset?: string; options?: TraceOptions };
        if (parsed.options) {
          onChangeOptions(parsed.options);
          if (parsed.preset) setActivePreset(parsed.preset);
          onToast?.('Preset recommended applied', 'success');
        } else if (parsed.preset) {
          setActivePreset(parsed.preset);
          onToast?.(`Recommended preset: ${parsed.preset}`, 'success');
        }
      } catch {
        onToast?.('Failed to parse recommendation', 'error');
      }
    } else {
      onToast?.('Recommendation failed', 'error');
    }
  }, [inputPath, callRecommend, onChangeOptions, onToast]);

  const currentPreset = presets.find((p) => p.name === activePreset);

  return (
    <div className="param-panel">
      <div className="param-section">
        <label className="param-label">Preset</label>
        <div className="param-preset-row">
          <select
            className="param-select"
            value={activePreset}
            onChange={(e) => setActivePreset(e.target.value)}
            disabled={loadingPresets}
          >
            {presets.map((p) => (
              <option key={p.name} value={p.name}>
                {p.displayName || p.name} {p.isBuiltin ? '(Built-in)' : '(Custom)'}
              </option>
            ))}
          </select>
          <button className="btn btn-sm" onClick={() => setShowSave((s) => !s)} disabled={savingPreset}>
            Save
          </button>
          {currentPreset && !currentPreset.isBuiltin && (
            <button className="btn btn-sm btn-danger" onClick={() => handleDelete(currentPreset.name)}>
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
            <button className="btn btn-sm btn-primary" onClick={handleSave} disabled={savingPreset}>
              OK
            </button>
          </div>
        )}
        <button className="btn btn-sm btn-secondary" onClick={handleRecommend} disabled={isRecommending || !inputPath}>
          {isRecommending ? 'Analyzing...' : 'Recommend'}
        </button>
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
