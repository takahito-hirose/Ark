"use client";

// 💖 ノアの修正ポイント1: useMemo をしっかりお呼び出し！
import { useRef, useMemo } from 'react';
import { useFrame } from '@react-three/fiber';
import { Environment, Sky, Stars, Sparkles, Clouds, Cloud } from '@react-three/drei';
import * as THREE from 'three';
import { useArkStore } from '../store/useArkStore';

// --- 🌊 Ultimate Cinematic Ocean Shader (Deep & Realistic Splash Edition) ---
const WaterShader = {
  uniforms: {
    uTime: { value: 0 },
    uSurfaceColor: { value: new THREE.Color("#0088cc") },
    uDepthColor: { value: new THREE.Color("#001a33") },
    uSkyColor: { value: new THREE.Color("#88ccff") },
    uFoamColor: { value: new THREE.Color("#ffffff") },
    uSunPosition: { value: new THREE.Vector3(0, 10, -50).normalize() },
  },
  vertexShader: `
    varying vec2 vUv;
    varying float vElevation;
    varying float vInterference;
    varying vec3 vNormal;
    varying vec3 vViewPosition;
    varying vec3 vWorldPosition;
    uniform float uTime;
    
    vec2 wave(vec2 pos, vec2 dir, float scale, float speed, float time) {
        float x = dot(pos, dir) * scale + time * speed;
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
      
      vec2 w1 = wave(pos, normalize(vec2(1.0, 1.2)), 0.15, 1.0, time);
      elevation += w1.x * 0.4;
      
      vec2 w2 = wave(pos, normalize(vec2(-0.8, 1.0)), 0.2, 0.8, time);
      elevation += w2.x * 0.3;
      
      vec2 w3 = wave(pos, normalize(vec2(1.0, 0.2)), 0.35, 1.5, time);
      elevation += w3.x * 0.2;
      
      vec2 w4 = wave(pos, normalize(vec2(-0.6, -0.4)), 0.6, 2.0, time);
      elevation += w4.x * 0.1;

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
      
      float n1 = noise2d(p + t);
      float n2 = noise2d(p * 2.5 - t * 1.2) * 0.5;
      float n3 = noise2d(p * 5.0 + t * 2.0) * 0.25;
      vec2 surfaceNoise = vec2(n1 - n2, n2 + n3) * 0.12;
      
      vec3 normal = normalize(vNormal + vec3(surfaceNoise.x, 0.0, surfaceNoise.y));
      
      vec3 viewDir = normalize(vViewPosition);
      float fresnel = pow(1.0 - max(dot(viewDir, normal), 0.0), 5.0);
      
      float mixStrength = (vElevation + 0.1) * 1.5;
      vec3 baseColor = mix(uDepthColor, uSurfaceColor, clamp(mixStrength, 0.0, 1.0));
      vec3 waterColor = mix(baseColor, uSkyColor, fresnel * 0.4);
      
      vec3 reflectDir = reflect(-uSunPosition, normal);
      float spec = pow(max(dot(viewDir, reflectDir), 0.0), 300.0);
      vec3 specular = vec3(1.0, 0.95, 0.9) * spec * 1.5;
      
      float foamBase = smoothstep(0.4, 0.8, vElevation + vInterference * 0.5);
      
      vec2 foamUv = vWorldPosition.xz * 2.0;
      float fNoise = noise2d(foamUv - t * 0.5) * 0.6 + noise2d(foamUv * 4.0 + t) * 0.4;
      
      float splash = smoothstep(0.6, 0.9, fNoise) * smoothstep(0.3, 0.6, vInterference);
      
      float foamIntensity = clamp(foamBase * smoothstep(0.4, 0.7, fNoise) + splash * 1.5, 0.0, 1.0);
      waterColor = mix(waterColor, uFoamColor, foamIntensity * 0.8);
      
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

// 💖 ノアの修正ポイント2: TypeScriptちゃんを納得させるための「雲の設計図（型）」を作る！
type CloudData = {
  x: number;
  y: number;
  z: number;
  seed: number;
  volume: number;
  opacity: number;
};

// 🌌 ノアぴの流動的エモ空コンポーネント（エンドレス雲Ver） 🌌
function FluidAtmosphere() {
  const atmosphereRef = useRef<THREE.Group>(null);

  useFrame((state, delta) => {
    if (atmosphereRef.current) {
      atmosphereRef.current.rotation.y += delta * 0.015;
    }
  });

  // 💖 ノアの修正ポイント3: useMemoの出力が CloudData の配列だよって教えてあげる！
  const cloudPuffs = useMemo<CloudData[]>(() => {
    return Array.from({ length: 8 }).map((_, i) => {
      const angle = (i / 8) * Math.PI * 2; 
      const radius = 60 + Math.random() * 40; 
      
      return {
        x: Math.cos(angle) * radius,
        y: 25 + Math.random() * 15, 
        z: Math.sin(angle) * radius,
        seed: Math.random() * 100,
        volume: 10 + Math.random() * 10,
        opacity: 0.15 + Math.random() * 0.15,
      };
    });
  }, []);

  return (
    <group ref={atmosphereRef}>
      <Sky distance={450000} sunPosition={[0, 2, -50]} inclination={0.1} azimuth={0.25} rayleigh={1.5} />
      <Stars radius={100} depth={50} count={3000} factor={4} saturation={0} fade speed={1.5} />
      <Sparkles count={800} scale={250} size={3} speed={0.4} opacity={0.3} color="#8be9fd" position={[0, 10, 0]} />

      <Clouds material={THREE.MeshStandardMaterial}>
        {/* 💖 ノアの修正ポイント4: mapの引数に型 (cloud: CloudData, i: number) を明記！ */}
        {cloudPuffs.map((cloud: CloudData, i: number) => (
          <Cloud 
            key={i}
            seed={cloud.seed} 
            segments={20} 
            bounds={[40, 10, 40]} 
            volume={cloud.volume} 
            color={i % 2 === 0 ? "#ffffff" : "#e0f2fe"} 
            position={[cloud.x, cloud.y, cloud.z]} 
            opacity={cloud.opacity} 
          />
        ))}
      </Clouds>
    </group>
  );
}

export default function Viewport3D() {
  return (
    <>
      <ambientLight intensity={0.2} />
      <directionalLight position={[0, 5, -50]} intensity={2.0} color="#ffffff" />
      <pointLight position={[0, 5, 10]} intensity={1.0} color="#8be9fd" />
      
      <Environment preset="city" />
      
      <fog attach="fog" args={['#002244', 30, 200]} />
      
      <Ocean />
      <FluidAtmosphere />
    </>
  );
}