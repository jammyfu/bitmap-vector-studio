import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Theme } from '../types';
import { hasRecoveryState, loadRecoveryState, clearRecoveryState } from '../utils/crashRecovery';
import type { RecoveryData } from '../utils/crashRecovery';

interface Toast {
  message: string;
  type: 'success' | 'error' | 'warning';
}

interface AppState {
  theme: Theme;
  effectiveTheme: 'light' | 'dark';
  isReady: boolean;
  envStatus: string;
  toast: Toast | null;
  commandPaletteOpen: boolean;
  hasCrashRecovery: boolean;
  crashRecoveryData: RecoveryData | null;

  // actions
  setTheme: (t: Theme) => void;
  toggleTheme: () => void;
  showToast: (message: string, type: Toast['type']) => void;
  hideToast: () => void;
  openCommandPalette: () => void;
  closeCommandPalette: () => void;
  setReady: (ready: boolean) => void;
  setEnvStatus: (status: string) => void;
  recoverFromCrash: () => void;
  clearCrashRecovery: () => void;
}

function getSystemTheme(): 'light' | 'dark' {
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
    return 'dark';
  }
  return 'light';
}

let toastTimer: ReturnType<typeof setTimeout> | null = null;

export const useAppStore = create<AppState>()(
  persist(
    (set, get) => ({
      theme: 'system',
      get effectiveTheme() {
        const t = get().theme;
        return t === 'system' ? getSystemTheme() : t;
      },
      isReady: false,
      envStatus: 'Checking...',
      toast: null,
      commandPaletteOpen: false,
      hasCrashRecovery: hasRecoveryState(),
      crashRecoveryData: loadRecoveryState(),

      setTheme: (t) => {
        set({ theme: t });
        const effective = t === 'system' ? getSystemTheme() : t;
        document.documentElement.setAttribute('data-theme', effective);
      },

      toggleTheme: () => {
        set((state) => {
          const next: Theme =
            state.theme === 'light' ? 'dark' : state.theme === 'dark' ? 'system' : 'light';
          const effective = next === 'system' ? getSystemTheme() : next;
          document.documentElement.setAttribute('data-theme', effective);
          return { theme: next };
        });
      },

      showToast: (message, type) => {
        if (toastTimer) clearTimeout(toastTimer);
        set({ toast: { message, type } });
        toastTimer = setTimeout(() => {
          set({ toast: null });
        }, 3000);
      },

      hideToast: () => {
        if (toastTimer) clearTimeout(toastTimer);
        set({ toast: null });
      },

      openCommandPalette: () => set({ commandPaletteOpen: true }),
      closeCommandPalette: () => set({ commandPaletteOpen: false }),
      setReady: (ready) => set({ isReady: ready }),
      setEnvStatus: (status) => set({ envStatus: status }),
      recoverFromCrash: () => {
        const data = loadRecoveryState();
        if (data) {
          set({ crashRecoveryData: data, hasCrashRecovery: false });
        }
      },
      clearCrashRecovery: () => {
        clearRecoveryState();
        set({ hasCrashRecovery: false, crashRecoveryData: null });
      },
    }),
    {
      name: 'bvs_app_store',
      partialize: (state) => ({ theme: state.theme }),
    }
  )
);

// Sync system theme changes when in system mode
if (typeof window !== 'undefined') {
  const mq = window.matchMedia('(prefers-color-scheme: dark)');
  mq.addEventListener('change', () => {
    const state = useAppStore.getState();
    if (state.theme === 'system') {
      document.documentElement.setAttribute('data-theme', getSystemTheme());
      // Force re-render by touching state
      useAppStore.setState({ envStatus: state.envStatus });
    }
  });
}
