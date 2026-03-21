"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { motion, AnimatePresence } from 'framer-motion';
import Viewport3D from '@/components/Viewport3D';
import { useArkStore } from '../store/useArkStore';

/**
 * 🚢 PROJECT ODISSEY - REFINED COMMAND DECK
 * 下部ブロックを3カラム・等高に配置したプロフェッショナルHUDよ💋
 */
export default function App() {
  const {
    phase,
    isThinking,
    hasError,
    logs,
    goldCoins,
    mode,
    isAwaitingSearchApproval,
    pendingSearchQuery,
    autoApproveSearch,
    setPhase,
    setThinking,
    setHasError,
    addLog,
    spendCoins,
    setMode,
    setSearchApprovalRequest,
    clearSearchApproval,
    toggleAutoApprove
  } = useArkStore();

  const [command, setCommand] = useState('');
  const [targetPath, setTargetPath] = useState('');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // URLリンク化関数
  const renderMessage = (msg: string) => {
    if (!msg) return "";
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = msg.split(urlRegex);
    return parts.map((part, i) => {
      if (part.match(urlRegex)) {
        return (
          <a 
            key={i} href={part} target="_blank" rel="noopener noreferrer" 
            className="text-cyan-400 underline hover:text-pink-400 transition-all cursor-pointer pointer-events-auto"
          >
            {part}
          </a>
        );
      }
      return part;
    });
  };

  // WebSocket 同期
  useEffect(() => {
    const connectWebSocket = () => {
      const socket = new WebSocket('ws://127.0.0.1:8000/ws/logs');
      socket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'SEARCH_REQUEST') {
            setSearchApprovalRequest(data.query);
            addLog({ timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }), agent: 'ARCHITECT', message: `🔭 リサーチ要求: "${data.query}"`, level: 'warning' });
          } else if (data.type === 'ARK_EVENT') {
            addLog({
              timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
              agent: 'ARK',
              message: `[${data.phase}] ${data.status}${data.detail ? ` - ${data.detail}` : ''}`,
              level: data.status === 'FAIL' || data.status === 'ERROR' ? 'error' : 'info'
            });
            if (data.phase) setPhase(data.phase.toUpperCase() as any);
            if (data.status === 'FINISH' || data.phase === 'DONE') setThinking(false);
            if (data.status === 'ERROR') setHasError(true);
          } else if (data.type === 'TOKEN_USAGE') {
            spendCoins(data.tokens);
          }
        } catch (e) { console.error(e); }
      };
      socket.onclose = () => setTimeout(connectWebSocket, 3000);
      setWs(socket);
    };
    connectWebSocket();
    return () => ws?.close();
  }, [addLog, setPhase, setThinking, setHasError, spendCoins, setSearchApprovalRequest]);

  const handleSearchApproval = (approved: boolean) => {
    if (ws?.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ type: 'SEARCH_RESPONSE', approved, query: pendingSearchQuery }));
      addLog({
        timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
        agent: 'CAPTAIN',
        message: approved ? `✅ リサーチを承認したわ。` : `❌ リサーチを却下したわ。`,
        level: approved ? 'success' : 'warning'
      });
      clearSearchApproval();
    }
  };

  const handleCommandSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim() || isThinking) return;

    const currentCommand = command;
    setCommand('');
    setThinking(true);
    setHasError(false);
    
    addLog({
      timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
      agent: 'CAPTAIN',
      message: targetPath ? `[Target: ${targetPath}]\n${currentCommand}` : currentCommand,
      level: 'info'
    });

    try {
      await fetch('http://127.0.0.1:8000/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: currentCommand, mode, auto_approve: autoApproveSearch, workspace_path: targetPath.trim() || undefined })
      });
    } catch (e) {
      setHasError(true);
      setThinking(false);
    }
  };

  return (
    <main className="h-screen w-screen overflow-hidden bg-black font-mono relative text-white select-none">
      {/* 🌟 3D BACKGROUND */}
      <div className="fixed inset-0 z-0">
        <Canvas shadows camera={{ position: [0, 1.2, 8], fov: 45 }}>
          <Viewport3D />
        </Canvas>
      </div>

      {/* 🌟 SEARCH APPROVAL MODAL */}
      <AnimatePresence>
        {isAwaitingSearchApproval && (
          <motion.div 
            initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-md p-4 pointer-events-auto"
          >
            <motion.div 
              initial={{ scale: 0.9, y: 20 }} animate={{ scale: 1, y: 0 }}
              className="bg-slate-900 border-2 border-cyan-500 shadow-[0_0_60px_rgba(6,182,212,0.5)] p-8 rounded-lg max-w-md w-full relative"
            >
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-cyan-500 text-black px-4 py-1 text-[10px] font-bold tracking-[0.3em]">
                TELESCOPE AUTH REQUIRED
              </div>
              <h2 className="text-cyan-400 text-xl font-bold mb-4 flex items-center gap-3 italic">
                <span className="text-2xl not-italic">🔭</span> 望遠鏡の起動承認
              </h2>
              <div className="bg-black/50 border border-cyan-500/30 p-4 rounded-md mb-8 text-cyan-200 text-sm break-words leading-relaxed">
                "{pendingSearchQuery}"
              </div>
              <div className="flex gap-4">
                <button onClick={() => handleSearchApproval(true)} className="flex-1 py-3 bg-cyan-500 hover:bg-cyan-400 text-black font-bold rounded-sm transition-all active:scale-95">APPROVE ⚓️</button>
                <button onClick={() => handleSearchApproval(false)} className="flex-1 py-3 bg-red-900/40 hover:bg-red-900/60 text-red-400 border border-red-500/50 font-bold rounded-sm transition-all">SKIP 🚫</button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="fixed inset-0 z-20 p-6 flex flex-col pointer-events-none">
        
        {/* TOP HUD: TREASURY & SETTINGS */}
        <div className="flex justify-between items-start pointer-events-auto">
          <div className="bg-slate-900/80 backdrop-blur-lg border border-cyan-500/40 p-4 rounded-sm w-80 shadow-2xl">
             <div className="flex justify-between items-center mb-4">
               <span className="text-[10px] font-bold text-cyan-400 tracking-widest flex items-center gap-2">
                 <div className={`w-2 h-2 rounded-full ${isThinking ? 'bg-pink-500 animate-pulse' : 'bg-green-500'}`} />
                 ARK TREASURY
               </span>
               <span className="text-xl font-bold text-yellow-300 drop-shadow-[0_0_8px_rgba(253,224,71,0.5)]">🪙 {goldCoins.toLocaleString()}</span>
             </div>
             <div className="grid grid-cols-2 gap-2 mb-3">
               {['ECO', 'RICH'].map(m => (
                 <button 
                   key={m} onClick={() => setMode(m as any)}
                   className={`py-1 text-[10px] border transition-all font-bold ${mode === m ? 'bg-cyan-500 text-black border-cyan-500 shadow-[0_0_15px_rgba(6,182,212,0.4)]' : 'text-gray-500 border-gray-700 hover:border-gray-500'}`}
                 >
                   {m} MODE
                 </button>
               ))}
             </div>
             <div className="flex items-center justify-between border-t border-cyan-500/10 pt-3">
                <span className="text-[9px] text-gray-400 uppercase tracking-widest">Auto-Approve Research</span>
                <button 
                  onClick={toggleAutoApprove}
                  className={`w-10 h-5 rounded-full relative transition-colors ${autoApproveSearch ? 'bg-cyan-500' : 'bg-gray-700'}`}
                >
                  <div className={`absolute top-1 w-3 h-3 bg-white rounded-full transition-all ${autoApproveSearch ? 'left-6' : 'left-1'}`} />
                </button>
             </div>
          </div>
        </div>

        <div className="flex-1" />

        {/* 🌟 BOTTOM COMMAND DECK (TRIPLE COLUMN - EQUAL HEIGHT) */}
        <div className="flex gap-4 pointer-events-auto h-[35vh] w-full shrink-0">
          
          {/* 1. SYLPH ACTIVITY LOG (Left - Flex 2) */}
          <div className="flex-[2] bg-slate-900/80 backdrop-blur-md border border-purple-500/40 rounded-sm flex flex-col overflow-hidden shadow-2xl">
             <div className="p-2 border-b border-purple-500/20 bg-purple-500/10 text-[9px] text-purple-300 tracking-[0.3em] uppercase font-bold">SYLPH_ACTIVITY_STREAM</div>
             <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar text-[11px]">
                {logs.map((log, i) => (
                  <div key={i} className={`flex gap-3 leading-relaxed ${log.level === 'warning' ? 'text-cyan-300 font-bold' : ''}`}>
                    <span className="text-gray-600 shrink-0 font-normal">[{log.timestamp}]</span>
                    <span className={`font-black shrink-0 ${log.agent === 'CAPTAIN' ? 'text-orange-400' : 'text-pink-400'}`}>{log.agent}:</span>
                    <span className={`break-words ${log.level === 'error' ? 'text-red-400 font-bold' : 'text-gray-300'}`}>
                      {renderMessage(log.message)}
                    </span>
                  </div>
                ))}
                <div ref={logsEndRef} />
             </div>
          </div>

          {/* 2. VOYAGE PHASE (Middle - Flex 1) */}
          <div className="flex-1 bg-slate-900/80 backdrop-blur-md border border-cyan-500/40 rounded-sm flex flex-col overflow-hidden shadow-xl">
            <div className="p-2 border-b border-cyan-500/20 bg-cyan-500/10 text-[9px] text-cyan-300 tracking-[0.3em] uppercase font-bold">NAV_PHASE_MONITOR</div>
            <div className="flex-1 flex flex-col justify-center p-6 space-y-4">
               {['PLANNING', 'CODING', 'REVIEWING', 'COMMITTING', 'DONE'].map(p => (
                 <div key={p} className={`flex items-center gap-4 text-[10px] font-black tracking-[0.2em] transition-all duration-500 ${phase === p ? 'text-cyan-400' : 'text-gray-700'}`}>
                   <div className={`w-2.5 h-2.5 rounded-full transition-all duration-700 ${phase === p ? 'bg-cyan-400 shadow-[0_0_15px_#22d3ee] scale-125' : 'bg-gray-800'}`} />
                   {p}
                 </div>
               ))}
            </div>
          </div>

          {/* 3. MISSION CONTROL (Right - Flex 1.5) */}
          <div className="flex-[1.5] bg-slate-900/90 border-t-4 border-cyan-500 rounded-sm flex flex-col shadow-2xl relative">
            <div className="absolute -top-3 left-4 bg-cyan-500 text-black text-[9px] px-3 py-0.5 font-bold tracking-widest">MISSION_CTRL_V2</div>
            <form onSubmit={handleCommandSubmit} className="flex-1 flex flex-col p-4 gap-3">
              <div className="relative group">
                <span className="absolute left-3 top-2 text-xs">📁</span>
                <input
                  type="text" value={targetPath} onChange={(e) => setTargetPath(e.target.value)}
                  placeholder="Target Repository or Local Path"
                  className="w-full bg-black/60 border border-gray-800 text-[10px] text-gray-400 pl-9 pr-3 py-2 focus:border-purple-500 focus:bg-black/80 outline-none transition-all placeholder:text-gray-700"
                />
              </div>
              <div className="relative flex-1">
                <span className="absolute left-3 top-3 text-[10px] text-orange-500 font-bold">❯</span>
                <textarea 
                  value={command} onChange={(e) => setCommand(e.target.value)} disabled={isThinking}
                  placeholder="指令を入力してください、船長💋"
                  className="w-full h-full bg-black/60 border border-gray-800 p-3 pl-7 text-xs text-white outline-none focus:border-cyan-500 focus:bg-black/80 resize-none custom-scrollbar placeholder:text-gray-700"
                />
              </div>
              <button 
                disabled={isThinking || !command.trim()}
                className="w-full py-3 bg-cyan-500 text-black font-black text-[10px] tracking-[0.4em] uppercase hover:bg-cyan-400 disabled:opacity-30 disabled:grayscale transition-all shadow-[0_0_20px_rgba(6,182,212,0.3)] active:scale-95"
              >
                {isThinking ? 'VOYAGING_NOW...' : 'TRANSMIT_DIRECTIVES'}
              </button>
            </form>
          </div>

        </div>
      </div>
    </main>
  );
}