"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { motion, AnimatePresence } from 'framer-motion';
import Viewport3D from '@/components/Viewport3D';
import { useArkStore } from '../store/useArkStore';

/**
 * 🚢 PROJECT ODISSEY - ULTIMATE HUD LAYER
 * 既存プロジェクトのパス指定機能を統合した司令部 UI。
 */
export default function App() {
  const {
    phase,
    isThinking,
    hasError,
    logs,
    goldCoins,
    mode,
    setPhase,
    setThinking,
    setHasError,
    addLog,
    spendCoins,
    setMode
  } = useArkStore();

  const [command, setCommand] = useState('');
  const [targetPath, setTargetPath] = useState('');
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // リンクをハイライトするヘルパー
  const renderMessage = (msg: string) => {
    const urlRegex = /(https?:\/\/[^\s]+)/g;
    const parts = msg.split(urlRegex);
    return parts.map((part, i) => {
      if (part.match(urlRegex)) {
        return (
          <a
            key={i}
            href={part}
            target="_blank"
            rel="noopener noreferrer"
            className="text-[#bd93f9] underline hover:text-[#ff79c6] transition-all cursor-pointer pointer-events-auto"
          >
            {part}
          </a>
        );
      }
      return part;
    });
  };

  // 🧠 Neuro-Link (WebSocket) 接続
  useEffect(() => {
    let ws: WebSocket;
    const connectWebSocket = () => {
      ws = new WebSocket('ws://127.0.0.1:8000/ws/logs');
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'ARK_EVENT') {
            addLog({
              timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
              agent: 'ARK',
              message: `[${data.phase}] ${data.status}${data.detail ? ` - ${data.detail}` : ''}`,
              level: data.status === 'FAIL' ? 'error' : 'info'
            });
            if (data.phase) setPhase(data.phase.toUpperCase());
            if (data.phase === 'DONE') setThinking(false);
            if (data.phase === 'BLOCKED') { setHasError(true); setThinking(false); }
          }
          if (data.type === 'TOKEN_USAGE') spendCoins(data.tokens);
        } catch (e) { console.error(e); }
      };
      ws.onclose = () => setTimeout(connectWebSocket, 3000);
    };
    connectWebSocket();
    return () => ws?.close();
  }, [addLog, setPhase, spendCoins, setHasError, setThinking]);

  // 🚀 指示送信
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
      const res = await fetch('http://127.0.0.1:8000/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          command: currentCommand, 
          mode: mode,
          workspace_path: targetPath.trim() || undefined
        })
      });
      if (!res.ok) throw new Error('Transmission Failed');
    } catch (error: any) {
      setHasError(true);
      setThinking(false);
      addLog({
        timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
        agent: 'SYSTEM',
        message: 'Bridge Connection Lost.',
        level: 'error'
      });
    }
  };

  return (
    <main className="h-screen w-screen overflow-hidden bg-black font-mono relative text-white">
      <div className="fixed inset-0 z-0">
        <Canvas shadows camera={{ position: [0, 1.2, 8], fov: 45 }}>
          <Viewport3D />
        </Canvas>
      </div>

      <div className={`fixed inset-0 z-10 pointer-events-none transition-colors duration-1000 ${hasError ? 'bg-red-900/20' : 'bg-black/40'}`} />

      <div className="fixed inset-0 z-20 p-6 flex flex-col pointer-events-none">
        
        {/* TOP STATUS */}
        <div className="flex justify-between items-start pointer-events-auto shrink-0">
          <motion.div className="bg-slate-900/60 backdrop-blur-md border border-cyan-500/30 p-4 rounded-sm w-72">
            <h2 className="text-[10px] uppercase tracking-widest text-cyan-400 mb-2 flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isThinking ? 'bg-pink-500 animate-pulse' : 'bg-green-500'}`} />
              Telemetry
            </h2>
            <div className="flex justify-between items-baseline">
              <span className="text-[10px] text-gray-400">Treasury</span>
              <span className="text-xl font-bold text-yellow-300">🪙 {goldCoins.toLocaleString()}</span>
            </div>
            <div className="mt-3 flex gap-2">
              {['ECO', 'RICH'].map(m => (
                <button key={m} onClick={() => setMode(m as any)} className={`flex-1 py-1 text-[10px] border transition-all ${mode === m ? 'bg-cyan-500 text-black border-cyan-500 shadow-[0_0_10px_rgba(6,182,212,0.5)]' : 'border-gray-700 text-gray-500'}`}>
                  {m}
                </button>
              ))}
            </div>
          </motion.div>

          <div className="bg-slate-900/60 border border-pink-500/30 p-3 rounded-sm text-right">
            <div className="text-[8px] text-gray-500 uppercase tracking-widest">Target Status</div>
            <div className={`text-xs font-bold ${hasError ? 'text-red-500' : 'text-white'}`}>
              {targetPath ? 'MOUNTED: EXISTING SHIP' : 'NEW BUILD: READY'}
            </div>
          </div>
        </div>

        <div className="flex-1" />

        {/* BOTTOM HUD */}
        <div className="flex gap-6 pointer-events-auto h-[40vh] w-full shrink-0">
          
          {/* LOGS */}
          <div className="flex-[3] bg-slate-900/60 backdrop-blur-md border border-purple-500/30 rounded-sm flex flex-col overflow-hidden relative">
            <div className="p-2 border-b border-purple-500/20 bg-purple-500/5 text-[10px] text-purple-300 uppercase tracking-widest px-4">
              Activity Stream
            </div>
            <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
              {logs.map((log, i) => (
                <div key={i} className="text-[11px] flex gap-3 leading-relaxed">
                  <span className="text-gray-600 shrink-0">[{log.timestamp}]</span>
                  <span className={`font-bold ${log.agent === 'CAPTAIN' ? 'text-orange-400' : 'text-pink-400'}`}>{log.agent}:</span>
                  <span className={log.level === 'error' ? 'text-red-400' : 'text-gray-200'}>{renderMessage(log.message)}</span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
          </div>

          {/* CONTROL */}
          <div className="flex-[2] flex flex-col gap-4">
            <div className="flex-1 bg-slate-900/60 border border-cyan-500/30 p-4 rounded-sm flex flex-col">
              <span className="text-[9px] text-cyan-500 uppercase tracking-[0.3em] mb-3 border-b border-cyan-500/10 pb-1">Voyage Phase</span>
              <div className="space-y-2 flex-1 flex flex-col justify-center">
                {['PLANNING', 'CODING', 'REVIEWING', 'COMMITTING', 'DONE'].map(p => (
                  <div key={p} className="flex items-center gap-3">
                    <div className={`w-2 h-2 rounded-full ${phase === p ? 'bg-cyan-400 shadow-[0_0_10px_#22d3ee]' : 'bg-gray-800'}`} />
                    <span className={`text-[10px] font-bold tracking-widest ${phase === p ? 'text-cyan-400' : 'text-gray-600'}`}>{p}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="flex-1 bg-slate-900/80 border-t-2 border-cyan-500 p-4 relative shadow-2xl">
              <div className="absolute -top-3 left-4 bg-cyan-500 text-black text-[9px] px-2 py-0.5 font-bold">MISSION_CTRL</div>
              <form onSubmit={handleCommandSubmit} className="h-full flex flex-col gap-3">
                <div className="relative">
                  <span className="absolute left-2 top-1.5 text-xs">📁</span>
                  <input
                    type="text"
                    value={targetPath}
                    onChange={(e) => setTargetPath(e.target.value)}
                    placeholder="Existing Project Path (Optional)"
                    className="w-full bg-black/40 border border-gray-800 text-[10px] text-gray-300 pl-8 pr-3 py-1.5 focus:border-purple-500 outline-none transition-all"
                  />
                </div>
                <div className="flex-1 relative">
                  <span className="absolute left-2 top-2 text-xs text-orange-400">❯</span>
                  <textarea
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    placeholder="Enter mission directives..."
                    className="w-full h-full bg-black/40 border border-gray-800 text-xs text-white pl-6 pr-3 py-2 resize-none outline-none focus:border-cyan-500 transition-all custom-scrollbar"
                  />
                </div>
                <button
                  type="submit"
                  disabled={isThinking || !command.trim()}
                  className="w-full py-2 bg-cyan-500 hover:bg-cyan-400 text-black font-bold text-[10px] tracking-widest transition-all disabled:opacity-50"
                >
                  {isThinking ? 'ENGAGING...' : 'TRANSMIT DIRECTIVES'}
                </button>
              </form>
            </div>
          </div>

        </div>
      </div>
    </main>
  );
}