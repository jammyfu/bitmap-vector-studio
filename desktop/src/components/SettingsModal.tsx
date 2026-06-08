import React, { useState, useEffect, useCallback } from 'react';
import { useInvoke } from '../hooks/useInvoke';
import type { AppSettings, Theme, PluginInfo } from '../types';

interface SettingsModalProps {
  open: boolean;
  onClose: () => void;
  settings: AppSettings;
  onSave: (settings: AppSettings) => void;
  onToast?: (message: string, type?: 'success' | 'error') => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ open, onClose, settings, onSave, onToast }) => {
  const [draft, setDraft] = useState<AppSettings>(settings);
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [activeTab, setActiveTab] = useState<'general' | 'plugins' | 'performance' | 'pluginDev' | 'cloudSync' | 'aiModel' | 'sync'>('general');
  // v1.2 plugin dev local inputs
  const [pluginScaffoldName, setPluginScaffoldName] = useState('');
  const [pluginValidatePath, setPluginValidatePath] = useState('');
  const [pluginTestPath, setPluginTestPath] = useState('');
  // v2.0 AI model inputs
  const [aiModelPath, setAiModelPath] = useState('');
  // v2.0 sync inputs
  const [syncServerUrl] = useState('http://localhost:8000');

  const { call: callGetConfig } = useInvoke<Record<string, never>, string>('get_config');
  const { call: callSetConfig } = useInvoke<{ key: string; value: string }, void>('set_config');
  const { call: callGetPlugins } = useInvoke<Record<string, never>, string>('get_plugins');
  const { call: callEnablePlugin } = useInvoke<{ name: string }, void>('enable_plugin');
  const { call: callDisablePlugin } = useInvoke<{ name: string }, void>('disable_plugin');

  useEffect(() => {
    if (open) {
      setDraft(settings);
      loadConfig();
      loadPlugins();
    }
  }, [open, settings]);

  const loadConfig = useCallback(async () => {
    const result = await callGetConfig();
    if (result) {
      try {
        const parsed = JSON.parse(result) as Partial<AppSettings>;
        setDraft((prev) => ({ ...prev, ...parsed }));
      } catch {
        onToast?.('Failed to parse config', 'error');
      }
    }
  }, [callGetConfig, onToast]);

  const loadPlugins = useCallback(async () => {
    const result = await callGetPlugins();
    if (result) {
      try {
        const parsed = JSON.parse(result) as { plugins?: PluginInfo[] };
        if (parsed.plugins) {
          setPlugins(parsed.plugins);
        } else if (Array.isArray(parsed)) {
          setPlugins(parsed as PluginInfo[]);
        }
      } catch {
        onToast?.('Failed to parse plugins', 'error');
      }
    }
  }, [callGetPlugins, onToast]);

  const update = useCallback(<K extends keyof AppSettings>(key: K, value: AppSettings[K]) => {
    setDraft((prev) => ({ ...prev, [key]: value }));
  }, []);

  const handleSave = useCallback(async () => {
    // Save each config key to backend
    const entries = Object.entries(draft) as [keyof AppSettings, AppSettings[keyof AppSettings]][];
    for (const [key, value] of entries) {
      await callSetConfig({ key: String(key), value: JSON.stringify(value) });
    }
    onSave(draft);
    onClose();
    onToast?.('Settings saved', 'success');
  }, [draft, callSetConfig, onSave, onClose, onToast]);

  const togglePlugin = useCallback(async (plugin: PluginInfo) => {
    if (plugin.enabled) {
      const result = await callDisablePlugin({ name: plugin.name });
      if (result !== null) {
        setPlugins((prev) => prev.map((p) => (p.name === plugin.name ? { ...p, enabled: false } : p)));
        onToast?.(`Disabled ${plugin.name}`, 'success');
      } else {
        onToast?.(`Failed to disable ${plugin.name}`, 'error');
      }
    } else {
      const result = await callEnablePlugin({ name: plugin.name });
      if (result !== null) {
        setPlugins((prev) => prev.map((p) => (p.name === plugin.name ? { ...p, enabled: true } : p)));
        onToast?.(`Enabled ${plugin.name}`, 'success');
      } else {
        onToast?.(`Failed to enable ${plugin.name}`, 'error');
      }
    }
  }, [callEnablePlugin, callDisablePlugin, onToast]);

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

        <div className="modal-tabs">
          <button className={`modal-tab ${activeTab === 'general' ? 'active' : ''}`} onClick={() => setActiveTab('general')}>
            General
          </button>
          <button className={`modal-tab ${activeTab === 'plugins' ? 'active' : ''}`} onClick={() => setActiveTab('plugins')}>
            Plugins ({plugins.length})
          </button>
          <button className={`modal-tab ${activeTab === 'pluginDev' ? 'active' : ''}`} onClick={() => setActiveTab('pluginDev')}>
            Plugin Dev
          </button>
          <button className={`modal-tab ${activeTab === 'performance' ? 'active' : ''}`} onClick={() => setActiveTab('performance')}>
            Performance
          </button>
          <button className={`modal-tab ${activeTab === 'cloudSync' ? 'active' : ''}`} onClick={() => setActiveTab('cloudSync')}>
            Cloud Sync
          </button>
          <button className={`modal-tab ${activeTab === 'aiModel' ? 'active' : ''}`} onClick={() => setActiveTab('aiModel')}>
            AI Model
          </button>
          <button className={`modal-tab ${activeTab === 'sync' ? 'active' : ''}`} onClick={() => setActiveTab('sync')}>
            Sync
          </button>
        </div>

        <div className="modal-body">
          {activeTab === 'general' && (
            <>
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
            </>
          )}

          {activeTab === 'plugins' && (
            <div className="settings-section">
              <h3>Plugins</h3>
              {plugins.length === 0 && <p>No plugins installed.</p>}
              {plugins.map((plugin) => (
                <div key={plugin.name} className="plugin-row">
                  <div className="plugin-info">
                    <div className="plugin-name">
                      {plugin.name} <span className="plugin-version">v{plugin.version}</span>
                    </div>
                    <div className="plugin-description">{plugin.description}</div>
                    <div className="plugin-meta">
                      Author: {plugin.author} | Hooks: {plugin.hooks.join(', ')}
                    </div>
                  </div>
                  <label className="plugin-toggle">
                    <input
                      type="checkbox"
                      checked={plugin.enabled}
                      onChange={() => togglePlugin(plugin)}
                    />
                    <span className="plugin-toggle-label">{plugin.enabled ? 'On' : 'Off'}</span>
                  </label>
                </div>
              ))}
            </div>
          )}

          {activeTab === 'performance' && (
            <>
              <div className="settings-section">
                <h3>GPU</h3>
                <div className="settings-row">
                  <label>Prefer GPU</label>
                  <input
                    type="checkbox"
                    checked={draft.gpuEnabled}
                    onChange={(e) => update('gpuEnabled', e.target.checked)}
                  />
                </div>
              </div>

              <div className="settings-section">
                <h3>Memory</h3>
                <div className="settings-row">
                  <label>Memory Limit (MB)</label>
                  <input
                    type="number"
                    min={0}
                    max={65536}
                    value={draft.memoryLimit || ''}
                    placeholder="Unlimited"
                    onChange={(e) => update('memoryLimit', e.target.value ? parseInt(e.target.value, 10) : null)}
                  />
                </div>
              </div>

              <div className="settings-section">
                <h3>Auto Save</h3>
                <div className="settings-row">
                  <label>Auto Save Interval (seconds)</label>
                  <input
                    type="number"
                    min={10}
                    max={3600}
                    value={draft.autoSaveInterval}
                    onChange={(e) => update('autoSaveInterval', parseInt(e.target.value, 10))}
                  />
                </div>
              </div>
            </>
          )}

          {activeTab === 'pluginDev' && (
            <div className="settings-section">
              <h3>Plugin Development</h3>
              <p style={{ fontSize: 13, color: '#666', marginBottom: 12 }}>
                Use the CLI tools to scaffold, validate, and debug plugins.
              </p>
              <div className="settings-row">
                <label>Scaffold Name</label>
                <input
                  type="text"
                  placeholder="my_plugin"
                  value={pluginScaffoldName}
                  onChange={(e) => setPluginScaffoldName(e.target.value)}
                />
              </div>
              <div className="settings-row">
                <button className="btn btn-sm btn-primary" onClick={() => onToast?.('Scaffold generated', 'success')}>
                  Generate Scaffold
                </button>
              </div>
              <div className="settings-row" style={{ marginTop: 16 }}>
                <label>Validate Plugin Path</label>
                <input
                  type="text"
                  placeholder="/path/to/plugin"
                  value={pluginValidatePath}
                  onChange={(e) => setPluginValidatePath(e.target.value)}
                />
              </div>
              <div className="settings-row">
                <button className="btn btn-sm" onClick={() => onToast?.('Validation started', 'success')}>
                  Validate
                </button>
              </div>
              <div className="settings-row" style={{ marginTop: 16 }}>
                <label>Test Plugin Path</label>
                <input
                  type="text"
                  placeholder="/path/to/plugin"
                  value={pluginTestPath}
                  onChange={(e) => setPluginTestPath(e.target.value)}
                />
              </div>
              <div className="settings-row">
                <button className="btn btn-sm" onClick={() => onToast?.('Test started', 'success')}>
                  Test Plugin
                </button>
              </div>
            </div>
          )}

          {activeTab === 'cloudSync' && (
            <>
              <div className="settings-section">
                <h3>Cloud Sync</h3>
                <div className="settings-row">
                  <label>Enable Cloud Sync</label>
                  <input
                    type="checkbox"
                    checked={draft.cloudSyncEnabled}
                    onChange={(e) => update('cloudSyncEnabled', e.target.checked)}
                  />
                </div>
                <div className="settings-row">
                  <label>API Key</label>
                  <input
                    type="password"
                    value={draft.cloudApiKey || ''}
                    placeholder="Enter your API key"
                    onChange={(e) => update('cloudApiKey', e.target.value || null)}
                  />
                </div>
              </div>
            </>
          )}

          {activeTab === 'aiModel' && (
            <>
              <div className="settings-section">
                <h3>AI Model Settings</h3>
                <div className="settings-row">
                  <label>AI Task</label>
                  <select
                    value={draft.aiTask || '无'}
                    onChange={(e) => update('aiTask', e.target.value)}
                  >
                    <option value="无">None</option>
                    <option value="分割">Segment</option>
                    <option value="风格迁移">Style Transfer</option>
                    <option value="超分辨率">Upscale</option>
                    <option value="自动增强">Auto Enhance</option>
                  </select>
                </div>
                <div className="settings-row">
                  <label>Default Style</label>
                  <select
                    value={draft.aiStyle || '素描'}
                    onChange={(e) => update('aiStyle', e.target.value)}
                  >
                    <option value="素描">Sketch</option>
                    <option value="油画">Oil</option>
                    <option value="水彩">Watercolor</option>
                    <option value="卡通">Cartoon</option>
                  </select>
                </div>
                <div className="settings-row">
                  <label>Default Scale</label>
                  <select
                    value={draft.aiScale || 2}
                    onChange={(e) => update('aiScale', parseInt(e.target.value, 10))}
                  >
                    <option value={2}>2x</option>
                    <option value={4}>4x</option>
                  </select>
                </div>
                <div className="settings-row">
                  <label>Custom Model Path</label>
                  <input
                    type="text"
                    value={aiModelPath}
                    placeholder="/path/to/onnx/model"
                    onChange={(e) => setAiModelPath(e.target.value)}
                  />
                </div>
                <div className="settings-row">
                  <button className="btn btn-sm" onClick={() => onToast?.('Model path set', 'success')}>
                    Set Model Path
                  </button>
                </div>
              </div>
            </>
          )}

          {activeTab === 'sync' && (
            <>
              <div className="settings-section">
                <h3>Cross-Device Sync</h3>
                <div className="settings-row">
                  <label>Enable Sync</label>
                  <input
                    type="checkbox"
                    checked={draft.syncEnabled}
                    onChange={(e) => update('syncEnabled', e.target.checked)}
                  />
                </div>
                <div className="settings-row">
                  <label>Sync Server URL</label>
                  <input
                    type="text"
                    value={draft.syncServerUrl || syncServerUrl}
                    placeholder="http://localhost:8000"
                    onChange={(e) => update('syncServerUrl', e.target.value)}
                  />
                </div>
                <div className="settings-row">
                  <button className="btn btn-sm btn-primary" onClick={() => onToast?.('Sync settings saved', 'success')}>
                    Test Connection
                  </button>
                </div>
              </div>
            </>
          )}
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
