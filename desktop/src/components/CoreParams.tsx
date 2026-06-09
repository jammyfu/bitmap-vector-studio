import React from 'react';
import { useI18n } from '../i18n';
import type { Preset } from '../types';

interface CoreParamsProps {
  preset: string;
  onChangePreset: (preset: string) => void;
  presets: Preset[];
  colorMode: 'color' | 'binary';
  onChangeColorMode: (mode: 'color' | 'binary') => void;
  curveMode: 'spline' | 'polygon' | 'pixel' | 'none';
  onChangeCurveMode: (mode: 'spline' | 'polygon' | 'pixel' | 'none') => void;
  optimizeLevel: 'none' | 'basic' | 'comprehensive' | 'aggressive';
  onChangeOptimizeLevel: (level: 'none' | 'basic' | 'comprehensive' | 'aggressive') => void;
}

const CoreParams: React.FC<CoreParamsProps> = ({
  preset,
  onChangePreset,
  presets,
  colorMode,
  onChangeColorMode,
  curveMode,
  onChangeCurveMode,
  optimizeLevel,
  onChangeOptimizeLevel,
}) => {
  const { t } = useI18n();

  const selectStyle: React.CSSProperties = {
    height: 40,
    borderRadius: 8,
    border: '1px solid #e5e3df',
    background: '#ffffff',
    color: '#1a1a1a',
    fontSize: 13,
    fontFamily: 'inherit',
    padding: '0 10px',
    outline: 'none',
    cursor: 'pointer',
    transition: 'border-color 0.2s ease',
    flex: 1,
    minWidth: 0,
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      <div style={{ display: 'flex', gap: 12, alignItems: 'center' }}>
        {/* Preset */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#6b6b6b' }}>
            {t('params.preset')}
          </label>
          <select
            value={preset}
            onChange={(e) => onChangePreset(e.target.value)}
            style={selectStyle}
            onFocus={(e) => {
              (e.currentTarget as HTMLSelectElement).style.borderColor = '#c45c26';
            }}
            onBlur={(e) => {
              (e.currentTarget as HTMLSelectElement).style.borderColor = '#e5e3df';
            }}
          >
            {presets.map((p) => (
              <option key={p.name} value={p.name}>
                {p.isBuiltin ? '🔧 ' : '✨ '}
                {p.displayName || p.name}
              </option>
            ))}
          </select>
        </div>

        {/* Color Mode */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#6b6b6b' }}>
            {t('params.colormode')}
          </label>
          <select
            value={colorMode}
            onChange={(e) => onChangeColorMode(e.target.value as 'color' | 'binary')}
            style={selectStyle}
            onFocus={(e) => {
              (e.currentTarget as HTMLSelectElement).style.borderColor = '#c45c26';
            }}
            onBlur={(e) => {
              (e.currentTarget as HTMLSelectElement).style.borderColor = '#e5e3df';
            }}
          >
            <option value="color">🎨 {t('params.color')} (color)</option>
            <option value="binary">⬛ {t('params.binary')} (binary)</option>
          </select>
        </div>

        {/* Curve Mode */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#6b6b6b' }}>
            {t('params.curvemode')}
          </label>
          <select
            value={curveMode}
            onChange={(e) => onChangeCurveMode(e.target.value as 'spline' | 'polygon' | 'pixel' | 'none')}
            style={selectStyle}
            onFocus={(e) => {
              (e.currentTarget as HTMLSelectElement).style.borderColor = '#c45c26';
            }}
            onBlur={(e) => {
              (e.currentTarget as HTMLSelectElement).style.borderColor = '#e5e3df';
            }}
          >
            <option value="spline">〰 {t('params.spline')} (spline)</option>
            <option value="polygon">⬡ {t('params.polygon')} (polygon)</option>
            <option value="pixel">▣ {t('params.pixel')} (pixel)</option>
            <option value="none">✕ {t('params.none')} (none)</option>
          </select>
        </div>

        {/* Optimize Level */}
        <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
          <label style={{ fontSize: 11, fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.5px', color: '#6b6b6b' }}>
            {t('params.optimize')}
          </label>
          <select
            value={optimizeLevel}
            onChange={(e) =>
              onChangeOptimizeLevel(e.target.value as 'none' | 'basic' | 'comprehensive' | 'aggressive')
            }
            style={selectStyle}
            onFocus={(e) => {
              (e.currentTarget as HTMLSelectElement).style.borderColor = '#c45c26';
            }}
            onBlur={(e) => {
              (e.currentTarget as HTMLSelectElement).style.borderColor = '#e5e3df';
            }}
          >
            <option value="none">✕ {t('params.no_optimize')}</option>
            <option value="basic">⚡ {t('params.basic')}</option>
            <option value="comprehensive">🔧 {t('params.comprehensive')}</option>
            <option value="aggressive">🚀 {t('params.aggressive')}</option>
          </select>
        </div>
      </div>
    </div>
  );
};

export default CoreParams;
