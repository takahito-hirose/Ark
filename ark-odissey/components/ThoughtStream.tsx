"use client";

import React, { useEffect, useRef, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useArkStore } from '../store/useArkStore';

const agentColors: Record<string, { bg: string; text: string; border: string }> = {
  ARCHITECT: { bg: 'bg-blue-950/90', text: 'text-blue-200', border: 'border-blue-500/70' },
  CODER: { bg: 'bg-emerald-950/90', text: 'text-emerald-200', border: 'border-emerald-500/70' },
  REVIEWER: { bg: 'bg-red-950/90', text: 'text-red-200', border: 'border-red-500/70' },
  REFLECTOR: { bg: 'bg-purple-950/90', text: 'text-purple-200', border: 'border-purple-500/70' },
  SYSTEM: { bg: 'bg-gray-900/90', text: 'text-gray-200', border: 'border-gray-500/70' },
};

const renderHighlightedText = (text: string) => {
  if (!text) return null;
  const parts = text.split(/`([^`]+)`/g);
  return parts.map((part, i) => {
    if (i % 2 === 1) {
      return (
        <code key={i} className="text-yellow-300 bg-yellow-900/40 px-1.5 py-0.5 rounded font-bold tracking-tight">
          {part}
        </code>
      );
    }
    const words = part.split(/\b(Error|Exception|Fail|Failed|Warning|Critical)\b/g);
    return words.map((w, j) => {
      if (j % 2 === 1) {
         return <span key={`${i}-${j}`} className="text-red-400 font-black underline decoration-red-500/50">{w}</span>;
      }
      return <span key={`${i}-${j}`}>{w}</span>;
    });
  });
};

export default function ThoughtStream() {
  const { thoughts } = useArkStore();
  const streamEndRef = useRef<HTMLDivElement>(null);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [copiedAll, setCopiedAll] = useState<boolean>(false); // 🌟 NEW: 一括コピー用の状態

  useEffect(() => {
    streamEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thoughts]);

  // 🌟 既存の個別コピー機能
  const handleCopy = (text: string, id: string) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // 🌟 NEW: 全ログ一括コピー機能
  const handleCopyAll = () => {
    if (thoughts.length === 0) return;
    
    // 全思考ログを見やすくフォーマットして結合
    const allText = thoughts.map((t, idx) => {
      let formatted = `[${idx + 1}] =================================\n`;
      formatted += `AGENT : ${t.agent}\n`;
      formatted += `TASK  : ${t.task}\n`;
      if (t.current_tool) formatted += `TOOL  : ${t.current_tool}\n`;
      formatted += `---------------------------------\n`;
      formatted += `${t.thought_process}\n`;
      return formatted;
    }).join('\n');

    navigator.clipboard.writeText(allText);
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  if (thoughts.length === 0) return null;

  return (
    <div className="absolute right-6 top-6 bottom-[38vh] w-[420px] pointer-events-auto flex flex-col z-10">
      <div className="bg-slate-900/80 backdrop-blur-xl border border-cyan-500/40 rounded-sm shadow-2xl flex flex-col h-full overflow-hidden">
        
        {/* 🌟 ヘッダー部分に一括コピーボタンを追加 */}
        <div className="p-2 border-b border-cyan-500/20 bg-cyan-500/10 text-[9px] text-cyan-300 tracking-[0.3em] uppercase font-bold shrink-0 flex justify-between items-center">
          <span>🧠 NEURAL_THOUGHT_STREAM</span>
          <div className="flex items-center gap-3">
            <button 
              onClick={handleCopyAll}
              className="bg-cyan-900/50 hover:bg-cyan-700/80 text-cyan-100 px-2 py-0.5 rounded transition-colors border border-cyan-500/50"
              title="すべての思考ログをコピー"
            >
              {copiedAll ? '✅ COPIED ALL' : '📋 COPY ALL'}
            </button>
            <span className="text-cyan-500 animate-pulse">LIVE</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto custom-scrollbar p-4 space-y-4">
          <AnimatePresence initial={false}>
            {thoughts.map((thought, idx) => {
              const style = agentColors[thought.agent.toUpperCase()] || agentColors.SYSTEM;
              const uniqueId = `${thought.timestamp}-${idx}`;

              return (
                <motion.div
                  key={uniqueId}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, scale: 0.9 }}
                  transition={{ duration: 0.2 }}
                  className="flex w-full justify-start"
                >
                  <div className={`w-full border ${style.border} ${style.bg} p-3 rounded-lg shadow-lg relative group`}>
                    
                    {/* 個別コピーボタン */}
                    <button 
                      onClick={() => handleCopy(thought.thought_process, uniqueId)}
                      className="absolute top-2 right-2 bg-black/40 hover:bg-black/80 text-gray-400 hover:text-white p-1.5 rounded transition-all flex items-center gap-1 border border-transparent hover:border-gray-500/50"
                      title="この思考ログだけコピー"
                    >
                      {copiedId === uniqueId ? (
                        <span className="text-[10px] text-green-400 font-bold">✅ COPIED</span>
                      ) : (
                        <span className="text-[12px] opacity-70 group-hover:opacity-100">📋</span>
                      )}
                    </button>

                    <div className="flex items-center justify-between mb-2 border-b border-white/10 pb-2 pr-8">
                      <span className={`text-[10px] font-black tracking-widest uppercase ${style.text}`}>
                        {thought.agent}
                      </span>
                      <span className="text-[8px] text-gray-300 bg-black/60 px-2 py-0.5 rounded-sm truncate max-w-[50%]">
                        {thought.task}
                      </span>
                    </div>
                    
                    <div className="text-xs text-gray-100 leading-relaxed font-sans whitespace-pre-wrap">
                      {renderHighlightedText(thought.thought_process)}
                    </div>
                    
                    {thought.current_tool && (
                      <div className="mt-2 text-[9px] text-yellow-400/90 flex items-center gap-1 font-mono bg-black/40 p-1.5 rounded">
                        <span className="animate-spin">⚙️</span>
                        Executing: {thought.current_tool}
                      </div>
                    )}
                  </div>
                </motion.div>
              );
            })}
          </AnimatePresence>
          <div ref={streamEndRef} />
        </div>
      </div>
    </div>
  );
}