import React from 'react';
import { useI18n } from '../i18n';

interface SmartRecommendProps {
  recommendedPreset?: string;
  confidence?: number;
  onApply?: () => void;
  onDismiss?: () => void;
}

const SmartRecommend: React.FC<SmartRecommendProps> = ({
  recommendedPreset,
  confidence = 0,
  onApply,
  onDismiss,
}) => {
  const { t } = useI18n();

  if (!recommendedPreset || confidence <= 0.7) {
    return null;
  }

  const percent = Math.round(confidence * 100);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: 12,
        padding: '0 12px',
        height: 36,
        borderRadius: 8,
        background: 'rgba(196, 92, 38, 0.08)',
        border: '1px solid rgba(196, 92, 38, 0.15)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
        <span style={{ fontSize: 14, flexShrink: 0 }}>💡</span>
        <span
          style={{
            fontSize: 13,
            color: '#c45c26',
            fontWeight: 500,
            whiteSpace: 'nowrap',
            overflow: 'hidden',
            textOverflow: 'ellipsis',
          }}
        >
          {t('recommend.title')}：{recommendedPreset}{t('params.preset')}（{t('recommend.confidence')} {percent}%）
        </span>
      </div>
      <div style={{ display: 'flex', gap: 8, flexShrink: 0 }}>
        <button
          onClick={onApply}
          style={{
            padding: '4px 10px',
            borderRadius: 6,
            border: '1px solid #c45c26',
            background: '#c45c26',
            color: '#ffffff',
            fontSize: 12,
            fontWeight: 500,
            cursor: 'pointer',
            fontFamily: 'inherit',
            transition: 'opacity 0.2s ease',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.opacity = '0.9';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.opacity = '1';
          }}
        >
          {t('recommend.apply')}
        </button>
        <button
          onClick={onDismiss}
          style={{
            padding: '4px 10px',
            borderRadius: 6,
            border: '1px solid transparent',
            background: 'transparent',
            color: '#6b6b6b',
            fontSize: 12,
            cursor: 'pointer',
            fontFamily: 'inherit',
            transition: 'background 0.2s ease',
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = 'rgba(0,0,0,0.04)';
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
          }}
        >
          {t('recommend.dismiss')}
        </button>
      </div>
    </div>
  );
};

export default SmartRecommend;
