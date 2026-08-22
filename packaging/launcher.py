"""Entry point for the packaged macOS app.

Starts the FastAPI/Uvicorn server in a background thread, waits for it to
report healthy, then either opens the default browser + shows a minimal
status window (normal use), or -- under FANTASY_DRAFT_SMOKE_TEST=1 -- blocks
headlessly in the foreground so CI can curl /health and kill the process
without a display or default browser available.
"""

import multiprocessing
import os
import sys
import threading
import time
import urllib.request
import webbrowser

PORT = 8765
HEALTH_URL = f"http://127.0.0.1:{PORT}/health"


def start_server():
    import uvicorn

    from project.webapp.server import app

    uvicorn.run(app, host="127.0.0.1", port=PORT, log_level="warning")


def wait_for_health(timeout=15):
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(HEALTH_URL, timeout=1):
                return True
        except Exception:
            time.sleep(0.5)
    return False


def build_status_window(healthy):
    import tkinter as tk

    root = tk.Tk()
    root.title("Fantasy Draft Assistant")
    root.geometry("360x160")

    message = (
        f"Running at {HEALTH_URL.replace('/health', '')}\n\nClose this window's Quit "
        "button to stop the app."
        if healthy
        else "Failed to start the local server.\nCheck your network connection and try again."
    )
    tk.Label(root, text=message, wraplength=320, justify="left", padx=16, pady=16).pack()
    tk.Button(root, text="Quit", command=lambda: os._exit(0)).pack(pady=8)

    root.mainloop()


def main():
    # MUST be the first line: macOS frozen apps use the "spawn" multiprocessing
    # start method (unlike Linux "fork"). Without this, a ProcessPoolExecutor
    # worker can re-execute and recursively relaunch the whole packaged app.
    multiprocessing.freeze_support()

    threading.Thread(target=start_server, daemon=True).start()

    if os.environ.get("FANTASY_DRAFT_SMOKE_TEST"):
        # Headless CI path: no tkinter, no browser -- block in the foreground
        # so the CI step can curl /health against this process, then kill it.
        wait_for_health()
        threading.Event().wait()
        return

    healthy = wait_for_health()
    if healthy:
        webbrowser.open(HEALTH_URL.replace("/health", ""))
    build_status_window(healthy)


if __name__ == "__main__":
    main()
