export interface TraceOptions {
  colormode: 'color' | 'binary';
  hierarchical: 'stacked' | 'cutout';
  mode: 'spline' | 'polygon' | 'pixel' | 'none';
  filter_speckle: number;
  color_precision: number;
  layer_difference: number;
  corner_threshold: number;
  length_threshold: number;
  max_iterations: number;
  splice_threshold: number;
  path_precision: number;
  denoise: boolean;
  posterize: number | null;
  max_input_side: number | null;
}

export interface ConversionTask {
  id: string;
  fileName: string;
  inputPath: string;
  outputPath: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  preset: string;
  error?: string;
}

export interface Preset {
  name: string;
  displayName: string;
  description: string;
  options: TraceOptions;
  isBuiltin: boolean;
}

export interface PluginInfo {
  name: string;
  version: string;
  description: string;
  author: string;
  enabled: boolean;
  hooks: string[];
}

export type Theme = 'light' | 'dark' | 'system';

export interface AppSettings {
  language: string;
  theme: Theme;
  defaultOutputDir: string | null;
  defaultFormat: 'svg' | 'pdf' | 'png';
  optimizeLevel: number;
  externalEditor: string | null;
  apiHost: string;
  apiPort: number;
  // v1.1 performance
  gpuEnabled: boolean;
  streamingEnabled: boolean;
  memoryLimit: number | null;
  autoSaveInterval: number;
  // v1.2 cloud sync
  cloudSyncEnabled: boolean;
  cloudApiKey: string | null;
  // v2.0 AI
  aiTask: string;
  aiStyle: string;
  aiScale: number;
  // v2.0 sync
  syncServerUrl: string;
  syncEnabled: boolean;
}
