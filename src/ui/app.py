import os
from dotenv import load_dotenv

# ---------------------------------------------------------------------------
# 【超重要】ARKの心臓部を読み込む前に、.env（ジェニーのAPIキー）を強制ロード！
# ---------------------------------------------------------------------------
load_dotenv()

import streamlit as st
import threading
import queue
import time
import sys
import logging
from pathlib import Path

# load_dotenv() の後にインポートすること！
from src.core.orchestrator import Orchestrator, Phase

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

    # Setup logging to capture Orchestrator logs
    root_logger = logging.getLogger()
    handler = QueueHandler(log_queue)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(message)s", "%H:%M:%S"))
    root_logger.addHandler(handler)
    
    try:
        orc = Orchestrator(on_status_change=on_status_change)
        orc.run(goal)
    except Exception as e:
        log_queue.put(f"CRITICAL ERROR: {str(e)}")
    finally:
        status_queue.put({"phase": Phase.DONE, "status": "FINISHED", "retry_count": 0, "detail": "Loop ended"})
        root_logger.removeHandler(handler)

# ---------------------------------------------------------------------------
# Streamlit App
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="ARK Orchestrator Dashboard", layout="wide")
    
    st.title("🚀 ARK Orchestrator Dashboard")
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
        st.session_state.current_status = {"phase": Phase.IDLE, "status": "READY", "retry_count": 0, "detail": "Waiting for task..."}

    # Sidebar: Status & Controls
    with st.sidebar:
        st.header("Control Panel")
        goal_input = st.text_area("Task Goal", placeholder="e.g. Create a FastAPI app with CRUD for users", height=150)
        
        if st.button("Start Autonomous Loop", disabled=st.session_state.running or not goal_input):
            st.session_state.running = True
            st.session_state.logs = []
            st.session_state.status_queue = queue.Queue()
            st.session_state.log_queue = queue.Queue()
            
            # Start background thread
            thread = threading.Thread(
                target=run_orchestrator, 
                args=(goal_input, st.session_state.status_queue, st.session_state.log_queue),
                daemon=True
            )
            thread.start()
            st.rerun()

        st.markdown("---")
        st.subheader("Current Phase")
        phase = st.session_state.current_status["phase"]
        st.info(f"**{phase}**")
        
        st.subheader("Progress (Retries)")
        retry_val = st.session_state.current_status["retry_count"]
        st.progress(retry_val / 3.0, text=f"Attempt {retry_val}/3")
        
        st.subheader("Details")
        st.write(st.session_state.current_status["detail"])

    # Main Area: Logs
    st.subheader("Real-time Logs")
    log_container = st.empty()
    
    # Update logic (polling queues)
    if st.session_state.running:
        # Check for status updates
        while not st.session_state.status_queue.empty():
            new_status = st.session_state.status_queue.get()
            st.session_state.current_status = new_status
            if new_status["phase"] == Phase.DONE:
                st.session_state.running = False

        # Check for log updates
        while not st.session_state.log_queue.empty():
            new_log = st.session_state.log_queue.get()
            st.session_state.logs.append(new_log)

        # Re-render logs
        log_text = "\n".join(st.session_state.logs)
        log_container.code(log_text, language="text")

        # Force refresh if running
        if st.session_state.running:
            time.sleep(0.5)
            st.rerun()
    else:
        # Display final logs if any
        if st.session_state.logs:
            log_container.code("\n".join(st.session_state.logs), language="text")
        else:
            st.info("Log output will appear here once the task starts.")

if __name__ == "__main__":
    main()