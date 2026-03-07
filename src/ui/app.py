import os
import threading
import queue
import time
import logging
import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 環境変数の読み込み
# ---------------------------------------------------------------------------
load_dotenv()

try:
    from src.orchestrator import ARKAgent as Orchestrator
except ImportError:
    class Orchestrator:
        def __init__(self): pass
        def run_loop(self, goal): time.sleep(10) # 10秒間のデモ航海

# ---------------------------------------------------------------------------
# Custom CSS (The Wheelhouse Design 🪵⚓)
# ---------------------------------------------------------------------------
def inject_custom_css():
    st.markdown("""
    <style>
    /* 全体をブラックアウトして没入感を出す */
    .stApp { background-color: #000; color: #f4e4bc; }
    header { visibility: hidden; }
    
    /* 操舵室の重厚な雰囲気 */
    h1 { 
        color: #d4af37 !important; 
        text-shadow: 0 0 10px rgba(212, 175, 55, 0.5); 
        font-family: 'Georgia', serif; 
        text-align: center;
        margin-top: -50px;
    }

    /* Streamlitの枠を消して全画面っぽく */
    [data-testid="stVerticalBlock"] { padding: 0 !important; }
    
    /* サイドバーやコントロール類をアンティークに */
    .stTextArea textarea { 
        background-color: #1a120b !important; 
        color: #d4af37 !important; 
        border: 2px solid #5d4037 !important;
        font-family: 'Courier New', monospace;
    }
    .stButton>button {
        background-color: #3e2723 !important;
        color: #d4af37 !important;
        border: 2px solid #d4af37 !important;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #d4af37 !important;
        color: #000 !important;
        box-shadow: 0 0 20px #d4af37;
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ODISSEY Hyper-Visual Engine (Three.js + HTML/CSS Overlay)
# ---------------------------------------------------------------------------
def render_odissey_visual(is_thinking=False, logs=[], progress=0):
    # ログをJSに渡せるように整形
    formatted_logs = "\\n".join(logs[-10:]) if logs else "Awaiting Mission..."
    
    # 思考中かどうかでアニメーションパラメータを変更
    wheel_speed = 1.0 if is_thinking else 0.0
    ship_speed = 0.05 if is_thinking else 0.005
    
    html_code = f"""
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/objects/Water.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/objects/Sky.js"></script>

    <div id="odissey-viewport" style="width: 100%; height: 600px; position: relative; overflow: hidden; border: 15px solid #3e2723; border-radius: 20px; box-shadow: inset 0 0 50px #000;">
        
        <!-- 3D Canvas -->
        <div id="three-container" style="width: 100%; height: 100%;"></div>

        <!-- キャビン・オーバーレイ (船の窓枠風) -->
        <div style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none;
            background: linear-gradient(0deg, rgba(62,39,35,1) 0%, rgba(62,39,35,0) 20%, rgba(62,39,35,0) 80%, rgba(62,39,35,1) 100%),
                        linear-gradient(90deg, rgba(62,39,35,1) 0%, rgba(62,39,35,0) 10%, rgba(62,39,35,0) 90%, rgba(62,39,35,1) 100%);">
        </div>

        <!-- 左パネル: SYLPH ACTIVITY (Hologram) -->
        <div style="position: absolute; top: 50px; left: 30px; width: 250px; height: 350px; 
            background: rgba(0, 255, 255, 0.05); border-left: 2px solid rgba(0, 255, 255, 0.5); 
            padding: 15px; color: #00ffff; font-family: monospace; font-size: 10px; overflow: hidden;
            box-shadow: -10px 0 20px rgba(0, 255, 255, 0.1); backdrop-filter: blur(2px);">
            <div style="border-bottom: 1px solid #00ffff; margin-bottom: 10px; font-weight: bold; font-size: 12px;">🛰️ SYLPH ACTIVITY LOG</div>
            <pre id="hologram-logs" style="white-space: pre-wrap;">{formatted_logs}</pre>
        </div>

        <!-- 右パネル: SEA CHART (Hologram) -->
        <div style="position: absolute; top: 50px; right: 30px; width: 250px; height: 200px; 
            background: rgba(255, 255, 0, 0.05); border-right: 2px solid rgba(255, 255, 0, 0.5); 
            padding: 15px; color: #ffff00; font-family: 'Georgia', serif; text-align: center;
            box-shadow: 10px 0 20px rgba(255, 255, 0, 0.1); backdrop-filter: blur(2px);">
            <div style="border-bottom: 1px solid #ffff00; margin-bottom: 10px; font-weight: bold;">🗺️ SEA CHART</div>
            <div style="font-size: 10px; margin-bottom: 5px;">DESTINATION: CODE ISLAND</div>
            <div style="width: 100%; height: 10px; background: rgba(255,255,0,0.2); border-radius: 5px; overflow: hidden;">
                <div style="width: {progress}%; height: 100%; background: #ffff00; transition: width 0.5s;"></div>
            </div>
            <div style="font-size: 24px; margin-top: 10px; font-weight: bold;">{progress}%</div>
            <div style="font-size: 10px; margin-top: 10px; color: #00ff00;">STATUS: {'NAVIGATING' if is_thinking else 'STATIONARY'}</div>
        </div>

        <!-- 中央: 舵 (Ship's Wheel) -->
        <div id="main-wheel" style="position: absolute; bottom: -40px; left: 50%; transform: translateX(-50%); width: 300px; height: 300px; 
            background: url('https://img.icons8.com/ios-filled/300/d4af37/ship-wheel.png') no-repeat;
            background-size: contain; opacity: 0.8; filter: drop-shadow(0 0 20px #000); z-index: 20;">
        </div>

        <!-- 100% 到着時の宝箱 (Overlay) -->
        <div id="arrival-overlay" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%; 
            background: rgba(255,255,255,0.9); display: { 'flex' if progress >= 100 else 'none' }; 
            flex-direction: column; justify-content: center; align-items: center; z-index: 100; color: #3e2723;">
            <h1 style="font-size: 4rem;">ARRIVED! ⚓</h1>
            <p style="font-size: 1.5rem;">The Treasure (Source Code) has been secured.</p>
            <div style="font-size: 100px;">📦</div>
        </div>

    </div>

    <script>
        let scene, camera, renderer, water, island;
        const isThinking = {str(is_thinking).lower()};
        
        function init() {{
            const container = document.getElementById('three-container');
            renderer = new THREE.WebGLRenderer({{ antialias: true }});
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.setSize(container.clientWidth, container.clientHeight);
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            container.appendChild(renderer.domElement);

            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(55, container.clientWidth / container.clientHeight, 1, 20000);
            camera.position.set(0, 30, 200);

            const sun = new THREE.Vector3();

            // 水面
            const waterGeometry = new THREE.PlaneGeometry(10000, 10000);
            water = new THREE.Water(waterGeometry, {{
                textureWidth: 512, textureHeight: 512,
                waterNormals: new THREE.TextureLoader().load('https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/waternormals.jpg', function (texture) {{
                    texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
                }}),
                sunDirection: new THREE.Vector3(), sunColor: 0xffffff, waterColor: 0x001e0f, distortionScale: 3.7
            }});
            water.rotation.x = -Math.PI / 2;
            scene.add(water);

            // 空
            const sky = new THREE.Sky();
            sky.scale.setScalar(10000);
            scene.add(sky);
            const skyUniforms = sky.material.uniforms;
            skyUniforms['turbidity'].value = 10;
            skyUniforms['rayleigh'].value = 2;
            skyUniforms['mieCoefficient'].value = 0.005;
            skyUniforms['mieDirectionalG'].value = 0.8;
            sun.setFromSphericalCoords(1, THREE.MathUtils.degToRad(88), THREE.MathUtils.degToRad(180));
            skyUniforms['sunPosition'].value.copy(sun);
            water.material.uniforms['sunDirection'].value.copy(sun).normalize();

            // 島 (遠くにあるターゲット)
            const islandGeo = new THREE.ConeGeometry(50, 80, 4);
            const islandMat = new THREE.MeshPhongMaterial({{ color: 0x1a2e1a, flatShading: true }});
            island = new THREE.Mesh(islandGeo, islandMat);
            island.position.set(0, 20, -2000);
            scene.add(island);
            
            const ambientLight = new THREE.AmbientLight(0xffffff, 0.8);
            scene.add(ambientLight);

            animate();
        }}

        let wheelRotation = 0;
        function animate() {{
            requestAnimationFrame(animate);
            const time = Date.now() * 0.001;
            water.material.uniforms['time'].value += 1.0 / 60.0;
            
            // 舵の回転
            if (isThinking) {{
                wheelRotation += 0.02;
                document.getElementById('main-wheel').style.transform = `translateX(-50%) rotate(${{wheelRotation * 50}}deg)`;
                
                // 島に近づく
                if (camera.position.z > 200) camera.position.z -= 2;
            }}

            renderer.render(scene, camera);
        }}
        
        init();
    </script>
    """
    components.html(html_code, height=620)

# ---------------------------------------------------------------------------
# Main App Logic
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="ARK ODISSEY v3.0", layout="wide")
    inject_custom_css()
    
    st.title("🚢 ARK Navigator v2.0: Project ODISSEY")
    
    # State管理
    if "running" not in st.session_state: st.session_state.running = False
    if "logs" not in st.session_state: st.session_state.logs = []
    if "progress" not in st.session_state: st.session_state.progress = 0
    if "log_queue" not in st.session_state: st.session_state.log_queue = queue.Queue()

    # ビジュアルポート
    render_odissey_visual(is_thinking=st.session_state.running, logs=st.session_state.logs, progress=st.session_state.progress)

    # コントロールパネル
    st.markdown("---")
    col_in, col_btn = st.columns([3, 1])
    
    with col_in:
        goal = st.text_input("📍 Set Destination (Prompt):", placeholder="例: Python 3.12の最新機能を調査してデモを作成せよ")
    
    with col_btn:
        if st.button("⚓ WEIGH ANCHOR (抜錨)", use_container_width=True, disabled=st.session_state.running or not goal):
            st.session_state.running = True
            st.session_state.progress = 10 # 航海開始
            st.session_state.logs.append("Weighing anchor... Setting course for Code Island.")
            
            # 本来はここで Orchestrator スレッドを起動
            # デモ用にプログレスを進めるロジックを入れるのもアリね💋
            st.rerun()

    # ダミーの進行シミュレーション (デモ用)
    if st.session_state.running and st.session_state.progress < 100:
        time.sleep(1)
        st.session_state.progress += 5
        st.session_state.logs.append(f"Navigating... Distance to island: {100 - st.session_state.progress}%")
        if st.session_state.progress >= 100:
            st.session_state.logs.append("Land ho!接岸完了しました、キャプテン！")
        st.rerun()

if __name__ == "__main__":
    main()