import React, { useState, useCallback, useEffect } from 'react';
import { useInvoke } from '../hooks/useInvoke';
import type { ConversionTask } from '../types';

interface HistoryEntry {
  id: string;
  fileName: string;
  inputPath: string;
  outputPath: string;
  status: string;
  preset: string;
  timestamp?: string;
}

interface SidebarProps {
  tasks: ConversionTask[];
  onRemoveTask: (id: string) => void;
  onCancelTask: (id: string) => void;
  onReorder: (startIndex: number, endIndex: number) => void;
  onSelectTask?: (id: string) => void;
  selectedTaskId?: string | null;
  onAddFiles?: (files: string[]) => void;
  onLoadHistoryParams?: (params: unknown) => void;
  onToast?: (message: string, type?: 'success' | 'error') => void;
  // v1.1 workspace
  onSaveWorkspace?: () => void;
  onLoadWorkspace?: (name: string) => void;
  onRestoreLast?: () => void;
  workspaces?: { name: string }[];
  hasCrashRecovery?: boolean;
  // v1.1 checkpoint
  checkpoints?: { name: string; queue_id: string }[];
  onResumeCheckpoint?: (id: string) => void;
}

const statusIcon: Record<ConversionTask['status'], string> = {
  pending: '⏳',
  running: '▶',
  completed: '✓',
  failed: '✗',
  cancelled: '⊘',
};

const statusLabel: Record<ConversionTask['status'], string> = {
  pending: 'Pending',
  running: 'Running',
  completed: 'Done',
  failed: 'Failed',
  cancelled: 'Cancelled',
};

