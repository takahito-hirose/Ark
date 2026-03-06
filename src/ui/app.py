import os
import threading
import queue
import time
import logging
import streamlit as st
from dotenv import load_dotenv
from pathlib import Path

# ---------------------------------------------------------------------------
# 【超重要】ARKの心臓部を読み込む前に、.envを強制ロード！
# ---------------------------------------------------------------------------
load_dotenv()

# load_dotenv() の後にインポート！
from src.core.orchestrator import Orchestrator, Phase

# ---------------------------------------------------------------------------
# Custom CSS Injection (サイバーギャル仕様💋)
# ---------------------------------------------------------------------------
def inject_custom_css():
    st.markdown("""
    <style>
    /* メインタイトルにネオンエフェクト */
    .stApp > header { background-color: transparent; }
    h1 { color: #BD93F9; text-shadow: 0 0 10px #BD93F9; }
    /* ステータスボックスのカスタマイズ */
    div[data-testid="metric-container"] {
        background-color: #1E1E2E;
        border: 1px solid #BD93F9;
        padding: 15px;
        border-radius: 10px;
        box-shadow: 0 0 10px rgba(189, 147, 249, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Logging Handler for Streamlit
# ---------------------------------------------------------------------------
class QueueHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        msg = self.format(record)
        self.log_queue.put(msg)

# ---------------------------------------------------------------------------
# UI State & Orchestrator Runner
# ---------------------------------------------------------------------------
def run_orchestrator(goal, status_queue, log_queue):
    def on_status_change(phase, status, retry_count, detail=""):
        status_queue.put({
            "phase": phase,
            "status": status,
            "retry_count": retry_count,
            "detail": detail
        })

    root_logger = logging.getLogger()
    handler = QueueHandler(log_queue)
    # ログフォーマットを少しリッチに✨
    handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)s | %(message)s", "%H:%M:%S"))
    root_logger.addHandler(handler)
    
    try:
        orc = Orchestrator(on_status_change=on_status_change)
        orc.run(goal)
    except Exception as e:
        log_queue.put(f"CRITICAL ERROR | {str(e)}")
    finally:
        status_queue.put({"phase": Phase.DONE, "status": "FINISHED", "retry_count": 0, "detail": "Loop ended"})
        root_logger.removeHandler(handler)

# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------
def main():
    st.set_page_config(page_title="ARK ODISSEY", page_icon="🛸", layout="wide")
    inject_custom_css()
    
    st.title("🛸 ARK ODISSEY Dashboard")
    st.markdown("Welcome to the secret control room, Captain. 💋")
    st.markdown("---")

    # Initialize session state
    if "running" not in st.session_state:
        st.session_state.running = False
    if "status_queue" not in st.session_state:
        st.session_state.status_queue = queue.Queue()
    if "log_queue" not in st.session_state:
        st.session_state.log_queue = queue.Queue()
    if "logs" not in st.session_state:
        st.session_state.logs = []
    if "current_status" not in st.session_state:
        st.session_state.current_status = {"phase": Phase.IDLE, "status": "READY", "retry_count": 0, "detail": "Waiting for command..."}

    # -----------------------------------------------------------------------
    # Top Control Panel (メインダッシュボード化)
    # -----------------------------------------------------------------------
    col_input, col_status = st.columns([2, 1])
    
    with col_input:
        goal_input = st.text_area("🎯 Mission Objective", placeholder="例: FastAPIでユーザー管理のCRUDアプリを作って！", height=120)
        start_btn = st.button("🚀 IGNITE (Start Autonomous Loop)", type="primary", use_container_width=True, disabled=st.session_state.running or not goal_input)
        
        if start_btn:
            st.session_state.running = True
            st.session_state.logs = ["System initialized. Starting sequence..."]
            st.session_state.status_queue = queue.Queue()
            st.session_state.log_queue = queue.Queue()
            
            thread = threading.Thread(
                target=run_orchestrator, 
                args=(goal_input, st.session_state.status_queue, st.session_state.log_queue),
                daemon=True
            )
            thread.start()
            st.rerun()

    with col_status:
        # ステータスをカッコいいメトリクス風に表示
        st.subheader("System Status")
        m1, m2 = st.columns(2)
        curr_phase = st.session_state.current_status["phase"]
        curr_retry = st.session_state.current_status["retry_count"]
        
        m1.metric("Current Phase", str(curr_phase).replace("Phase.", ""))
        m2.metric("Retry Attempt", f"{curr_retry} / 3")
        
        st.caption("Detail:")
        st.info(st.session_state.current_status["detail"])
        if st.session_state.running:
            st.progress(curr_retry / 3.0)

    st.markdown("---")

    # -----------------------------------------------------------------------
    # Main Terminal Area
    # -----------------------------------------------------------------------
    st.subheader("💻 Terminal Oracle")
    
    # Update logic (polling queues)
    if st.session_state.running:
        while not st.session_state.status_queue.empty():
            new_status = st.session_state.status_queue.get()
            st.session_state.current_status = new_status
            if new_status["phase"] == Phase.DONE:
                st.session_state.running = False

        while not st.session_state.log_queue.empty():
            new_log = st.session_state.log_queue.get()
            # ログを少し見やすく装飾（Markdownの色付け用）
            if "CRITICAL" in new_log or "ERROR" in new_log:
                new_log = f"🔴 {new_log}"
            elif "Thought" in new_log:
                new_log = f"🧠 {new_log}"
            elif "Command" in new_log or "Execution" in new_log:
                new_log = f"⚡ {new_log}"
            else:
                new_log = f"🟢 {new_log}"
                
            st.session_state.logs.append(new_log)

        # Force refresh for real-time feel
        time.sleep(0.3)
        st.rerun()

    # ログの表示領域（常に最新が下に来るようにする）
    log_text = "\n".join(st.session_state.logs)
    if log_text:
        # text_areaを使うとスクロールバーが維持されやすいわよ
        st.text_area("Live Output", value=log_text, height=400, label_visibility="collapsed")
    else:
        st.caption("Awaiting transmission...")

if __name__ == "__main__":
    main()