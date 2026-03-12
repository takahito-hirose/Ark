"use client";

import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Environment, Sky, Stars, Float } from '@react-three/drei';
import * as THREE from 'three';
import { useArkStore } from '../store/useArkStore';

// --- 🌊 Ultimate Cinematic Ocean Shader (Deep & Realistic Splash Edition) ---
// 白飛びを抑え、波が干渉した時だけリアルな飛沫が舞うように調整されたシェーダー
const WaterShader = {
  uniforms: {
    uTime: { value: 0 },
    uSurfaceColor: { value: new THREE.Color("#0088cc") }, // 透き通るシアン
    uDepthColor: { value: new THREE.Color("#001a33") },   // 深い青
    uSkyColor: { value: new THREE.Color("#88ccff") },     // 空の反射色
    uFoamColor: { value: new THREE.Color("#ffffff") },    // 白波（波飛沫）の色
    uSunPosition: { value: new THREE.Vector3(0, 10, -50).normalize() },
  },
  vertexShader: `
    varying vec2 vUv;
    varying float vElevation;
    varying float vInterference; // 波の干渉度合い
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    varying vec3 vWorldPosition;
    uniform float uTime;
    
    vec2 wave(vec2 pos, vec2 dir, float scale, float speed, float time) {
        float x = dot(pos, dir) * scale + time * speed;
        // exp()を使って、谷はなだらかに、山（波頭）は尖らせる
        float waveValue = exp(sin(x) - 1.0); 
        return vec2(waveValue, 0.0);
    }
    
    void main() {
      vUv = uv;
      vec4 modelPosition = modelMatrix * vec4(position, 1.0);
      vec2 pos = modelPosition.xz;
      
      float time = uTime * 0.8;
      float elevation = 0.0;
      float interference = 0.0;
      
      // 1. 方向を散らした4つの波を合成
      vec2 w1 = wave(pos, normalize(vec2(1.0, 1.2)), 0.15, 1.0, time);
      elevation += w1.x * 0.4;
      
      vec2 w2 = wave(pos, normalize(vec2(-0.8, 1.0)), 0.2, 0.8, time);
      elevation += w2.x * 0.3;
      
      vec2 w3 = wave(pos, normalize(vec2(1.0, 0.2)), 0.35, 1.5, time);
      elevation += w3.x * 0.2;
      
      vec2 w4 = wave(pos, normalize(vec2(-0.6, -0.4)), 0.6, 2.0, time);
      elevation += w4.x * 0.1;

      // 2. 波がぶつかり合う（干渉する）場所の計算
      // 負の値にならないようにmaxを取る
      interference = max(0.0, (w1.x * w2.x * 4.0) + (w3.x * w4.x * 2.0));
      
      modelPosition.y += elevation;
      vElevation = elevation;
      vInterference = interference;
      vWorldPosition = modelPosition.xyz;
      
      vec4 viewPosition = viewMatrix * modelPosition;
      vViewPosition = -viewPosition.xyz;
      
      gl_Position = projectionMatrix * viewPosition;
      vNormal = normalize(normalMatrix * normal);
    }
  `,
  fragmentShader: `
    varying vec2 vUv;
    varying float vElevation;
    varying float vInterference;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    varying vec3 vWorldPosition;
    
    uniform vec3 uSurfaceColor;
    uniform vec3 uDepthColor;
    uniform vec3 uSkyColor;
    uniform vec3 uFoamColor;
    uniform vec3 uSunPosition;
    uniform float uTime;
    
    float hash(vec2 p) {
        return fract(sin(dot(p, vec2(12.9898, 78.233))) * 43758.5453);
    }
    
    float noise2d(vec2 p) {
        vec2 i = floor(p);
        vec2 f = fract(p);
        vec2 u = f * f * (3.0 - 2.0 * f);
        return mix(mix(hash(i + vec2(0.0, 0.0)), hash(i + vec2(1.0, 0.0)), u.x),
                   mix(hash(i + vec2(0.0, 1.0)), hash(i + vec2(1.0, 1.0)), u.x), u.y);
    }

    void main() {
      vec2 p = vWorldPosition.xz * 0.4;
      float t = uTime * 0.5;
      
      // 水面全体の微細な揺らぎ
      float n1 = noise2d(p + t);
      float n2 = noise2d(p * 2.5 - t * 1.2) * 0.5;
      float n3 = noise2d(p * 5.0 + t * 2.0) * 0.25;
      vec2 surfaceNoise = vec2(n1 - n2, n2 + n3) * 0.12;
      
      vec3 normal = normalize(vNormal + vec3(surfaceNoise.x, 0.0, surfaceNoise.y));
      
      // 空の映り込み（フレネル反射）
      vec3 viewDir = normalize(vViewPosition);
      // 白飛びを防ぐため、反射が効く角度を狭くする（4.0 -> 5.0）
      float fresnel = pow(1.0 - max(dot(viewDir, normal), 0.0), 5.0);
      
      // 海の基本グラデーション（少し深みを出す）
      float mixStrength = (vElevation + 0.1) * 1.5;
      vec3 baseColor = mix(uDepthColor, uSurfaceColor, clamp(mixStrength, 0.0, 1.0));
      // フレネルのブレンド率を下げて、海本来の青を残す（0.6 -> 0.4）
      vec3 waterColor = mix(baseColor, uSkyColor, fresnel * 0.4);
      
      // 太陽の鋭い反射（Specular）
      vec3 reflectDir = reflect(-uSunPosition, normal);
      // powの値を極端に上げて（120 -> 300）、白飛びではなく「点で鋭く光る」ようにする
      float spec = pow(max(dot(viewDir, reflectDir), 0.0), 300.0);
      vec3 specular = vec3(1.0, 0.95, 0.9) * spec * 1.5;
      
      // 💋 波飛沫 (Dynamic Foam & Splash) の計算
      // 閾値を厳しくして、本当に高い波にしかベース泡が出ないようにする
      float foamBase = smoothstep(0.4, 0.8, vElevation + vInterference * 0.5);
      
      // 泡のテクスチャ（網目状のノイズを少し細かく）
      vec2 foamUv = vWorldPosition.xz * 2.0;
      float fNoise = noise2d(foamUv - t * 0.5) * 0.6 + noise2d(foamUv * 4.0 + t) * 0.4;
      
      // 干渉による強烈な白波（Splash）
      // 波がぶつかっている場所（vInterferenceが高い）かつ、ノイズが強い点だけを白くする
      float splash = smoothstep(0.6, 0.9, fNoise) * smoothstep(0.3, 0.6, vInterference);
      
      // 泡全体を合成し、強すぎる白を海の色と馴染ませる（max 80%の不透明度）
      float foamIntensity = clamp(foamBase * smoothstep(0.4, 0.7, fNoise) + splash * 1.5, 0.0, 1.0);
      waterColor = mix(waterColor, uFoamColor, foamIntensity * 0.8);
      
      // 波頭に光が透ける表現（Subsurface Scattering）を少し抑える
      if (vElevation > 0.15) {
          float sss = smoothstep(0.15, 0.5, vElevation) * (1.0 - foamIntensity);
          waterColor += uSurfaceColor * sss * 0.5;
      }
      
      gl_FragColor = vec4(waterColor + specular, 0.95);
    }
  `
};

