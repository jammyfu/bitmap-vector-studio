import React, { useState } from 'react';
import { useI18n } from '../i18n';

interface ControlBarProps {
  isConverting: boolean;
  canDownload: boolean;
  onConvert: () => void;
  onDownload: (format: 'svg' | 'pdf' | 'png') => void;
  downloadFormat?: 'svg' | 'pdf' | 'png';
  onOpenExternal?: () => void;
  onShare?: () => void;
  onAddToQueue?: () => void;
}

const ControlBar: React.FC<ControlBarProps> = ({
  isConverting,
  canDownload,
  onConvert,
  onDownload,
  downloadFormat = 'svg',
  onOpenExternal,
  onShare,
  onAddToQueue,
}) => {
  const [showDownloadMenu, setShowDownloadMenu] = useState(false);
  const { t } = useI18n();

  return (
    <div
      style={{
        height: 72,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        background: '#faf9f7',
        borderTop: '1px solid #e5e3df',
        flexShrink: 0,
        gap: 16,
      }}
    >
      {/* Left: Convert Button */}
      <button
        onClick={onConvert}
        disabled={isConverting}
        style={{
          height: 44,
          padding: '0 24px',
          borderRadius: 8,
          border: 'none',
          background: '#c45c26',
          color: '#ffffff',
          fontSize: 14,
          fontWeight: 600,
          cursor: isConverting ? 'not-allowed' : 'pointer',
          display: 'flex',
                alignItems: 'center',
          justifyContent: 'center',
          gap: 8,
          fontFamily: 'inherit',
          transition: 'opacity 0.2s ease, transform 0.15s ease',
          opacity: isConverting ? 0.8 : 1,
          minWidth: 160,
        }}
        onMouseEnter={(e) => {
          if (!isConverting) (e.currentTarget as HTMLButtonElement).style.opacity = '0.9';
        }}
        onMouseLeave={(e) => {
          if (!isConverting) (e.currentTarget as HTMLButtonElement).style.opacity = '1';
        }}
        onMouseDown={(e) => {
          if (!isConverting) (e.currentTarget as HTMLButtonElement).style.transform = 'scale(0.98)';
        }}
        onMouseUp={(e) => {
          (e.currentTarget as HTMLButtonElement).style.transform = 'scale(1)';
        }}
      >
        {isConverting && (
          <span
            style={{
              display: 'inline-block',
              width: 14,
              height: 14,
              border: '2px solid rgba(255,255,255,0.3)',
              borderTopColor: '#ffffff',
              borderRadius: '50%',
              animation: 'spin 0.8s linear infinite',
            }}
          />
        )}
        {isConverting ? t('control.converting') : t('control.convert')}
      </button>

      {/* Center: Download */}
      <div style={{ position: 'relative' }}>
        <button
          onClick={() => canDownload && onDownload(downloadFormat)}
          disabled={!canDownload}
          onContextMenu={(e) => {
            e.preventDefault();
            if (canDownload) setShowDownloadMenu((v) => !v);
          }}
          style={{
            height: 40,
            padding: '0 16px',
            borderRadius: 8,
            border: `1px solid ${canDownload ? '#e5e3df' : '#e5e3df'}`,
            background: '#ffffff',
            color: canDownload ? '#1a1a1a' : '#a1a1a6',
            fontSize: 13,
            fontWeight: 500,
            cursor: canDownload ? 'pointer' : 'not-allowed',
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            fontFamily: 'inherit',
            transition: 'border-color 0.2s ease',
          }}
        >
          <span>⬇</span>
          <span>{t('control.download')} {downloadFormat.toUpperCase()}</span>
          <span
            style={{ fontSize: 10, marginLeft: 2 }}
            onClick={(e) => {
              e.stopPropagation();
              if (canDownload) setShowDownloadMenu((v) => !v);
            }}
          >
            ▼
          </span>
        </button>

        {showDownloadMenu && canDownload && (
          <div
            style={{
              position: 'absolute',
              bottom: 'calc(100% + 6px)',
              left: 0,
              background: '#ffffff',
              border: '1px solid #e5e3df',
              borderRadius: 8,
              boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
              padding: 4,
              minWidth: 140,
              zIndex: 20,
            }}
          >
            {(['svg', 'pdf', 'png'] as const).map((fmt) => (
              <button
                key={fmt}
                onClick={() => {
                  onDownload(fmt);
                  setShowDownloadMenu(false);
                }}
                style={{
                  display: 'block',
                  width: '100%',
                  textAlign: 'left',
                  padding: '6px 10px',
                  borderRadius: 6,
                  border: 'none',
                  background: downloadFormat === fmt ? 'rgba(196,92,38,0.08)' : 'transparent',
                  color: downloadFormat === fmt ? '#c45c26' : '#1a1a1a',
                  fontSize: 13,
                  cursor: 'pointer',
                  fontFamily: 'inherit',
                }}
              >
                {fmt.toUpperCase()}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Right: More Actions */}
      <div style={{ display: 'flex', gap: 8 }}>
        <GhostButton onClick={onOpenExternal} disabled={!canDownload}>
          🖊 {t('control.external_editor')}
        </GhostButton>
        <GhostButton onClick={onShare} disabled={!canDownload}>
          🔗 {t('control.share')}
        </GhostButton>
        <GhostButton onClick={onAddToQueue}>
          ➕ {t('control.add_to_queue')}
        </GhostButton>
      </div>
    </div>
  );
};

const GhostButton: React.FC<{
  onClick?: () => void;
  disabled?: boolean;
  children: React.ReactNode;
}> = ({ onClick, disabled, children }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    style={{
      height: 36,
      padding: '0 12px',
      borderRadius: 8,
      border: '1px solid transparent',
      background: 'transparent',
      color: disabled ? '#a1a1a6' : '#6b6b6b',
      fontSize: 12,
      cursor: disabled ? 'not-allowed' : 'pointer',
      display: 'flex',
      alignItems: 'center',
      gap: 4,
      fontFamily: 'inherit',
      transition: 'background 0.2s ease, color 0.2s ease',
    }}
    onMouseEnter={(e) => {
      if (!disabled) {
        (e.currentTarget as HTMLButtonElement).style.background = 'rgba(0,0,0,0.04)';
        (e.currentTarget as HTMLButtonElement).style.color = '#1a1a1a';
      }
    }}
    onMouseLeave={(e) => {
      (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
      (e.currentTarget as HTMLButtonElement).style.color = disabled ? '#a1a1a6' : '#6b6b6b';
    }}
  >
    {children}
  </button>
);

export default ControlBar;
