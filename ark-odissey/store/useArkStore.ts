
import { create } from 'zustand';

interface ArkState {
  logs: string[];
  phase: 'IDLE' | 'PLAN' | 'CODE' | 'RUN' | 'REVIEW';
  isThinking: boolean;
  goldCoins: number;
  mode: 'ECO' | 'RICH';
  targetDir: string;
  addLog: (log: string) => void;
  setPhase: (phase: ArkState['phase']) => void;
  setIsThinking: (val: boolean) => void;
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
  addLog: (log) => set((state) => ({ logs: [log, ...state.logs].slice(0, 50) })),
  setPhase: (phase) => set({ phase }),
  setIsThinking: (isThinking) => set({ isThinking }),
  spendCoins: (amount) => set((state) => ({ goldCoins: Math.max(0, state.goldCoins - amount) })),
  setMode: (mode) => set({ mode }),
  setTargetDir: (targetDir) => set({ targetDir }),
}));
