import React, { useState } from 'react';
import { useI18n } from '../i18n';

interface TopBarProps {
  onOpenCommandPalette?: () => void;
  onOpenSettings?: () => void;
  onOpenUserMenu?: () => void;
  theme?: 'light' | 'dark';
  onToggleTheme?: () => void;
}

const TopBar: React.FC<TopBarProps> = ({
  onOpenCommandPalette,
  onOpenSettings,
  onOpenUserMenu,
  theme = 'light',
  onToggleTheme,
}) => {
  const isDark = theme === 'dark';
  const { locale, setLocale, t } = useI18n();
  const [showLangMenu, setShowLangMenu] = useState(false);

  React.useEffect(() => {
    const listener = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        onOpenCommandPalette?.();
      }
    };
    window.addEventListener('keydown', listener);
    return () => window.removeEventListener('keydown', listener);
  }, [onOpenCommandPalette]);

  const langOptions: { value: typeof locale; label: string }[] = [
    { value: 'zh-CN', label: '简体中文' },
    { value: 'en-US', label: 'English' },
    { value: 'ja-JP', label: '日本語' },
  ];

  return (
    <header
      style={{
        height: 52,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 16px',
        background: isDark ? '#1a1a1a' : '#faf9f7',
        borderBottom: `1px solid ${isDark ? '#2a2a2a' : '#e5e3df'}`,
        flexShrink: 0,
        gap: 16,
      }}
    >
      {/* Left: Logo */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <div
          style={{
            width: 28,
            height: 28,
            borderRadius: 8,
            background: '#c45c26',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: '#fff',
            fontSize: 16,
            fontWeight: 700,
          }}
        >
          ◈
        </div>
        <span
          style={{
            fontSize: 14,
            fontWeight: 500,
            color: isDark ? '#f5f5f7' : '#1a1a1a',
            letterSpacing: '-0.2px',
            whiteSpace: 'nowrap',
          }}
        >
          {t('app.title')}
        </span>
      </div>

      {/* Center: Command Palette Trigger */}
      <button
        onClick={onOpenCommandPalette}
        style={{
          flex: 1,
          maxWidth: 480,
          height: 36,
          borderRadius: 8,
          border: `1px solid ${isDark ? '#2a2a2a' : '#e5e3df'}`,
          background: isDark ? '#2a2a2a' : '#ffffff',
          color: isDark ? '#a1a1a6' : '#6b6b6b',
          fontSize: 13,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 12px',
          cursor: 'pointer',
          transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
          fontFamily: 'inherit',
        }}
        onMouseEnter={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = '#c45c26';
        }}
        onMouseLeave={(e) => {
          (e.currentTarget as HTMLButtonElement).style.borderColor = isDark ? '#2a2a2a' : '#e5e3df';
        }}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <span style={{ fontSize: 14 }}>🔍</span>
          <span>{t('topbar.search')}</span>
        </span>
        <kbd
          style={{
            fontSize: 11,
            fontFamily: 'var(--font-mono)',
            background: isDark ? '#1a1a1a' : '#f5f5f7',
            padding: '2px 6px',
            borderRadius: 4,
            border: `1px solid ${isDark ? '#3a3a3c' : '#d2d2d7'}`,
            color: isDark ? '#6e6e73' : '#6b6b6b',
          }}
        >
          {navigator.platform.indexOf('Mac') !== -1 ? '⌘ K' : 'Ctrl K'}
        </kbd>
      </button>

      {/* Right: Actions */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 4, flexShrink: 0 }}>
        {/* Language Switcher */}
        <div style={{ position: 'relative' }}>
          <button
            onClick={() => setShowLangMenu((v) => !v)}
            title={t('topbar.language')}
            style={iconBtnStyle(isDark)}
          >
            🌐
          </button>
          {showLangMenu && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                background: '#ffffff',
                border: '1px solid #e5e3df',
                borderRadius: 8,
                boxShadow: '0 4px 16px rgba(0,0,0,0.08)',
                padding: 4,
                minWidth: 120,
                zIndex: 50,
              }}
            >
              {langOptions.map((opt) => (
                <button
                  key={opt.value}
                  onClick={() => {
                    setLocale(opt.value);
                    setShowLangMenu(false);
                  }}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    padding: '6px 10px',
                    borderRadius: 6,
                    border: 'none',
                    background: locale === opt.value ? 'rgba(196,92,38,0.08)' : 'transparent',
                    color: locale === opt.value ? '#c45c26' : '#1a1a1a',
                    fontSize: 13,
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                  }}
                >
                  {opt.label}
                </button>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={onToggleTheme}
          title={isDark ? t('topbar.theme_light') : t('topbar.theme_dark')}
          style={iconBtnStyle(isDark)}
        >
          {isDark ? '☀' : '☾'}
        </button>
        <button
          onClick={onOpenSettings}
          title={t('topbar.settings')}
          style={iconBtnStyle(isDark)}
        >
          ⚙
        </button>
        <button
          onClick={onOpenUserMenu}
          title={t('topbar.user')}
          style={iconBtnStyle(isDark)}
        >
          👤
        </button>
      </div>
    </header>
  );
};

function iconBtnStyle(isDark: boolean): React.CSSProperties {
  return {
    width: 36,
    height: 36,
    borderRadius: 8,
    border: '1px solid transparent',
    background: 'transparent',
    color: isDark ? '#a1a1a6' : '#6b6b6b',
    fontSize: 16,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    transition: 'background 0.2s ease, color 0.2s ease',
    fontFamily: 'inherit',
  };
}

export default TopBar;
