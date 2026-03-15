"use client";

import React, { useState, useEffect, useRef } from 'react';
import { Canvas } from '@react-three/fiber';
import Viewport3D from '@/components/Viewport3D';
import { useArkStore } from '../store/useArkStore';

/**
 * 🚢 PROJECT ODISSEY - HUD Layer
 * 半透明のグラスモーフィズムとネオンボーダーを駆使した、
 * サイバーパンクなホログラムUIを構築するわよ！💋
 */
export default function Home() {
  // 💖 ノアぴの追加ポイント: phase と setPhase をストアから取得！
  const { phase, isThinking, logs, goldCoins, setPhase, setThinking, addLog, spendCoins } = useArkStore();
  const [command, setCommand] = useState('');
  const logsEndRef = useRef<HTMLDivElement>(null);

  // ログが追加されたら一番下までスクロール
  useEffect(() => {
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [logs]);

  // 🌟 NEW: Neuro-Link (WebSocket) 接続用フック！
  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: NodeJS.Timeout;

    const connectWebSocket = () => {
      // Python側のWebSocketエンドポイントに接続！
      ws = new WebSocket('ws://127.0.0.1:8000/ws/logs');

      ws.onopen = () => {
        addLog({
          timestamp: new Date().toISOString(),
          agent: 'SYSTEM',
          message: 'Neuro-Link (WebSocket) Connection Established. 🧠✨',
          level: 'success'
        });
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          // バックエンドからの生きたログ（思考プロセス）をUIに流し込む！
          if (data.type === 'ARK_EVENT') {
            const phaseTag = data.phase ? `[${data.phase}] ` : '';
            const detail = data.detail ? ` - ${data.detail}` : '';
            
            addLog({
              timestamp: new Date().toISOString(),
              agent: 'ARK',
              message: `${phaseTag}${data.status}${detail}`,
              // リトライが発生してたらエラー色で目立たせる工夫よ💋
              level: data.retry_count > 0 ? 'error' : 'info'
            });

            // 💖 ノアぴの追加ポイント: フェーズが送られてきたらストアを更新！
            if (data.phase) {
              setPhase(data.phase.toUpperCase() as any);
            }
          }
          // 🌟 NEW: バックエンドからトークン消費の報告が来たら、金貨を減らす！
          if (data.type === 'TOKEN_USAGE') {
            spendCoins(data.tokens);
            // オプションで「チャリンチャリン🪙」ってログに出しても可愛いかも💋
          }
        } catch (error) {
          console.error('Failed to parse WebSocket message:', error);
        }
      };

      ws.onclose = () => {
        addLog({
          timestamp: new Date().toISOString(),
          agent: 'SYSTEM',
          message: 'Neuro-Link Disconnected. Attempting to reconnect in 3s...',
          level: 'error'
        });
        // 切断されたら3秒後に再接続！
        reconnectTimer = setTimeout(connectWebSocket, 3000);
      };
      
      ws.onerror = (error) => {
        console.error('WebSocket encountered an error:', error);
      };
    };

    // 初回マウント時に接続開始！
    connectWebSocket();

    // クリーンアップ関数（画面を閉じた時に通信を切る）
    return () => {
      clearTimeout(reconnectTimer);
      if (ws) {
        ws.onclose = null; // クリーンアップ時の意図的なクローズでは再接続させない
        ws.close();
      }
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // 💖 コマンド送信ロジック
  const handleCommandSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim() || isThinking) return;

    const currentCommand = command;
    setCommand(''); // 入力欄をサクッとクリア！
    setThinking(true); // 考え中ステータスをON！

    // 1. ジェニーの指示をログに追加
    addLog({
      timestamp: new Date().toISOString(),
      agent: 'CAPTAIN',
      message: currentCommand,
      level: 'info'
    });

    try {
      // 2. バックエンド（さっき作ったAPI）にリクエストを投げる！🚀
      const res = await fetch('/api/command', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ command: currentCommand })
      });
      
      const data = await res.json();

      if (!res.ok) throw new Error(data.message);

      // 3. APIからの返答をログに追加！
      addLog({
        timestamp: new Date().toISOString(),
        agent: 'SYLPH', 
        message: data.message,
        level: data.level
      });

      // 4. トークン消費（コインを減らすロジック）🪙
      // if (data.tokens) {
      //  spendCoins(data.tokens);
      // }

    } catch (error: any) {
      // エラーが起きたら赤文字でログに出すよ！
      addLog({
        timestamp: new Date().toISOString(),
        agent: 'SYSTEM',
        message: error.message || '通信エラー発生！APIの応答がないみたい💦',
        level: 'error'
      });
    } finally {
      // 最後に必ず「考え中」を解除！
      setThinking(false);
    }
  };

  return (
    <main className="h-screen w-screen overflow-hidden bg-black font-mono relative text-white selection:bg-[#8be9fd] selection:text-black">
      
      {/* === LAYER 1: THE HORIZON (3Dの海) === */}
      <div className="fixed inset-0 z-0">
        <Canvas shadows camera={{ position: [0, 1.2, 10], fov: 38 }}>
          <Viewport3D />
        </Canvas>
      </div>

      {/* 画面全体のヴィネット（UIを見やすくするため少し暗く） */}
      <div className="fixed inset-0 z-10 pointer-events-none" style={{ background: 'radial-gradient(circle at center, transparent 20%, rgba(0,10,20,0.8) 100%)' }} />

      {/* === LAYER 3: HOLOGRAPHIC HUD (UIレイヤー) === */}
      <div className="fixed inset-0 z-20 p-6 flex flex-col justify-between pointer-events-none">
        
        {/* --- 👆 TOP SECTION: ステータス＆リンク --- */}
        <div className="flex justify-between items-start pointer-events-auto">
          
          {/* 左上: 船のステータスとトークン/金額表示 */}
          <div className="bg-[#0f172a]/60 backdrop-blur-md border border-[#8be9fd]/30 p-4 rounded-lg shadow-[0_0_15px_rgba(139,233,253,0.1)] min-w-[250px]">
            <h2 className="text-[#8be9fd] text-xs uppercase tracking-[0.2em] mb-3 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-[#50fa7b] animate-pulse" />
              Ark Status
            </h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-400">Tokens Used:</span>
                <span className="font-bold text-[#f1fa8c]">{goldCoins.toLocaleString()}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-400">Estimated Cost:</span>
                <span className="font-bold text-[#ffb86c]">${(goldCoins * 0.00001).toFixed(4)}</span>
              </div>
            </div>
          </div>

          {/* 右上: Git リポジトリリンク */}
          <a 
            href="#" 
            className="group flex items-center gap-3 bg-[#0f172a]/60 backdrop-blur-md border border-[#ff79c6]/30 px-5 py-3 rounded-lg shadow-[0_0_15px_rgba(255,121,198,0.1)] hover:bg-[#ff79c6]/20 transition-all duration-300"
          >
            <div className="text-[#ff79c6] group-hover:scale-110 transition-transform">
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.08-1.25-.27-2.48-1-3.5.28-1.15.28-2.35 0-3.5 0 0-1 0-3 1.5-2.64-.5-5.36-.5-8 0C6 2 5 2 5 2c-.3 1.15-.3 2.35 0 3.5A5.403 5.403 0 0 0 4 9c0 3.5 3 5.5 6 5.5-.39.49-.68 1.05-.85 1.65-.17.6-.22 1.23-.15 1.85v4"/><path d="M9 18c-4.51 2-5-2-7-2"/></svg>
            </div>
            <div className="flex flex-col text-right">
              <span className="text-xs text-gray-400 uppercase tracking-wider">Repository</span>
              <span className="text-sm font-bold text-white group-hover:text-[#ff79c6] transition-colors">ark-odissey</span>
            </div>
          </a>
        </div>

        {/* --- 👇 BOTTOM SECTION: ログ＆コマンド --- */}
        <div className="flex gap-6 h-[40vh] pointer-events-auto">
          
          {/* 左下: SYLPH ACTIVITY (ターミナルログ) */}
          <div className="flex-1 bg-[#0f172a]/70 backdrop-blur-md border border-[#bd93f9]/30 rounded-lg shadow-[0_0_20px_rgba(189,147,249,0.15)] flex flex-col overflow-hidden relative">
            {/* 装飾用ヘッダー */}
            <div className="bg-gradient-to-r from-[#bd93f9]/20 to-transparent p-2 px-4 border-b border-[#bd93f9]/20 flex items-center justify-between">
              <span className="text-xs text-[#bd93f9] uppercase tracking-[0.3em] font-bold">SYLPH ACTIVITY</span>
              {isThinking && <span className="text-[10px] text-[#8be9fd] animate-pulse">PROCESSING...</span>}
            </div>
            
            {/* ログエリア */}
            <div className="flex-1 overflow-y-auto p-4 space-y-2 custom-scrollbar">
              {logs.map((log, i) => (
                <div key={i} className="text-sm flex gap-3 leading-relaxed">
                  <span className="text-gray-500 shrink-0">[{log.timestamp.split('T')[1].substring(0,8)}]</span>
                  
                  {/* 🌟 修正ポイント: エージェントごとにバキバキのネオンカラー＆ドロップシャドウ！ */}
                  <span className={`shrink-0 font-bold 
                    ${log.agent === 'CAPTAIN' ? 'text-[#ffb86c] drop-shadow-[0_0_8px_rgba(255,184,108,0.8)]' : 
                      log.agent === 'ARK' ? 'text-[#ff79c6] drop-shadow-[0_0_8px_rgba(255,121,198,0.8)]' : 
                      'text-[#8be9fd] drop-shadow-[0_0_8px_rgba(139,233,253,0.8)]'}`}>
                    {log.agent}:
                  </span>
                  
                  <span className={`
                    ${log.level === 'error' ? 'text-[#ff5555]' : ''}
                    ${log.level === 'success' ? 'text-[#50fa7b]' : ''}
                    ${log.level === 'info' ? 'text-gray-300' : ''}
                  `}>
                    {log.message}
                  </span>
                </div>
              ))}
              <div ref={logsEndRef} />
            </div>
            
            {/* スキャンラインエフェクト（ターミナルっぽさ） */}
            <div className="absolute inset-0 pointer-events-none bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] bg-[length:100%_4px,3px_100%] opacity-20" />
          </div>

          {/* 右下: 指示入力 (コマンドインターフェース) と 航路図 */}
          <div className="w-[400px] flex flex-col justify-end gap-6">
            
            {/* 🗺️ 動的航路図 (SEA CHART) */}
            <div className="bg-[#0f172a]/80 backdrop-blur-xl border border-[#8be9fd]/50 rounded-lg p-4 shadow-[0_0_30px_rgba(139,233,253,0.1)]">
              <h3 className="text-xs text-[#8be9fd] uppercase tracking-widest mb-4 border-b border-[#8be9fd]/20 pb-2 text-right">Sea Chart</h3>
              <div className="flex flex-col gap-3 w-full px-4 py-2">
                {['IDLE', 'PLANNING', 'CODING', 'REVIEWING', 'COMMITTING', 'DONE'].map((p, i, arr) => {
                  const isActive = phase === p;
                  const phaseIndex = arr.indexOf(phase);
                  const isPast = phaseIndex > i;

                  return (
                    <div key={p} className="flex items-center gap-4 relative">
                      {/* 接続ライン */}
                      {i !== arr.length - 1 && (
                        <div className={`absolute left-2.5 top-6 w-0.5 h-6 ${isPast ? 'bg-[#50fa7b]' : 'bg-[#30363d]'}`} style={{ zIndex: 0 }} />
                      )}
                      
                      {/* チェックポイント（島） */}
                      <div className={`w-5 h-5 rounded-full border-2 flex items-center justify-center z-10 bg-[#0d1117] transition-all duration-500
                        ${isActive ? 'border-[#8be9fd] shadow-[0_0_15px_rgba(139,233,253,0.8)] scale-125' : 
                          isPast ? 'border-[#50fa7b]' : 'border-[#30363d]'}`}
                      >
                        {isActive && <div className="w-1.5 h-1.5 bg-[#8be9fd] rounded-full animate-pulse" />}
                        {isPast && <div className="w-1.5 h-1.5 bg-[#50fa7b] rounded-full" />}
                      </div>
                      
                      {/* ラベル */}
                      <span className={`font-bold tracking-[0.2em] text-xs transition-colors duration-300 ${isActive ? 'text-[#8be9fd] drop-shadow-[0_0_5px_rgba(139,233,253,0.8)]' : isPast ? 'text-[#50fa7b]' : 'text-[#30363d]'}`}>
                        {p}
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* コマンド入力 */}
            <div className="bg-[#0f172a]/80 backdrop-blur-xl border border-[#8be9fd]/50 rounded-lg p-4 shadow-[0_0_30px_rgba(139,233,253,0.2)] relative overflow-hidden">
              
              {/* 装飾: コーナーの光 */}
              <div className="absolute top-0 left-0 w-8 h-8 border-t-2 border-l-2 border-[#8be9fd] opacity-50" />
              <div className="absolute bottom-0 right-0 w-8 h-8 border-b-2 border-r-2 border-[#8be9fd] opacity-50" />

              <h3 className="text-xs text-[#8be9fd] uppercase tracking-widest mb-4">Command Input</h3>
              
              <form onSubmit={handleCommandSubmit} className="relative">
                <span className="absolute left-3 top-3 text-[#ffb86c] font-bold">❯</span>
                <input
                  type="text"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  disabled={isThinking}
                  placeholder="Enter coordinates or directives..."
                  className="w-full bg-black/50 border border-gray-700 text-white pl-8 pr-4 py-3 rounded focus:outline-none focus:border-[#8be9fd] focus:ring-1 focus:ring-[#8be9fd] transition-all disabled:opacity-50 font-mono text-sm"
                />
                <button 
                  type="submit" 
                  disabled={isThinking || !command.trim()}
                  className="mt-3 w-full bg-[#8be9fd]/10 hover:bg-[#8be9fd]/20 text-[#8be9fd] border border-[#8be9fd]/50 py-2 rounded uppercase text-xs tracking-[0.2em] font-bold transition-all disabled:opacity-30 disabled:cursor-not-allowed"
                >
                  {isThinking ? 'Executing...' : 'Transmit'}
                </button>
              </form>
            </div>

          </div>

        </div>
      </div>

    </main>
  );
}