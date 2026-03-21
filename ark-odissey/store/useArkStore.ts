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
  goldCoins: number;
  mode: 'ECO' | 'RICH';
  targetDir: string;

  // 🔭 SEARCH APPROVAL STATES
  isAwaitingSearchApproval: boolean;
  pendingSearchQuery: string;
  autoApproveSearch: boolean;

  addLog: (log: LogEntry) => void;
  setPhase: (phase: ArkState['phase']) => void;
  setThinking: (val: boolean) => void;
  setHasError: (val: boolean) => void;
  spendCoins: (amount: number) => void;
  setMode: (mode: 'ECO' | 'RICH') => void;
  setTargetDir: (dir: string) => void;
  
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
  mode: 'ECO',
  targetDir: '',

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
  setMode: (mode) => set({ mode }),
  setTargetDir: (targetDir) => set({ targetDir }),

  setSearchApprovalRequest: (query) => set({ isAwaitingSearchApproval: true, pendingSearchQuery: query }),
  clearSearchApproval: () => set({ isAwaitingSearchApproval: false, pendingSearchQuery: '' }),
  toggleAutoApprove: () => set((state) => ({ autoApproveSearch: !state.autoApproveSearch })),
}));