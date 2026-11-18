import os
import sys
from datetime import datetime

# Supabase URL fallback
DEFAULT_SUPABASE_URL = "postgresql://postgres.mngekqtbfbtianfhafja:Fengabes295123.@aws-0-eu-west-1.pooler.supabase.com:6543/postgres?sslmode=require"
ACTIVE_URL = os.environ.get("DATABASE_URL") or DEFAULT_SUPABASE_URL

def ping_supabase():
    try:
        import psycopg2
    except ImportError:
        print("[ERROR] psycopg2 is not installed.")
        sys.exit(1)

    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Pinging Supabase to prevent inactivity pause...")
    
    try:
        conn = psycopg2.connect(ACTIVE_URL, connect_timeout=15)
        conn.autocommit = True
        cur = conn.cursor()
        
        # Simple ping query
        cur.execute("SELECT 1;")
        res = cur.fetchone()
        
        # Check files count if table exists
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
        print(f"[WARNING] Keep-Alive ping failed: {e}")
        # Return false but don't crash with non-zero exit code so workflow doesn't mark as red if Supabase is temporarily restarting
        return False

if __name__ == "__main__":
    ping_supabase()
