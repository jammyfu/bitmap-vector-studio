import React, { useState, useCallback, useRef } from 'react';
import type { ConversionTask } from '../types';

interface SidebarProps {
  tasks: ConversionTask[];
  onRemoveTask: (id: string) => void;
  onCancelTask: (id: string) => void;
  onReorder: (startIndex: number, endIndex: number) => void;
  onSelectTask?: (id: string) => void;
  selectedTaskId?: string | null;
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
}) => {
  const [contextMenu, setContextMenu] = useState<{ x: number; y: number; taskId: string } | null>(null);
  const [dragIndex, setDragIndex] = useState<number | null>(null);
  const dragOverIndex = useRef<number | null>(null);

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

  return (
    <div className="sidebar" onClick={closeContextMenu}>
      <div className="sidebar-header">
        <h3>Queue ({tasks.length})</h3>
      </div>
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
