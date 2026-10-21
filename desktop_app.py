import subprocess
import time
import sys
import os
import urllib.request
import webview

def wait_for_server(url, timeout=30):
    start = time.time()
    while time.time() - start < timeout:
        try:
            with urllib.request.urlopen(url) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.5)
    return False

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    app_path = os.path.join(base_dir, "app.py")
    port = "8501"
    url = f"http://localhost:{port}"

    python_exe = sys.executable

    # Streamlit sunucusunu arka planda başlat
    cmd = [
        python_exe, "-m", "streamlit", "run", app_path,
        "--server.port", port,
        "--server.headless", "true",
        "--browser.serverAddress", "localhost",
        "--global.developmentMode", "false"
    ]

    # Windows'ta konsol penceresini gizle
    creationflags = 0
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NO_WINDOW

    proc = subprocess.Popen(cmd, cwd=base_dir, creationflags=creationflags)

    try:
        if wait_for_server(url):
            # Masaüstü penceresini aç
            window = webview.create_window(
                title="Jus Tahsilat Makinesi - İcra Takip & Cari Çözüm Masası",
                url=url,
                width=1320,
                height=840,
                min_size=(900, 600),
                confirm_close=True
            )
            webview.start()
        else:
            print("Sunucu başlatılamadı.")
    finally:
        # Masaüstü penceresi kapatıldığında arka plandaki streamlit'i kapat
        try:
            proc.terminate()
            proc.wait(timeout=2)
        except Exception:
            proc.kill()

if __name__ == "__main__":
    main()
