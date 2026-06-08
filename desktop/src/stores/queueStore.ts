import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface QueueItem {
  id: string;
  fileName: string;
  filePath: string;
  status: 'pending' | 'converting' | 'done' | 'error';
  progress: number;
  outputPath?: string;
  error?: string;
}

interface QueueState {
  items: QueueItem[];
  selectedId: string | null;
  isExpanded: boolean;

  addFiles: (files: { name: string; path: string }[]) => void;
  removeItem: (id: string) => void;
  updateStatus: (id: string, status: QueueItem['status'], progress?: number) => void;
  setOutput: (id: string, outputPath: string) => void;
  setError: (id: string, error: string) => void;
  selectItem: (id: string | null) => void;
  toggleExpanded: () => void;
  clearCompleted: () => void;
  reorderItems: (startIndex: number, endIndex: number) => void;
}

let idCounter = 0;
function generateId(): string {
  return `task-${Date.now()}-${++idCounter}`;
}

export const useQueueStore = create<QueueState>()(
  persist(
    (set) => ({
      items: [],
      selectedId: null,
      isExpanded: true,

      addFiles: (files) =>
        set((state) => {
          const newItems: QueueItem[] = files.map((file) => ({
            id: generateId(),
            fileName: file.name,
            filePath: file.path,
            status: 'pending',
            progress: 0,
          }));
          return { items: [...state.items, ...newItems] };
        }),

      removeItem: (id) =>
        set((state) => ({
          items: state.items.filter((i) => i.id !== id),
          selectedId: state.selectedId === id ? null : state.selectedId,
        })),

      updateStatus: (id, status, progress) =>
        set((state) => ({
          items: state.items.map((i) =>
            i.id === id ? { ...i, status, progress: progress ?? i.progress } : i
          ),
        })),

      setOutput: (id, outputPath) =>
        set((state) => ({
          items: state.items.map((i) =>
            i.id === id ? { ...i, outputPath, status: 'done' as const, progress: 100 } : i
          ),
        })),

      setError: (id, error) =>
        set((state) => ({
          items: state.items.map((i) =>
            i.id === id ? { ...i, error, status: 'error' as const } : i
          ),
        })),

      selectItem: (id) => set({ selectedId: id }),

      toggleExpanded: () => set((state) => ({ isExpanded: !state.isExpanded })),

      clearCompleted: () =>
        set((state) => ({
          items: state.items.filter((i) => i.status !== 'done'),
          selectedId:
            state.selectedId &&
            state.items.find((i) => i.id === state.selectedId)?.status === 'done'
              ? null
              : state.selectedId,
        })),

      reorderItems: (startIndex, endIndex) =>
        set((state) => {
          const result = Array.from(state.items);
          const [removed] = result.splice(startIndex, 1);
          result.splice(endIndex, 0, removed);
          return { items: result };
        }),
    }),
    {
      name: 'bvs_queue_store',
      partialize: (state) => ({ isExpanded: state.isExpanded }),
    }
  )
);
