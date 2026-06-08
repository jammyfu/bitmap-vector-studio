import React, { useState, useEffect, createContext, useContext, useCallback } from 'react';
import type { Theme } from '../types';

interface ThemeContextValue {
  theme: Theme;
  effectiveTheme: 'light' | 'dark';
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextValue>({
  theme: 'system',
  effectiveTheme: 'dark',
  setTheme: () => {},
  toggleTheme: () => {},
});

export function useTheme() {
  return useContext(ThemeContext);
}

function getSystemTheme(): 'light' | 'dark' {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

interface LayoutProps {
  sidebar: React.ReactNode;
  main: React.ReactNode;
  preview: React.ReactNode;
  statusBar: React.ReactNode;
  dropZone?: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ sidebar, main, preview, statusBar, dropZone }) => {
  const [theme, setThemeState] = useState<Theme>(() => {
    try {
      return (localStorage.getItem('bvs_theme') as Theme) || 'system';
    } catch {
      return 'system';
    }
  });
  const [sidebarVisible, setSidebarVisible] = useState(true);
  const [previewVisible, setPreviewVisible] = useState(true);
  const [isSmallScreen, setIsSmallScreen] = useState(false);

  const effectiveTheme: 'light' | 'dark' =
    theme === 'system' ? getSystemTheme() : theme;

  useEffect(() => {
    try {
      localStorage.setItem('bvs_theme', theme);
    } catch {
      // ignore
    }
    document.documentElement.setAttribute('data-theme', effectiveTheme);
  }, [theme, effectiveTheme]);

  useEffect(() => {
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const handler = () => {
      if (theme === 'system') {
        document.documentElement.setAttribute('data-theme', getSystemTheme());
      }
    };
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, [theme]);

  useEffect(() => {
    const check = () => {
      const small = window.innerWidth < 1024;
      setIsSmallScreen(small);
      if (small) {
        setSidebarVisible(false);
        setPreviewVisible(false);
      } else {
        setSidebarVisible(true);
        setPreviewVisible(true);
      }
    };
    check();
    window.addEventListener('resize', check);
    return () => window.removeEventListener('resize', check);
  }, []);

  const setTheme = useCallback((t: Theme) => setThemeState(t), []);
  const toggleTheme = useCallback(() => {
    setThemeState((prev: Theme) => {
      if (prev === 'light') return 'dark';
      if (prev === 'dark') return 'system';
      return 'light';
    });
  }, []);

  return (
    <ThemeContext.Provider value={{ theme, effectiveTheme, setTheme, toggleTheme }}>
      <div className="layout-root">
        <header className="layout-header">
          <div className="layout-header-left">
            <button
              className="icon-btn"
              onClick={() => setSidebarVisible((v) => !v)}
              aria-label="Toggle sidebar"
              title="Toggle sidebar"
            >
              ☰
            </button>
            <span className="app-title">Bitmap Vector Studio</span>
          </div>
          <div className="layout-header-right">
            <button className="icon-btn" onClick={toggleTheme} aria-label="Toggle theme" title="Toggle theme">
              {effectiveTheme === 'dark' ? '☀' : '☾'}
            </button>
            <button
              className="icon-btn"
              onClick={() => setPreviewVisible((v) => !v)}
              aria-label="Toggle preview"
              title="Toggle preview"
            >
              👁
            </button>
          </div>
        </header>

        <div className="layout-body">
          {(!isSmallScreen || sidebarVisible) && (
            <aside className={`layout-sidebar ${isSmallScreen && sidebarVisible ? 'sidebar-overlay' : ''}`}>
              {sidebar}
            </aside>
          )}

          <main className="layout-main">{main}</main>

          {(!isSmallScreen || previewVisible) && (
            <aside className={`layout-preview ${isSmallScreen && previewVisible ? 'preview-overlay' : ''}`}>
              {preview}
            </aside>
          )}
        </div>

        <footer className="layout-statusbar">{statusBar}</footer>
        {dropZone}
      </div>
    </ThemeContext.Provider>
  );
};
