import React, { useState, useEffect, useCallback } from 'react';
import type { AppSettings, Theme } from '../types';

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
  settings: AppSettings;
  onSave: (settings: AppSettings) => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ open, onClose, settings, onSave }) => {
  const [draft, setDraft] = useState<AppSettings>(settings);

  useEffect(() => {
    if (open) {
      setDraft(settings);
    }
  }, [open, settings]);

  const update = useCallback(<K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSave = useCallback(() => {
    onSave(draft);
    onClose();
  }, [draft, onSave, onClose]);

  if (!open) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Settings</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="settings-section">
            <h3>General</h3>
            <div className="settings-row">
              <label>Language</label>
              <select value={draft.language} onChange={(e) => update('language', e.target.value)}>
                <option value="en">English</option>
                <option value="zh">中文</option>
                <option value="ja">日本語</option>
                <option value="de">Deutsch</option>
              </select>
            </div>
            <div className="settings-row">
              <label>Theme</label>
              <select value={draft.theme} onChange={(e) => update('theme', e.target.value as Theme)}>
                <option value="light">Light</option>
                <option value="dark">Dark</option>
                <option value="system">System</option>
              </select>
            </div>
          </div>

          <div className="settings-section">
            <h3>Output</h3>
            <div className="settings-row">
              <label>Default Output Directory</label>
              <input
                type="text"
                value={draft.defaultOutputDir || ''}
                placeholder="Same as input"
                onChange={(e) => update('defaultOutputDir', e.target.value || null)}
              />
            </div>
            <div className="settings-row">
              <label>Default Format</label>
              <select value={draft.defaultFormat} onChange={(e) => update('defaultFormat', e.target.value as AppSettings['defaultFormat'])}>
                <option value="svg">SVG</option>
                <option value="pdf">PDF</option>
                <option value="png">PNG</option>
              </select>
            </div>
            <div className="settings-row">
              <label>Optimize Level</label>
              <input
                type="range"
                min={0}
                max={3}
                step={1}
                value={draft.optimizeLevel}
                onChange={(e) => update('optimizeLevel', parseInt(e.target.value, 10))}
              />
              <span>{draft.optimizeLevel}</span>
            </div>
          </div>

          <div className="settings-section">
            <h3>External Editor</h3>
            <div className="settings-row">
              <label>Editor Path</label>
              <input
                type="text"
                value={draft.externalEditor || ''}
                placeholder="e.g., /usr/bin/inkscape"
                onChange={(e) => update('externalEditor', e.target.value || null)}
              />
            </div>
          </div>

          <div className="settings-section">
            <h3>API Service</h3>
            <div className="settings-row">
              <label>Host</label>
              <input type="text" value={draft.apiHost} onChange={(e) => update('apiHost', e.target.value)} />
            </div>
            <div className="settings-row">
              <label>Port</label>
              <input type="number" value={draft.apiPort} onChange={(e) => update('apiPort', parseInt(e.target.value, 10))} />
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn" onClick={onClose}>
            Cancel
          </button>
          <button className="btn btn-primary" onClick={handleSave}>
            Save
          </button>
        </div>
      </div>
    </div>
  );
};
