"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { motion, AnimatePresence } from 'framer-motion';
import Viewport3D from '@/components/Viewport3D';
import { useArkStore } from '../store/useArkStore';

/**
 * 🚢 PROJECT ODISSEY - ULTIMATE HUD LAYER
 * 日本時間対応、URLリンク化、大容量入力コンソールを搭載した
 * ARK専用の操舵室インターフェースよ！💋
 */
export default function App() {
  const { 
    phase, 
    isThinking, 
    logs, 
    goldCoins, 
    setPhase, 
    setThinking, 
    addLog, 
    spendCoins 
  } = useArkStore();
  
  const [command, setCommand] = useState('');
  const logsEndRef = useRef<HTMLDivElement>(null);

  // ログが追加されたら一番下まで自動スクロール
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // 🌟 メッセージ内の URL を自動でリンク <a> タグに変換するわよ！
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
            className="text-[#bd93f9] underline decoration-[#ff79c6] hover:text-[#ff79c6] hover:drop-shadow-[0_0_8px_#ff79c6] transition-all cursor-pointer pointer-events-auto"
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
    let reconnectTimer: NodeJS.Timeout;

    const connectWebSocket = () => {
      ws = new WebSocket('ws://127.0.0.1:8000/ws/logs');

      ws.onopen = () => {
        addLog({
          timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
          agent: 'SYSTEM',
          message: 'Neuro-Link (WebSocket) Connection Established. 🧠✨',
          level: 'success'
        });
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'ARK_EVENT') {
            const phaseTag = data.phase ? `[${data.phase}] ` : '';
            const detail = data.detail ? ` - ${data.detail}` : '';
            
            addLog({
              timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
              agent: 'ARK',
              message: `${phaseTag}${data.status}${detail}`,
              level: data.retry_count > 0 ? 'error' : 'info'
            });

            if (data.phase) {
              setPhase(data.phase.toUpperCase() as any);
            }
          }

          if (data.type === 'TOKEN_USAGE') {
            spendCoins(data.tokens);
          }
        } catch (error) {
          console.error('WebSocket Error:', error);
        }
      };

      ws.onclose = () => {
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      };
    };

    connectWebSocket();
    return () => {
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, [addLog, setPhase, spendCoins]);

  // 🚀 指示送信
  const handleCommandSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim() || isThinking) return;

    const currentCommand = command;
    setCommand('');
    setThinking(true);

    addLog({
      timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
      agent: 'CAPTAIN',
      message: currentCommand,
      level: 'info'
    });

    try {
      const res = await fetch('http://127.0.0.1:8000/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: currentCommand })
      });
      
      const data = await res.json();
      if (!res.ok) throw new Error(data.message);

    } catch (error: any) {
      addLog({
        timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
        agent: 'SYSTEM',
        message: error.message || 'Transmission Failed.',
        level: 'error'
      });
      setThinking(false);
    }
  };

  return (
    <main className="h-screen w-screen overflow-hidden bg-black font-mono relative text-white">
      
      {/* BACKGROUND: 3D OCEAN */}
      <div className="fixed inset-0 z-0">
        <Canvas shadows camera={{ position: [0, 1.2, 8], fov: 45 }}>
          <Viewport3D />
        </Canvas>
      </div>

      {/* VIGNETTE & OVERLAY */}
      <div className="fixed inset-0 z-10 pointer-events-none bg-[radial-gradient(circle_at_center,transparent_30%,rgba(0,0,0,0.8)_100%)]" />

      {/* UI LAYER */}
      <div className="fixed inset-0 z-20 p-8 flex flex-col justify-between pointer-events-none">
        
        {/* TOP HUD */}
        <div className="flex justify-between items-start pointer-events-auto">
          <motion.div 
            initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
            /* 🌟 透過度を 60 -> 40 に、ブラーを md に統一して透け感をアップ！ */
            className="bg-[#0f172a]/40 backdrop-blur-md border border-[#8be9fd]/30 p-5 rounded-sm shadow-[0_0_20px_rgba(139,233,253,0.1)] min-w-[280px]"
          >
            <h2 className="text-[#8be9fd] text-[10px] uppercase tracking-[0.4em] mb-4 flex items-center gap-2">
              <div className={`w-2 h-2 rounded-full ${isThinking ? 'bg-[#ff79c6] animate-pulse' : 'bg-[#50fa7b]'}`} />
              System Telemetry
            </h2>
            <div className="space-y-3">
              <div className="flex justify-between items-baseline">
                <span className="text-[10px] text-gray-500 uppercase">Treasury</span>
                <span className="text-xl font-bold text-[#f1fa8c] drop-shadow-[0_0_10px_rgba(241,250,140,0.5)]">
                  🪙 {goldCoins.toLocaleString()} <span className="text-[10px] text-gray-400">G</span>
                </span>
              </div>
              <div className="w-full bg-gray-800 h-1 rounded-full overflow-hidden">
                <motion.div 
                  className="h-full bg-[#f1fa8c]" 
                  initial={{ width: '100%' }}
                  animate={{ width: `${(goldCoins / 20000) * 100}%` }}
                />
              </div>
            </div>
          </motion.div>

          <motion.div 
            initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
            className="flex flex-col items-end gap-2"
          >
            {/* 🌟 ここも透過度を 60 -> 40 に！ */}
            <div className="bg-[#0f172a]/40 backdrop-blur-md border border-[#ff79c6]/30 px-6 py-3 rounded-sm flex items-center gap-4">
              <div className="text-right">
                <div className="text-[9px] text-gray-500 uppercase tracking-widest">Target Harbor</div>
                <div className="text-sm font-bold text-white uppercase tracking-tighter">GitHub / {phase === 'DONE' ? 'DEPLOYED' : 'NAVIGATING'}</div>
              </div>
              <div className="w-10 h-10 rounded-full border border-[#ff79c6]/50 flex items-center justify-center text-[#ff79c6]">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>
              </div>
            </div>
          </motion.div>
        </div>

        {/* BOTTOM HUD */}
        {/* 🌟 修正: items-end を items-stretch に変えて、左右の高さを強制的に合わせるわよ！高さも40vhくらいに調整！ */}
        <div className="flex gap-8 h-[40vh] pointer-events-auto items-stretch">
          
          {/* SYLPH ACTIVITY (Terminal) */}
          {/* 🌟 透過度を 80 -> 40 に！ */}
          <div className="flex-1 h-full bg-[#0f172a]/40 backdrop-blur-md border border-[#bd93f9]/40 rounded-sm flex flex-col overflow-hidden relative shadow-[0_0_40px_rgba(0,0,0,0.5)]">
            <div className="bg-[#bd93f9]/10 p-3 px-5 border-b border-[#bd93f9]/20 flex justify-between items-center">
              <div className="flex items-center gap-3">
                <div className="w-1.5 h-1.5 bg-[#bd93f9] rounded-full animate-pulse" />
                <span className="text-[11px] text-[#bd93f9] font-bold tracking-[0.3em] uppercase">Sylph Activity Log</span>
              </div>
              <div className="text-[10px] text-[#bd93f9]/50 font-mono">NODE: ARK_ODISSEY_V5</div>
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-3 custom-scrollbar">
              <AnimatePresence initial={false}>
                {logs.map((log, i) => (
                  <motion.div 
                    key={i} 
                    initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                    className="text-[13px] flex gap-4 leading-relaxed group"
                  >
                    <span className="text-gray-600 shrink-0 font-mono text-[11px]">[{log.timestamp}]</span>
                    <span className={`shrink-0 font-bold tracking-tighter ${
                      log.agent === 'CAPTAIN' ? 'text-[#ffb86c]' : 
                      log.agent === 'ARK' ? 'text-[#ff79c6]' : 'text-[#8be9fd]'
                    }`}>
                      {log.agent}:
                    </span>
                    <span className={`
                      flex-1 break-all
                      ${log.level === 'error' ? 'text-[#ff5555]' : ''}
                      ${log.level === 'success' ? 'text-[#50fa7b]' : ''}
                      ${log.level === 'info' ? 'text-gray-300' : ''}
                    `}>
                      {renderMessage(log.message)}
                    </span>
                  </motion.div>
                ))}
              </AnimatePresence>
              <div ref={logsEndRef} />
            </div>
            
            {/* TERMINAL EFFECTS */}
            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:100%_4px,3px_100%] opacity-30" />
            <div className="scanline" />
          </div>

          {/* COMMAND CENTER */}
          {/* 🌟 修正: 親コンテナにも h-full を付与して左と高さを揃える！ */}
          <div className="w-[500px] flex flex-col gap-6 h-full">
            
            {/* SEA CHART (Status map) */}
            {/* 🌟 修正: flex-1 を付与して、余った高さをコイツに埋めさせる！透過度も 90 -> 40 に！ */}
            <div className="flex-1 bg-[#0f172a]/40 backdrop-blur-md border border-[#8be9fd]/40 p-5 shadow-[0_0_30px_rgba(139,233,253,0.1)] flex flex-col">
              <h3 className="text-[10px] text-[#8be9fd] uppercase tracking-[0.4em] mb-6 border-b border-[#8be9fd]/20 pb-2">Voyage Progress</h3>
              {/* 中身を上下中央揃えにして綺麗に見せるわ💋 */}
              <div className="flex flex-col gap-4 px-2 flex-1 justify-center">
                {['PLANNING', 'CODING', 'REVIEWING', 'COMMITTING', 'DONE'].map((p, i, arr) => {
                  const isActive = phase === p;
                  const isPast = arr.indexOf(phase) > i;
                  return (
                    <div key={p} className="flex items-center gap-4 relative">
                      <div className={`w-3 h-3 rounded-full border transition-all duration-500 z-10 
                        ${isActive ? 'border-[#8be9fd] bg-[#8be9fd] shadow-[0_0_15px_#8be9fd]' : 
                          isPast ? 'border-[#50fa7b] bg-[#50fa7b]' : 'border-gray-700 bg-transparent'}`} 
                      />
                      <span className={`text-[11px] font-bold tracking-[0.2em] transition-colors ${
                        isActive ? 'text-[#8be9fd]' : isPast ? 'text-[#50fa7b]' : 'text-gray-600'
                      }`}>
                        {p}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* COMMAND CONSOLE (Textarea Expansion) */}
            {/* 🌟 透過度を 95 -> 50 に！（入力エリアだから少しだけ濃いめに残す） */}
            <div className="bg-[#0f172a]/50 backdrop-blur-lg border-t-2 border-[#8be9fd] p-6 shadow-[0_-10px_40px_rgba(139,233,253,0.2)] relative">
              <div className="absolute -top-3 left-6 bg-[#8be9fd] text-black text-[9px] px-3 py-0.5 font-bold tracking-widest uppercase">
                Mission Control
              </div>
              <form onSubmit={handleCommandSubmit} className="space-y-4">
                <div className="relative">
                  <span className="absolute left-3 top-4 text-[#ffb86c] font-bold">❯</span>
                  <textarea
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleCommandSubmit(e as any);
                      }
                    }}
                    disabled={isThinking}
                    placeholder="Describe your requirements in detail..."
                    className="w-full bg-black/60 border border-gray-800 text-white pl-8 pr-4 py-4 rounded-sm focus:outline-none focus:border-[#8be9fd] focus:ring-1 focus:ring-[#8be9fd] transition-all disabled:opacity-50 font-mono text-[13px] resize-none h-32 custom-scrollbar"
                  />
                </div>
                <button 
                  type="submit" 
                  disabled={isThinking || !command.trim()}
                  className="w-full bg-[#8be9fd] hover:bg-[#a2ffff] text-black py-3 rounded-sm uppercase text-[11px] tracking-[0.3em] font-bold transition-all disabled:bg-gray-800 disabled:text-gray-500 flex items-center justify-center gap-3"
                >
                  {isThinking ? (
                    <>
                      <div className="w-3 h-3 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                      Engaging Engines...
                    </>
                  ) : (
                    'Transmit Directives'
                  )}
                </button>
              </form>
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}