export const Sidebar: React.FC<SidebarProps> = ({
  tasks,
  onRemoveTask,
  onCancelTask,
  onReorder,
  onSelectTask,
  selectedTaskId,
  onAddFiles,
  onLoadHistoryParams,
  onToast,
  onSaveWorkspace,
  onLoadWorkspace,
  onRestoreLast,
  workspaces = [],
  hasCrashRecovery = false,
  checkpoints = [],
  onResumeCheckpoint,
}) => {
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; taskId: string } | null>(null);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [showHistory, setShowHistory] = useState(false);
  const dragOverIndex = React.useRef<number | null>(null);

  const { call: callGetHistory } = useInvoke<{ limit: number }, string>('get_history');
  const { call: callOpenFileDialog } = useInvoke<Record<string, never>, string[]>('open_file_dialog');

  // Load history from backend
  useEffect(() => {
    async function loadHistory() {
      const result = await callGetHistory({ limit: 20 });
      if (result) {
        try {
          const parsed = JSON.parse(result) as { history?: HistoryEntry[] };
          if (parsed.history) {
            setHistory(parsed.history);
          } else if (Array.isArray(parsed)) {
            setHistory(parsed);
          }
        } catch {
          // ignore parse errors
        }
      }
    }
    loadHistory();
  }, [callGetHistory]);

  const handleAddFiles = useCallback(async () => {
    const files = await callOpenFileDialog();
    if (files && files.length > 0) {
      onAddFiles?.(files);
    }
  }, [callOpenFileDialog, onAddFiles]);

  const handleContextMenu = useCallback((e: React.MouseEvent, taskId: string) => {
    e.preventDefault();
    setContextMenu({ x: e.clientX, y: e.clientY, taskId });
  }, []);

  const closeContextMenu = useCallback(() => setContextMenu(null), []);

  const handleDragStart = useCallback((index: number) => {
    setDragIndex(index);
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent, index: number) => {
    e.preventDefault();
    dragOverIndex.current = index;
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (dragIndex !== null && dragOverIndex.current !== null && dragIndex !== dragOverIndex.current) {
        onReorder(dragIndex, dragOverIndex.current);
      }
      setDragIndex(null);
      dragOverIndex.current = null;
    },
    [dragIndex, onReorder]
  );

  const handleDragEnd = useCallback(() => {
    setDragIndex(null);
    dragOverIndex.current = null;
  }, []);

  const handleHistoryClick = useCallback((entry: HistoryEntry) => {
    onLoadHistoryParams?.({
      inputPath: entry.inputPath,
      preset: entry.preset,
    });
    onToast?.(`Loaded history: ${entry.fileName}`, 'success');
  }, [onLoadHistoryParams, onToast]);

  return (
    <div className="sidebar" onClick={closeContextMenu}>
      {/* v1.1 Workspace Management */}
      <div className="sidebar-workspace">
        <div className="sidebar-workspace-row">
          <button className="btn btn-sm" onClick={onSaveWorkspace} title="Save workspace">
            💾 Save
          </button>
          {workspaces.length > 0 && (
            <select
              className="sidebar-select"
              onChange={(e) => onLoadWorkspace?.(e.target.value)}
              defaultValue=""
            >
              <option value="" disabled>Load workspace…</option>
              {workspaces.map((ws) => (
                <option key={ws.name} value={ws.name}>{ws.name}</option>
              ))}
            </select>
          )}
          {hasCrashRecovery && (
            <button className="btn btn-sm btn-warning" onClick={onRestoreLast} title="Restore last session">
              🔄 Restore
            </button>
          )}
        </div>
      </div>

      {/* v1.1 Checkpoint Recovery */}
      {checkpoints.length > 0 && (
        <div className="sidebar-checkpoint">
          <div className="sidebar-checkpoint-row">
            <select
              className="sidebar-select"
              onChange={(e) => onResumeCheckpoint?.(e.target.value)}
              defaultValue=""
            >
              <option value="" disabled>Resume checkpoint…</option>
              {checkpoints.map((cp) => (
                <option key={cp.queue_id} value={cp.queue_id}>{cp.name || cp.queue_id}</option>
              ))}
            </select>
          </div>
        </div>
      )}

      <div className="sidebar-header">
        <h3>Queue ({tasks.length})</h3>
        <div className="sidebar-actions">
          <button className="btn btn-sm" onClick={handleAddFiles} title="Add files">
            + Files
          </button>
          <button className="btn btn-sm" onClick={() => setShowHistory((s) => !s)} title="Toggle history">
            {showHistory ? 'Queue' : 'History'}
          </button>
        </div>
      </div>

      {!showHistory && (
        <div className="sidebar-list" onDrop={handleDrop} onDragOver={(e) => e.preventDefault()}>
          {tasks.length === 0 && (
            <div className="sidebar-empty">Drop images here or use the drop zone</div>
          )}
          {tasks.map((task, index) => (
            <div
              key={task.id}
              className={`sidebar-item ${task.id === selectedTaskId ? 'selected' : ''} ${task.status === 'running' ? 'running' : ''} ${dragIndex === index ? 'dragging' : ''}`}
              draggable
              onDragStart={() => handleDragStart(index)}
              onDragOver={(e) => handleDragOver(e, index)}
              onDragEnd={handleDragEnd}
              onContextMenu={(e) => handleContextMenu(e, task.id)}
              onClick={() => onSelectTask?.(task.id)}
            >
              <div className="sidebar-thumb">
                <span className="sidebar-thumb-placeholder">🖼</span>
              </div>
              <div className="sidebar-info">
                <div className="sidebar-filename" title={task.fileName}>
                  {task.fileName}
                </div>
                <div className="sidebar-meta">
                  <span className={`sidebar-status sidebar-status-${task.status}`}>
                    {statusIcon[task.status]} {statusLabel[task.status]}
                  </span>
                  {task.progress > 0 && task.status === 'running' && (
                    <span className="sidebar-progress-text">{task.progress}%</span>
                  )}
                </div>
                {task.status === 'running' && (
                  <div className="sidebar-progress-bar">
                    <div className="sidebar-progress-fill" style={{ width: `${task.progress}%` }} />
                  </div>
                )}
                {task.error && <div className="sidebar-error" title={task.error}>{task.error}</div>}
              </div>
            </div>
          ))}
        </div>
      )}

      {showHistory && (
        <div className="sidebar-list">
          {history.length === 0 && (
            <div className="sidebar-empty">No recent history</div>
          )}
          {history.map((entry) => (
            <div
              key={entry.id}
              className="sidebar-item sidebar-history-item"
              onClick={() => handleHistoryClick(entry)}
              title="Click to load parameters"
            >
              <div className="sidebar-thumb">
                <span className="sidebar-thumb-placeholder">🕘</span>
              </div>
              <div className="sidebar-info">
                <div className="sidebar-filename" title={entry.fileName}>
                  {entry.fileName}
                </div>
                <div className="sidebar-meta">
                  <span className="sidebar-status sidebar-status-completed">
                    ✓ {entry.preset}
                  </span>
                  {entry.timestamp && (
                    <span className="sidebar-progress-text">{entry.timestamp}</span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}

      {contextMenu && (
        <div className="context-menu" style={{ left: contextMenu.x, top: contextMenu.y }}>
          <button
            className="context-menu-item"
            onClick={() => {
              const task = tasks.find((t) => t.id === contextMenu.taskId);
              if (task && (task.status === 'pending' || task.status === 'running')) {
                onCancelTask(contextMenu.taskId);
              }
              closeContextMenu();
            }}
          >
            Cancel / Requeue
          </button>
          <button
            className="context-menu-item"
            onClick={() => {
              onRemoveTask(contextMenu.taskId);
              closeContextMenu();
            }}
          >
            Remove
          </button>
        </div>
      )}
    </div>
  );
};
