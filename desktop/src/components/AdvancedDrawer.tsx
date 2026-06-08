import React, { useState, useCallback } from 'react';
import type { TraceOptions } from '../types';

interface AdvancedDrawerProps {
  options: TraceOptions;
  onChangeOptions: (opts: TraceOptions) => void;
  defaultOptions?: TraceOptions;
}

const AdvancedDrawer: React.FC<AdvancedDrawerProps> = ({
  options,
  onChangeOptions,
  defaultOptions,
}) => {
  const [expanded, setExpanded] = useState(false);

  const update = useCallback(
    <K extends keyof TraceOptions>(key: K, value: TraceOptions[K]) => {
      onChangeOptions({ ...options, [key]: value });
    },
    [options, onChangeOptions]
  );

  const handleReset = useCallback(() => {
    if (defaultOptions) {
      onChangeOptions({ ...defaultOptions });
    }
  }, [defaultOptions, onChangeOptions]);

  const handleLoadFromPreset = useCallback(() => {
    // Placeholder: parent can provide a callback if needed
    // For now, this is a no-op that can be wired up externally
  }, []);

  const params: {
    key: keyof TraceOptions;
    label: string;
    type: 'number' | 'range' | 'checkbox';
    min?: number;
    max?: number;
    step?: number;
  }[] = [
    { key: 'filter_speckle', label: 'Filter Speckle', type: 'range', min: 0, max: 20, step: 1 },
    { key: 'color_precision', label: 'Color Precision', type: 'range', min: 1, max: 16, step: 1 },
    { key: 'layer_difference', label: 'Layer Difference', type: 'range', min: 1, max: 64, step: 1 },
    { key: 'corner_threshold', label: 'Corner Threshold', type: 'range', min: 0, max: 180, step: 1 },
    { key: 'length_threshold', label: 'Length Threshold', type: 'range', min: 0, max: 20, step: 0.5 },
    { key: 'max_iterations', label: 'Max Iterations', type: 'range', min: 1, max: 50, step: 1 },
    { key: 'splice_threshold', label: 'Splice Threshold', type: 'range', min: 0, max: 180, step: 1 },
    { key: 'path_precision', label: 'Path Precision', type: 'range', min: 1, max: 16, step: 1 },
    { key: 'denoise', label: 'Denoise', type: 'checkbox' },
    { key: 'posterize', label: 'Posterize', type: 'number' },
    { key: 'max_input_side', label: 'Max Input Side', type: 'number' },
  ];

  return (
    <div style={{ borderTop: '1px solid #e5e3df' }}>
      {/* Toggle */}
      <button
        onClick={() => setExpanded((v) => !v)}
        style={{
          width: '100%',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          gap: 6,
          padding: '8px 0',
          background: 'transparent',
          border: 'none',
          color: '#6b6b6b',
          fontSize: 13,
          cursor: 'pointer',
          fontFamily: 'inherit',
          transition: 'color 0.2s ease',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.color = '#1a1a1a';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.color = '#6b6b6b';
        }}
      >
        <span
          style={{
            display: 'inline-block',
            transform: expanded ? 'rotate(180deg)' : 'rotate(0deg)',
            transition: 'transform 0.3s ease',
          }}
        >
          ▼
        </span>
        <span>高级参数</span>
      </button>

      {/* Drawer Content */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '12px 16px',
          overflow: 'hidden',
          transition: 'max-height 0.3s ease, opacity 0.3s ease, padding 0.3s ease',
          maxHeight: expanded ? 600 : 0,
          opacity: expanded ? 1 : 0,
          padding: expanded ? '12px 16px 16px' : '0 16px',
        }}
      >
        {params.map((param) => (
          <div key={String(param.key)} style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
            <label
              style={{
                fontSize: 11,
                fontWeight: 600,
                textTransform: 'uppercase',
                letterSpacing: '0.5px',
                color: '#6b6b6b',
              }}
            >
              {param.label}
            </label>
            {param.type === 'range' && (
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <input
                  type="range"
                  min={param.min}
                  max={param.max}
                  step={param.step}
                  value={Number(options[param.key])}
                  onChange={(e) => update(param.key, parseFloat(e.target.value) as TraceOptions[typeof param.key])}
                  style={{ flex: 1 }}
                />
                <span
                  style={{
                    fontSize: 12,
                    fontVariantNumeric: 'tabular-nums',
                    minWidth: 32,
                    textAlign: 'right',
                    color: '#1a1a1a',
                    fontWeight: 500,
                  }}
                >
                  {String(options[param.key])}
                </span>
              </div>
            )}
            {param.type === 'number' && (
              <input
                type="number"
                value={options[param.key] === null ? '' : Number(options[param.key])}
                onChange={(e) => {
                  const val = e.target.value === '' ? null : parseInt(e.target.value, 10);
                  update(param.key, val as TraceOptions[typeof param.key]);
                }}
                style={{
                  height: 32,
                  borderRadius: 6,
                  border: '1px solid #e5e3df',
                  padding: '0 8px',
                  fontSize: 13,
                  fontFamily: 'inherit',
                  outline: 'none',
                  width: '100%',
                }}
                onFocus={(e) => {
                  (e.currentTarget as HTMLInputElement).style.borderColor = '#c45c26';
                }}
                onBlur={(e) => {
                  (e.currentTarget as HTMLInputElement).style.borderColor = '#e5e3df';
                }}
              />
            )}
            {param.type === 'checkbox' && (
              <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 13 }}>
                <input
                  type="checkbox"
                  checked={!!options[param.key]}
                  onChange={(e) => update(param.key, e.target.checked as TraceOptions[typeof param.key])}
                  style={{ width: 16, height: 16, accentColor: '#c45c26' }}
                />
                <span style={{ color: '#1a1a1a' }}>启用</span>
              </label>
            )}
          </div>
        ))}

        {/* Bottom actions */}
        <div style={{ gridColumn: '1 / -1', display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 4 }}>
          <button
            onClick={handleReset}
            style={{
              padding: '6px 12px',
              borderRadius: 8,
              border: '1px solid #e5e3df',
              background: '#ffffff',
              color: '#6b6b6b',
              fontSize: 12,
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            重置为默认
          </button>
          <button
            onClick={handleLoadFromPreset}
            style={{
              padding: '6px 12px',
              borderRadius: 8,
              border: '1px solid #e5e3df',
              background: '#ffffff',
              color: '#6b6b6b',
              fontSize: 12,
              cursor: 'pointer',
              fontFamily: 'inherit',
            }}
          >
            从预设加载
          </button>
        </div>
      </div>
    </div>
  );
};

export default AdvancedDrawer;
