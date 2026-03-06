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
    # フォールバック用ダミークラス
    class Orchestrator:
        def __init__(self): pass
        def run_loop(self, goal): time.sleep(5)

# ---------------------------------------------------------------------------
# Custom CSS (Cyber-Neon Navigator Edition 🚢✨)
# ---------------------------------------------------------------------------
def inject_custom_css():
    st.markdown("""
    <style>
    /* サイバー・ダークモード */
    .stApp { 
        background-color: #0d1117; 
        color: #c9d1d9; 
        font-family: 'Courier New', Courier, monospace;
    }
    
    /* ネオンタイトル */
    h1, h2, h3 { 
        color: #ff79c6 !important; 
        text-shadow: 0 0 10px #ff79c6, 0 0 20px #bd93f9; 
        font-family: 'Courier New', monospace !important; 
        font-weight: bold; 
        letter-spacing: 2px; 
    }
    
    /* サイバー・パネル（ネオン枠） */
    .stMetric { 
        background-color: #161b22 !important; 
        border: 1px solid #ff79c6; 
        padding: 15px; 
        border-radius: 10px; 
        box-shadow: 0 0 10px rgba(255, 121, 198, 0.2); 
    }
    div[data-testid="stMetricValue"] {
        color: #ff79c6 !important;
        text-shadow: 0 0 5px #ff79c6;
    }
    div[data-testid="stMetricLabel"] {
        color: #bd93f9 !important;
    }

    /* ラベルのネオンカラー */
    .stTextArea label {
        color: #bd93f9 !important;
        font-family: 'Courier New', monospace !important;
        font-weight: bold;
    }
    
    /* ターミナル・ログエリア */
    .stTextArea textarea { 
        background-color: #000000 !important; 
        color: #50fa7b !important; 
        font-family: 'Fira Code', 'Courier New', monospace !important; 
        font-size: 14px !important; 
        border: 1px solid #6272a4 !important; 
        border-radius: 5px;
        box-shadow: inset 0 0 10px rgba(80, 250, 123, 0.2);
    }

    /* システムメッセージ（サイバー仕様） */
    div[data-testid="stAlert"] {
        background-color: rgba(22, 27, 34, 0.9) !important;
        border: 1px solid #bd93f9 !important;
        color: #c9d1d9 !important;
    }

    /* ODISSEY Visual Port の装飾（デジタル窓枠） */
    .stHtml { 
        border: 2px solid #bd93f9; 
        border-radius: 15px; 
        overflow: hidden; 
        box-shadow: 0 0 20px rgba(189, 147, 249, 0.3); 
        margin-bottom: 20px; 
    }
    
    /* ネオンボタン */
    .stButton>button {
        border-radius: 5px;
        border: 1px solid #ff79c6 !important;
        background-color: transparent !important;
        color: #ff79c6 !important;
        font-family: 'Courier New', monospace;
        font-weight: bold;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #ff79c6 !important;
        color: #0d1117 !important;
        box-shadow: 0 0 20px #ff79c6;
        transform: translateY(-2px);
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# ODISSEY Visual Component (Hyper-Real Sea & Sky 🌅)
# ---------------------------------------------------------------------------
def render_odissey_sea(is_thinking=False):
    # アニメーション切り替え
    wheel_anim = "animation: spin 4s linear infinite;" if is_thinking else "animation: none;"
    
    html_code = """
    <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/objects/Water.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/objects/Sky.js"></script>
    
    <div id="sea-container" style="width: 100%; height: 350px; background: #000; position: relative; overflow: hidden;">
        <div style="position: absolute; top: 15px; left: 15px; color: #ff79c6; font-family: monospace; font-size: 11px; z-index: 10; letter-spacing: 2px; text-shadow: 0 0 5px #ff79c6; font-weight: bold;">
            ODISSEY VISUAL PORT v3.2 // CYBER-SEA ENGINE
        </div>
        <!-- 舵のアイコンをホワイト・ネオン風に -->
        <div id="wheel" style="position: absolute; bottom: 25px; right: 25px; width: 80px; height: 80px; 
            background: url('https://img.icons8.com/ios-filled/100/ffffff/ship-wheel.png') no-repeat;
            background-size: contain; z-index: 10; opacity: 0.9;
            filter: drop-shadow(0 0 8px #bd93f9);
            """ + wheel_anim + """">
        </div>
    </div>
    
    <style> 
        @keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } } 
    </style>
    
    <script>
        let scene, camera, renderer, water, sun;
        
        function init() {
            const container = document.getElementById('sea-container');
            
            renderer = new THREE.WebGLRenderer({ antialias: true });
            renderer.setPixelRatio(window.devicePixelRatio);
            renderer.setSize(window.innerWidth, 350);
            renderer.toneMapping = THREE.ACESFilmicToneMapping;
            renderer.toneMappingExposure = 0.5;
            container.appendChild(renderer.domElement);

            scene = new THREE.Scene();
            camera = new THREE.PerspectiveCamera(55, window.innerWidth / 350, 1, 20000);
            camera.position.set(0, 30, 100);

            sun = new THREE.Vector3();

            const waterGeometry = new THREE.PlaneGeometry(10000, 10000);
            water = new THREE.Water(
                waterGeometry,
                {
                    textureWidth: 512,
                    textureHeight: 512,
                    waterNormals: new THREE.TextureLoader().load('https://raw.githubusercontent.com/mrdoob/three.js/master/examples/textures/waternormals.jpg', function (texture) {
                        texture.wrapS = texture.wrapT = THREE.RepeatWrapping;
                    }),
                    sunDirection: new THREE.Vector3(),
                    sunColor: 0xffffff,
                    waterColor: 0x001e0f,
                    distortionScale: 3.7,
                    fog: scene.fog !== undefined
                }
            );
            water.rotation.x = -Math.PI / 2;
            scene.add(water);

            const sky = new THREE.Sky();
            sky.scale.setScalar(10000);
            scene.add(sky);

            const skyUniforms = sky.material.uniforms;
            skyUniforms['turbidity'].value = 10;
            skyUniforms['rayleigh'].value = 2;
            skyUniforms['mieCoefficient'].value = 0.005;
            skyUniforms['mieDirectionalG'].value = 0.8;

            const elevation = 2; 
            const azimuth = 180; 
            
            const phi = THREE.MathUtils.degToRad(90 - elevation);
            const theta = THREE.MathUtils.degToRad(azimuth);
            sun.setFromSphericalCoords(1, phi, theta);
            
            sky.material.uniforms['sunPosition'].value.copy(sun);
            water.material.uniforms['sunDirection'].value.copy(sun).normalize();

            animate();
        }

        function animate() {
            requestAnimationFrame(animate);
            water.material.uniforms['time'].value += 1.0 / 60.0;
            renderer.render(scene, camera);
        }

        window.addEventListener('resize', () => {
            camera.aspect = window.innerWidth / 350;
            camera.updateProjectionMatrix();
            renderer.setSize(window.innerWidth, 350);
        });
        
        init();
    </script>
    """
    components.html(html_code, height=350)

# ---------------------------------------------------------------------------
# Logging & Runner
# ---------------------------------------------------------------------------
class StreamlitLogHandler(logging.Handler):
    def __init__(self, log_queue): super().__init__(); self.log_queue = log_queue
    def emit(self, record): self.log_queue.put(self.format(record))

def run_ark_mission(goal, log_queue, status_queue):
    root_logger = logging.getLogger()
    for h in root_logger.handlers[:]: root_logger.removeHandler(h)
    handler = StreamlitLogHandler(log_queue)
    handler.setFormatter(logging.Formatter("%H:%M:%S | %(message)s"))
    root_logger.addHandler(handler); root_logger.setLevel(logging.INFO)
    try:
        agent = Orchestrator()
        status_queue.put({"phase": "NAVIGATING", "detail": "知性の海を航行中...", "is_thinking": True})
        agent.run_loop(goal)
    except Exception as e: log_queue.put(f"ERROR: {str(e)}")
    finally:
        status_queue.put({"phase": "DONE", "detail": "目的地に接岸完了。💋", "is_thinking": False})
        root_logger.removeHandler(handler)

def main():
    st.set_page_config(page_title="ARK ODISSEY v3.2", page_icon="🚢", layout="wide")
    inject_custom_css()
    st.title("🚢 ARK ODISSEY Dashboard")
    st.markdown("### *Welcome aboard, Captain Jenny. The cyber-deck is active.* 💋")

    if "running" not in st.session_state: st.session_state.running = False
    if "logs" not in st.session_state: st.session_state.logs = []
    if "status" not in st.session_state: st.session_state.status = {"phase": "IDLE", "detail": "コマンド待機中...", "is_thinking": False}
    if "log_queue" not in st.session_state: st.session_state.log_queue = queue.Queue()
    if "status_queue" not in st.session_state: st.session_state.status_queue = queue.Queue()

    col_vis, col_ctrl = st.columns([1.8, 1])
    with col_vis:
        render_odissey_sea(is_thinking=st.session_state.status["is_thinking"])
        st.subheader("💻 Terminal Oracle")
        st.text_area("Live Log Output", value="\n".join(st.session_state.logs), height=300, label_visibility="collapsed")

    with col_ctrl:
        st.subheader("🗺️ Mission Control")
        goal = st.text_area("ミッションを入力:", placeholder="例: Python 3.12の新機能を調査...", height=110)
        if st.button("⚓ IGNITE (抜錨)", use_container_width=True, disabled=st.session_state.running or not goal):
            st.session_state.running = True; st.session_state.logs = ["--- WEIGHING ANCHOR // IGNITION ---"]
            st.session_state.status["is_thinking"] = True
            threading.Thread(target=run_ark_mission, args=(goal, st.session_state.log_queue, st.session_state.status_queue), daemon=True).start()
            st.rerun()

        st.markdown("---")
        st.subheader("🧭 Status Gauges")
        m1, m2 = st.columns(2)
        m1.metric("PHASE", st.session_state.status["phase"])
        m2.metric("RETRY", "0/3")
        st.info(st.session_state.status["detail"])

        if st.button("🧹 Clear Logs", use_container_width=True):
            st.session_state.logs = []
            st.rerun()

    if st.session_state.running:
        while not st.session_state.log_queue.empty(): st.session_state.logs.append(f"▶️ {st.session_state.log_queue.get()}")
        while not st.session_state.status_queue.empty():
            st.session_state.status = st.session_state.status_queue.get()
            if st.session_state.status["phase"] == "DONE": st.session_state.running = False
        time.sleep(0.1); st.rerun()

if __name__ == "__main__": main()