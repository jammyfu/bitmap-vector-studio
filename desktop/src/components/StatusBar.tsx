import React, { useMemo } from 'react';
import type { ConversionTask } from '../types';

interface StatusBarProps {
  tasks: ConversionTask[];
  isRunning: boolean;
  onStart: () => void;
  onPause: () => void;
  onCancelAll: () => void;
  onClearCompleted: () => void;
  elapsedMs?: number;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const s = Math.floor(ms / 1000);
  const m = Math.floor(s / 60);
  const h = Math.floor(m / 60);
  if (h > 0) return `${h}h ${m % 60}m ${s % 60}s`;
  if (m > 0) return `${m}m ${s % 60}s`;
  return `${s}s`;
}

export const StatusBar: React.FC<StatusBarProps> = ({
  tasks,
  isRunning,
  onStart,
  onPause,
  onCancelAll,
  onClearCompleted,
  elapsedMs = 0,
}) => {
  const currentTask = useMemo(() => tasks.find((t) => t.status === 'running'), [tasks]);
  const totalProgress = useMemo(() => {
    if (tasks.length === 0) return 0;
    const sum = tasks.reduce((acc, t) => acc + t.progress, 0);
    return Math.round(sum / tasks.length);
  }, [tasks]);

  const counts = useMemo(() => {
    const pending = tasks.filter((t) => t.status === 'pending').length;
    const running = tasks.filter((t) => t.status === 'running').length;
    const completed = tasks.filter((t) => t.status === 'completed').length;
    const failed = tasks.filter((t) => t.status === 'failed').length;
    return { pending, running, completed, failed, total: tasks.length };
  }, [tasks]);

  return (
    <div className="statusbar">
      <div className="statusbar-left">
        {currentTask ? (
          <span className="statusbar-current" title={currentTask.fileName}>
            ▶ {currentTask.fileName} ({currentTask.progress}%)
          </span>
        ) : (
          <span className="statusbar-idle">Ready</span>
        )}
      </div>

      <div className="statusbar-center">
        <div className="statusbar-progress">
          <div className="statusbar-progress-bar">
            <div className="statusbar-progress-fill" style={{ width: `${totalProgress}%` }} />
          </div>
          <span className="statusbar-progress-text">{totalProgress}%</span>
        </div>
        <div className="statusbar-stats">
          <span>⏳ {counts.pending}</span>
          <span>▶ {counts.running}</span>
          <span>✓ {counts.completed}</span>
          <span>✗ {counts.failed}</span>
          <span>⏱ {formatDuration(elapsedMs)}</span>
        </div>
      </div>

      <div className="statusbar-right">
        {!isRunning ? (
          <button className="btn btn-sm btn-primary" onClick={onStart} disabled={counts.pending === 0}>
            Start
          </button>
        ) : (
          <button className="btn btn-sm" onClick={onPause}>
            Pause
          </button>
        )}
        <button className="btn btn-sm btn-danger" onClick={onCancelAll} disabled={counts.running === 0 && counts.pending === 0}>
          Cancel All
        </button>
        <button className="btn btn-sm" onClick={onClearCompleted} disabled={counts.completed === 0}>
          Clear Done
        </button>
      </div>
    </div>
  );
};
