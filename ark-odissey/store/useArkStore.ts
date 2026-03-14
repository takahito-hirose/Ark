import { create } from 'zustand';

// ログの型定義を新しく追加！💋
export interface LogEntry {
  timestamp: string;
  agent: string;
  message: string;
  level?: 'info' | 'success' | 'error' | 'warning';
}

interface ArkState {
  logs: LogEntry[]; // 文字列の配列から、オブジェクトの配列に変更
  phase: 'IDLE' | 'PLAN' | 'CODE' | 'RUN' | 'REVIEW';
  isThinking: boolean;
  goldCoins: number;
  mode: 'ECO' | 'RICH';
  targetDir: string;
  addLog: (log: LogEntry) => void;
  setPhase: (phase: ArkState['phase']) => void;
  setThinking: (val: boolean) => void; // setIsThinking から変更
  spendCoins: (amount: number) => void;
  setMode: (mode: 'ECO' | 'RICH') => void;
  setTargetDir: (dir: string) => void;
}

export const useArkStore = create<ArkState>((set) => ({
  logs: [],
  phase: 'IDLE',
  isThinking: false,
  goldCoins: 20000,
  mode: 'ECO',
  targetDir: '',
  
  // 新しいログを配列の後ろ（末尾）に追加し、直近50件を保持する
  addLog: (log) => set((state) => {
    const newLogs = [...state.logs, log];
    return { logs: newLogs.length > 50 ? newLogs.slice(newLogs.length - 50) : newLogs };
  }),
  
  setPhase: (phase) => set({ phase }),
  setThinking: (isThinking) => set({ isThinking }),
  spendCoins: (amount) => set((state) => ({ goldCoins: Math.max(0, state.goldCoins - amount) })),
  setMode: (mode) => set({ mode }),
  setTargetDir: (targetDir) => set({ targetDir }),
}));