import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface ConvertState {
  // 核心参数（始终显示）
  preset: string;
  colormode: 'color' | 'binary';
  mode: 'spline' | 'polygon' | 'pixel' | 'none';
  optimizeLevel: 'none' | 'basic' | 'comprehensive' | 'aggressive';

  // 高级参数（默认折叠）
  advancedOpen: boolean;
  filterSpeckle: number;
  colorPrecision: number;
  layerDifference: number;
  cornerThreshold: number;
  lengthThreshold: number;
  maxIterations: number;
  spliceThreshold: number;
  pathPrecision: number;
  denoise: boolean;
  posterize: number | null;
  maxInputSide: number | null;

  // 智能功能
  smartRemoveBg: boolean;
  enhance: string | null;
  aiSimplify: boolean;
  aiOcr: boolean;
  ocrLang: string;

  // 输出
  outputFormat: 'svg' | 'pdf' | 'png' | 'eps';
  exportPdf: boolean;
  exportPng: boolean;

  // 预览
  previewResult: string | undefined;
  isConverting: boolean;

  // 智能推荐
  recommendedPreset: string | null;
  recommendationConfidence: number;

  // actions
  setPreset: (p: string) => void;
  applyRecommendation: () => void;
  setCoreParam: (key: string, value: unknown) => void;
  toggleAdvanced: () => void;
  setAdvancedParam: (key: string, value: unknown) => void;
  startConvert: () => void;
  finishConvert: (result: string) => void;
  setPreviewResult: (result: string | undefined) => void;
  setRecommendation: (preset: string, confidence: number) => void;
  resetToDefaults: () => void;
}

const DEFAULTS: Omit<
  ConvertState,
  | 'setPreset'
  | 'applyRecommendation'
  | 'setCoreParam'
  | 'toggleAdvanced'
  | 'setAdvancedParam'
  | 'startConvert'
  | 'finishConvert'
  | 'setPreviewResult'
  | 'setRecommendation'
  | 'resetToDefaults'
> = {
  preset: 'default',
  colormode: 'color',
  mode: 'spline',
  optimizeLevel: 'basic',
  advancedOpen: false,
  filterSpeckle: 4,
  colorPrecision: 6,
  layerDifference: 16,
  cornerThreshold: 60,
  lengthThreshold: 4,
  maxIterations: 10,
  spliceThreshold: 45,
  pathPrecision: 8,
  denoise: false,
  posterize: null,
  maxInputSide: null,
  smartRemoveBg: false,
  enhance: null,
  aiSimplify: false,
  aiOcr: false,
  ocrLang: 'eng',
  outputFormat: 'svg',
  exportPdf: false,
  exportPng: false,
  previewResult: undefined,
  isConverting: false,
  recommendedPreset: null,
  recommendationConfidence: 0,
};

export const useConvertStore = create<ConvertState>()(
  persist(
    (set) => ({
      ...DEFAULTS,

      setPreset: (p) => set({ preset: p }),

      applyRecommendation: () =>
        set((state) => {
          if (state.recommendedPreset) {
            return {
              preset: state.recommendedPreset,
              recommendationConfidence: 0,
              recommendedPreset: null,
            };
          }
          return {};
        }),

      setCoreParam: (key, value) =>
        set((state) => {
          if (key === 'colormode' && (value === 'color' || value === 'binary')) {
            return { colormode: value };
          }
          if (key === 'mode' && ['spline', 'polygon', 'pixel', 'none'].includes(value as string)) {
            return { mode: value as ConvertState['mode'] };
          }
          if (key === 'optimizeLevel' && ['none', 'basic', 'comprehensive', 'aggressive'].includes(value as string)) {
            return { optimizeLevel: value as ConvertState['optimizeLevel'] };
          }
          if (key === 'outputFormat' && ['svg', 'pdf', 'png', 'eps'].includes(value as string)) {
            return { outputFormat: value as ConvertState['outputFormat'] };
          }
          return state;
        }),

      toggleAdvanced: () => set((state) => ({ advancedOpen: !state.advancedOpen })),

      setAdvancedParam: (key, value) =>
        set((state) => {
          const map: Record<string, keyof ConvertState> = {
            filterSpeckle: 'filterSpeckle',
            colorPrecision: 'colorPrecision',
            layerDifference: 'layerDifference',
            cornerThreshold: 'cornerThreshold',
            lengthThreshold: 'lengthThreshold',
            maxIterations: 'maxIterations',
            spliceThreshold: 'spliceThreshold',
            pathPrecision: 'pathPrecision',
            denoise: 'denoise',
            posterize: 'posterize',
            maxInputSide: 'maxInputSide',
            smartRemoveBg: 'smartRemoveBg',
            enhance: 'enhance',
            aiSimplify: 'aiSimplify',
            aiOcr: 'aiOcr',
            ocrLang: 'ocrLang',
            exportPdf: 'exportPdf',
            exportPng: 'exportPng',
          };
          const mapped = map[key];
          if (!mapped) return state;
          return { [mapped]: value } as Partial<ConvertState>;
        }),

      startConvert: () => set({ isConverting: true }),

      finishConvert: (result) =>
        set({
          isConverting: false,
          previewResult: result,
        }),

      setPreviewResult: (result) => set({ previewResult: result }),

      setRecommendation: (preset, confidence) =>
        set({ recommendedPreset: preset, recommendationConfidence: confidence }),

      resetToDefaults: () => set({ ...DEFAULTS }),
    }),
    {
      name: 'bvs_convert_store',
      partialize: (state) => ({
        preset: state.preset,
        colormode: state.colormode,
        mode: state.mode,
        optimizeLevel: state.optimizeLevel,
        advancedOpen: state.advancedOpen,
        filterSpeckle: state.filterSpeckle,
        colorPrecision: state.colorPrecision,
        layerDifference: state.layerDifference,
        cornerThreshold: state.cornerThreshold,
        lengthThreshold: state.lengthThreshold,
        maxIterations: state.maxIterations,
        spliceThreshold: state.spliceThreshold,
        pathPrecision: state.pathPrecision,
        denoise: state.denoise,
        posterize: state.posterize,
        maxInputSide: state.maxInputSide,
        smartRemoveBg: state.smartRemoveBg,
        enhance: state.enhance,
        aiSimplify: state.aiSimplify,
        aiOcr: state.aiOcr,
        ocrLang: state.ocrLang,
        outputFormat: state.outputFormat,
        exportPdf: state.exportPdf,
        exportPng: state.exportPng,
      }),
    }
  )
);
