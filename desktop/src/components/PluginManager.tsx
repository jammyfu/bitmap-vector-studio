import React, { useState, useEffect, useCallback } from 'react';
import { useInvoke } from '../hooks/useInvoke';
import type { PluginInfo } from '../types';

interface PluginManagerProps {
  visible: boolean;
  onClose: () => void;
  onToast?: (message: string, type?: 'success' | 'error') => void;
}

export const PluginManager: React.FC<PluginManagerProps> = ({ visible, onClose, onToast }) => {
  const [plugins, setPlugins] = useState<PluginInfo[]>([]);
  const [selectedPlugin, setSelectedPlugin] = useState<PluginInfo | null>(null);
  const [search, setSearch] = useState('');

  const { call: callGetPlugins } = useInvoke<Record<string, never>, string>('get_plugins');
  const { call: callEnablePlugin } = useInvoke<{ name: string }, void>('enable_plugin');
  const { call: callDisablePlugin } = useInvoke<{ name: string }, void>('disable_plugin');

  useEffect(() => {
    if (visible) {
      loadPlugins();
    }
  }, [visible]);

  const loadPlugins = useCallback(async () => {
    const result = await callGetPlugins();
    if (result) {
      try {
        const parsed = JSON.parse(result) as { plugins?: PluginInfo[] };
        const list = parsed.plugins || (Array.isArray(parsed) ? parsed : []);
        setPlugins(list as PluginInfo[]);
      } catch {
        onToast?.('Failed to load plugins', 'error');
      }
    } else {
      onToast?.('Failed to fetch plugins', 'error');
    }
  }, [callGetPlugins, onToast]);

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

  const filtered = search.trim()
    ? plugins.filter(
        (p) =>
          p.name.toLowerCase().includes(search.trim().toLowerCase()) ||
          p.description.toLowerCase().includes(search.trim().toLowerCase())
      )
    : plugins;

  if (!visible) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Plugin Manager</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="plugin-search-row">
            <input
              className="plugin-search-input"
              type="text"
              placeholder="Search plugins..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button className="btn btn-sm" onClick={loadPlugins}>
              Refresh
            </button>
          </div>

          <div className="plugin-layout">
            <div className="plugin-list">
              {filtered.length === 0 && <p>No plugins found.</p>}
              {filtered.map((plugin) => (
                <div
                  key={plugin.name}
                  className={`plugin-list-item ${selectedPlugin?.name === plugin.name ? 'selected' : ''} ${plugin.enabled ? 'enabled' : ''}`}
                  onClick={() => setSelectedPlugin(plugin)}
                >
                  <div className="plugin-list-name">
                    {plugin.name} <span className="plugin-list-version">v{plugin.version}</span>
                  </div>
                  <div className="plugin-list-status">{plugin.enabled ? '● On' : '○ Off'}</div>
                </div>
              ))}
            </div>

            <div className="plugin-detail">
              {selectedPlugin ? (
                <>
                  <h3>{selectedPlugin.name}</h3>
                  <div className="plugin-detail-meta">
                    <span>Version: {selectedPlugin.version}</span>
                    <span>Author: {selectedPlugin.author}</span>
                  </div>
                  <p>{selectedPlugin.description}</p>
                  <div className="plugin-detail-hooks">
                    <strong>Hooks:</strong> {selectedPlugin.hooks.join(', ') || 'None'}
                  </div>
                  <div className="plugin-detail-actions">
                    <button
                      className={`btn ${selectedPlugin.enabled ? 'btn-danger' : 'btn-primary'}`}
                      onClick={() => togglePlugin(selectedPlugin)}
                    >
                      {selectedPlugin.enabled ? 'Disable' : 'Enable'}
                    </button>
                  </div>
                </>
              ) : (
                <div className="plugin-detail-empty">Select a plugin to view details</div>
              )}
            </div>
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
};
