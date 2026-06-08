import React from 'react';

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

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
      e.preventDefault();
      onOpenCommandPalette?.();
    }
  };

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
          Bitmap Vector Studio
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
          <span>搜索预设、命令、文件...</span>
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
        <button
          onClick={onToggleTheme}
          title={isDark ? '切换亮色主题' : '切换暗色主题'}
          style={iconBtnStyle(isDark)}
        >
          {isDark ? '☀' : '☾'}
        </button>
        <button
          onClick={onOpenSettings}
          title="设置"
          style={iconBtnStyle(isDark)}
        >
          ⚙
        </button>
        <button
          onClick={onOpenUserMenu}
          title="用户"
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
