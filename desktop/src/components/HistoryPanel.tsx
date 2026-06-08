import React, { useState, useEffect, useCallback } from 'react';
import { useInvoke } from '../hooks/useInvoke';

interface HistoryEntry {
  id: string;
  fileName: string;
  inputPath: string;
  outputPath: string;
  status: string;
  preset: string;
  options?: string;
  timestamp?: string;
  duration?: number;
}

interface HistoryPanelProps {
  visible: boolean;
  onClose: () => void;
  onLoadTask?: (entry: HistoryEntry) => void;
  onToast?: (message: string, type?: 'success' | 'error') => void;
}

export const HistoryPanel: React.FC<HistoryPanelProps> = ({ visible, onClose, onLoadTask, onToast }) => {
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [search, setSearch] = useState('');
  const [limit, setLimit] = useState(20);

  const { call: callGetHistory, loading } = useInvoke<{ limit: number }, string>('get_history');

  useEffect(() => {
    if (visible) {
      loadHistory();
    }
  }, [visible, limit]);

  const loadHistory = useCallback(async () => {
    const result = await callGetHistory({ limit });
    if (result) {
      try {
        const parsed = JSON.parse(result) as { history?: HistoryEntry[] };
        const list = parsed.history || (Array.isArray(parsed) ? parsed : []);
        setHistory(list as HistoryEntry[]);
      } catch {
        onToast?.('Failed to parse history', 'error');
      }
    } else {
      onToast?.('Failed to fetch history', 'error');
    }
  }, [callGetHistory, limit, onToast]);

  const filtered = search.trim()
    ? history.filter(
        (h) =>
          h.fileName.toLowerCase().includes(search.trim().toLowerCase()) ||
          h.preset.toLowerCase().includes(search.trim().toLowerCase())
      )
    : history;

  const handleExportReport = useCallback(() => {
    const report = filtered.map((h) => ({
      file: h.fileName,
      input: h.inputPath,
      output: h.outputPath,
      preset: h.preset,
      status: h.status,
      timestamp: h.timestamp,
      duration: h.duration,
    }));
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `bvs-history-report-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
    onToast?.('Report exported', 'success');
  }, [filtered, onToast]);

  if (!visible) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content modal-large" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>History</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">
            ×
          </button>
        </div>

        <div className="modal-body">
          <div className="history-toolbar">
            <input
              className="history-search-input"
              type="text"
              placeholder="Search history..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <select value={limit} onChange={(e) => setLimit(parseInt(e.target.value, 10))}>
              <option value={10}>Last 10</option>
              <option value={20}>Last 20</option>
              <option value={50}>Last 50</option>
              <option value={100}>Last 100</option>
            </select>
            <button className="btn btn-sm" onClick={loadHistory} disabled={loading}>
              {loading ? 'Loading...' : 'Refresh'}
            </button>
            <button className="btn btn-sm btn-secondary" onClick={handleExportReport}>
              Export Report
            </button>
          </div>

          <div className="history-list">
            {filtered.length === 0 && <p>No history entries found.</p>}
            {filtered.map((entry) => (
              <div
                key={entry.id}
                className="history-row"
                onClick={() => onLoadTask?.(entry)}
                title="Click to load parameters"
              >
                <div className="history-row-main">
                  <span className="history-row-status history-row-status-completed">✓</span>
                  <span className="history-row-filename" title={entry.fileName}>
                    {entry.fileName}
                  </span>
                  <span className="history-row-preset">{entry.preset}</span>
                </div>
                <div className="history-row-meta">
                  {entry.timestamp && <span>{entry.timestamp}</span>}
                  {entry.duration !== undefined && <span>{entry.duration}ms</span>}
                  <span className="history-row-path" title={entry.outputPath}>
                    {entry.outputPath}
                  </span>
                </div>
              </div>
            ))}
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