function Ocean() {
  const materialRef = useRef<THREE.ShaderMaterial>(null);
  useFrame((state) => {
    if (materialRef.current) materialRef.current.uniforms.uTime.value = state.clock.elapsedTime;
  });

  return (
    <mesh rotation={[-Math.PI / 2, 0, 0]} position={[0, -2, 0]}>
      <planeGeometry args={[300, 300, 512, 512]} />
      <shaderMaterial ref={materialRef} {...WaterShader} transparent />
    </mesh>
  );
}

function Island() {
  return (
    <group position={[0, -1.8, -60]}>
      <mesh castShadow>
        <coneGeometry args={[12, 6, 5]} />
        <meshStandardMaterial color="#0f1a24" roughness={0.9} metalness={0.1} />
      </mesh>
      <mesh position={[-5, -1, 3]} rotation={[0, 1, 0]}>
        <coneGeometry args={[6, 4, 4]} />
        <meshStandardMaterial color="#050a0f" roughness={1} />
      </mesh>
    </group>
  );
}

export default function Viewport3D() {
  return (
    <>
      {/* --- LIGHTING --- */}
      {/* 全体的に光を絞って、白飛びを防ぎコントラストを高める */}
      <ambientLight intensity={0.2} />
      <directionalLight position={[0, 20, -50]} intensity={2.0} color="#ffffff" />
      <pointLight position={[0, 5, 10]} intensity={1.0} color="#8be9fd" />
      
      <Environment preset="city" />
      <Sky distance={450000} sunPosition={[0, 10, -50]} inclination={0} azimuth={0.25} />
      
      <fog attach="fog" args={['#00447a', 30, 150]} />
      
      <Ocean />
      <Float speed={1.5} rotationIntensity={0.1} floatIntensity={0.2}>
        <Island />
      </Float>
    </>
  );
}