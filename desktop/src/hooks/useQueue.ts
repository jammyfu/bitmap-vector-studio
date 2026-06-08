import { useState, useCallback, useRef } from 'react';
import type { ConversionTask } from '../types';

let idCounter = 0;
function generateId(): string {
  return `task-${Date.now()}-${++idCounter}`;
}

export function useQueue() {
  const [tasks, setTasks] = useState<ConversionTask[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const runningRef = useRef(false);

  const addTask = useCallback((file: string, preset: string) => {
    const fileName = file.split(/[/\\]/).pop() || file;
    const newTask: ConversionTask = {
      id: generateId(),
      fileName,
      inputPath: file,
      outputPath: '',
      status: 'pending',
      progress: 0,
      preset,
    };
    setTasks((prev) => [...prev, newTask]);
    return newTask.id;
  }, []);

  const addTasks = useCallback((files: string[], preset: string) => {
    const ids: string[] = [];
    setTasks((prev) => {
      const newTasks: ConversionTask[] = files.map((file) => {
        const fileName = file.split(/[/\\]/).pop() || file;
        const id = generateId();
        ids.push(id);
        return {
          id,
          fileName,
          inputPath: file,
          outputPath: '',
          status: 'pending',
          progress: 0,
          preset,
        };
      });
      return [...prev, ...newTasks];
    });
    return ids;
  }, []);

  const updateTask = useCallback((id: string, updates: Partial<ConversionTask>) => {
    setTasks((prev) =>
      prev.map((t) => (t.id === id ? { ...t, ...updates } : t))
    );
  }, []);

  const startQueue = useCallback(() => {
    setIsRunning(true);
    runningRef.current = true;
    setTasks((prev) =>
      prev.map((t) =>
        t.status === 'pending' ? { ...t, status: 'running' as const } : t
      )
    );
  }, []);

  const pauseQueue = useCallback(() => {
    setIsRunning(false);
    runningRef.current = false;
    setTasks((prev) =>
      prev.map((t) =>
        t.status === 'running' ? { ...t, status: 'pending' as const } : t
      )
    );
  }, []);

  const cancelTask = useCallback((id: string) => {
    setTasks((prev) =>
      prev.map((t) =>
        t.id === id && (t.status === 'pending' || t.status === 'running')
          ? { ...t, status: 'cancelled' as const, progress: 0 }
          : t
      )
    );
  }, []);

  const removeTask = useCallback((id: string) => {
    setTasks((prev) => prev.filter((t) => t.id !== id));
  }, []);

  const clearCompleted = useCallback(() => {
    setTasks((prev) => prev.filter((t) => t.status !== 'completed'));
  }, []);

  const clearAll = useCallback(() => {
    setTasks([]);
    setIsRunning(false);
    runningRef.current = false;
  }, []);

  const reorderTasks = useCallback((startIndex: number, endIndex: number) => {
    setTasks((prev) => {
      const result = Array.from(prev);
      const [removed] = result.splice(startIndex, 1);
      result.splice(endIndex, 0, removed);
      return result;
    });
  }, []);

  const pendingCount = tasks.filter((t) => t.status === 'pending').length;
  const runningCount = tasks.filter((t) => t.status === 'running').length;
  const completedCount = tasks.filter((t) => t.status === 'completed').length;
  const failedCount = tasks.filter((t) => t.status === 'failed').length;

  return {
    tasks,
    isRunning,
    runningRef,
    addTask,
    addTasks,
    updateTask,
    startQueue,
    pauseQueue,
    cancelTask,
    removeTask,
    clearCompleted,
    clearAll,
    reorderTasks,
    pendingCount,
    runningCount,
    completedCount,
    failedCount,
  };
}
