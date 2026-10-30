"""
Project Rakshak - One-Click Application Launcher
Starts the FastAPI WebSocket simulation backend and opens the 3D Digital Twin in the default browser.
"""

import sys
import os
import webbrowser
import time
import subprocess

def main():
    print("=" * 70)
    print("  ⚡ PROJECT RAKSHAK: EDGE-INTELLIGENT GRID RESILIENCE SYSTEM")
    print("  Aligned with UN SDG 11: Sustainable Cities and Communities")
    print("=" * 70)
    print("\n[1/2] Starting FastAPI Co-Simulation Backend on http://localhost:8000 ...")

    backend_dir = os.path.join(os.path.dirname(__file__), "backend")
    
    # Launch uvicorn
    cmd = [sys.executable, "-m", "uvicorn", "main:app", "--host", "127.0.0.1", "--port", "8000"]
    proc = subprocess.Popen(cmd, cwd=backend_dir)

    print("[2/2] Opening 3D Street Digital Twin in browser ...")
    time.sleep(1.5)
    webbrowser.open("http://127.0.0.1:8000/index.html")

    print("\n>>> System running! Press Ctrl+C in this terminal to stop.")
    try:
        proc.wait()
    except KeyboardInterrupt:
        print("\nStopping Project Rakshak backend...")
        proc.terminate()

if __name__ == "__main__":
    main()
