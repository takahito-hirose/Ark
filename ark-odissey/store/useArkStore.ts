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

// 🌟 NEW: モデルの型定義
export interface ArkModel {
  id: string;
  name: string;
  isLocal: boolean;
}

interface ArkState {
  logs: LogEntry[];
  phase: 'IDLE' | 'PLANNING' | 'CODING' | 'REVIEWING' | 'COMMITTING' | 'PROPOSING' | 'DONE' | 'BLOCKED';
  isThinking: boolean;
  hasError: boolean;

  goldCoins: number;
  sessionCost: number;
  sessionTokens: number;

  targetDir: string;

  modelOverrides: {
    architect: string;
    coder: string;
    reviewer: string;
    reflector: string;
  };

  isAwaitingSearchApproval: boolean;
  pendingSearchQuery: string;
  autoApproveSearch: boolean;

  isAwaitingPlanApproval: boolean;
  pendingPlanData: PlanData | null;

  proposal: ProposalData | null;

  // 🌟 NEW: 動的モデルリストとフェッチ関数
  availableModels: ArkModel[];
  fetchModels: () => Promise<void>;

  addLog: (log: LogEntry) => void;
  setPhase: (phase: ArkState['phase']) => void;
  setThinking: (val: boolean) => void;
  setHasError: (val: boolean) => void;
  spendCoins: (amount: number) => void;
  updateTreasury: (cost: number, tokens: number) => void;
  setTargetDir: (dir: string) => void;
  setModelOverride: (role: keyof ArkState['modelOverrides'], provider: string) => void;

  setSearchApprovalRequest: (query: string) => void;
  clearSearchApproval: () => void;
  toggleAutoApprove: () => void;

  setPlanApprovalRequest: (plan: PlanData) => void;
  clearPlanApproval: () => void;

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

  isAwaitingPlanApproval: false,
  pendingPlanData: null,

  proposal: null,

  // 🌟 NEW: 初期値としてクラウドモデルを入れておく
  availableModels: [
    { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', isLocal: false },
    { id: 'gemini-2.5-Pro', name: 'Gemini 2.5 Pro', isLocal: false },
    { id: 'gpt-4o', name: 'GPT-4o (OpenAI)', isLocal: false },
    { id: 'claude-3.5-sonnet', name: 'Claude 3.5 Sonnet', isLocal: false },
  ],

  // 🌟 NEW: Ollamaからモデル一覧を取得してストアに追加するアクション
  fetchModels: async () => {
    try {
      // Reactアプリ（ブラウザ）から直接OllamaのAPIを叩く
      const res = await fetch('http://localhost:11434/api/tags');
      if (!res.ok) throw new Error('Ollama API response was not ok');

      const data = await res.json();
      const localModels: ArkModel[] = data.models.map((m: any) => ({
        id: `ollama|${m.name}`,       // 例: ollama|qwen2.5-coder:7b
        name: `🦙 Ollama (${m.name})`, // UI表示用
        isLocal: true
      }));

      set((state) => {
        // 既存のクラウドモデルと、新しく取得したローカルモデルを合体！
        const cloudModels = state.availableModels.filter(m => !m.isLocal);
        return { availableModels: [...localModels, ...cloudModels] };
      });
    } catch (error) {
      console.warn('Ollamaのモデル取得に失敗しました。CORSエラーかOllamaが停止しています。', error);
      // 取得失敗時は、フォールバック用のデフォルトOllamaを1つだけ追加する
      set((state) => {
        const cloudModels = state.availableModels.filter(m => !m.isLocal);
        return {
          availableModels: [
            { id: 'ollama', name: 'Ollama (Local Default)', isLocal: true },
            ...cloudModels
          ]
        };
      });
    }
  },

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

  setPlanApprovalRequest: (plan) => set({ isAwaitingPlanApproval: true, pendingPlanData: plan }),
  clearPlanApproval: () => set({ isAwaitingPlanApproval: false, pendingPlanData: null }),

  setProposal: (proposal) => set({ proposal }),
}));