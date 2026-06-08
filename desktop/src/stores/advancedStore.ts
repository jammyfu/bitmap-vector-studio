import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export interface AdvancedState {
  // AI功能
  aiTask: string;
  aiStyle: string;
  aiScale: number;
  aiSegment: boolean;
  aiStyleTransfer: string | null;
  aiSuperRes: boolean;

  // 动画
  animateType: string | null;
  animateDuration: number;

  // 协作
  collabSessionId: string | null;
  collabUsers: string[];

  // 工作流
  workflowId: string | null;

  // 3D
  threeDEnabled: boolean;
  extrudeDepth: number;

  // 渲染农场
  renderFarmEnabled: boolean;
  farmCoordinatorUrl: string | null;

  // actions
  setAiParam: (key: string, value: unknown) => void;
  setAnimationParam: (key: string, value: unknown) => void;
  setCollabSession: (id: string | null) => void;
  setCollabUsers: (users: string[]) => void;
  setWorkflow: (id: string | null) => void;
  setThreeDParam: (key: string, value: unknown) => void;
  setFarmParam: (key: string, value: unknown) => void;
}

const DEFAULTS: Omit<
  AdvancedState,
  | 'setAiParam'
  | 'setAnimationParam'
  | 'setCollabSession'
  | 'setCollabUsers'
  | 'setWorkflow'
  | 'setThreeDParam'
  | 'setFarmParam'
> = {
  aiTask: '无',
  aiStyle: '素描',
  aiScale: 2,
  aiSegment: false,
  aiStyleTransfer: null,
  aiSuperRes: false,
  animateType: null,
  animateDuration: 2,
  collabSessionId: null,
  collabUsers: [],
  workflowId: null,
  threeDEnabled: false,
  extrudeDepth: 10,
  renderFarmEnabled: false,
  farmCoordinatorUrl: null,
};

export const useAdvancedStore = create<AdvancedState>()(
  persist(
    (set) => ({
      ...DEFAULTS,

      setAiParam: (key, value) =>
        set((state) => {
          const map: Record<string, keyof AdvancedState> = {
            aiTask: 'aiTask',
            aiStyle: 'aiStyle',
            aiScale: 'aiScale',
            aiSegment: 'aiSegment',
            aiStyleTransfer: 'aiStyleTransfer',
            aiSuperRes: 'aiSuperRes',
          };
          const mapped = map[key];
          if (!mapped) return state;
          return { [mapped]: value } as Partial<AdvancedState>;
        }),

      setAnimationParam: (key, value) =>
        set((state) => {
          const map: Record<string, keyof AdvancedState> = {
            animateType: 'animateType',
            animateDuration: 'animateDuration',
          };
          const mapped = map[key];
          if (!mapped) return state;
          return { [mapped]: value } as Partial<AdvancedState>;
        }),

      setCollabSession: (id) => set({ collabSessionId: id }),
      setCollabUsers: (users) => set({ collabUsers: users }),
      setWorkflow: (id) => set({ workflowId: id }),

      setThreeDParam: (key, value) =>
        set((state) => {
          const map: Record<string, keyof AdvancedState> = {
            threeDEnabled: 'threeDEnabled',
            extrudeDepth: 'extrudeDepth',
          };
          const mapped = map[key];
          if (!mapped) return state;
          return { [mapped]: value } as Partial<AdvancedState>;
        }),

      setFarmParam: (key, value) =>
        set((state) => {
          const map: Record<string, keyof AdvancedState> = {
            renderFarmEnabled: 'renderFarmEnabled',
            farmCoordinatorUrl: 'farmCoordinatorUrl',
          };
          const mapped = map[key];
          if (!mapped) return state;
          return { [mapped]: value } as Partial<AdvancedState>;
        }),
    }),
    {
      name: 'bvs_advanced_store',
      partialize: (state) => ({
        aiTask: state.aiTask,
        aiStyle: state.aiStyle,
        aiScale: state.aiScale,
        aiSegment: state.aiSegment,
        aiStyleTransfer: state.aiStyleTransfer,
        aiSuperRes: state.aiSuperRes,
        animateType: state.animateType,
        animateDuration: state.animateDuration,
        threeDEnabled: state.threeDEnabled,
        extrudeDepth: state.extrudeDepth,
        renderFarmEnabled: state.renderFarmEnabled,
        farmCoordinatorUrl: state.farmCoordinatorUrl,
      }),
    }
  )
);
