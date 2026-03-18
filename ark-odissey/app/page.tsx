"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import { motion, AnimatePresence } from 'framer-motion';
import Viewport3D from '@/components/Viewport3D';
import { useArkStore } from '../store/useArkStore';

/**
 * 🚢 PROJECT ODISSEY - ULTIMATE HUD LAYER (Perfect Responsive Ratio)
 * 画面の比率（% と vh）でガチガチに固めた最強のレスポンシブレイアウト！
 * これでもう、どんな画面サイズでも見切れないし、左右の高さも完全に一致するわよ！💋
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
  const logsEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

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
            className={`${hasError ? 'text-[#ff5555] decoration-[#ff5555]' : 'text-[#bd93f9] decoration-[#ff79c6] hover:text-[#ff79c6]'} underline hover:drop-shadow-[0_0_8px_currentColor] transition-all cursor-pointer pointer-events-auto`}
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
        setHasError(false);
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);

          if (data.type === 'ARK_EVENT') {
            const phaseTag = data.phase ? `[${data.phase}] ` : '';
            const detail = data.detail ? ` - ${data.detail}` : '';
            const isErr = data.status === 'FAIL' || data.retry_count > 0;

            addLog({
              timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
              agent: 'ARK',
              message: `${phaseTag}${data.status}${detail}`,
              level: isErr ? 'error' : 'info'
            });

            if (data.phase) {
              const upperPhase = data.phase.toUpperCase() as any;
              setPhase(upperPhase);

              if (upperPhase === 'BLOCKED') {
                setHasError(true);
                setThinking(false);
              }
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
        addLog({
          timestamp: new Date().toLocaleTimeString('ja-JP', { hour12: false }),
          agent: 'SYSTEM',
          message: 'Neuro-Link Disconnected. Core system failure or rebooting...',
          level: 'error'
        });
        setHasError(true);
        setThinking(false);
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      };
    };

    connectWebSocket();
    return () => {
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
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
      message: currentCommand,
      level: 'info'
    });

    try {
      const res = await fetch('http://127.0.0.1:8000/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: currentCommand, mode: mode })
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
      setHasError(true);
      setThinking(false);
    }
  };

  return (
    <main className="h-screen w-screen overflow-hidden bg-black font-mono relative text-white">

      {/* 3D OCEAN BACKGROUND */}
      <div className="fixed inset-0 z-0">
        <Canvas shadows camera={{ position: [0, 1.2, 8], fov: 45 }}>
          <Viewport3D />
        </Canvas>
      </div>

      <div className={`fixed inset-0 z-10 pointer-events-none transition-colors duration-1000 ${hasError ? 'bg-[radial-gradient(circle_at_center,transparent_30%,rgba(50,0,0,0.8)_100%)]' : 'bg-[radial-gradient(circle_at_center,transparent_30%,rgba(0,0,0,0.8)_100%)]'}`} />

      {/* 🌟 フレックスボックスで全体を上下に押し分けるレスポンシブ構造 */}
      <div className="fixed inset-0 z-20 p-4 md:p-8 flex flex-col pointer-events-none overflow-hidden">

        {/* TOP HUD */}
        {/* 横幅も%指定にして、画面全体とのバランスを保つわよ！ */}
        <div className="flex justify-between items-start pointer-events-auto shrink-0 w-full">
          <motion.div
            initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
            className={`bg-[#0f172a]/40 backdrop-blur-md border p-4 md:p-5 rounded-sm transition-colors duration-500 w-[30%] min-w-[240px] ${hasError ? 'border-[#ff5555]/50 shadow-[0_0_30px_rgba(255,85,85,0.2)]' : 'border-[#8be9fd]/30 shadow-[0_0_20px_rgba(139,233,253,0.1)]'}`}
          >
            <h2 className={`text-[10px] uppercase tracking-[0.4em] mb-3 md:mb-4 flex items-center gap-2 ${hasError ? 'text-[#ff5555]' : 'text-[#8be9fd]'}`}>
              <div className={`w-2 h-2 rounded-full ${hasError ? 'bg-[#ff5555] animate-ping' : isThinking ? 'bg-[#ff79c6] animate-pulse' : 'bg-[#50fa7b]'}`} />
              System Telemetry
            </h2>
            <div className="space-y-2 md:space-y-3">
              <div className="flex justify-between items-baseline">
                <span className="text-[10px] text-gray-500 uppercase">Treasury</span>
                <span className={`text-lg md:text-xl font-bold drop-shadow-[0_0_10px_currentColor] ${hasError ? 'text-[#ff5555]' : 'text-[#f1fa8c]'}`}>
                  🪙 {goldCoins.toLocaleString()} <span className="text-[10px] text-gray-400">G</span>
                </span>
              </div>
              <div className="w-full bg-gray-800 h-1 rounded-full overflow-hidden">
                <motion.div
                  className={`h-full ${hasError ? 'bg-[#ff5555]' : 'bg-[#f1fa8c]'}`}
                  initial={{ width: '100%' }}
                  animate={{ width: `${(goldCoins / 20000) * 100}%` }}
                />
              </div>

              {/* ECO / RICH SWITCH */}
              <div className="mt-3 md:mt-4 pt-2 md:pt-3 border-t border-gray-800 flex items-center justify-between">
                <span className="text-[10px] text-gray-500 uppercase">Engine Mode</span>
                <div className="flex bg-black/50 p-1 rounded-sm border border-gray-800">
                  <button
                    onClick={() => setMode('ECO')}
                    disabled={isThinking}
                    className={`px-3 md:px-4 py-1 text-[9px] md:text-[10px] font-bold tracking-widest transition-all rounded-sm ${mode === 'ECO' ? 'bg-[#50fa7b] text-black shadow-[0_0_10px_rgba(80,250,123,0.5)]' : 'text-gray-500 hover:text-white'}`}
                  >
                    ECO
                  </button>
                  <button
                    onClick={() => setMode('RICH')}
                    disabled={isThinking}
                    className={`px-3 md:px-4 py-1 text-[9px] md:text-[10px] font-bold tracking-widest transition-all rounded-sm ${mode === 'RICH' ? 'bg-[#ffb86c] text-black shadow-[0_0_10px_rgba(255,184,108,0.5)]' : 'text-gray-500 hover:text-white'}`}
                  >
                    RICH
                  </button>
                </div>
              </div>

            </div>
          </motion.div>

          <motion.div
            initial={{ y: -20, opacity: 0 }} animate={{ y: 0, opacity: 1 }}
            className="w-[25%] min-w-[200px] flex flex-col items-end gap-2"
          >
            <div className={`w-full bg-[#0f172a]/40 backdrop-blur-md border px-4 md:px-6 py-2 md:py-3 rounded-sm flex items-center justify-between transition-colors duration-500 ${hasError ? 'border-[#ff5555]/50' : 'border-[#ff79c6]/30'}`}>
              <div className="text-right">
                <div className="text-[8px] md:text-[9px] text-gray-500 uppercase tracking-widest">Target Harbor</div>
                <div className={`text-[10px] md:text-xs font-bold uppercase tracking-tighter ${hasError ? 'text-[#ff5555] animate-pulse' : 'text-white'}`}>
                  GitHub / {hasError ? 'CRITICAL ERROR' : phase === 'DONE' ? 'DEPLOYED' : 'NAVIGATING'}
                </div>
              </div>
              <div className={`shrink-0 w-8 h-8 md:w-10 md:h-10 rounded-full border flex items-center justify-center ${hasError ? 'border-[#ff5555]/50 text-[#ff5555]' : 'border-[#ff79c6]/50 text-[#ff79c6]'}`}>
                {hasError ? (
                  <span className="font-bold text-lg animate-pulse">!</span>
                ) : (
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4" /><path d="M9 18c-4.51 2-5-2-7-2" /></svg>
                )}
              </div>
            </div>
          </motion.div>
        </div>

        {/* 🌟 SPACER: 海を見るためのスペース。自動で縮んで場所を譲るわ！ */}
        <div className="flex-1 min-h-[10px]" />

        {/* BOTTOM HUD */}
        {/* 🌟 FIX: 高さを 40vh (画面の高さの40%) に完全固定！これではみ出さない！ */}
        <div className="flex gap-4 md:gap-6 pointer-events-auto h-[40vh] min-h-[250px] w-full shrink-0">

          {/* SYLPH ACTIVITY (Terminal) */}
          {/* 🌟 FIX: 左パネルの幅を全体の60%に指定 */}
          <div className={`w-[60%] h-full bg-[#0f172a]/40 backdrop-blur-md border rounded-sm flex flex-col overflow-hidden relative shadow-[0_0_40px_rgba(0,0,0,0.5)] transition-colors duration-500 ${hasError ? 'border-[#ff5555]/50' : 'border-[#bd93f9]/40'}`}>
            <div className={`shrink-0 p-2 md:p-3 px-4 md:px-5 border-b flex justify-between items-center transition-colors duration-500 ${hasError ? 'bg-[#ff5555]/10 border-[#ff5555]/30' : 'bg-[#bd93f9]/10 border-[#bd93f9]/20'}`}>
              <div className="flex items-center gap-2 md:gap-3">
                <div className={`w-1.5 h-1.5 rounded-full ${hasError ? 'bg-[#ff5555] animate-ping' : 'bg-[#bd93f9] animate-pulse'}`} />
                <span className={`text-[9px] md:text-[11px] font-bold tracking-[0.3em] uppercase ${hasError ? 'text-[#ff5555]' : 'text-[#bd93f9]'}`}>Sylph Activity Log</span>
              </div>
              <div className={`text-[8px] md:text-[10px] font-mono ${hasError ? 'text-[#ff5555]' : 'text-[#bd93f9]/50'}`}>{hasError ? 'SYS_FAILURE' : 'NODE: ARK_ODISSEY_V5'}</div>
            </div>

            <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-2 md:space-y-3 custom-scrollbar">
              <AnimatePresence initial={false}>
                {logs.map((log, i) => {
                  let displayLevel = log.level;
                  if (log.message.includes('PASS') || log.message.includes('OK')) {
                    displayLevel = 'success';
                  } else if (log.message.includes('FAIL') || log.message.includes('Error') || log.message.includes('エラー')) {
                    displayLevel = 'error';
                  }

                  return (
                    <motion.div
                      key={i}
                      initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }}
                      className="text-[10px] md:text-[12px] flex gap-3 md:gap-4 leading-relaxed group"
                    >
                      <span className="text-gray-600 shrink-0 font-mono text-[9px] md:text-[11px]">[{log.timestamp}]</span>
                      <span className={`shrink-0 font-bold tracking-tighter ${log.agent === 'CAPTAIN' ? 'text-[#ffb86c]' :
                          log.agent === 'ARK' ? (hasError ? 'text-[#ff5555]' : 'text-[#ff79c6]') : (hasError ? 'text-[#ff5555]' : 'text-[#8be9fd]')
                        }`}>
                        {log.agent}:
                      </span>
                      <span className={`
                        flex-1 break-all
                        ${displayLevel === 'error' ? 'text-[#ff5555]' : ''}
                        ${displayLevel === 'success' ? 'text-[#50fa7b]' : ''}
                        ${displayLevel === 'info' || !displayLevel ? 'text-gray-300' : ''}
                      `}>
                        {renderMessage(log.message)}
                      </span>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
              <div ref={logsEndRef} />
            </div>

            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.1)_50%),linear-gradient(90deg,rgba(255,0,0,0.03),rgba(0,255,0,0.01),rgba(0,0,255,0.03))] bg-[length:100%_4px,3px_100%] opacity-30" />
            <div className={`scanline ${hasError ? 'opacity-50 bg-gradient-to-b from-transparent via-[#ff5555] to-transparent' : ''}`} />
          </div>

          {/* COMMAND CENTER */}
          {/* 🌟 FIX: 右パネルの幅を全体の40%に指定 */}
          <div className="w-[40%] flex flex-col gap-4 h-full min-w-[280px]">

            {/* SEA CHART (Status map) */}
            {/* 🌟 FIX: 高さを親の50%に固定！これで左のログ画面と高さがピッタリ一致する！ */}
            <div className={`flex-1 bg-[#0f172a]/40 backdrop-blur-md border p-3 md:p-5 shadow-[0_0_30px_rgba(0,0,0,0.5)] flex flex-col overflow-hidden transition-colors duration-500 ${hasError ? 'border-[#ff5555]/40' : 'border-[#8be9fd]/40'}`}>
              <h3 className={`text-[9px] md:text-[10px] uppercase tracking-[0.4em] mb-2 border-b pb-1 shrink-0 ${hasError ? 'text-[#ff5555] border-[#ff5555]/20' : 'text-[#8be9fd] border-[#8be9fd]/20'}`}>Voyage Progress</h3>

              <div className="flex flex-col gap-2 px-1 flex-1 overflow-y-auto custom-scrollbar justify-center">
                {['PLANNING', 'CODING', 'REVIEWING', 'COMMITTING', 'DONE'].map((p, i, arr) => {
                  const isActive = phase === p;
                  const isPast = arr.indexOf(phase) > i || phase === 'DONE';
                  const isBlockedHere = hasError && isActive;

                  return (
                    <div key={p} className="flex items-center gap-3 md:gap-4 relative shrink-0">
                      <div className={`w-2 h-2 md:w-3 md:h-3 rounded-full border transition-all duration-500 z-10 
                        ${isBlockedHere ? 'border-[#ff5555] bg-[#ff5555] shadow-[0_0_15px_#ff5555] animate-ping' :
                          isActive ? 'border-[#8be9fd] bg-[#8be9fd] shadow-[0_0_15px_#8be9fd]' :
                            isPast ? 'border-[#50fa7b] bg-[#50fa7b]' : 'border-gray-700 bg-transparent'}`}
                      />
                      <span className={`text-[9px] md:text-[11px] font-bold tracking-[0.2em] transition-colors ${isBlockedHere ? 'text-[#ff5555] drop-shadow-[0_0_5px_rgba(255,85,85,0.8)]' :
                          isActive ? 'text-[#8be9fd]' : isPast ? 'text-[#50fa7b]' : 'text-gray-600'
                        }`}>
                        {p} {isBlockedHere && ' (BLOCKED)'}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* COMMAND CONSOLE */}
            {/* 🌟 FIX: ここも高さを親の50%に固定！中のテキストエリアも親に合わせて伸縮するよ！ */}
            <div className={`flex-1 bg-[#0f172a]/50 backdrop-blur-lg border-t-2 p-4 md:p-5 shadow-[0_-10px_40px_rgba(0,0,0,0.5)] relative transition-colors duration-500 flex flex-col ${hasError ? 'border-[#ff5555]' : 'border-[#8be9fd]'}`}>
              <div className={`absolute -top-3 left-4 md:left-6 text-black text-[8px] md:text-[9px] px-2 py-0.5 font-bold tracking-widest uppercase transition-colors duration-500 z-10 ${hasError ? 'bg-[#ff5555]' : 'bg-[#8be9fd]'}`}>
                Mission Control
              </div>

              <form onSubmit={handleCommandSubmit} className="flex-1 flex flex-col gap-3 h-full">
                <div className="relative flex-1 flex flex-col min-h-0">
                  <span className={`absolute left-3 top-3 font-bold z-10 ${hasError ? 'text-[#ff5555]' : 'text-[#ffb86c]'}`}>❯</span>
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
                    placeholder={hasError ? "System halted. Enter new directives..." : "Describe your requirements..."}
                    className={`flex-1 w-full h-full bg-black/60 border text-white pl-7 pr-3 py-3 rounded-sm focus:outline-none focus:ring-1 transition-all disabled:opacity-50 font-mono text-[11px] md:text-[12px] resize-none custom-scrollbar
                      ${hasError ? 'border-[#ff5555]/50 focus:border-[#ff5555] focus:ring-[#ff5555]' : 'border-gray-800 focus:border-[#8be9fd] focus:ring-[#8be9fd]'}`}
                  />
                </div>
                <button
                  type="submit"
                  disabled={isThinking || !command.trim()}
                  className={`shrink-0 w-full py-2 rounded-sm uppercase text-[9px] md:text-[11px] tracking-[0.3em] font-bold transition-all disabled:opacity-50 flex items-center justify-center gap-2
                    ${hasError ? 'bg-[#ff5555]/20 hover:bg-[#ff5555]/30 text-[#ff5555] border border-[#ff5555]/50' :
                      isThinking ? 'bg-gray-800 text-gray-500' : 'bg-[#8be9fd] hover:bg-[#a2ffff] text-black'}`}
                >
                  {isThinking ? (
                    <>
                      <div className="w-2.5 h-2.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
                      Engaging...
                    </>
                  ) : hasError ? (
                    'REBOOT & TRANSMIT'
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