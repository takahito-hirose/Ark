import { create } from 'zustand';

export interface LogEntry {
  timestamp: string;
  agent: string;
  message: string;
  level?: 'info' | 'success' | 'error' | 'warning';
}

interface ArkState {
  logs: LogEntry[];
  phase: 'IDLE' | 'PLANNING' | 'CODING' | 'REVIEWING' | 'COMMITTING' | 'DONE' | 'BLOCKED';
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

  // デフォルトはすべて Gemini 2.5 Flash
  modelOverrides: {
    architect: 'gemini-2.5-flash',
    coder: 'gemini-2.5-flash',
    reviewer: 'gemini-2.5-flash',
    reflector: 'gemini-2.5-flash'
  },

  isAwaitingSearchApproval: false,
  pendingSearchQuery: '',
  autoApproveSearch: false,

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
}));