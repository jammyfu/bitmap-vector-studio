import React, { useState, useEffect, useCallback } from 'react';
import { useInvoke } from '../hooks/useInvoke';

interface MarketPreset {
  id: string;
  name: string;
  description: string;
  author: string;
  downloads: number;
  tags: string[];
  installed?: boolean;
}

interface MarketBrowserProps {
  visible: boolean;
  onClose: () => void;
  onToast?: (message: string, type?: 'success' | 'error') => void;
}

export const MarketBrowser: React.FC<MarketBrowserProps> = ({ visible, onClose, onToast }) => {
  const [presets, setPresets] = useState<MarketPreset[]>([]);
  const [filtered, setFiltered] = useState<MarketPreset[]>([]);
  const [search, setSearch] = useState('');
  const [installingId, setInstallingId] = useState<string | null>(null);

  const { call: callMarketList, loading: loadingList } = useInvoke<Record<string, never>, string>('market_list');
  const { call: callMarketInstall } = useInvoke<{ id: string; name?: string }, string>('market_install');

  useEffect(() => {
    if (visible) {
      loadPresets();
    }
  }, [visible]);

  const loadPresets = useCallback(async () => {
    const result = await callMarketList();
    if (result) {
      try {
        const parsed = JSON.parse(result) as { presets?: MarketPreset[] };
        const list = parsed.presets || (Array.isArray(parsed) ? parsed : []);
        setPresets(list);
        setFiltered(list);
      } catch {
        onToast?.('Failed to load market presets', 'error');
      }
    } else {
      onToast?.('Failed to fetch market list', 'error');
    }
  }, [callMarketList, onToast]);

  useEffect(() => {
    const term = search.trim().toLowerCase();
    if (!term) {
      setFiltered(presets);
      return;
    }
    setFiltered(
      presets.filter(
        (p) =>
          p.name.toLowerCase().includes(term) ||
          p.description.toLowerCase().includes(term) ||
          p.tags.some((t) => t.toLowerCase().includes(term))
      )
    );
  }, [search, presets]);

  const handleInstall = useCallback(async (preset: MarketPreset) => {
    setInstallingId(preset.id);
    const result = await callMarketInstall({ id: preset.id, name: preset.name });
    setInstallingId(null);
    if (result) {
      setPresets((prev) =>
        prev.map((p) => (p.id === preset.id ? { ...p, installed: true } : p))
      );
      onToast?.(`Installed ${preset.name}`, 'success');
    } else {
      onToast?.(`Failed to install ${preset.name}`, 'error');
    }
  }, [callMarketInstall, onToast]);

  if (!visible) return null;

  const popular = [...presets].sort((a, b) => b.downloads - a.downloads).slice(0, 5);

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Preset Market</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="market-search-row">
            <input
              className="market-search-input"
              type="text"
              placeholder="Search presets..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button className="btn btn-sm" onClick={loadPresets} disabled={loadingList}>
              {loadingList ? 'Loading...' : 'Refresh'}
            </button>
          </div>

          {popular.length > 0 && !search.trim() && (
            <div className="market-section">
              <h3>🔥 Popular</h3>
              <div className="market-grid">
                {popular.map((preset) => (
                  <div key={`pop-${preset.id}`} className="market-card market-card-popular">
                    <div className="market-card-header">
                      <span className="market-card-name">{preset.name}</span>
                      <span className="market-card-downloads">{preset.downloads} ↓</span>
                    </div>
                    <div className="market-card-desc">{preset.description}</div>
                    <div className="market-card-tags">
                      {preset.tags.map((t) => (
                        <span key={t} className="market-tag">
                          {t}
                        </span>
                      ))}
                    </div>
                    <button
                      className="btn btn-sm btn-primary"
                      onClick={() => handleInstall(preset)}
                      disabled={installingId === preset.id || preset.installed}
                    >
                      {preset.installed ? 'Installed' : installingId === preset.id ? 'Installing...' : 'Install'}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="market-section">
            <h3>{search.trim() ? `Results (${filtered.length})` : 'All Presets'}</h3>
            {filtered.length === 0 && <p>No presets found.</p>}
            <div className="market-list">
              {filtered.map((preset) => (
                <div key={preset.id} className="market-row">
                  <div className="market-row-info">
                    <div className="market-row-name">
                      {preset.name} <span className="market-row-author">by {preset.author}</span>
                    </div>
                    <div className="market-row-desc">{preset.description}</div>
                    <div className="market-row-meta">
                      <span>{preset.downloads} downloads</span>
                      <span className="market-row-tags">
                        {preset.tags.map((t) => (
                          <span key={t} className="market-tag">
                            {t}
                          </span>
                        ))}
                      </span>
                    </div>
                  </div>
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => handleInstall(preset)}
                    disabled={installingId === preset.id || preset.installed}
                  >
                    {preset.installed ? 'Installed' : installingId === preset.id ? 'Installing...' : 'Install'}
                  </button>
                </div>
              ))}
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
