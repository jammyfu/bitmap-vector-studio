import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import type { Preset } from '../types';

interface CommandPaletteItem {
  id: string;
  type: 'preset' | 'command' | 'file' | 'setting';
  title: string;
  subtitle?: string;
  icon?: string;
  shortcut?: string;
  action: () => void;
}

interface CommandPaletteProps {
  open: boolean;
  onClose: () => void;
  presets?: Preset[];
  recentFiles?: string[];
  onSelectPreset?: (presetName: string) => void;
  onSelectFile?: (filePath: string) => void;
  onOpenSettings?: () => void;
  onOpenCommand?: (commandId: string) => void;
}

const COMMANDS: CommandPaletteItem[] = [
  { id: 'cmd-convert', type: 'command', title: '开始转换', subtitle: '转换当前图片', icon: '▶', shortcut: 'Enter', action: () => {} },
  { id: 'cmd-download', type: 'command', title: '下载结果', subtitle: '下载 SVG/PDF/PNG', icon: '⬇', shortcut: 'Ctrl+D', action: () => {} },
  { id: 'cmd-open', type: 'command', title: '打开文件', subtitle: '打开图片文件', icon: '📂', shortcut: 'Ctrl+O', action: () => {} },
  { id: 'cmd-settings', type: 'command', title: '设置', subtitle: '应用设置', icon: '⚙', shortcut: 'Ctrl+,', action: () => {} },
  { id: 'cmd-queue', type: 'command', title: '显示队列', subtitle: '展开文件队列', icon: '📁', shortcut: '', action: () => {} },
  { id: 'cmd-clear', type: 'command', title: '清空队列', subtitle: '移除所有任务', icon: '🗑', shortcut: '', action: () => {} },
];

const SETTINGS_ITEMS: CommandPaletteItem[] = [
  { id: 'set-theme', type: 'setting', title: '切换主题', subtitle: '亮色 / 暗色', icon: '☀', action: () => {} },
  { id: 'set-lang', type: 'setting', title: '语言', subtitle: '中文 / English', icon: '🌐', action: () => {} },
  { id: 'set-output', type: 'setting', title: '默认输出目录', subtitle: '更改保存位置', icon: '📂', action: () => {} },
];

