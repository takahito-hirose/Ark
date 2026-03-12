"use client";

import React from 'react';
import { Canvas } from '@react-three/fiber';
import Viewport3D from '@/components/Viewport3D';
import { useArkStore } from '../store/useArkStore';

/**
 * 🚢 PROJECT ODISSEY - Layer 2: The Cabin Frame Construction
 * 真ん中を50%、両サイドを25%の「2.5 : 5.0 : 2.5」の黄金比に再調整！
 * 各パーツに直接 `perspective` をかけて確実に立体的に折り曲げるわよ💋
 */
export default function Home() {
  const { goldCoins } = useArkStore();

  // 柱の高さが120%にオーバースケールされているため、
  // 画面内に見える範囲（15% 〜 85%付近）にリベットが収まるように計算し直し！
  const rivetsPositions = Array.from({ length: 12 }, (_, i) => `${15 + i * 6}%`);

  return (
    <main className="h-screen w-screen overflow-hidden bg-black font-mono relative">
      
      {/* === LAYER 1: THE HORIZON (3Dの海) === */}
      <div className="fixed inset-0 z-0">
        <Canvas shadows camera={{ position: [0, 1.2, 10], fov: 38 }}>
          <Viewport3D />
        </Canvas>
      </div>

      {/* === LAYER 2: THE CABIN FRAME (窓枠の建造) === */}
      <div className="fixed inset-0 z-10 pointer-events-none">
        
        {/* 1. 天井の巨大梁 (Top Beam) */}
        {/* 上端を支点にして、奥へ15度傾ける */}
        <div 
          className="absolute top-0 left-[-10%] w-[120%] h-[15vh] wood-grain-heavy wood-texture border-b-4 border-[#0a0503] shadow-[0_40px_60px_rgba(0,0,0,0.95)] z-20"
          style={{ transformOrigin: 'top center', transform: 'perspective(800px) rotateX(15deg)' }}
        >
          <div className="absolute bottom-0 w-full h-4 brass-molding" />
          {/* リベットも梁の傾きに合わせて立体的に配置されるわ */}
          <div className="flex justify-between px-[15%] pt-4 opacity-90">
            {[...Array(14)].map((_, i) => <div key={i} className="rivet-heavy relative" />)}
          </div>
        </div>

        {/* 2. 左の重厚な柱 (Left Pillar: 幅25vw) */}
        {/* 左端を支点にして、右側を奥へ20度傾ける */}
        <div 
          className="absolute left-0 top-[-10%] h-[120%] w-[25vw] flex flex-col z-10"
          style={{ transformOrigin: 'left center', transform: 'perspective(800px) rotateY(20deg)' }}
        >
          <div className="flex-grow wood-grain-heavy wood-texture shadow-[40px_0_70px_rgba(0,0,0,1)] flex relative">
            <div className="h-full w-5 brass-molding-vertical absolute right-0" />
            
            <div className="flex-grow h-full ml-8 my-20 bg-[#0a0503]/60 box-shadow-inner border-r border-[#ffffff]/10 relative shadow-inner">
               {rivetsPositions.map((pos, i) => (
                 <div key={i} className="rivet-heavy" style={{ top: pos, right: '-12px' }} />
               ))}
            </div>
          </div>
        </div>

        {/* 3. 右の重厚な柱 (Right Pillar: 幅25vw) */}
        {/* 右端を支点にして、左側を奥へ20度傾ける */}
        <div 
          className="absolute right-0 top-[-10%] h-[120%] w-[25vw] flex flex-col z-10"
          style={{ transformOrigin: 'right center', transform: 'perspective(800px) rotateY(-20deg)' }}
        >
          <div className="flex-grow wood-grain-heavy wood-texture shadow-[-40px_0_70px_rgba(0,0,0,1)] flex justify-end relative">
            <div className="h-full w-5 brass-molding-vertical absolute left-0" />
            
            <div className="flex-grow h-full mr-8 my-20 bg-[#0a0503]/60 box-shadow-inner border-l border-[#ffffff]/10 relative shadow-inner">
               {rivetsPositions.map((pos, i) => (
                 <div key={i} className="rivet-heavy" style={{ top: pos, left: '-12px' }} />
               ))}
            </div>
          </div>
        </div>

        {/* 4. 足元の基礎デッキ (Bottom Deck Foundation) */}
        {/* 下端を支点にして、上部を奥へ20度傾ける */}
        <div 
          className="absolute bottom-0 left-[-10%] w-[120%] h-[20vh] wood-grain-heavy wood-texture border-t-4 border-[#0a0503] shadow-[0_-40px_70px_rgba(0,0,0,1)] z-20"
          style={{ transformOrigin: 'bottom center', transform: 'perspective(800px) rotateX(-20deg)' }}
        >
           <div className="absolute top-0 w-full h-4 brass-molding" />
           {/* 少し内側にリベットを配置 */}
           <div className="absolute top-6 left-[15%] rivet-heavy w-10 h-10" />
           <div className="absolute top-6 right-[15%] rivet-heavy w-10 h-10" />
        </div>
      </div>

      {/* 5. 画面全体のヴィネット効果（一番手前に配置して画面の四隅を暗くする） */}
      <div 
        className="fixed inset-0 pointer-events-none z-30" 
        style={{ background: 'radial-gradient(circle at center, transparent 35%, rgba(0,0,0,0.95) 100%)' }}
      />
    </main>
  );
}