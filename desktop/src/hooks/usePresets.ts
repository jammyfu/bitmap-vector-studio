import { useState, useCallback, useEffect } from 'react';
import type { Preset, TraceOptions } from '../types';

const BUILTIN_PRESETS: Preset[] = [
  {
    name: 'default',
    displayName: 'Default',
    description: 'Balanced settings for most images',
    isBuiltin: true,
    options: {
      colormode: 'color',
      hierarchical: 'stacked',
      mode: 'spline',
      filter_speckle: 4,
      color_precision: 6,
      layer_difference: 16,
      corner_threshold: 60,
      length_threshold: 4,
      max_iterations: 10,
      splice_threshold: 45,
      path_precision: 8,
      denoise: false,
      posterize: null,
      max_input_side: null,
    },
  },
  {
    name: 'photo',
    displayName: 'Photo',
    description: 'Optimized for photographs',
    isBuiltin: true,
    options: {
      colormode: 'color',
      hierarchical: 'stacked',
      mode: 'spline',
      filter_speckle: 2,
      color_precision: 8,
      layer_difference: 8,
      corner_threshold: 30,
      length_threshold: 2,
      max_iterations: 15,
      splice_threshold: 30,
      path_precision: 6,
      denoise: true,
      posterize: null,
      max_input_side: 2048,
    },
  },
  {
    name: 'logo',
    displayName: 'Logo',
    description: 'Sharp edges for logos and icons',
    isBuiltin: true,
    options: {
      colormode: 'color',
      hierarchical: 'cutout',
      mode: 'polygon',
      filter_speckle: 1,
      color_precision: 2,
      layer_difference: 32,
      corner_threshold: 90,
      length_threshold: 1,
      max_iterations: 5,
      splice_threshold: 60,
      path_precision: 10,
      denoise: false,
      posterize: null,
      max_input_side: null,
    },
  },
  {
    name: 'sketch',
    displayName: 'Sketch',
    description: 'Black and white line art',
    isBuiltin: true,
    options: {
      colormode: 'binary',
      hierarchical: 'stacked',
      mode: 'spline',
      filter_speckle: 6,
      color_precision: 1,
      layer_difference: 1,
      corner_threshold: 45,
      length_threshold: 4,
      max_iterations: 10,
      splice_threshold: 45,
      path_precision: 8,
      denoise: true,
      posterize: null,
      max_input_side: null,
    },
  },
];

const STORAGE_KEY = 'bvs_custom_presets';

function loadCustomPresets(): Preset[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) {
      const parsed = JSON.parse(raw) as Preset[];
      return parsed.map((p) => ({ ...p, isBuiltin: false }));
    }
  } catch {
    // ignore
  }
  return [];
}

function saveCustomPresets(presets: Preset[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(presets));
  } catch {
    // ignore
  }
}

export function usePresets() {
  const [presets, setPresets] = useState<Preset[]>([...BUILTIN_PRESETS]);
  const [activePreset, setActivePreset] = useState<string>('default');
  const [isLoaded, setIsLoaded] = useState(false);

  useEffect(() => {
    const custom = loadCustomPresets();
    setPresets([...BUILTIN_PRESETS, ...custom]);
    setIsLoaded(true);
  }, []);

  const loadPresets = useCallback(() => {
    const custom = loadCustomPresets();
    setPresets([...BUILTIN_PRESETS, ...custom]);
  }, []);

  const getPresetOptions = useCallback(
    (name?: string): TraceOptions => {
      const target = name || activePreset;
      const preset = presets.find((p) => p.name === target);
      return preset ? { ...preset.options } : { ...BUILTIN_PRESETS[0].options };
    },
    [presets, activePreset]
  );

  const savePreset = useCallback((name: string, options: TraceOptions, displayName?: string, description?: string) => {
    setPresets((prev) => {
      const filtered = prev.filter((p) => p.name !== name || p.isBuiltin);
      const newPreset: Preset = {
        name,
        displayName: displayName || name,
        description: description || '',
        options: { ...options },
        isBuiltin: false,
      };
      const next = [...filtered, newPreset];
      saveCustomPresets(next.filter((p) => !p.isBuiltin));
      return next;
    });
  }, []);

  const deletePreset = useCallback((name: string) => {
    setPresets((prev) => {
      const next = prev.filter((p) => p.name !== name || p.isBuiltin);
      saveCustomPresets(next.filter((p) => !p.isBuiltin));
      return next;
    });
  }, []);

  const selectPreset = useCallback((name: string) => {
    setActivePreset(name);
  }, []);

  return {
    presets,
    activePreset,
    isLoaded,
    loadPresets,
    savePreset,
    deletePreset,
    selectPreset,
    getPresetOptions,
  };
}
