import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface SettingsState {
  language: string;
  defaultOutputDir: string | null;
  defaultFormat: string;
  externalEditor: string | null;
  apiHost: string;
  apiPort: number;
  gpuEnabled: boolean;
  streamingEnabled: boolean;
  autoSaveInterval: number;
  cloudSyncEnabled: boolean;
  syncServerUrl: string;
  // v3.0 new
  smartDefaultsEnabled: boolean;
  compactMode: boolean;

  // actions
  updateSetting: (key: string, value: unknown) => void;
  loadSettings: () => void;
  saveSettings: () => void;
}

const DEFAULT_SETTINGS: Omit<SettingsState, 'updateSetting' | 'loadSettings' | 'saveSettings'> = {
  language: 'en',
  defaultOutputDir: null,
  defaultFormat: 'svg',
  externalEditor: null,
  apiHost: '127.0.0.1',
  apiPort: 8000,
  gpuEnabled: false,
  streamingEnabled: false,
  autoSaveInterval: 60,
  cloudSyncEnabled: false,
  syncServerUrl: 'http://localhost:8000',
  smartDefaultsEnabled: true,
  compactMode: false,
};

export const useSettingsStore = create<SettingsState>()(
  persist(
    (set, get) => ({
      ...DEFAULT_SETTINGS,

      updateSetting: (key, value) =>
        set((state) => {
          if (key in state) {
            return { [key]: value } as Partial<SettingsState>;
          }
          return state;
        }),

      loadSettings: () => {
        try {
          const raw = localStorage.getItem('bvs_settings_store');
          if (raw) {
            const parsed = JSON.parse(raw);
            if (parsed && typeof parsed === 'object') {
              set((state) => ({
                ...state,
                ...parsed,
              }));
            }
          }
        } catch {
          // ignore parse errors
        }
      },

      saveSettings: () => {
        try {
          const state = get();
          const payload = {
            language: state.language,
            defaultOutputDir: state.defaultOutputDir,
            defaultFormat: state.defaultFormat,
            externalEditor: state.externalEditor,
            apiHost: state.apiHost,
            apiPort: state.apiPort,
            gpuEnabled: state.gpuEnabled,
            streamingEnabled: state.streamingEnabled,
            autoSaveInterval: state.autoSaveInterval,
            cloudSyncEnabled: state.cloudSyncEnabled,
            syncServerUrl: state.syncServerUrl,
            smartDefaultsEnabled: state.smartDefaultsEnabled,
            compactMode: state.compactMode,
          };
          localStorage.setItem('bvs_settings_store', JSON.stringify(payload));
        } catch {
          // ignore storage errors
        }
      },
    }),
    {
      name: 'bvs_settings_store',
    }
  )
);