const CommandPalette: React.FC<CommandPaletteProps> = ({
  open,
  onClose,
  presets = [],
  recentFiles = [],
  onSelectPreset,
  onSelectFile,
  onOpenSettings,
  onOpenCommand,
}) => {
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const items = useMemo(() => {
    const all: CommandPaletteItem[] = [];

    // Presets
    presets.forEach((p) => {
      all.push({
        id: `preset-${p.name}`,
        type: 'preset',
        title: p.displayName || p.name,
        subtitle: p.description || (p.isBuiltin ? '内置预设' : '用户预设'),
        icon: p.isBuiltin ? '🔧' : '✨',
        action: () => onSelectPreset?.(p.name),
      });
    });

    // Commands
    COMMANDS.forEach((c) => {
      all.push({
        ...c,
        action: () => onOpenCommand?.(c.id),
      });
    });

    // Recent files
    recentFiles.forEach((f, i) => {
      const name = f.split(/[/\\]/).pop() || f;
      all.push({
        id: `file-${i}`,
        type: 'file',
        title: name,
        subtitle: f,
        icon: '🖼',
        action: () => onSelectFile?.(f),
      });
    });

    // Settings
    SETTINGS_ITEMS.forEach((s) => {
      all.push({
        ...s,
        action: () => {
          if (s.id === 'set-settings') onOpenSettings?.();
          else onOpenCommand?.(s.id);
        },
      });
    });

    if (!query.trim()) return all;

    const q = query.toLowerCase();
    return all.filter(
      (item) =>
        item.title.toLowerCase().indexOf(q) !== -1 ||
        (item.subtitle && item.subtitle.toLowerCase().indexOf(q) !== -1) ||
        (item.type as string).indexOf(q) !== -1
    );
  }, [query, presets, recentFiles, onSelectPreset, onSelectFile, onOpenSettings, onOpenCommand]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [open]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedIndex((i) => Math.min(i + 1, items.length - 1));
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedIndex((i) => Math.max(i - 1, 0));
      } else if (e.key === 'Enter') {
        e.preventDefault();
        const item = items[selectedIndex];
        if (item) {
          item.action();
          onClose();
        }
      }
    },
    [items, selectedIndex, onClose]
  );

  useEffect(() => {
    if (!listRef.current) return;
    const selectedEl = listRef.current.querySelector(`[data-index="${selectedIndex}"]`) as HTMLElement;
    if (selectedEl) {
      selectedEl.scrollIntoView({ block: 'nearest' });
    }
  }, [selectedIndex]);

  if (!open) return null;

  const groupLabels: Record<string, string> = {
    preset: '预设',
    command: '命令',
    file: '最近文件',
    setting: '设置',
  };

  let lastType = '';

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        background: 'rgba(0,0,0,0.3)',
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        zIndex: 100,
        paddingTop: '12vh',
      }}
      onClick={onClose}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 600,
          background: '#ffffff',
          borderRadius: 12,
          boxShadow: '0 20px 60px rgba(0,0,0,0.2)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          maxHeight: '70vh',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 10,
            padding: '14px 16px',
            borderBottom: '1px solid #e5e3df',
          }}
        >
          <span style={{ fontSize: 18, color: '#6b6b6b' }}>🔍</span>
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="搜索预设、命令、文件..."
            style={{
              flex: 1,
              border: 'none',
              outline: 'none',
              fontSize: 15,
              fontFamily: 'inherit',
              color: '#1a1a1a',
              background: 'transparent',
            }}
          />
          <kbd
            style={{
              fontSize: 11,
              fontFamily: 'var(--font-mono)',
              background: '#f5f5f7',
              padding: '2px 6px',
              borderRadius: 4,
              border: '1px solid #e5e3df',
              color: '#6b6b6b',
            }}
          >
            Esc
          </kbd>
        </div>

        {/* Results */}
        <div
          ref={listRef}
          style={{
            flex: 1,
            overflow: 'auto',
            padding: '8px 0',
          }}
        >
          {items.length === 0 && (
            <div
              style={{
                padding: 32,
                textAlign: 'center',
                color: '#6b6b6b',
                fontSize: 14,
              }}
            >
              未找到结果，尝试其他关键词
            </div>
          )}

          {items.map((item, index) => {
            const showGroup = item.type !== lastType;
            lastType = item.type;
            const isSelected = index === selectedIndex;

            return (
              <React.Fragment key={item.id}>
                {showGroup && (
                  <div
                    style={{
                      padding: '6px 16px 4px',
                      fontSize: 11,
                      fontWeight: 600,
                      textTransform: 'uppercase',
                      letterSpacing: '0.5px',
                      color: '#a1a1a6',
                    }}
                  >
                    {groupLabels[item.type] || item.type}
                  </div>
                )}
                <div
                  data-index={index}
                  onClick={() => {
                    item.action();
                    onClose();
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 10,
                    padding: '8px 16px',
                    cursor: 'pointer',
                    background: isSelected ? 'rgba(196, 92, 38, 0.08)' : 'transparent',
                    borderLeft: isSelected ? '3px solid #c45c26' : '3px solid transparent',
                    transition: 'background 0.1s ease',
                  }}
                  onMouseEnter={() => setSelectedIndex(index)}
                >
                  <span style={{ fontSize: 16, width: 20, textAlign: 'center' }}>{item.icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div
                      style={{
                        fontSize: 14,
                        fontWeight: 500,
                        color: '#1a1a1a',
                        whiteSpace: 'nowrap',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                      }}
                    >
                      {item.title}
                    </div>
                    {item.subtitle && (
                      <div
                        style={{
                          fontSize: 12,
                          color: '#6b6b6b',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                        }}
                      >
                        {item.subtitle}
                      </div>
                    )}
                  </div>
                  {item.shortcut && (
                    <kbd
                      style={{
                        fontSize: 11,
                        fontFamily: 'var(--font-mono)',
                        background: '#f5f5f7',
                        padding: '2px 6px',
                        borderRadius: 4,
                        border: '1px solid #e5e3df',
                        color: '#6b6b6b',
                        flexShrink: 0,
                      }}
                    >
                      {item.shortcut}
                    </kbd>
                  )}
                </div>
              </React.Fragment>
            );
          })}
        </div>

        {/* Footer hint */}
        <div
          style={{
            display: 'flex',
            gap: 12,
            padding: '8px 16px',
            borderTop: '1px solid #e5e3df',
            fontSize: 11,
            color: '#a1a1a6',
          }}
        >
          <span>↑↓ 选择</span>
          <span>↵ 执行</span>
          <span>Esc 关闭</span>
        </div>
      </div>
    </div>
  );
};

export default CommandPalette;
