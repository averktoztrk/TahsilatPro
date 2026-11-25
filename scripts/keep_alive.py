import http.cookiejar
import os
import sys
import urllib.request
from datetime import datetime

STREAMLIT_URL = os.environ.get("STREAMLIT_URL", "https://tahsilatpro.streamlit.app")
DEFAULT_SUPABASE_URL = "postgresql://postgres.mngekqtbfbtianfhafja:Fengabes295123.@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require"
ACTIVE_URL = os.environ.get("DATABASE_URL") or DEFAULT_SUPABASE_URL

def ping_streamlit():
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pinging Streamlit Cloud app ({STREAMLIT_URL})...")
    cj = http.cookiejar.CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
    opener.addheaders = [
        ("User-Agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    ]
    
    endpoints = [
        f"{STREAMLIT_URL.rstrip('/')}/_stcore/health",
        STREAMLIT_URL
    ]
    
    success = False
    for ep in endpoints:
        try:
            resp = opener.open(ep, timeout=25)
            if resp.status in (200, 302, 303):
                print(f"[OK] Streamlit Cloud pinged successfully ({ep} -> HTTP {resp.status})")
                success = True
        except Exception as e:
            print(f"[WARNING] Streamlit ping failed for {ep}: {e}")
            
    return success

def ping_supabase():
    try:
        import psycopg2
    except ImportError:
        print("[ERROR] psycopg2 is not installed.")
        return False

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pinging Supabase to prevent inactivity pause...")
    
    try:
        conn = psycopg2.connect(ACTIVE_URL, connect_timeout=15)
        conn.autocommit = True
        cur = conn.cursor()
        
        cur.execute("SELECT 1;")
        res = cur.fetchone()
        
        try:
            cur.execute("SELECT count(*) FROM dosyalar;")
            c = cur.fetchone()[0]
            print(f"[OK] Database active! Total cases in database: {c}")
        except Exception:
            print("[OK] Database active! (SELECT 1 succeeded)")
            
        cur.close()
        conn.close()
        print("[SUCCESS] Supabase Keep-Alive ping completed successfully.")
        return True
    except Exception as e:
        print(f"[WARNING] Supabase Keep-Alive ping failed: {e}")
        return False

if __name__ == "__main__":
    st_ok = ping_streamlit()
    sb_ok = ping_supabase()
    print(f"All keep-alive pings finished. Streamlit: {st_ok}, Supabase: {sb_ok}")
