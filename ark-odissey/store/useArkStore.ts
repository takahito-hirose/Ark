import { create } from 'zustand';

export interface LogEntry {
  timestamp: string;
  agent: string;
  message: string;
  level?: 'info' | 'success' | 'error' | 'warning';
}

export interface ProposalData {
  next_goal: string;
  expected_artifacts: string[];
  risks: string[];
  workspace_path?: string;
}

// 🌟 NEW: Architectが生成したプラン（海図とテスト）の型定義
export interface SubTask {
  id: string;
  title: string;
  description: string;
  dependencies: string[];
}

export interface PlanData {
  goal: string;
  target_files: string[];
  tasks: SubTask[];
  test_code: string;
}

interface ArkState {
  logs: LogEntry[];
  phase: 'IDLE' | 'PLANNING' | 'CODING' | 'REVIEWING' | 'COMMITTING' | 'PROPOSING' | 'DONE' | 'BLOCKED';
  isThinking: boolean;
  hasError: boolean;

  // 🪙 The Treasury
  goldCoins: number;
  sessionCost: number;
  sessionTokens: number;

  targetDir: string;

  // 🛠 CURRENT MODELS
  modelOverrides: {
    architect: string;
    coder: string;
    reviewer: string;
    reflector: string;
  };

  // 🔭 SEARCH APPROVAL STATES
  isAwaitingSearchApproval: boolean;
  pendingSearchQuery: string;
  autoApproveSearch: boolean;

  // 🌟 NEW: PLAN/TEST APPROVAL STATES (TDDの入り口)
  isAwaitingPlanApproval: boolean;
  pendingPlanData: PlanData | null;

  // 🌟 PROPOSAL STATES
  proposal: ProposalData | null;

  addLog: (log: LogEntry) => void;
  setPhase: (phase: ArkState['phase']) => void;
  setThinking: (val: boolean) => void;
  setHasError: (val: boolean) => void;
  spendCoins: (amount: number) => void;
  updateTreasury: (cost: number, tokens: number) => void;
  setTargetDir: (dir: string) => void;
  setModelOverride: (role: keyof ArkState['modelOverrides'], provider: string) => void;

  // 🔭 SEARCH ACTIONS
  setSearchApprovalRequest: (query: string) => void;
  clearSearchApproval: () => void;
  toggleAutoApprove: () => void;

  // 🌟 NEW: PLAN APPROVAL ACTIONS
  setPlanApprovalRequest: (plan: PlanData) => void;
  clearPlanApproval: () => void;

  // 🌟 PROPOSAL ACTIONS
  setProposal: (proposal: ProposalData | null) => void;
}

export const useArkStore = create<ArkState>((set) => ({
  logs: [],
  phase: 'IDLE',
  isThinking: false,
  hasError: false,
  goldCoins: 20000,
  sessionCost: 0,
  sessionTokens: 0,
  targetDir: '',

  modelOverrides: {
    architect: 'gemini-2.5-flash',
    coder: 'gemini-2.5-flash',
    reviewer: 'gemini-2.5-flash',
    reflector: 'gemini-2.5-flash'
  },

  isAwaitingSearchApproval: false,
  pendingSearchQuery: '',
  autoApproveSearch: false,

  // 🌟 NEW: 初期値
  isAwaitingPlanApproval: false,
  pendingPlanData: null,

  proposal: null,

  addLog: (log) => set((state) => {
    const newLogs = [...state.logs, log];
    return { logs: newLogs.length > 50 ? newLogs.slice(newLogs.length - 50) : newLogs };
  }),

  setPhase: (phase) => set({ phase }),
  setThinking: (isThinking) => set({ isThinking }),
  setHasError: (hasError) => set({ hasError }),
  spendCoins: (amount) => set((state) => ({ goldCoins: Math.max(0, state.goldCoins - amount) })),

  updateTreasury: (cost, tokens) => set((state) => ({
    sessionCost: state.sessionCost + cost,
    sessionTokens: state.sessionTokens + tokens
  })),

  setTargetDir: (targetDir) => set({ targetDir }),

  setModelOverride: (role, provider) => set((state) => ({
    modelOverrides: { ...state.modelOverrides, [role]: provider }
  })),

  setSearchApprovalRequest: (query) => set({ isAwaitingSearchApproval: true, pendingSearchQuery: query }),
  clearSearchApproval: () => set({ isAwaitingSearchApproval: false, pendingSearchQuery: '' }),
  toggleAutoApprove: () => set((state) => ({ autoApproveSearch: !state.autoApproveSearch })),

  // 🌟 NEW: プラン承認のアクション実装
  setPlanApprovalRequest: (plan) => set({ isAwaitingPlanApproval: true, pendingPlanData: plan }),
  clearPlanApproval: () => set({ isAwaitingPlanApproval: false, pendingPlanData: null }),

  setProposal: (proposal) => set({ proposal }),
}));