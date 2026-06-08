import React, { useMemo, useEffect, useState, useCallback } from 'react';
import { useInvoke } from '../hooks/useInvoke';
import type { ConversionTask } from '../types';

interface QueueStatus {
  pending: number;
  running: number;
  completed: number;
  failed: number;
  total: number;
  totalProgress: number;
  currentTask?: { fileName: string; progress: number };
  elapsedMs: number;
}

interface StatusBarProps {
  tasks: ConversionTask[];
  isRunning: boolean;
  onStart: () => void;
  onPause: () => void;
  onCancelAll: () => void;
  onClearCompleted: () => void;
  elapsedMs?: number;
  onToast?: (message: string, type?: 'success' | 'error') => void;
  // v1.1 performance
  memoryStatus?: { percent?: number; used_mb?: number; total_mb?: number; available?: boolean; message?: string } | null;
  gpuStatus?: string;
  performanceSuggestions?: string[];
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
  onToast,
  memoryStatus,
  gpuStatus,
  performanceSuggestions,
}) => {
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [polling, setPolling] = useState(false);

  const { call: callStartQueue } = useInvoke<Record<string, never>, void>('start_queue');
  const { call: callPauseQueue } = useInvoke<Record<string, never>, void>('pause_queue');
  const { call: callCancelQueue } = useInvoke<Record<string, never>, void>('cancel_queue');
  const { call: callGetQueueStatus } = useInvoke<Record<string, never>, string>('get_queue_status');

  // Poll queue status from backend when running
  useEffect(() => {
    if (!isRunning) {
      setQueueStatus(null);
      return;
    }
    setPolling(true);
    const interval = setInterval(async () => {
      const result = await callGetQueueStatus();
      if (result) {
        try {
          const parsed = JSON.parse(result) as QueueStatus;
          setQueueStatus(parsed);
        } catch {
          // ignore parse errors
        }
      }
    }, 1000);
    return () => {
      clearInterval(interval);
      setPolling(false);
    };
  }, [isRunning, callGetQueueStatus]);

  const handleStart = useCallback(async () => {
    const result = await callStartQueue();
    if (result !== null) {
      onStart();
      onToast?.('Queue started', 'success');
    } else {
      onToast?.('Failed to start queue', 'error');
    }
  }, [callStartQueue, onStart, onToast]);

  const handlePause = useCallback(async () => {
    const result = await callPauseQueue();
    if (result !== null) {
      onPause();
      onToast?.('Queue paused', 'success');
    } else {
      onToast?.('Failed to pause queue', 'error');
    }
  }, [callPauseQueue, onPause, onToast]);

  const handleCancelAll = useCallback(async () => {
    const result = await callCancelQueue();
    if (result !== null) {
      onCancelAll();
      onToast?.('Queue cancelled', 'success');
    } else {
      onToast?.('Failed to cancel queue', 'error');
    }
  }, [callCancelQueue, onCancelAll, onToast]);

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

  // Prefer backend queue status when available
  const displayCurrent = queueStatus?.currentTask
    ? { fileName: queueStatus.currentTask.fileName, progress: queueStatus.currentTask.progress }
    : currentTask
    ? { fileName: currentTask.fileName, progress: currentTask.progress }
    : null;

  const displayProgress = queueStatus?.totalProgress ?? totalProgress;
  const displayCounts = queueStatus
    ? {
        pending: queueStatus.pending,
        running: queueStatus.running,
        completed: queueStatus.completed,
        failed: queueStatus.failed,
        total: queueStatus.total,
      }
    : counts;

  return (
    <div className="statusbar">
      <div className="statusbar-left">
        {displayCurrent ? (
          <span className="statusbar-current" title={displayCurrent.fileName}>
            ▶ {displayCurrent.fileName} ({displayCurrent.progress}%)
          </span>
        ) : (
          <span className="statusbar-idle">Ready</span>
        )}
        {polling && <span className="statusbar-polling">●</span>}
        {/* v1.1 performance info */}
        {memoryStatus && memoryStatus.available && (
          <span className="statusbar-mem" title={`Memory: ${memoryStatus.used_mb}MB / ${memoryStatus.total_mb}MB`}>
            🧠 {memoryStatus.percent?.toFixed(0)}%
          </span>
        )}
        {gpuStatus && gpuStatus !== '未检测到' && gpuStatus !== '不可用' && (
          <span className="statusbar-gpu" title={`GPU: ${gpuStatus}`}>
            ⚡ {gpuStatus}
          </span>
        )}
        {performanceSuggestions && performanceSuggestions.length > 0 && (
          <span className="statusbar-suggestion" title={performanceSuggestions.join('\n')}>
            💡 {performanceSuggestions.length} tips
          </span>
        )}
      </div>

      <div className="statusbar-center">
        <div className="statusbar-progress">
          <div className="statusbar-progress-bar">
            <div className="statusbar-progress-fill" style={{ width: `${displayProgress}%` }} />
          </div>
          <span className="statusbar-progress-text">{displayProgress}%</span>
        </div>
        <div className="statusbar-stats">
          <span>⏳ {displayCounts.pending}</span>
          <span>▶ {displayCounts.running}</span>
          <span>✓ {displayCounts.completed}</span>
          <span>✗ {displayCounts.failed}</span>
          <span>⏱ {formatDuration(elapsedMs)}</span>
        </div>
      </div>

      <div className="statusbar-right">
        {!isRunning ? (
          <button className="btn btn-sm btn-primary" onClick={handleStart} disabled={displayCounts.pending === 0}>
            Start
          </button>
        ) : (
          <button className="btn btn-sm" onClick={handlePause}>
            Pause
          </button>
        )}
        <button className="btn btn-sm btn-danger" onClick={handleCancelAll} disabled={displayCounts.running === 0 && displayCounts.pending === 0}>
          Cancel All
        </button>
        <button className="btn btn-sm" onClick={onClearCompleted} disabled={displayCounts.completed === 0}>
          Clear Done
        </button>
      </div>
    </div>
  );
};
