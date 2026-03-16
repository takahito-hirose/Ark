import { create } from 'zustand';

export interface LogEntry {
  timestamp: string;
  agent: string;
  message: string;
  level?: 'info' | 'success' | 'error' | 'warning';
}

interface ArkState {
  logs: LogEntry[];
  // 🌟 修正: バックエンドの定義に合わせて PLANNING などの現在進行形と BLOCKED を追加！
  phase: 'IDLE' | 'PLANNING' | 'CODING' | 'REVIEWING' | 'COMMITTING' | 'DONE' | 'BLOCKED';
  isThinking: boolean;
  hasError: boolean; // 🚨 NEW: エマージェンシー状態を管理するフラグ
  goldCoins: number;
  mode: 'ECO' | 'RICH';
  targetDir: string;
  addLog: (log: LogEntry) => void;
  setPhase: (phase: ArkState['phase']) => void;
  setThinking: (val: boolean) => void;
  setHasError: (val: boolean) => void; // 🚨 NEW
  spendCoins: (amount: number) => void;
  setMode: (mode: 'ECO' | 'RICH') => void;
  setTargetDir: (dir: string) => void;
}

export const useArkStore = create<ArkState>((set) => ({
  logs: [],
  phase: 'IDLE',
  isThinking: false,
  hasError: false,
  goldCoins: 20000,
  mode: 'ECO',
  targetDir: '',
  
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
}));