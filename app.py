import streamlit as st
import pandas as pd
import sqlite3
from datetime import date, datetime, timedelta
import io
import os
import re
import hashlib
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from faiz_sync import kontrol_et_faiz_guncellemeleri, uygula_faiz_guncellemesi
from udf_parser import parse_udf_file, parse_udf_files, UDF_IL_ILCE

# -------------------------------------------------------------
# 1. GÜVENLİ KULLANICI YÖNETİMİ & ŞİFRELEME (AUTH)
# -------------------------------------------------------------
def make_hashes(password):
    return hashlib.sha256(str.encode(password)).hexdigest()

def check_hashes(password, hashed_text):
    if make_hashes(password) == hashed_text:
        return True
    return False

KULLANICILAR = {
    "Erkut": {
        "ad_soyad": "Av. Erkut",
        "sifre_hash": make_hashes("Betül")
    },
    "Taylan": {
        "ad_soyad": "Av. Taylan",
        "sifre_hash": make_hashes("jus123")
    }
}

# -------------------------------------------------------------
# 2. SAYFA KONFİGÜRASYONU & MODERN KURUMSAL TEMA
# -------------------------------------------------------------
st.set_page_config(
    page_title="Jus Tahsilat Makinesi",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "current_user" not in st.session_state:
    st.session_state["current_user"] = None
if "theme_mode" not in st.session_state:
    st.session_state["theme_mode"] = "Gece Modu"

is_dark = st.session_state["theme_mode"] == "Gece Modu"

if is_dark:
    bg_main = "#0B0F17"
    card_bg = "#111827"
    card_border = "#1F2937"
    text_main = "#F3F4F6"
    text_muted = "#9CA3AF"
    accent_green = "#0D9488"
    accent_dark_green = "#0F766E"
    kpi_bg = "#111827"
    sidebar_bg = "#080C14"
    input_bg = "#111827"
    input_text = "#F3F4F6"
    input_border = "#374151"
    btn_sec_bg = "#1F2937"
    btn_sec_text = "#F3F4F6"
    btn_sec_border = "#374151"
    menu_active_bg = "#0F766E"
    menu_active_text = "#FFFFFF"
else:
    bg_main = "#F8FAFC"
    card_bg = "#FFFFFF"
    card_border = "#E2E8F0"
    text_main = "#0F172A"
    text_muted = "#64748B"
    accent_green = "#0D9488"
    accent_dark_green = "#0F766E"
    kpi_bg = "#FFFFFF"
    sidebar_bg = "#F1F5F9"
    input_bg = "#FFFFFF"
    input_text = "#0F172A"
    input_border = "#CBD5E1"
    btn_sec_bg = "#FFFFFF"
    btn_sec_text = "#334155"
    btn_sec_border = "#CBD5E1"
    menu_active_bg = "#0D9488"
    menu_active_text = "#FFFFFF"

st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    html, body, p, label, li, td, th {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        font-size: 12.5px;
        letter-spacing: -0.1px;
    }}
    span:not([data-testid*="icon"]):not([class*="material"]):not([class*="icon"]):not([data-testid="stIconMaterial"]) {{
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
        font-size: 12.5px;
        letter-spacing: -0.1px;
    }}
    /* Streamlit Material Icon Gliflerini ve Expander Okunu Koruma */
    [data-testid*="icon"], [data-testid="stIconMaterial"], [class*="material-symbols"], [class*="material-icons"] {{
        font-family: 'Material Symbols Rounded', 'Material Symbols Outlined', 'Material Icons', sans-serif !important;
        font-feature-settings: 'liga' 1 !important;
        -webkit-font-feature-settings: 'liga' 1 !important;
        letter-spacing: normal !important;
        text-transform: none !important;
        display: inline-block !important;
        white-space: nowrap !important;
        word-wrap: normal !important;
        direction: ltr !important;
        line-height: 1 !important;
    }}
    [data-testid="stExpander"] details summary {{
        display: flex !important;
        align-items: center !important;
        gap: 8px !important;
    }}
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Inter', -apple-system, sans-serif !important;
        font-weight: 600 !important;
        letter-spacing: -0.3px !important;
        color: {accent_green} !important;
    }}
    h1 {{ font-size: 20px !important; }}
    h2 {{ font-size: 17px !important; margin-bottom: 2px !important; }}
    h3 {{ font-size: 15px !important; }}
    h4 {{ font-size: 14px !important; }}
    h5 {{ font-size: 13px !important; }}
    
    .stApp {{
        background-color: {bg_main} !important;
        color: {text_main} !important;
    }}
    .block-container {{
        padding-top: 1.8rem !important;
        padding-bottom: 2rem !important;
        max-width: 96% !important;
    }}
    section[data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        border-right: 1px solid {card_border} !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label {{
        background-color: {card_bg} !important;
        border: 1px solid {card_border} !important;
        border-radius: 6px !important;
        padding: 6px 10px !important;
        margin-bottom: 4px !important;
        color: {text_main} !important;
        font-weight: 500 !important;
        font-size: 12px !important;
        display: flex !important;
        align-items: center !important;
        transition: all 0.15s ease !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"],
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {{
        background-color: {menu_active_bg} !important;
        border-color: {accent_green} !important;
    }}
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] div,
    section[data-testid="stSidebar"] div[role="radiogroup"] label[data-checked="true"] p,
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) div,
    section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p {{
        color: {menu_active_text} !important;
        font-weight: 600 !important;
    }}
    div[data-testid="metric-container"] {{
        background: {kpi_bg} !important;
        border: 1px solid {card_border} !important;
        padding: 10px 14px !important;
        border-radius: 8px !important;
        box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04) !important;
    }}
    div[data-testid="metric-container"] label {{
        color: {text_muted} !important;
        font-weight: 500 !important;
        font-size: 11px !important;
        text-transform: uppercase;
        letter-spacing: 0.3px;
    }}
    div[data-testid="metric-container"] [data-testid="stMetricValue"] {{
        color: {accent_green} !important;
        font-weight: 700 !important;
        font-size: 18px !important;
    }}
    .search-card {{
        background: {card_bg};
        border: 1px solid {card_border};
        border-radius: 8px;
        padding: 10px 14px;
        margin-bottom: 10px;
    }}
    input, textarea, select {{
        background-color: {input_bg} !important;
        color: {input_text} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
        font-size: 12px !important;
        font-weight: 500 !important;
        padding: 5px 8px !important;
    }}
    div[data-baseweb="select"] > div {{
        background-color: {input_bg} !important;
        color: {input_text} !important;
        border: 1px solid {input_border} !important;
        border-radius: 6px !important;
        font-size: 12px !important;
        min-height: 36px !important;
    }}
    div[data-baseweb="select"] * {{
        color: {input_text} !important;
        font-size: 12px !important;
    }}
    .financial-card {{
        background: {card_bg} !important;
        border-radius: 8px !important;
        border: 1px solid {card_border} !important;
        padding: 14px !important;
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.04) !important;
        margin-bottom: 14px !important;
    }}
    .financial-card-header {{
        display: flex;
        align-items: center;
        justify-content: space-between;
        border-bottom: 1px solid {card_border};
        padding-bottom: 8px;
        margin-bottom: 10px;
    }}
    .financial-row {{
        display: flex;
        justify-content: space-between;
        padding: 5px 0;
        font-size: 11.5px;
        color: {text_muted} !important;
        font-weight: 500;
        border-bottom: 1px solid {card_border};
    }}
    .financial-row strong {{
        color: {text_main} !important;
        font-weight: 600;
        font-size: 12px;
    }}
    .financial-total-box {{
        background: {accent_dark_green} !important;
        border: 1px solid {accent_green} !important;
        border-radius: 6px !important;
        padding: 10px !important;
        text-align: center !important;
        margin-top: 12px !important;
    }}
    .stButton > button {{
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 12px !important;
        padding: 5px 12px !important;
        background-color: {btn_sec_bg} !important;
        color: {btn_sec_text} !important;
        border: 1px solid {btn_sec_border} !important;
        transition: all 0.15s ease !important;
    }}
    .stButton > button:hover {{
        border-color: {accent_green} !important;
        color: {accent_green} !important;
    }}
    .stButton > button[kind="primary"], .stButton > button[data-testid="baseButton-primary"] {{
        background-color: {accent_green} !important;
        color: #FFFFFF !important;
        border: 1px solid {accent_dark_green} !important;
        font-weight: 600 !important;
    }}
    .stButton > button[kind="primary"]:hover, .stButton > button[data-testid="baseButton-primary"]:hover {{
        background-color: {accent_dark_green} !important;
        color: #FFFFFF !important;
    }}
    .stTabs [data-baseweb="tab-list"] {{
        gap: 4px;
        background-color: transparent !important;
        border-bottom: 1px solid {card_border} !important;
    }}
    .stTabs [data-baseweb="tab"] {{
        font-weight: 500 !important;
        font-size: 12px !important;
        border-radius: 6px 6px 0 0 !important;
        padding: 6px 12px !important;
        color: {text_muted} !important;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: {card_bg} !important;
        color: {accent_green} !important;
        border: 1px solid {card_border} !important;
        border-bottom: 2px solid {accent_green} !important;
        font-weight: 600 !important;
    }}
    /* Tablo ve Veri Kompaktlığı */
    div[data-testid="stDataFrame"] {{
        font-size: 11.5px !important;
    }}
</style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 3. GİRİŞ EKRANI (LOGIN PORTAL)
# -------------------------------------------------------------
if not st.session_state["authenticated"]:
    col_bos1, col_form, col_bos2 = st.columns([1, 1.2, 1])
    with col_form:
        st.write("")
        st.write("")
        logo_path = None
        for olasi_ad in ["Minimalist Logo .jpg", "logo.jpg", "logo.png", "Minimalist Logo.jpg"]:
            if os.path.exists(olasi_ad):
                logo_path = olasi_ad
                break

        if logo_path:
            st.image(logo_path, use_container_width=True)
        else:
            st.markdown(f"""
                <div style="text-align: center; padding: 20px; background: {card_bg}; border-radius: 12px; border: 1.5px solid {card_border}; margin-bottom: 20px;">
                    <div style="font-size: 32px; font-weight: 800; letter-spacing: 6px; color: {text_main}; line-height: 1;">
                        J<span style="color: {accent_green};">U</span>S
                    </div>
                    <div style="font-size: 13px; letter-spacing: 5px; font-weight: 800; color: {accent_green}; text-transform: uppercase; margin-top: 6px;">
                        LEGAL
                    </div>
                </div>
            """, unsafe_allow_html=True)

        st.markdown(f"""
            <div style="text-align: center; margin-bottom: 25px;">
                <h2 style="margin: 0; color: {accent_green}; font-weight: 800; font-size: 24px;">Jus Tahsilat Makinesi</h2>
                <p style="margin: 4px 0 0 0; color: {text_muted}; font-size: 13px; font-weight: 600; text-transform: uppercase;">
                    Güvenli Ofis Giriş Portalı
                </p>
            </div>
        """, unsafe_allow_html=True)

        with st.form("login_form"):
            secilen_kullanici = st.selectbox("Avukat / Kullanıcı Seçimi", list(KULLANICILAR.keys()))
            girilen_sifre = st.text_input("Giriş Şifresi", type="password", placeholder="Şifrenizi giriniz")
            giris_btn = st.form_submit_button("Oturum Aç", type="primary", use_container_width=True)

            if giris_btn:
                if secilen_kullanici in KULLANICILAR:
                    dogru_hash = KULLANICILAR[secilen_kullanici]["sifre_hash"]
                    if check_hashes(girilen_sifre, dogru_hash):
                        st.session_state["authenticated"] = True
                        st.session_state["current_user"] = KULLANICILAR[secilen_kullanici]["ad_soyad"]
                        st.success(f"Hoş geldiniz, {st.session_state['current_user']}!")
                        st.rerun()
                    else:
                        st.error("Hatalı şifre girdiniz. Lütfen tekrar deneyin.")

        st.caption("🔒 Tüm oturum hareketleri SHA-256 güvenlik protokolü ile şifrelenmektedir.")
    st.stop()

# -------------------------------------------------------------
# 4. TÜRK LİRASI & HESAPLAMA MOTORLARI
# -------------------------------------------------------------
def parse_tr_money(val_str):
    if not val_str:
        return 0.0
    s = str(val_str).strip().replace("TL", "").replace("-", "").strip()
    s = s.replace(".", "").replace(",", ".")
    try:
        return float(s)
    except Exception:
        return 0.0

def format_tr_money(amount):
    if amount is None:
        amount = 0.0
    formatted = f"{float(amount):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{formatted}-TL"

def hesapla_icra_vekalet_ucreti(takip_cikisi):
    if takip_cikisi <= 0:
        return 0.0
    basamaklar = [
        (600000.0, 0.16),
        (600000.0, 0.15),
        (1200000.0, 0.14),
        (1200000.0, 0.13),
        (1800000.0, 0.11),
        (2400000.0, 0.08),
        (3000000.0, 0.05),
        (3600000.0, 0.03),
        (4200000.0, 0.02),
        (float('inf'), 0.01)
    ]
    kalan = float(takip_cikisi)
    nisbi = 0.0
    for dilim, oran in basamaklar:
        if kalan <= 0:
            break
        hesaplanan = min(kalan, dilim)
        nisbi += hesaplanan * oran
        kalan -= hesaplanan
    maktu = 9000.0
    vekalet = max(nisbi, maktu)
    if vekalet > takip_cikisi:
        vekalet = takip_cikisi
    return round(vekalet, 2)

FAIZ_TURLERI_LISTESI = [
    "Ticari Avans Faizi (%48.00)",
    "TCMB Reeskont Faizi (%39.75)",
    "Yasal Faiz (%31.00)",
    "Özel Oran",
    "Faizsiz"
]

def get_faiz_default_rate(faiz_turu_str):
    if not faiz_turu_str:
        return 48.00
    s = str(faiz_turu_str)
    if "Reeskont" in s:
        return 39.75
    elif "Ticari Avans" in s or "Avans" in s:
        return 48.00
    elif "Yasal Faiz" in s:
        return 31.00
    elif "Faizsiz" in s:
        return 0.0
    return 30.0

@st.cache_data(ttl=600)
def get_faiz_oranlari_list(faiz_turu_adi):
    if not faiz_turu_adi:
        return []
    sorgu_turu = None
    if "Reeskont" in faiz_turu_adi:
        sorgu_turu = "Reeskont Faizi"
    elif "Ticari Avans" in faiz_turu_adi or "Avans" in faiz_turu_adi:
        sorgu_turu = "Ticari Avans Faizi"
    elif "Yasal Faiz" in faiz_turu_adi:
        sorgu_turu = "Yasal Faiz"
    if not sorgu_turu:
        return []
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT baslangic_tarihi, bitis_tarihi, oran 
            FROM faiz_oranlari 
            WHERE faiz_turu = ? 
            ORDER BY baslangic_tarihi ASC
        """, (sorgu_turu,))
        rows = cur.fetchall()
        liste = []
        for b_str, e_str, o in rows:
            b_d = datetime.strptime(b_str, "%Y-%m-%d").date()
            e_d = datetime.strptime(e_str, "%Y-%m-%d").date()
            liste.append((b_d, e_d, float(o)))
        return liste
    except Exception:
        return []

@st.cache_data(ttl=60)
def get_cached_taraflar_list():
    try:
        return pd.read_sql_query("SELECT ad_unvan FROM taraflar ORDER BY ad_unvan", conn)['ad_unvan'].tolist()
    except Exception:
        return []

def check_existing_dosya(db_cursor, il, ilce, daire, secilen_yil, esas_sira_no):
    """
    Belirtilen il, ilçe, icra dairesi ve dosya/esas numarasına göre sistemde
    mükerrer dosya bulunup bulunmadığını denetler.
    Bulursa sözlük olarak dosya bilgilerini döndürür, bulamazsa None döner.
    """
    if not esas_sira_no or not str(esas_sira_no).strip():
        return None
    sira_raw = str(esas_sira_no).strip()
    clean_sira = re.sub(r'[^0-9]', '', sira_raw)
    yil = str(secilen_yil).strip() if secilen_yil else "2026"

    patterns = set()
    if clean_sira:
        patterns.add(f"{yil}/{clean_sira} E.")
        patterns.add(f"{yil}/{clean_sira}")
        patterns.add(f"{yil}/{clean_sira} E")
    patterns.add(f"{yil}/{sira_raw} E.")
    patterns.add(f"{yil}/{sira_raw}")
    if sira_raw.endswith(" E.") or sira_raw.endswith(" E"):
        patterns.add(sira_raw)

    m_esas = re.search(r'(?:(\d{4})[/_])?(\d+)', sira_raw)
    if m_esas:
        ext_yil = m_esas.group(1) or yil
        ext_sira = m_esas.group(2)
        patterns.add(f"{ext_yil}/{ext_sira} E.")
        patterns.add(f"{ext_yil}/{ext_sira}")
    
    pat_list = list(patterns)
    placeholders = ", ".join(["?"] * len(pat_list))
    sql = f"""
        SELECT id, il, ilce, icra_dairesi, dosya_no, alacakli, borclu, takip_tarihi, ana_para, takip_cikisi
        FROM dosyalar
        WHERE il = ? AND icra_dairesi = ? AND dosya_no IN ({placeholders})
    """
    params = [il, daire] + pat_list
    try:
        db_cursor.execute(sql, params)
        rows = db_cursor.fetchall()
        for r in rows:
            r_ilce = r[2] or "Merkez"
            # İstanbul'da adliye ayrımı (Çağlayan vs Anadolu) ilçe üzerinden yapılır
            if il == "İstanbul":
                if r_ilce == ilce:
                    return {
                        "id": r[0], "il": r[1], "ilce": r[2], "icra_dairesi": r[3],
                        "dosya_no": r[4], "alacakli": r[5], "borclu": r[6],
                        "takip_tarihi": r[7], "ana_para": r[8], "takip_cikisi": r[9]
                    }
            else:
                if ilce == "Merkez" or r_ilce == "Merkez" or r_ilce == ilce:
                    return {
                        "id": r[0], "il": r[1], "ilce": r[2], "icra_dairesi": r[3],
                        "dosya_no": r[4], "alacakli": r[5], "borclu": r[6],
                        "takip_tarihi": r[7], "ana_para": r[8], "takip_cikisi": r[9]
                    }
    except Exception as e:
        print(f"check_existing_dosya hatası: {e}")
    return None

def hesapla_aralik_faizi(principal, start_date, end_date, faiz_turu, sabit_oran):
    if principal <= 0 or start_date >= end_date:
        return 0.0
    
    if "Faizsiz" in str(faiz_turu):
        return 0.0

    sabit_oran = float(sabit_oran) if sabit_oran is not None else 0.0
    std_def = get_faiz_default_rate(faiz_turu)
    dilimler = get_faiz_oranlari_list(faiz_turu)
    
    # Eğer dilim yoksa veya Özel Oran ise veya kullanıcı bilinçli olarak standart orandan farklı bir oran girdiyse:
    if not dilimler or faiz_turu == "Özel Oran" or (abs(sabit_oran - std_def) > 0.05 and sabit_oran > 0):
        gun = (end_date - start_date).days
        if gun > 0:
            return (principal * (sabit_oran / 100.0) * gun) / 365.0
        return 0.0
    
    toplam_faiz = 0.0
    cur_s = start_date
    while cur_s < end_date:
        eslesen_oran = float(sabit_oran)
        next_boundary = end_date
        for b_d, e_d, o in dilimler:
            if b_d <= cur_s <= e_d:
                eslesen_oran = o
                try:
                    next_boundary = min(end_date, e_d + timedelta(days=1))
                except Exception:
                    next_boundary = end_date
                break
        
        days_in_chunk = (next_boundary - cur_s).days
        if days_in_chunk > 0:
            toplam_faiz += (principal * (eslesen_oran / 100.0) * days_in_chunk) / 365.0
            cur_s = next_boundary
        else:
            cur_s = cur_s + timedelta(days=1)
            
    return toplam_faiz

def hesapla_kademeli_dosya_hesabi(ana_para, faiz_orani, takip_tarihi_str, t_oncesi_faiz, tahsilatlar_df, hesap_tarihi=None, faiz_turu="Özel Oran", masraflar_df=None, alacak_kalemleri_df=None):
    if hesap_tarihi is None:
        hesap_tarihi = date.today()
    cur_date = datetime.strptime(str(takip_tarihi_str), "%Y-%m-%d").date()
    
    # Çoklu alacak kalemleri kontrolü
    has_custom_items = alacak_kalemleri_df is not None and not alacak_kalemleri_df.empty
    if has_custom_items:
        items = []
        for _, itm in alacak_kalemleri_df.iterrows():
            items.append({
                "adi": itm.get("kalem_adi", "Alacak"),
                "principal": float(itm.get("tutar", 0.0)),
                "pre_interest": float(itm.get("t_oncesi_faiz", 0.0)),
                "post_interest": 0.0,
                "faiz_turu": itm.get("faiz_turu", faiz_turu),
                "faiz_orani": float(itm.get("faiz_orani", faiz_orani))
            })
    else:
        items = [{
            "adi": "Asıl Alacak",
            "principal": float(ana_para),
            "pre_interest": float(t_oncesi_faiz),
            "post_interest": 0.0,
            "faiz_turu": faiz_turu,
            "faiz_orani": float(faiz_orani)
        }]

    # Olay günlüğü (kronolojik: tahsilat ve masraflar)
    events = []
    if tahsilatlar_df is not None and not tahsilatlar_df.empty:
        for _, row in tahsilatlar_df.iterrows():
            t_val = row.get('tarih') if hasattr(row, 'get') else (row['tarih'] if 'tarih' in row else None)
            if t_val and pd.notnull(t_val):
                try:
                    p_d = datetime.strptime(str(t_val)[:10], "%Y-%m-%d").date()
                except Exception:
                    p_d = cur_date
            else:
                p_d = cur_date
            if p_d <= hesap_tarihi:
                events.append({
                    "type": "payment",
                    "date": p_d,
                    "amount": float(row.get('tutar', 0.0) if hasattr(row, 'get') else row['tutar']),
                    "desc": str(row.get('aciklama', '') if hasattr(row, 'get') else (row['aciklama'] if 'aciklama' in row else '')),
                    "id": row.get('id', 0) if hasattr(row, 'get') else 0
                })

    # Masraflar takibi (TBK 100 gereği vadesi gelmiş masraflar tahsilattan düşülür)
    masraf_records = []
    if masraflar_df is not None and not masraflar_df.empty:
        for _, m_row in masraflar_df.iterrows():
            m_t_val = m_row.get('tarih') if hasattr(m_row, 'get') else (m_row['tarih'] if 'tarih' in m_row else None)
            if m_t_val and pd.notnull(m_t_val):
                try:
                    m_d = datetime.strptime(str(m_t_val)[:10], "%Y-%m-%d").date()
                except Exception:
                    m_d = cur_date
            else:
                m_d = cur_date
            net_m = float(m_row.get('masraf_tutari', 0.0) if hasattr(m_row, 'get') else m_row['masraf_tutari']) - float(m_row.get('iade_tutari', 0.0) if hasattr(m_row, 'get') else (m_row['iade_tutari'] if 'iade_tutari' in m_row else 0.0))
            if m_d <= hesap_tarihi:
                masraf_records.append({"date": m_d, "amount": net_m})

    # Tarihe göre sıralı olay akışı
    events = sorted(events, key=lambda x: x["date"])
    
    toplam_tahsilat = 0.0
    mahsup_gecmisi = []

    def get_unpaid_masraf_up_to(dt):
        return sum(m["amount"] for m in masraf_records if m["date"] <= dt)

    masraf_paid_total = 0.0

    for ev in events:
        ev_date = ev["date"]
        # cur_date'den ev_date'e kadar faiz işlet
        if ev_date > cur_date:
            for itm in items:
                if itm["principal"] > 0:
                    acc = hesapla_aralik_faizi(itm["principal"], cur_date, ev_date, itm["faiz_turu"], itm["faiz_orani"])
                    itm["post_interest"] += acc
            cur_date = ev_date

        pay_amount = ev["amount"]
        toplam_tahsilat += pay_amount
        rem_pay = pay_amount

        # 1. Aşama TBK 100: Vadesi gelmiş net masraflara mahsup
        masraf_due = max(0.0, get_unpaid_masraf_up_to(ev_date) - masraf_paid_total)
        paid_masraf = min(rem_pay, masraf_due)
        rem_pay -= paid_masraf
        masraf_paid_total += paid_masraf

        # 2. Aşama TBK 100: Önce takip öncesi faize, sonra takip sonrası faize mahsup
        paid_interest = 0.0
        
        # 2a. Takip Öncesi Faize Mahsup
        total_curr_pre = sum(itm["pre_interest"] for itm in items)
        if total_curr_pre > 0 and rem_pay > 0:
            take_pre = min(rem_pay, total_curr_pre)
            paid_interest += take_pre
            rem_pay -= take_pre
            ded = take_pre
            for itm in items:
                if ded <= 0:
                    break
                t = min(itm["pre_interest"], ded)
                itm["pre_interest"] -= t
                ded -= t

        # 2b. Takip Sonrası Faize Mahsup
        total_curr_post = sum(itm["post_interest"] for itm in items)
        if total_curr_post > 0 and rem_pay > 0:
            take_post = min(rem_pay, total_curr_post)
            paid_interest += take_post
            rem_pay -= take_post
            ded = take_post
            for itm in items:
                if ded <= 0:
                    break
                t = min(itm["post_interest"], ded)
                itm["post_interest"] -= t
                ded -= t

        # 3. Aşama TBK 100: Kalan tutar asıl alacağa (ana paraya) mahsup
        paid_principal = 0.0
        total_curr_principal = sum(itm["principal"] for itm in items)
        if total_curr_principal > 0 and rem_pay > 0:
            paid_principal = min(rem_pay, total_curr_principal)
            rem_pay -= paid_principal
            ded_p = paid_principal
            for itm in items:
                if ded_p <= 0:
                    break
                take = min(itm["principal"], ded_p)
                itm["principal"] -= take
                ded_p -= take

        curr_p_sum = sum(itm["principal"] for itm in items)
        curr_i_sum = sum(itm["pre_interest"] + itm["post_interest"] for itm in items)

        mahsup_gecmisi.append({
            "ID": ev.get("id", 0),
            "Tarih": str(ev_date),
            "Tahsil Edilen": format_tr_money(pay_amount),
            "Masrafa Mahsup": format_tr_money(paid_masraf),
            "Faize Mahsup": format_tr_money(paid_interest),
            "Ana Paraya Mahsup": format_tr_money(paid_principal),
            "Kalan Ana Para": format_tr_money(curr_p_sum),
            "Kalan Faiz": format_tr_money(curr_i_sum),
            "Açıklama": ev.get("desc", "")
        })

    # Son tahsilattan bugüne (hesap tarihine) kadar faiz işlet
    if hesap_tarihi > cur_date:
        for itm in items:
            if itm["principal"] > 0:
                acc = hesapla_aralik_faizi(itm["principal"], cur_date, hesap_tarihi, itm["faiz_turu"], itm["faiz_orani"])
                itm["post_interest"] += acc

    final_principal = sum(itm["principal"] for itm in items)
    final_pre_interest = sum(itm["pre_interest"] for itm in items)
    final_post_interest = sum(itm["post_interest"] for itm in items)
    final_total_interest = final_pre_interest + final_post_interest

    return round(final_principal, 2), round(final_total_interest, 2), round(toplam_tahsilat, 2), mahsup_gecmisi, round(final_pre_interest, 2), round(final_post_interest, 2)

# -------------------------------------------------------------
# 5. TEK DOSYA İÇİN EXECUTIVE EXCEL OLUŞTURUCU
# -------------------------------------------------------------
def build_executive_excel(dosya_data, mahsup_list, masraf_df, notlar_df, secenekler):
    wb = openpyxl.Workbook()
    
    fill_header = PatternFill(start_color="084840", end_color="084840", fill_type="solid")
    fill_sub = PatternFill(start_color="1F2421", end_color="1F2421", fill_type="solid")
    fill_zebra = PatternFill(start_color="F4F6F5", end_color="F4F6F5", fill_type="solid")
    fill_total = PatternFill(start_color="084840", end_color="084840", fill_type="solid")

    font_title = Font(name="Arial", size=13, bold=True, color="FFFFFF")
    font_sub_title = Font(name="Arial", size=10, bold=True, color="FFFFFF")
    font_bold = Font(name="Arial", size=10, bold=True, color="000000")
    font_regular = Font(name="Arial", size=10, color="000000")
    font_total = Font(name="Arial", size=11, bold=True, color="FFFFFF")

    thin_border = Border(
        left=Side(style='thin', color='D1D5DB'), right=Side(style='thin', color='D1D5DB'),
        top=Side(style='thin', color='D1D5DB'), bottom=Side(style='thin', color='D1D5DB')
    )

    ws1 = wb.active
    ws1.title = "Dosya Hesap Cetveli"
    ws1.views.sheetView[0].showGridLines = True

    ws1.merge_cells("A1:E1")
    ws1["A1"] = "JUS LEGAL | İCRA DOSYA HESAP CETVELİ VE RAPORU"
    ws1["A1"].font = font_title
    ws1["A1"].fill = fill_header
    ws1["A1"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[1].height = 36

    ws1.merge_cells("A2:E2")
    ws1["A2"] = f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y')} | Dosya: {dosya_data['icra_dairesi']} {dosya_data['dosya_no']}"
    ws1["A2"].font = Font(name="Arial", size=9, italic=True, color="334155")
    ws1["A2"].alignment = Alignment(horizontal="center", vertical="center")
    ws1.row_dimensions[2].height = 20

    row_idx = 4
    if secenekler.get("genel", True):
        ws1.merge_cells(f"A{row_idx}:E{row_idx}")
        ws1[f"A{row_idx}"] = "1. DOSYA VE TARAF BİLGİLERİ"
        ws1[f"A{row_idx}"].font = font_sub_title
        ws1[f"A{row_idx}"].fill = fill_sub
        ws1.row_dimensions[row_idx].height = 24
        row_idx += 1

        taraf_bilgileri = [
            ("Alacaklı (Müvekkil):", dosya_data['alacakli'], "İcra Dairesi:", dosya_data['icra_dairesi']),
            ("Borçlu Firma / Kişiler:", dosya_data['borclu'], "Dosya / Esas No:", dosya_data['dosya_no']),
            ("İcra Takip Türü:", dosya_data['takip_turu'], "Takip Açılış Tarihi:", str(dosya_data['takip_tarihi'])),
            ("Dosya İlerleme Statüsü:", dosya_data['durum'], "İtiraz Durumu:", dosya_data['İtiraz'])
        ]

        for b_sol, v_sol, b_sag, v_sag in taraf_bilgileri:
            ws1[f"A{row_idx}"] = b_sol
            ws1[f"A{row_idx}"].font = font_bold
            ws1[f"B{row_idx}"] = v_sol
            ws1[f"B{row_idx}"].font = font_regular
            ws1[f"C{row_idx}"] = ""
            ws1[f"D{row_idx}"] = b_sag
            ws1[f"D{row_idx}"].font = font_bold
            ws1[f"E{row_idx}"] = v_sag
            ws1[f"E{row_idx}"].font = font_regular
            for col_letter in ["A", "B", "C", "D", "E"]:
                ws1[f"{col_letter}{row_idx}"].border = thin_border
            ws1.row_dimensions[row_idx].height = 20
            row_idx += 1
        row_idx += 1

    if secenekler.get("finans", True):
        ws1.merge_cells(f"A{row_idx}:E{row_idx}")
        ws1[f"A{row_idx}"] = "2. MALİ HESAP CETVELİ (BAKİYE DÖKÜMÜ)"
        ws1[f"A{row_idx}"].font = font_sub_title
        ws1[f"A{row_idx}"].fill = fill_sub
        ws1.row_dimensions[row_idx].height = 24
        row_idx += 1

        mali_kalemler = [
            ("Açılış Asıl Alacak (İlk Ana Para)", dosya_data['ana_para'], "Takip talebindeki asıl alacak tutarı"),
            ("Kalan Takip Öncesi Faiz", dosya_data.get('rem_pre_i', dosya_data['t_oncesi_faiz']), "Kalan takip öncesi faiz bakiyesi"),
            ("Takip Çıkış Tutarı", dosya_data['takip_cikisi'], "Harç ve vekalet ücretine esas takip açılışı"),
            ("Sabit İcra Vekalet Ücreti", dosya_data['vekalet_ucreti'], "2026 TBB Asgari Avukatlık Ücret Tarifesi"),
            (f"Takip Sonrası İşlemiş Faiz (%{dosya_data['faiz_orani']})", dosya_data.get('rem_post_i', dosya_data['rem_i']), "Takip tarihinden bugüne kadar işlemiş faiz"),
            ("Kalan Asıl Alacak", dosya_data['rem_p'], "Tahsilatlar sonrası kalan net ana para"),
            ("Toplam Yapılan İcra Masrafları", dosya_data['top_masraf'], "Yargılama ve takip masrafları"),
            ("İcra İadeleri (-)", -dosya_data['top_iade'], "İade edilen harç ve avanslar"),
            ("Net Masraf Bakiyesi", dosya_data['net_masraf'], "Dosyaya eklenen net masraf yükü"),
            (f"İcra Tahsil Harcı (%{dosya_data.get('tahsil_harci_orani', 9.10):.2f})", dosya_data['tahsil_harci'], f"Safha: {dosya_data.get('tahsil_harci_safhasi', 'Standart')}"),
            (f"Cezaevi Harcı (%{dosya_data.get('cezaevi_harci_orani', 2.00):.2f})", dosya_data['cezaevi_harci'], "Takip çıkışı üzerinden kanuni harç"),
            ("Toplam Tahsil Edilen Tutar (-)", -dosya_data['tot_pay'], "Borçludan bugüne kadar tahsil edilen")
        ]

        ws1[f"A{row_idx}"] = "Hesap Kalemi"
        ws1[f"B{row_idx}"] = "Açıklama / Yasal Dayanak"
        ws1[f"C{row_idx}"] = ""
        ws1[f"D{row_idx}"] = "Tutar (TL)"
        ws1[f"E{row_idx}"] = "Yön"
        ws1.merge_cells(f"B{row_idx}:C{row_idx}")
        for col_letter in ["A", "B", "C", "D", "E"]:
            ws1[f"{col_letter}{row_idx}"].fill = fill_zebra
            ws1[f"{col_letter}{row_idx}"].font = font_bold
            ws1[f"{col_letter}{row_idx}"].border = thin_border
        row_idx += 1

        for idx, (kalem, tutar, aciklama) in enumerate(mali_kalemler):
            ws1[f"A{row_idx}"] = kalem
            ws1[f"B{row_idx}"] = aciklama
            ws1[f"C{row_idx}"] = ""
            ws1.merge_cells(f"B{row_idx}:C{row_idx}")
            ws1[f"D{row_idx}"] = tutar
            ws1[f"E{row_idx}"] = "(-) Mahsup" if tutar < 0 else "(+) Borç"
            
            ws1[f"A{row_idx}"].font = font_regular
            ws1[f"B{row_idx}"].font = Font(name="Arial", size=9, color="4B5563")
            ws1[f"D{row_idx}"].font = font_bold
            ws1[f"D{row_idx}"].number_format = '#,##0.00 "TL"'
            ws1[f"D{row_idx}"].alignment = Alignment(horizontal="right")
            ws1[f"E{row_idx}"].alignment = Alignment(horizontal="center")

            fill_row = fill_zebra if idx % 2 == 1 else PatternFill(fill_type=None)
            for col_letter in ["A", "B", "C", "D", "E"]:
                if fill_row.fill_type:
                    ws1[f"{col_letter}{row_idx}"].fill = fill_row
                ws1[f"{col_letter}{row_idx}"].border = thin_border
            ws1.row_dimensions[row_idx].height = 20
            row_idx += 1

        ws1[f"A{row_idx}"] = "GÜNCEL TOPLAM DOSYA BORCU (HARÇLAR DAHİL)"
        ws1.merge_cells(f"A{row_idx}:C{row_idx}")
        ws1[f"D{row_idx}"] = dosya_data['kalan_toplam_dosya_borcu']
        ws1[f"E{row_idx}"] = "BAKİYE"
        
        for col_letter in ["A", "B", "C", "D", "E"]:
            ws1[f"{col_letter}{row_idx}"].fill = fill_total
            ws1[f"{col_letter}{row_idx}"].font = font_total
            ws1[f"{col_letter}{row_idx}"].border = thin_border
        ws1[f"D{row_idx}"].number_format = '#,##0.00 "TL"'
        ws1[f"D{row_idx}"].alignment = Alignment(horizontal="right")
        ws1[f"E{row_idx}"].alignment = Alignment(horizontal="center")
        ws1.row_dimensions[row_idx].height = 28

    col_widths = {"A": 36, "B": 28, "C": 18, "D": 22, "E": 14}
    for c_letter, w in col_widths.items():
        ws1.column_dimensions[c_letter].width = w

    if secenekler.get("tahsilat", True) and mahsup_list:
        ws2 = wb.create_sheet("Tahsilat Mahsup")
        ws2.views.sheetView[0].showGridLines = True
        ws2.merge_cells("A1:H1")
        ws2["A1"] = f"TAHSİLAT VE MAHSUP TABLOSU (TBK m. 100) | {dosya_data['dosya_no']}"
        ws2["A1"].font = font_title
        ws2["A1"].fill = fill_header
        ws2["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws2.row_dimensions[1].height = 32

        headers_t = ["İşlem ID", "Ödeme Tarihi", "Tahsil Edilen", "Masrafa Mahsup", "Faize Mahsup", "Ana Paraya Mahsup", "Kalan Ana Para", "Açıklama"]
        for c_i, h_txt in enumerate(headers_t, start=1):
            cell = ws2.cell(row=3, column=c_i, value=h_txt)
            cell.font = font_sub_title
            cell.fill = fill_sub
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
        ws2.row_dimensions[3].height = 24

        for r_i, item in enumerate(mahsup_list, start=4):
            ws2.cell(row=r_i, column=1, value=item.get("ID", "")).alignment = Alignment(horizontal="center")
            ws2.cell(row=r_i, column=2, value=item.get("Tarih", "")).alignment = Alignment(horizontal="center")
            ws2.cell(row=r_i, column=3, value=item.get("Tahsil Edilen", "")).alignment = Alignment(horizontal="right")
            ws2.cell(row=r_i, column=4, value=item.get("Masrafa Mahsup", "0,00-TL")).alignment = Alignment(horizontal="right")
            ws2.cell(row=r_i, column=5, value=item.get("Faize Mahsup", "")).alignment = Alignment(horizontal="right")
            ws2.cell(row=r_i, column=6, value=item.get("Ana Paraya Mahsup", "")).alignment = Alignment(horizontal="right")
            ws2.cell(row=r_i, column=7, value=item.get("Kalan Ana Para", "")).alignment = Alignment(horizontal="right")
            ws2.cell(row=r_i, column=8, value=item.get("Açıklama", "")).alignment = Alignment(horizontal="left")
            
            for c_i in range(1, 9):
                c_cell = ws2.cell(row=r_i, column=c_i)
                c_cell.font = font_regular
                c_cell.border = thin_border
                if r_i % 2 == 1:
                    c_cell.fill = fill_zebra
            ws2.row_dimensions[r_i].height = 20

        for col in ws2.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws2.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 14)

    if secenekler.get("masraf", True) and not masraf_df.empty:
        ws3 = wb.create_sheet("Masraflar")
        ws3.views.sheetView[0].showGridLines = True
        ws3.merge_cells("A1:D1")
        ws3["A1"] = f"İCRA MASRAF VE İADE HAREKETLERİ | {dosya_data['dosya_no']}"
        ws3["A1"].font = font_title
        ws3["A1"].fill = fill_header
        ws3["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws3.row_dimensions[1].height = 32

        headers_m = ["İşlem Tarihi", "Açıklama", "Yapılan Masraf (TL)", "İade Alınan (TL)"]
        for c_i, h_txt in enumerate(headers_m, start=1):
            cell = ws3.cell(row=3, column=c_i, value=h_txt)
            cell.font = font_sub_title
            cell.fill = fill_sub
            cell.alignment = Alignment(horizontal="center", vertical="center")
            cell.border = thin_border
        ws3.row_dimensions[3].height = 24

        for r_i, (_, m_row) in enumerate(masraf_df.iterrows(), start=4):
            ws3.cell(row=r_i, column=1, value=str(m_row['tarih'])).alignment = Alignment(horizontal="center")
            ws3.cell(row=r_i, column=2, value=str(m_row['aciklama'])).alignment = Alignment(horizontal="left")
            c_m = ws3.cell(row=r_i, column=3, value=float(m_row['masraf_tutari']))
            c_m.number_format = '#,##0.00 "TL"'
            c_m.alignment = Alignment(horizontal="right")
            c_i = ws3.cell(row=r_i, column=4, value=float(m_row['iade_tutari']))
            c_i.number_format = '#,##0.00 "TL"'
            c_i.alignment = Alignment(horizontal="right")

            for c_col in range(1, 5):
                c_cell = ws3.cell(row=r_i, column=c_col)
                c_cell.font = font_regular
                c_cell.border = thin_border
                if r_i % 2 == 1:
                    c_cell.fill = fill_zebra
            ws3.row_dimensions[r_i].height = 20

        for col in ws3.columns:
            max_len = max(len(str(cell.value or '')) for cell in col)
            ws3.column_dimensions[get_column_letter(col[0].column)].width = max(max_len + 4, 16)

    if secenekler.get("notlar", True) and not notlar_df.empty:
        ws4 = wb.create_sheet("Notlar")
        ws4.views.sheetView[0].showGridLines = True
        ws4.merge_cells("A1:B1")
        ws4["A1"] = f"DOSYA İŞLEM VE GÖRÜŞME NOTLARI | {dosya_data['dosya_no']}"
        ws4["A1"].font = font_title
        ws4["A1"].fill = fill_header
        ws4["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws4.row_dimensions[1].height = 32

        ws4.cell(row=3, column=1, value="Tarih").fill = fill_sub
        ws4.cell(row=3, column=1).font = font_sub_title
        ws4.cell(row=3, column=1).alignment = Alignment(horizontal="center", vertical="center")
        ws4.cell(row=3, column=1).border = thin_border

        ws4.cell(row=3, column=2, value="Görüşme / İşlem Notu Detayı").fill = fill_sub
        ws4.cell(row=3, column=2).font = font_sub_title
        ws4.cell(row=3, column=2).alignment = Alignment(horizontal="left", vertical="center")
        ws4.cell(row=3, column=2).border = thin_border
        ws4.row_dimensions[3].height = 24

        for r_i, (_, n_row) in enumerate(notlar_df.iterrows(), start=4):
            c_t = ws4.cell(row=r_i, column=1, value=str(n_row['tarih']))
            c_t.alignment = Alignment(horizontal="center", vertical="top")
            c_n = ws4.cell(row=r_i, column=2, value=str(n_row['not_icerik']))
            c_n.alignment = Alignment(horizontal="left", wrap_text=True)
            
            c_t.font = font_bold
            c_n.font = font_regular
            c_t.border = thin_border
            c_n.border = thin_border
            if r_i % 2 == 1:
                c_t.fill = fill_zebra
                c_n.fill = fill_zebra
            ws4.row_dimensions[r_i].height = 32

        ws4.column_dimensions["A"].width = 16
        ws4.column_dimensions["B"].width = 80

    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    return output

# -------------------------------------------------------------
# 6. VERİTABANI VE KURULUM
# -------------------------------------------------------------
TURKIYE_IL_ILCE = UDF_IL_ILCE
ICRA_DAIRE_LISTESI = ["İcra Dairesi", "İcra Müdürlüğü", "Genel İcra Dairesi"] + [f"{i}. İcra Dairesi" for i in range(1, 100)] + [f"{i}. İcra Müdürlüğü" for i in range(1, 100)] + [f"{i}. İflas Dairesi" for i in range(1, 10)]
YILLAR_LISTESI = [str(y) for y in range(2000, 2051)]
TAKIP_TURLERI = [
    "Örnek No: 7 (İlamsız Takip - Para/Teminat)",
    "Örnek No: 4-5 (İlamlı Takip - Para/Teminat)",
    "Örnek No: 10 (Kambiyo Senetleri - Çek/Bono/Poliçe)",
    "Örnek No: 13 (Kira Borcu ve Tahliye Talepli)",
    "Örnek No: 14 (Tahliye Taahhüdüne Dayalı)",
    "Örnek No: 1 (İflas Yolu)",
    "Örnek No: 6 (İpotek/Rehin - İlamlı)",
    "Örnek No: 8 (İpotek/Rehin - İlamsız)",
    "Diğer Takip Yolu"
]

TAHSIL_HARCI_SECENEKLERI = {
    "Ödeme Emri Tebliğinden Sonra, Hacizden Önce (%9.10)": 9.10,
    "Hacizden Sonra, Satıştan Önce (%9.10)": 9.10,
    "Ödeme Emri Tebliğinden Önce (%4.55)": 4.55,
    "Satıştan Sonra / Paraya Çevrilerek (%11.38)": 11.38,
    "Hacizden Evvel Takipten Vazgeçme / Feragat (%2.275)": 2.275,
    "Hacizden Sonra Takipten Vazgeçme / Feragat (%4.55)": 4.55,
    "Satıştan Sonra Takipten Vazgeçme / Feragat (%5.69)": 5.69,
    "Harçtan Muaf (%0.00)": 0.0,
    "Özel Oran Girilsin": -1.0
}

CEZAEVI_HARCI_SECENEKLERI = {
    "Standart Cezaevi Harcı (%2.00)": 2.00,
    "Cezaevi Harcından Muaf (%0.00)": 0.0
}

from db_manager import conn, cursor, IntegrityError, DB_STATUS, DB_ERROR, IS_POSTGRES

def init_sqlite_tables_if_needed():
    if IS_POSTGRES:
        return
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS taraflar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        tip TEXT,
        ad_unvan TEXT UNIQUE,
        tc_vkn TEXT,
        vergi_dairesi TEXT,
        telefon TEXT,
        adres TEXT
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dosyalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        il TEXT,
        ilce TEXT,
        icra_dairesi TEXT,
        dosya_no TEXT,
        alacakli TEXT,
        borclu TEXT,
        takip_turu TEXT DEFAULT 'Örnek No: 7 (İlamsız Takip - Para/Teminat)',
        takip_tarihi TEXT,
        ana_para REAL DEFAULT 0,
        t_oncesi_faiz REAL DEFAULT 0,
        takip_cikisi REAL DEFAULT 0,
        vekalet_ucreti REAL DEFAULT 0,
        faiz_turu TEXT,
        faiz_orani REAL DEFAULT 0,
        itiraz_edildi INTEGER DEFAULT 0,
        kesinlesme_durumu INTEGER DEFAULT 0,
        durum TEXT DEFAULT 'Açık',
        tahsil_harci_safhasi TEXT DEFAULT 'Ödeme Emri Tebliğinden Sonra, Hacizden Önce (%9.10)',
        tahsil_harci_orani REAL DEFAULT 9.10,
        cezaevi_harci_orani REAL DEFAULT 2.00
    )
    """)
    cursor.execute("PRAGMA table_info(dosyalar)")
    mevcut_kolonlar = [row[1] for row in cursor.fetchall()]
    if "takip_turu" not in mevcut_kolonlar:
        try:
            cursor.execute("ALTER TABLE dosyalar ADD COLUMN takip_turu TEXT DEFAULT 'Örnek No: 7 (İlamsız Takip - Para/Teminat)'")
            conn.commit()
        except Exception:
            pass
    if "tahsil_harci_safhasi" not in mevcut_kolonlar:
        try:
            cursor.execute("ALTER TABLE dosyalar ADD COLUMN tahsil_harci_safhasi TEXT DEFAULT 'Ödeme Emri Tebliğinden Sonra, Hacizden Önce (%9.10)'")
            conn.commit()
        except Exception:
            pass
    if "tahsil_harci_orani" not in mevcut_kolonlar:
        try:
            cursor.execute("ALTER TABLE dosyalar ADD COLUMN tahsil_harci_orani REAL DEFAULT 9.10")
            conn.commit()
        except Exception:
            pass
    if "cezaevi_harci_orani" not in mevcut_kolonlar:
        try:
            cursor.execute("ALTER TABLE dosyalar ADD COLUMN cezaevi_harci_orani REAL DEFAULT 2.00")
            conn.commit()
        except Exception:
            pass
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS tahsilatlar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dosya_id INTEGER,
        tarih TEXT,
        tutar REAL DEFAULT 0,
        aciklama TEXT,
        FOREIGN KEY(dosya_id) REFERENCES dosyalar(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS masraflar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dosya_id INTEGER,
        tarih TEXT,
        aciklama TEXT,
        masraf_tutari REAL DEFAULT 0,
        iade_tutari REAL DEFAULT 0,
        FOREIGN KEY(dosya_id) REFERENCES dosyalar(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dosya_notlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dosya_id INTEGER,
        tarih TEXT,
        not_icerik TEXT,
        FOREIGN KEY(dosya_id) REFERENCES dosyalar(id)
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faiz_oranlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        faiz_turu TEXT,
        baslangic_tarihi TEXT,
        bitis_tarihi TEXT,
        oran REAL,
        aciklama TEXT
    )
    """)
    cursor.execute("SELECT COUNT(*) FROM faiz_oranlari")
    if cursor.fetchone()[0] == 0:
        varsayilan_faizler = [
            ("Ticari Avans Faizi", "2000-01-01", "2023-08-31", 9.75, "TCMB Avans Faizi"),
            ("Ticari Avans Faizi", "2023-09-01", "2023-12-22", 35.75, "TCMB Avans Faizi"),
            ("Ticari Avans Faizi", "2023-12-23", "2024-03-31", 44.25, "TCMB Avans Faizi"),
            ("Ticari Avans Faizi", "2024-04-01", "2099-12-31", 48.00, "TCMB Avans Faizi (Güncel)"),
            ("Reeskont Faizi", "2000-01-01", "2023-08-31", 8.75, "TCMB Reeskont İskonto Faizi"),
            ("Reeskont Faizi", "2023-09-01", "2023-12-22", 34.75, "TCMB Reeskont İskonto Faizi"),
            ("Reeskont Faizi", "2023-12-23", "2024-03-31", 43.25, "TCMB Reeskont İskonto Faizi"),
            ("Reeskont Faizi", "2024-04-01", "2099-12-31", 39.75, "TCMB Reeskont İskonto Faizi (Güncel)"),
            ("Yasal Faiz", "2000-01-01", "2005-12-31", 12.00, "3095 Sayılı Kanun m. 1"),
            ("Yasal Faiz", "2006-01-01", "2024-05-31", 9.00, "3095 Sayılı Kanun m. 1"),
            ("Yasal Faiz", "2024-06-01", "2026-07-30", 24.00, "3095 Sayılı Kanun (21.05.2024 C.B. Kararı: 8485)"),
            ("Yasal Faiz", "2026-07-31", "2099-12-31", 31.00, "3095 s.K. m. 1 (7589 s.K. 10. md - Güncel %31)")
        ]
        cursor.executemany("""
        INSERT INTO faiz_oranlari (faiz_turu, baslangic_tarihi, bitis_tarihi, oran, aciklama)
        VALUES (?, ?, ?, ?, ?)
        """, varsayilan_faizler)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS alacak_kalemleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dosya_id INTEGER,
        kalem_adi TEXT DEFAULT 'Asıl Alacak',
        tutar REAL DEFAULT 0,
        t_oncesi_faiz REAL DEFAULT 0,
        faiz_turu TEXT DEFAULT 'Ticari Avans Faizi (%48.00)',
        faiz_orani REAL DEFAULT 48.0,
        FOREIGN KEY(dosya_id) REFERENCES dosyalar(id)
    )
    """)
    conn.commit()

init_sqlite_tables_if_needed()

# -------------------------------------------------------------
# 7. SOL MENÜ & JUS LOGO & OTURUM KONTROLÜ
# -------------------------------------------------------------
with st.sidebar:
    logo_path = None
    for olasi_ad in ["Minimalist Logo .jpg", "logo.jpg", "logo.png", "Minimalist Logo.jpg"]:
        if os.path.exists(olasi_ad):
            logo_path = olasi_ad
            break

    if logo_path:
        st.image(logo_path, use_container_width=True)
    else:
        st.markdown(f"""
            <div style="text-align: center; padding: 14px 10px; background: {card_bg}; border-radius: 12px; border: 1.5px solid {card_border}; margin-bottom: 15px;">
                <div style="font-size: 28px; font-weight: 800; letter-spacing: 5px; color: {text_main}; line-height: 1;">
                    J<span style="color: {accent_green};">U</span>S
                </div>
                <div style="font-size: 11px; letter-spacing: 4px; font-weight: 800; color: {accent_green}; text-transform: uppercase; margin-top: 5px;">
                    LEGAL
                </div>
            </div>
        """, unsafe_allow_html=True)

    st.markdown(f"""
        <div style="text-align: center; margin-bottom: 15px;">
            <h3 style="margin: 0; color: {accent_green}; font-weight: 800; letter-spacing: -0.5px; font-size: 19px;">
                Jus Tahsilat Makinesi
            </h3>
            <p style="margin: 3px 0 0 0; color: {text_muted}; font-size: 11px; letter-spacing: 0.5px; text-transform: uppercase; font-weight: 700;">
                İcra Takip & Cari Çözüm Masası
            </p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
        <div style="padding: 10px; background-color: {card_bg}; border: 1.5px solid {accent_green}; border-radius: 8px; margin-bottom: 10px; font-size: 12px; text-align: center;">
            <span style="color: {text_muted};">Aktif Kullanıcı:</span><br>
            <strong style="color: {accent_green}; font-size: 13.5px;">👤 {st.session_state.get('current_user', 'Kullanıcı')}</strong>
        </div>
        <div style="font-size: 11px; text-align: center; color: {text_muted}; margin-bottom: 12px;">
            {DB_STATUS}
        </div>
    """, unsafe_allow_html=True)

    if DB_ERROR:
        st.error(f"⚠️ {DB_ERROR}")

    menu = st.radio(
        "NAVİGASYON",
        [
            "Dosya Arama & Çalışma Masası",
            "Müvekkil Portföy & Raporlama",
            "Yeni Dosya Açılışı",
            "Taraf (Cari) Yönetimi",
            "Masraf & Avans Kaydı",
            "Yasal Faiz Cetveli",
            "Yedekleme & Sistem"
        ],
        key="nav_menu_radio",
        label_visibility="collapsed"
    )

    st.markdown("---")
    st.markdown("<p style='font-size:11px; font-weight:600; text-transform:uppercase; letter-spacing:0.5px; color:#9CA3AF; margin-bottom:4px;'>⚖️ Faiz Cetveli Durumu</p>", unsafe_allow_html=True)
    
    if "faiz_sync_status" not in st.session_state:
        try:
            st.session_state["faiz_sync_status"] = kontrol_et_faiz_guncellemeleri(conn)
        except Exception:
            st.session_state["faiz_sync_status"] = {"durum": "GUNCEL", "mesaj": "Oranlar güncel"}

    fz_st = st.session_state.get("faiz_sync_status", {})
    if fz_st.get("durum") == "GUNCELLEME_VAR":
        st.warning(f"🔔 **{len(fz_st.get('farklar', []))} Yeni Oran Mevcut!**")
        if st.button("⚡ Şimdi Güncelle", use_container_width=True, type="primary", key="sb_quick_update"):
            ok, msg = uygula_faiz_guncellemesi(conn, fz_st.get("farklar", []))
            if ok:
                st.session_state["faiz_sync_status"] = kontrol_et_faiz_guncellemeleri(conn)
                st.success("Faizler başarıyla güncellendi!")
                st.rerun()
    else:
        st.markdown("<div style='font-size:11.5px; color:#10B981; font-weight:500; margin-bottom:6px;'>🟢 Oranlar Güncel</div>", unsafe_allow_html=True)

    if st.button("🔄 Faizleri Denetle", use_container_width=True, key="sb_check_faiz"):
        st.session_state["faiz_sync_status"] = kontrol_et_faiz_guncellemeleri(conn)
        st.rerun()

    st.markdown("---")
    
    secilen_tema = st.radio(
        "Görünüm Modu",
        ["🌙 Gece Modu", "☀️ Gündüz Modu"],
        index=0 if is_dark else 1,
        key="theme_mode_radio",
        horizontal=True
    )
    yeni_tema = "Gece Modu" if "Gece" in secilen_tema else "Gündüz Modu"
    if yeni_tema != st.session_state["theme_mode"]:
        st.session_state["theme_mode"] = yeni_tema
        st.rerun()

    st.write("")
    if st.button("🚪 Güvenli Çıkış Yap", use_container_width=True):
        st.session_state["authenticated"] = False
        st.session_state["current_user"] = None
        st.rerun()

# -------------------------------------------------------------
# 8. MODÜL 1: ÇALIŞMA MASASI & ARAMA MOTORU
# -------------------------------------------------------------
@st.cache_data(ttl=30)
def get_cached_dosyalar_kpi():
    try:
        t_dosyalar = pd.read_sql_query("SELECT id, ana_para, takip_cikisi, vekalet_ucreti, itiraz_edildi, kesinlesme_durumu, durum FROM dosyalar", conn)
        t_tahsilatlar = pd.read_sql_query("SELECT tutar FROM tahsilatlar", conn)
        return t_dosyalar, t_tahsilatlar
    except Exception:
        return pd.DataFrame(), pd.DataFrame()

# -------------------------------------------------------------
# 8. MODÜL 1: ÇALIŞMA MASASI & ARAMA MOTORU
# -------------------------------------------------------------
if menu == "Dosya Arama & Çalışma Masası":
    st.markdown(f"<h2 style='color:{accent_green}; margin-bottom: 4px;'>🗂️ İcra Dosyaları Çalışma Masası</h2>", unsafe_allow_html=True)
    st.caption("Derdest icra dosyalarınızı filtreleyin, üzerine tıklayarak canlı hesap cetvelini ve işlem panelini açın.")
    
    tum_dosyalar, tum_tahsilatlar = get_cached_dosyalar_kpi()
    
    toplam_dosya_sayisi = len(tum_dosyalar)
    is_closed_mask = tum_dosyalar['durum'].astype(str).str.contains("Kapatıldı|İnfaz|Kapalı", case=False, na=False) if not tum_dosyalar.empty else pd.Series([], dtype=bool)
    derdest_dosyalar = tum_dosyalar[~is_closed_mask] if not tum_dosyalar.empty else pd.DataFrame()
    toplam_derdest_sayisi = len(derdest_dosyalar)
    derdest_ana_para_tl = derdest_dosyalar['ana_para'].sum() if not derdest_dosyalar.empty else 0.0

    itirazli_sayisi = len(derdest_dosyalar[derdest_dosyalar['itiraz_edildi'] == 1]) if not derdest_dosyalar.empty else 0
    toplam_tahsil_tl = tum_tahsilatlar['tutar'].sum() if not tum_tahsilatlar.empty else 0.0
    
    kpi1, kpi2, kpi3, kpi4 = st.columns(4)
    kpi1.metric("Toplam Derdest Dosya", f"{toplam_derdest_sayisi} Adet", help=f"Toplam kayıtlı: {toplam_dosya_sayisi} dosya ({toplam_dosya_sayisi - toplam_derdest_sayisi} Kapalı/İnfaz)")
    kpi2.metric("Derdest Asıl Alacak", format_tr_money(derdest_ana_para_tl), help="Yalnızca açık/derdest icra dosyalarının asıl alacak toplamı")
    kpi3.metric("Kasaya Giren Tahsilat", format_tr_money(toplam_tahsil_tl))
    kpi4.metric("🚨 İtirazlı Dosyalar", f"{itirazli_sayisi} Adet")
    
    st.write("")
    
    taraflar_list = get_cached_taraflar_list()
    
    st.markdown(f"""
        <div class="search-card">
            <span style="font-weight: 700; font-size: 14px; color: {accent_green};">🔍 Akıllı Dosya Arama & Filtreleme Masası</span>
        </div>
    """, unsafe_allow_html=True)
    
    col_s1, col_s2 = st.columns([3, 1.2])
    with col_s1:
        hizli_arama = st.text_input("Akıllı Arama", placeholder="🔍 Esas No (Örn: 351), Borçlu, Müvekkil veya Daire yazarak anında bulun...", label_visibility="collapsed", key="in_smart_search")
    with col_s2:
        global_ch_haric = st.toggle(
            "🚫 Cezaevi Harcını Hariç Tut",
            value=st.session_state.get("global_ch_haric", False),
            key="global_ch_haric_tog",
            help="Açıldığında listedeki ve hesaplardaki %2 Cezaevi Harcı toplam borçtan düşülür (UYAP kapak hesabı teyidi için)."
        )
        if global_ch_haric != st.session_state.get("global_ch_haric", False):
            st.session_state["global_ch_haric"] = global_ch_haric
            for k in list(st.session_state.keys()):
                if k.startswith("ch_haric_"):
                    st.session_state[k] = global_ch_haric
        st.session_state["global_ch_haric"] = global_ch_haric

    # Hızlı Durum Filtre Çipleri (5 Seçenek: Tümü, İtirazlılar, Kesinleşenler, Bekleyenler, Kapalı/İnfaz)
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
    aktif_filtre = st.session_state.get("dosya_tab_filtre", "Tümü")
    if f_col1.button(f"📁 Tümü ({toplam_dosya_sayisi})", use_container_width=True, type="primary" if aktif_filtre == "Tümü" else "secondary"):
        st.session_state["dosya_tab_filtre"] = "Tümü"
        st.rerun()
    if f_col2.button(f"🚨 İtirazlılar ({itirazli_sayisi})", use_container_width=True, type="primary" if aktif_filtre == "İtirazlı" else "secondary"):
        st.session_state["dosya_tab_filtre"] = "İtirazlı"
        st.rerun()
    kesin_sayisi = len(tum_dosyalar[tum_dosyalar['kesinlesme_durumu'] == 1]) if not tum_dosyalar.empty else 0
    if f_col3.button(f"✅ Kesinleşenler ({kesin_sayisi})", use_container_width=True, type="primary" if aktif_filtre == "Kesinleşen" else "secondary"):
        st.session_state["dosya_tab_filtre"] = "Kesinleşen"
        st.rerun()
    bekleyen_sayisi = len(tum_dosyalar[(tum_dosyalar['kesinlesme_durumu'] == 0) & (tum_dosyalar['itiraz_edildi'] == 0)]) if not tum_dosyalar.empty else 0
    if f_col4.button(f"⏳ Bekleyenler ({bekleyen_sayisi})", use_container_width=True, type="primary" if aktif_filtre == "Bekleyen" else "secondary"):
        st.session_state["dosya_tab_filtre"] = "Bekleyen"
        st.rerun()
    kapali_sayisi = len(tum_dosyalar[tum_dosyalar['durum'].astype(str).str.contains("Kapatıldı|İnfaz|Kapalı", case=False, na=False)]) if not tum_dosyalar.empty else 0
    if f_col5.button(f"🔒 Kapalı / İnfaz ({kapali_sayisi})", use_container_width=True, type="primary" if aktif_filtre == "Kapalı" else "secondary"):
        st.session_state["dosya_tab_filtre"] = "Kapalı"
        st.rerun()

    with st.expander("⚙️ Detaylı Filtreler (İl, İlçe, Daire, Taraf, Statü)", expanded=False):
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            il_filtre = st.selectbox("İl Filtresi", ["Tümü"] + list(TURKIYE_IL_ILCE.keys()))
            ara_daire = st.selectbox("İcra Dairesi", ["Tümü"] + ICRA_DAIRE_LISTESI)
        with col2:
            ilce_sec = ["Tümü"] + TURKIYE_IL_ILCE.get(il_filtre, []) if il_filtre != "Tümü" else ["Tümü"]
            ilce_filtre = st.selectbox("İlçe", ilce_sec)
            ara_esas = st.text_input("Esas No Ara", placeholder="Örn: 4644 veya 2026/4644")
        with col3:
            ara_alacakli = st.selectbox("Alacaklı (Müvekkil)", ["Tümü"] + taraflar_list)
            ara_borclu = st.selectbox("Borçlu Firma / Kişi", ["Tümü"] + taraflar_list)
        with col4:
            ara_durum = st.selectbox("Dosya Statüsü", ["Tümü", "Açık / Derdest Dosyalar", "Kapatıldı / İnfaz", "Protokol Yapıldı", "İflas"])

    query = "SELECT * FROM dosyalar WHERE 1=1"
    params = []
    if hizli_arama and hizli_arama.strip():
        query += " AND (dosya_no LIKE ? OR borclu LIKE ? OR alacakli LIKE ? OR icra_dairesi LIKE ? OR il LIKE ?)"
        params.extend([f"%{hizli_arama.strip()}%"] * 5)
    if aktif_filtre == "İtirazlı":
        query += " AND itiraz_edildi = 1"
    elif aktif_filtre == "Kesinleşen":
        query += " AND kesinlesme_durumu = 1"
    elif aktif_filtre == "Bekleyen":
        query += " AND kesinlesme_durumu = 0 AND itiraz_edildi = 0"
    elif aktif_filtre == "Kapalı":
        query += " AND (durum LIKE ? OR durum LIKE ? OR durum LIKE ?)"
        params.extend(["%Kapatıldı%", "%İnfaz%", "%Kapalı%"])
    
    if ara_durum == "Açık / Derdest Dosyalar":
        query += " AND (durum IS NULL OR (durum NOT LIKE ? AND durum NOT LIKE ? AND durum NOT LIKE ?))"
        params.extend(["%Kapatıldı%", "%İnfaz%", "%Kapalı%"])
    elif ara_durum == "Kapatıldı / İnfaz":
        query += " AND (durum LIKE ? OR durum LIKE ? OR durum LIKE ?)"
        params.extend(["%Kapatıldı%", "%İnfaz%", "%Kapalı%"])
    elif ara_durum != "Tümü":
        query += " AND durum = ?"
        params.append(ara_durum)

    if il_filtre != "Tümü":
        query += " AND il = ?"
        params.append(il_filtre)
    if ilce_filtre != "Tümü":
        query += " AND ilce = ?"
        params.append(ilce_filtre)
    if ara_daire != "Tümü":
        query += " AND icra_dairesi = ?"
        params.append(ara_daire)
    if ara_esas:
        query += " AND dosya_no LIKE ?"
        params.append(f"%{ara_esas}%")
    if ara_alacakli != "Tümü":
        query += " AND alacakli = ?"
        params.append(ara_alacakli)
    if ara_borclu != "Tümü":
        query += " AND borclu LIKE ?"
        params.append(f"%{ara_borclu}%")

    query += " ORDER BY id DESC"

    df = pd.read_sql_query(query, conn, params=params if params else None)

    if not df.empty:
        if "takip_turu" not in df.columns:
            df["takip_turu"] = "Örnek No: 7 (İlamsız Takip - Para/Teminat)"
        else:
            df["takip_turu"] = df["takip_turu"].fillna("Örnek No: 7 (İlamsız Takip - Para/Teminat)")

        kalan_anaparalar, kalan_faizler, toplam_tahsilatlar, guncel_bakiyeler = [], [], [], []
        
        file_ids = f"({','.join(map(str, df['id'].tolist()))})"
        all_tahsilatlar = pd.read_sql_query(f"SELECT * FROM tahsilatlar WHERE dosya_id IN {file_ids} ORDER BY tarih ASC", conn)
        all_masraflar = pd.read_sql_query(f"SELECT * FROM masraflar WHERE dosya_id IN {file_ids} ORDER BY tarih ASC", conn)
        all_alacak_kalemleri = pd.read_sql_query(f"SELECT * FROM alacak_kalemleri WHERE dosya_id IN {file_ids}", conn)

        tahsilat_groups = dict(tuple(all_tahsilatlar.groupby("dosya_id"))) if not all_tahsilatlar.empty else {}
        masraf_groups = dict(tuple(all_masraflar.groupby("dosya_id"))) if not all_masraflar.empty else {}
        ak_groups = dict(tuple(all_alacak_kalemleri.groupby("dosya_id"))) if not all_alacak_kalemleri.empty else {}

        empty_tahsilat = pd.DataFrame(columns=["id", "dosya_id", "tarih", "tutar", "aciklama"])
        empty_masraf = pd.DataFrame(columns=["id", "dosya_id", "tarih", "aciklama", "masraf_tutari", "iade_tutari"])
        empty_ak = pd.DataFrame(columns=["id", "dosya_id", "kalem_adi", "tutar", "t_oncesi_faiz", "faiz_turu", "faiz_orani", "kalem_turu", "sorumlu_borclular"])

        for _, r in df.iterrows():
            d_id = r['id']
            tahsilat_df = tahsilat_groups.get(d_id, empty_tahsilat)
            masraf_df = masraf_groups.get(d_id, empty_masraf)
            ak_df = ak_groups.get(d_id, empty_ak)
            
            toplam_m = masraf_df['masraf_tutari'].sum() if not masraf_df.empty else 0.0
            toplam_i = masraf_df['iade_tutari'].sum() if not masraf_df.empty else 0.0
            net_m = toplam_m - toplam_i

            is_infaz = bool(re.search(r"Kapatıldı|İnfaz|Kapalı", str(r.get('durum', '')), re.I))

            rem_p, rem_i, tot_pay, m_list, *_ = hesapla_kademeli_dosya_hesabi(
                r['ana_para'], r['faiz_orani'], r['takip_tarihi'], r['t_oncesi_faiz'], tahsilat_df,
                faiz_turu=r.get('faiz_turu', 'Özel Oran'),
                masraflar_df=masraf_df,
                alacak_kalemleri_df=ak_df
            )
            
            cikis_tutari = float(r['takip_cikisi'])
            t_harc_oran = float(r.get('tahsil_harci_orani', 9.10) if pd.notnull(r.get('tahsil_harci_orani')) else 9.10)
            c_harc_oran = float(r.get('cezaevi_harci_orani', 2.00) if pd.notnull(r.get('cezaevi_harci_orani')) else 2.00)
            tahsil_harci = round(cikis_tutari * (t_harc_oran / 100.0), 2)
            
            if f"ch_haric_{r['id']}" in st.session_state:
                d_ch_haric = st.session_state[f"ch_haric_{r['id']}"]
            else:
                d_ch_haric = global_ch_haric

            if d_ch_haric or c_harc_oran == 0.0:
                cezaevi_harci = 0.0
            else:
                cezaevi_harci = round(cikis_tutari * (c_harc_oran / 100.0), 2)

            if is_infaz:
                kalan_anaparalar.append("0,00 TL")
                kalan_faizler.append("0,00 TL")
                toplam_tahsilatlar.append(format_tr_money(tot_pay))
                guncel_bakiyeler.append("0,00 TL (İnfaz)")
            else:
                consumed_in_items = sum(
                    float(parse_tr_money(m_item.get("Masrafa Mahsup", "0"))) +
                    float(parse_tr_money(m_item.get("Faize Mahsup", "0"))) +
                    float(parse_tr_money(m_item.get("Ana Paraya Mahsup", "0")))
                    for m_item in m_list
                )
                leftover_pay = max(0.0, tot_pay - consumed_in_items)
                
                s_vekalet = float(r.get('vekalet_ucreti', 0.0))
                kalan_vekalet = max(0.0, s_vekalet - leftover_pay)
                leftover_pay = max(0.0, leftover_pay - s_vekalet)
                
                kalan_th = max(0.0, tahsil_harci - leftover_pay)
                leftover_pay = max(0.0, leftover_pay - tahsil_harci)
                
                kalan_ch = max(0.0, cezaevi_harci - leftover_pay)
                
                toplam_borc = rem_p + rem_i + kalan_vekalet + net_m + kalan_th + kalan_ch
                if toplam_borc <= 0.05:
                    toplam_borc = 0.0
                
                kalan_anaparalar.append(format_tr_money(rem_p))
                kalan_faizler.append(format_tr_money(rem_i))
                toplam_tahsilatlar.append(format_tr_money(tot_pay))
                guncel_bakiyeler.append(format_tr_money(toplam_borc))

        df['Kalan Ana Para'] = kalan_anaparalar
        df['İşlemiş Faiz'] = kalan_faizler
        df['Toplam Tahsilat'] = toplam_tahsilatlar
        df['Kalan Dosya Borcu'] = guncel_bakiyeler
        df['İtiraz'] = df['itiraz_edildi'].apply(lambda x: "🚨 İtiraz Edildi" if x == 1 else "Normal")
        df['Kesinleşme'] = df['kesinlesme_durumu'].apply(lambda x: "✅ Kesinleşti" if x == 1 else "Beklemede")

        borc_sutun_basligi = "Güncel Kalan Borç (Cezaevi Hariç)" if global_ch_haric else "Güncel Kalan Borç (Harçlar Dahil)"

        goster_df = pd.DataFrame({
            "Sıra": range(1, len(df) + 1),
            "Esas No": df["dosya_no"],
            "İcra Dairesi": df["icra_dairesi"],
            "Borçlu(lar)": df["borclu"],
            "Alacaklı": df["alacakli"],
            "Asıl Alacak": df["ana_para"].apply(format_tr_money),
            "Tahsil Edilen": df["Toplam Tahsilat"],
            borc_sutun_basligi: df["Kalan Dosya Borcu"],
            "İtiraz Durumu": df["İtiraz"],
            "Kesinleşme": df["Kesinleşme"]
        })
        
        # Hızlı Dosya Seçici Açılır Kutu
        col_pk1, col_pk2 = st.columns([3, 1])
        with col_pk1:
            picker_dict = {f"[{idx+1}] {r['dosya_no']} | {r['borclu']} ({r['icra_dairesi']})": int(r['id']) for idx, r in df.reset_index(drop=True).iterrows()}
            cur_p_keys = list(picker_dict.keys())
            
            cur_active_id = st.session_state.get("aktif_dosya_id")
            def_idx = 0
            if cur_active_id and cur_active_id in picker_dict.values():
                for ki, kv in enumerate(cur_p_keys):
                    if picker_dict[kv] == cur_active_id:
                        def_idx = ki + 1
                        break
            
            s_pick = st.selectbox(
                "🎯 Hızlı Dosya Seçici (Listeden Doğrudan Aç):",
                ["-- Dosya Seçin veya Aşağıdaki Tablodan Tıklayın --"] + cur_p_keys,
                index=def_idx,
                key="quick_p_select"
            )
            if s_pick != "-- Dosya Seçin veya Aşağıdaki Tablodan Tıklayın --":
                chosen_from_p = picker_dict[s_pick]
                if chosen_from_p != cur_active_id:
                    st.session_state["aktif_dosya_id"] = chosen_from_p
                    st.session_state["last_clicked_df_row"] = list(df['id']).index(chosen_from_p)
                    st.rerun()
        with col_pk2:
            st.write("")
            st.caption(f"⚡ Listelenen: **{len(df)} dosya**")

        st.markdown("##### 📌 Dosya Listesi *(Detayları açmak için satıra tıklayın)*")
        secim_olayi = st.dataframe(
            goster_df,
            use_container_width=True,
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row"
        )

        secilen_satirlar = secim_olayi.selection.rows if secim_olayi and secim_olayi.selection else []
        last_clicked = st.session_state.get("last_clicked_df_row", None)
        if secilen_satirlar:
            clicked_row = secilen_satirlar[0]
            if clicked_row != last_clicked:
                st.session_state["last_clicked_df_row"] = clicked_row
                st.session_state["aktif_dosya_id"] = int(df.iloc[clicked_row]['id'])

        if "aktif_dosya_id" in st.session_state and st.session_state["aktif_dosya_id"]:
            secili_id = st.session_state["aktif_dosya_id"]
            secili_dosya_rows = df[df['id'] == secili_id]
            if secili_dosya_rows.empty:
                secili_dosya_rows = pd.read_sql_query("SELECT * FROM dosyalar WHERE id = ?", conn, params=[secili_id])
            
            if not secili_dosya_rows.empty:
                secili_dosya = secili_dosya_rows.iloc[0]

                tahsilat_df = tahsilat_groups.get(secili_id)
                if tahsilat_df is None:
                    tahsilat_df = pd.read_sql_query("SELECT id, tarih, tutar, aciklama FROM tahsilatlar WHERE dosya_id = ? ORDER BY tarih ASC", conn, params=[secili_id])
                
                masraf_df = masraf_groups.get(secili_id)
                if masraf_df is None:
                    masraf_df = pd.read_sql_query("SELECT id, tarih, aciklama, masraf_tutari, iade_tutari FROM masraflar WHERE dosya_id = ? ORDER BY tarih ASC", conn, params=[secili_id])
                
                ak_df = ak_groups.get(secili_id)
                if ak_df is None:
                    ak_df = pd.read_sql_query("SELECT id, kalem_adi, kalem_turu, tutar, t_oncesi_faiz, faiz_turu, faiz_orani, sorumlu_borclular FROM alacak_kalemleri WHERE dosya_id = ?", conn, params=[secili_id])
                
                notlar_df = pd.read_sql_query("SELECT id, tarih, not_icerik FROM dosya_notlari WHERE dosya_id = ? ORDER BY tarih DESC", conn, params=[secili_id])
                
                top_masraf = masraf_df['masraf_tutari'].sum() if not masraf_df.empty else 0.0
                top_iade = masraf_df['iade_tutari'].sum() if not masraf_df.empty else 0.0
                net_masraf = top_masraf - top_iade

                rem_p, rem_i, tot_pay, mahsup_list, rem_pre_i, rem_post_i = hesapla_kademeli_dosya_hesabi(
                    secili_dosya['ana_para'], secili_dosya['faiz_orani'], secili_dosya['takip_tarihi'], secili_dosya['t_oncesi_faiz'], tahsilat_df,
                    faiz_turu=secili_dosya.get('faiz_turu', 'Özel Oran'),
                    masraflar_df=masraf_df,
                    alacak_kalemleri_df=ak_df
                )
                
                cikis_bedeli = float(secili_dosya['takip_cikisi'])
                s_th_oran = float(secili_dosya.get('tahsil_harci_orani', 9.10) if pd.notnull(secili_dosya.get('tahsil_harci_orani')) else 9.10)
                s_ch_oran = float(secili_dosya.get('cezaevi_harci_orani', 2.00) if pd.notnull(secili_dosya.get('cezaevi_harci_orani')) else 2.00)
                tahsil_harci_tutar = round(cikis_bedeli * (s_th_oran / 100.0), 2)
                
                if f"ch_haric_{secili_id}" in st.session_state:
                    ch_is_haric = st.session_state[f"ch_haric_{secili_id}"]
                else:
                    ch_is_haric = global_ch_haric

                is_infaz = bool(re.search(r"Kapatıldı|İnfaz|Kapalı", str(secili_dosya.get('durum', '')), re.I))

                if ch_is_haric or s_ch_oran == 0.0:
                    cezaevi_harci_tutar = 0.0
                else:
                    cezaevi_harci_tutar = round(cikis_bedeli * (s_ch_oran / 100.0), 2)
                
                if is_infaz:
                    rem_p = 0.0
                    rem_i = 0.0
                    rem_pre_i = 0.0
                    rem_post_i = 0.0
                    net_masraf = 0.0
                    kalan_vekalet = 0.0
                    kalan_th = 0.0
                    kalan_ch = 0.0
                    kalan_toplam_dosya_borcu = 0.0
                else:
                    consumed_in_items = sum(
                        float(parse_tr_money(m_item.get("Masrafa Mahsup", "0"))) +
                        float(parse_tr_money(m_item.get("Faize Mahsup", "0"))) +
                        float(parse_tr_money(m_item.get("Ana Paraya Mahsup", "0")))
                        for m_item in mahsup_list
                    )
                    leftover_pay = max(0.0, tot_pay - consumed_in_items)
                    
                    s_vekalet = float(secili_dosya.get('vekalet_ucreti', 0.0))
                    kalan_vekalet = max(0.0, s_vekalet - leftover_pay)
                    leftover_pay = max(0.0, leftover_pay - s_vekalet)
                    
                    kalan_th = max(0.0, tahsil_harci_tutar - leftover_pay)
                    leftover_pay = max(0.0, leftover_pay - tahsil_harci_tutar)
                    
                    kalan_ch = max(0.0, cezaevi_harci_tutar - leftover_pay)
                    
                    kalan_toplam_dosya_borcu = rem_p + rem_i + kalan_vekalet + net_masraf + kalan_th + kalan_ch
                    if kalan_toplam_dosya_borcu <= 0.05:
                        kalan_toplam_dosya_borcu = 0.0

                st.markdown("---")
                header_c1, header_c2 = st.columns([3.5, 1])
                with header_c1:
                    st.markdown(f"#### 📁 {secili_dosya['il']} {secili_dosya['icra_dairesi']} {secili_dosya['dosya_no']}")
                    st.caption(f"**Takip Tarihi:** 📅 `{secili_dosya['takip_tarihi']}` | **Alacaklı:** {secili_dosya['alacakli']} | **Borçlu(lar):** {secili_dosya['borclu']} | **Takip Yolu:** {secili_dosya['takip_turu']}")
                with header_c2:
                    if st.button("✖️ Dosyayı Kapat", use_container_width=True):
                        st.session_state["aktif_dosya_id"] = None
                        st.session_state["last_clicked_df_row"] = None
                        st.rerun()

                with st.expander("⚖️ UYAP Dosya Hesabı Doğrulama & Sağlama Aracı", expanded=False):
                    uy_c1, uy_c2 = st.columns([2.5, 1.5])
                    with uy_c1:
                        uyap_input_val = st.text_input("UYAP'taki Bakiye Borç Tutarı (TL):", placeholder="Örn: 653.737,00", key=f"uyap_check_{secili_id}")
                    with uy_c2:
                        durum_str = "🚫 HARİÇ (0,00 TL)" if (ch_is_haric or s_ch_oran == 0.0) else f"✅ DAHİL (%{s_ch_oran:.2f})"
                        st.markdown(f"<div style='font-size: 12px; margin-top: 4px; margin-bottom: 4px;'>Cezaevi Harcı: <b>{durum_str}</b></div>", unsafe_allow_html=True)
                        if st.button("🔄 Harcı Hariç/Dahil Değiştir", key=f"flip_ch_{secili_id}", use_container_width=True):
                            st.session_state[f"ch_haric_{secili_id}"] = not ch_is_haric
                            st.rerun()

                    if uyap_input_val and uyap_input_val.strip():
                        val_num = parse_tr_money(uyap_input_val)
                        fark = round(kalan_toplam_dosya_borcu - val_num, 2)
                        st_ch_val = round(cikis_bedeli * (s_ch_oran / 100.0), 2)
                        if abs(fark) < 0.05:
                            st.success(f"🎉 **Kusursuz Eşleşme!** TahsilatPro hesabı UYAP dosya hesabı ile birebir aynıdır (Fark: {format_tr_money(fark)}).")
                        elif abs(abs(fark) - st_ch_val) < 0.10:
                            st.warning(f"⚠️ **Cezaevi Harcı Farkı:** TahsilatPro ile UYAP arasında tam Cezaevi Harcı kadar ({format_tr_money(st_ch_val)}) fark bulunmaktadır. Harcı hariç tut butonuna basarak UYAP ile tam eşitleyebilirsiniz.")
                        else:
                            st.info(f"ℹ️ **Hesap Karşılaştırması:** TahsilatPro: **{format_tr_money(kalan_toplam_dosya_borcu)}** | UYAP: **{format_tr_money(val_num)}** | **Fark: {format_tr_money(fark)}**")

                col_sol, col_sag = st.columns([1.55, 1.0])

                with col_sol:
                    t_durum, t_alacak, t_tahsilat, t_notlar, t_rapor, t_ayar = st.tabs([
                        "📌 Durum", "📋 Alacak Kalemleri (UYAP)", "💰 Tahsilat (TBK 100)", "📝 Notlar", "📊 Müvekkil Raporu", "⚙️ Dosya Ayarları"
                    ])

                    with t_alacak:
                        st.markdown("##### 📋 Alacak Kalemleri (UYAP Takip Talebi Uyumu)")
                        st.caption("Farklı faiz türü ve oranına tabi asıl alacak, çek tazminatı, işlemiş faiz veya komisyon gibi kalemleri ayrı ayrı takip edin.")

                        if not ak_df.empty:
                            k_turu_col = ak_df["kalem_turu"].fillna("Asıl Alacak") if "kalem_turu" in ak_df.columns else pd.Series(["Asıl Alacak"] * len(ak_df), index=ak_df.index)
                            s_borclu_col = ak_df["sorumlu_borclular"].fillna("Tüm Borçlular") if "sorumlu_borclular" in ak_df.columns else pd.Series(["Tüm Borçlular"] * len(ak_df), index=ak_df.index)
                            ak_goster = pd.DataFrame({
                                "ID": ak_df["id"],
                                "Alacak Kalemi Adı": ak_df["kalem_adi"],
                                "Kalem Türü": k_turu_col,
                                "Tutar": ak_df["tutar"].apply(format_tr_money),
                                "Takip Öncesi Faiz": ak_df["t_oncesi_faiz"].apply(format_tr_money),
                                "Faiz Türü": ak_df["faiz_turu"],
                                "Faiz Oranı": ak_df["faiz_orani"].apply(lambda x: f"%{x:.2f}"),
                                "Sorumlu Borçlu(lar)": s_borclu_col
                            })
                            st.dataframe(ak_goster, use_container_width=True, hide_index=True)

                            with st.expander("✏️ Seçili Kalemi Düzenle", expanded=False):
                                edit_dict = {f"ID: {r['id']} | {r['kalem_adi']} ({format_tr_money(r['tutar'])})": r for _, r in ak_df.iterrows()}
                                sel_k_label = st.selectbox("Düzenlenecek Kalem", list(edit_dict.keys()), key="sel_k_edit_box")
                                sel_k_row = edit_dict[sel_k_label]

                                with st.form(f"form_edit_kalem_{sel_k_row['id']}"):
                                    ed_c1, ed_c2 = st.columns(2)
                                    with ed_c1:
                                        ed_adi = st.text_input("Kalem Adı", value=str(sel_k_row.get("kalem_adi", "")))
                                        turler = ["Asıl Alacak", "Tazminat", "Takip Öncesi Faiz", "Masraf/Komisyon", "Diğer"]
                                        cur_tur = sel_k_row.get("kalem_turu", "Asıl Alacak") or "Asıl Alacak"
                                        tur_idx = turler.index(cur_tur) if cur_tur in turler else 0
                                        ed_tur = st.selectbox("Kalem Türü", turler, index=tur_idx)
                                        ed_tutar = parse_tr_money(st.text_input("Kalem Tutarı (TL)", value=format_tr_money(sel_k_row.get("tutar", 0.0))))
                                        ed_toncesi = parse_tr_money(st.text_input("Takip Öncesi Faiz (TL)", value=format_tr_money(sel_k_row.get("t_oncesi_faiz", 0.0))))
                                    with ed_c2:
                                        cur_ft = sel_k_row.get("faiz_turu", "Ticari Avans Faizi (%48.00)") or "Ticari Avans Faizi (%48.00)"
                                        ft_idx = FAIZ_TURLERI_LISTESI.index(cur_ft) if cur_ft in FAIZ_TURLERI_LISTESI else 0
                                        ed_faiz_tipi = st.selectbox("Kalemin Faiz Türü", FAIZ_TURLERI_LISTESI, index=ft_idx, key=f"ed_ft_{sel_k_row['id']}")
                                        if ed_faiz_tipi == "Ticari Avans Faizi (%48.00)":
                                            ed_oran_def = 48.0
                                        elif ed_faiz_tipi == "TCMB Reeskont Faizi (%39.75)":
                                            ed_oran_def = 39.75
                                        elif "Yasal Faiz" in ed_faiz_tipi:
                                            ed_oran_def = 31.0
                                        elif ed_faiz_tipi == "Faizsiz":
                                            ed_oran_def = 0.0
                                        else:
                                            ed_oran_def = float(sel_k_row.get("faiz_orani", 30.0) or 30.0)
                                        ed_oran = st.number_input("Faiz Oranı (%)", value=float(ed_oran_def), step=0.5, key=f"ed_oran_{sel_k_row['id']}")
                                        ed_sorumlu = st.text_input("Sorumlu Borçlu(lar)", value=str(sel_k_row.get("sorumlu_borclular", "Tüm Borçlular") or "Tüm Borçlular"))

                                    if st.form_submit_button("💾 Kalem Bilgilerini Güncelle", type="primary"):
                                        if ed_faiz_tipi != "Özel Oran":
                                            final_ed_oran = get_faiz_default_rate(ed_faiz_tipi)
                                        else:
                                            final_ed_oran = float(ed_oran)

                                        cursor.execute("""
                                            UPDATE alacak_kalemleri 
                                            SET kalem_adi = ?, kalem_turu = ?, tutar = ?, t_oncesi_faiz = ?, faiz_turu = ?, faiz_orani = ?, sorumlu_borclular = ?
                                            WHERE id = ?
                                        """, (ed_adi, ed_tur, ed_tutar, ed_toncesi, ed_faiz_tipi, final_ed_oran, ed_sorumlu, sel_k_row['id']))
                                        cursor.execute("SELECT SUM(tutar), SUM(t_oncesi_faiz) FROM alacak_kalemleri WHERE dosya_id = ?", (secili_id,))
                                        tot_p, tot_i = cursor.fetchone()
                                        tot_p = tot_p or 0.0
                                        tot_i = tot_i or 0.0
                                        if tot_p > 0:
                                            cikis_h = tot_p + tot_i
                                            vek_h = hesapla_icra_vekalet_ucreti(cikis_h)
                                            cursor.execute("""
                                                UPDATE dosyalar 
                                                SET ana_para = ?, t_oncesi_faiz = ?, takip_cikisi = ?, vekalet_ucreti = ?, faiz_turu = ?, faiz_orani = ? 
                                                WHERE id = ?
                                            """, (tot_p, tot_i, cikis_h, vek_h, ed_faiz_tipi, final_ed_oran, secili_id))
                                        conn.commit()
                                        st.success("Kalem başarıyla güncellendi!")
                                        st.rerun()

                            col_del_k1, col_del_k2 = st.columns([3, 1])
                            with col_del_k1:
                                ak_sil_dict = {f"ID: {r['id']} | {r['kalem_adi']} ({format_tr_money(r['tutar'])})": r['id'] for _, r in ak_df.iterrows()}
                                s_ak_id = ak_sil_dict[st.selectbox("Silinecek Alacak Kalemi", list(ak_sil_dict.keys()), key="del_ak_select")]
                            with col_del_k2:
                                st.write("")
                                st.write("")
                                if st.button("🗑️ Kalemi Sil", use_container_width=True):
                                    cursor.execute("DELETE FROM alacak_kalemleri WHERE id = ?", (s_ak_id,))
                                    cursor.execute("SELECT SUM(tutar), SUM(t_oncesi_faiz) FROM alacak_kalemleri WHERE dosya_id = ?", (secili_id,))
                                    tot_p, tot_i = cursor.fetchone()
                                    tot_p = tot_p or 0.0
                                    tot_i = tot_i or 0.0
                                    if tot_p > 0:
                                        cikis_h = tot_p + tot_i
                                        vek_h = hesapla_icra_vekalet_ucreti(cikis_h)
                                        cursor.execute("UPDATE dosyalar SET ana_para = ?, t_oncesi_faiz = ?, takip_cikisi = ?, vekalet_ucreti = ? WHERE id = ?", (tot_p, tot_i, cikis_h, vek_h, secili_id))
                                    conn.commit()
                                    st.success("Alacak kalemi silindi!")
                                    st.rerun()
                        else:
                            st.info("Bu dosyada henüz ayrı alacak kalemi girilmemiş. Dosya genelindeki tek tutar üzerinden hesaplanıyor.")

                        st.markdown("---")
                        st.markdown("##### ➕ Yeni Alacak Kalemi Ekle")
                        with st.form("form_add_alacak_kalemi"):
                            ak_c1, ak_c2 = st.columns(2)
                            with ak_c1:
                                ak_ad = st.text_input("Kalem Adı", placeholder="Örn: Karşılıksız Çek Bedeli, Çek Tazminatı")
                                ak_tur = st.selectbox("Kalem Türü", ["Asıl Alacak", "Tazminat", "Takip Öncesi Faiz", "Masraf/Komisyon", "Diğer"])
                                ak_tutar = parse_tr_money(st.text_input("Kalem Tutarı (TL)", value="0,00", key="ak_in_tutar"))
                                ak_toncesi = parse_tr_money(st.text_input("Takip Öncesi Faiz (TL)", value="0,00", key="ak_in_toncesi"))
                            with ak_c2:
                                ak_faiz_tipi = st.selectbox("Kalemin Faiz Türü", FAIZ_TURLERI_LISTESI, key="ak_in_faiztipi")
                                if ak_faiz_tipi == "Ticari Avans Faizi (%48.00)":
                                    ak_oran = 48.0
                                elif ak_faiz_tipi == "TCMB Reeskont Faizi (%39.75)":
                                    ak_oran = 39.75
                                elif "Yasal Faiz" in ak_faiz_tipi:
                                    ak_oran = 31.0
                                elif ak_faiz_tipi == "Faizsiz":
                                    ak_oran = 0.0
                                else:
                                    ak_oran = st.number_input("Faiz Oranı (%)", value=30.0, step=0.5, key="ak_in_oran")
                                ak_sorumlu = st.text_input("Sorumlu Borçlu(lar)", value="Tüm Borçlular", help="Yalnızca belirli bir borçlu sorumluysa buraya unvanını yazabilirsiniz.")
                            
                            if st.form_submit_button("Kalemi Dosyaya Ekle", type="primary"):
                                if ak_faiz_tipi != "Özel Oran":
                                    final_ak_oran = get_faiz_default_rate(ak_faiz_tipi)
                                else:
                                    final_ak_oran = float(ak_oran)
                                
                                if (ak_tutar > 0 or ak_toncesi > 0) and ak_ad.strip():
                                    cursor.execute("""
                                        INSERT INTO alacak_kalemleri (dosya_id, kalem_adi, kalem_turu, tutar, t_oncesi_faiz, faiz_turu, faiz_orani, sorumlu_borclular)
                                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                                    """, (secili_id, ak_ad.strip(), ak_tur, ak_tutar, ak_toncesi, ak_faiz_tipi, final_ak_oran, ak_sorumlu.strip()))
                                    cursor.execute("SELECT SUM(tutar), SUM(t_oncesi_faiz) FROM alacak_kalemleri WHERE dosya_id = ?", (secili_id,))
                                    tot_p, tot_i = cursor.fetchone()
                                    tot_p = tot_p or 0.0
                                    tot_i = tot_i or 0.0
                                    cikis_h = tot_p + tot_i
                                    vek_h = hesapla_icra_vekalet_ucreti(cikis_h)
                                    cursor.execute("""
                                        UPDATE dosyalar 
                                        SET ana_para = ?, t_oncesi_faiz = ?, takip_cikisi = ?, vekalet_ucreti = ?, faiz_turu = ?, faiz_orani = ? 
                                        WHERE id = ?
                                    """, (tot_p, tot_i, cikis_h, vek_h, ak_faiz_tipi, final_ak_oran, secili_id))
                                    conn.commit()
                                    st.success(f"'{ak_ad}' kalemi eklendi ve dosya toplamı güncellendi!")
                                    st.rerun()
                                else:
                                    st.warning("Lütfen kalem adı ve 0'dan büyük bir tutar girin.")

                    with t_durum:
                        c_itiraz = st.checkbox("🚨 İtiraz Edildi (Takip Durduruldu)", value=bool(secili_dosya['itiraz_edildi']))
                        c_kesin = st.checkbox("✅ Takip Kesinleşti (Haciz Safhası)", value=bool(secili_dosya['kesinlesme_durumu']))
                        durum_opt = ["Açık", "Protokol Yapıldı", "İflas", "Kapatıldı / İnfaz"]
                        cur_index = durum_opt.index(secili_dosya['durum']) if secili_dosya['durum'] in durum_opt else 0
                        durum_aciklama = st.selectbox("Dosya İlerleme Statüsü", durum_opt, index=cur_index)
                        
                        if st.button("Statü Güncelle", type="primary"):
                            cursor.execute("UPDATE dosyalar SET itiraz_edildi = ?, kesinlesme_durumu = ?, durum = ? WHERE id = ?", (1 if c_itiraz else 0, 1 if c_kesin else 0, durum_aciklama, secili_id))
                            conn.commit()
                            st.success("Durum güncellendi!")
                            st.rerun()

                    with t_tahsilat:
                        st.markdown("##### ➕ Kısmi Ödeme Kaydet")
                        c_th1, c_th2, c_th3 = st.columns(3)
                        with c_th1:
                            t_tarih = st.date_input("Tahsilat Tarihi", value=date.today(), key="in_t_date")
                        with c_th2:
                            raw_t_tutar = st.text_input("Tutar (TL)", value="0,00", key="in_t_amt")
                            t_tutar = parse_tr_money(raw_t_tutar)
                            st.caption(f"İşlenecek: **{format_tr_money(t_tutar)}**")
                        with c_th3:
                            t_aciklama = st.text_input("Açıklama", placeholder="Örn: Haciz, Haricen, UYAP", key="in_t_desc")

                        if st.button("Ödemeyi İşle", type="primary"):
                            if t_tutar > 0:
                                cursor.execute("INSERT INTO tahsilatlar (dosya_id, tarih, tutar, aciklama) VALUES (?, ?, ?, ?)", (secili_id, str(t_tarih), t_tutar, t_aciklama))
                                cursor.execute("INSERT INTO dosya_notlari (dosya_id, tarih, not_icerik) VALUES (?, ?, ?)", (secili_id, str(t_tarih), f"{format_tr_money(t_tutar)} tahsilat yapıldı. ({t_aciklama})"))
                                conn.commit()
                                st.success("Tahsilat TBK m. 100 gereğince mahsup edildi!")
                                st.rerun()

                        st.markdown("---")
                        st.markdown("##### 📜 Mahsup Dökümü ve Düzeltme")
                        if not tahsilat_df.empty:
                            st.dataframe(pd.DataFrame(mahsup_list), use_container_width=True, hide_index=True)
                            
                            t_opt = {f"ID: {r['id']} | {r['tarih']} - {format_tr_money(r['tutar'])}": r['id'] for _, r in tahsilat_df.iterrows()}
                            sec_t_id = t_opt[st.selectbox("Düzeltilecek Tahsilat", list(t_opt.keys()))]
                            r_t = tahsilat_df[tahsilat_df['id'] == sec_t_id].iloc[0]

                            ce1, ce2, ce3 = st.columns(3)
                            with ce1:
                                edt_t_date = st.date_input("Düzeltme Tarihi", value=datetime.strptime(str(r_t['tarih']), "%Y-%m-%d").date())
                            with ce2:
                                edt_t_amt = parse_tr_money(st.text_input("Düzeltme Tutarı", value=str(r_t['tutar']).replace(".", ",")))
                            with ce3:
                                edt_t_dsc = st.text_input("Düzeltme Açıklaması", value=str(r_t['aciklama'] or ''))

                            btn_th1, btn_th2 = st.columns(2)
                            with btn_th1:
                                if st.button("Tahsilat Düzenle"):
                                    cursor.execute("UPDATE tahsilatlar SET tarih = ?, tutar = ?, aciklama = ? WHERE id = ?", (str(edt_t_date), edt_t_amt, edt_t_dsc, sec_t_id))
                                    conn.commit()
                                    st.rerun()
                            with btn_th2:
                                if st.button("🗑️ Tahsilatı Sil"):
                                    cursor.execute("DELETE FROM tahsilatlar WHERE id = ?", (sec_t_id,))
                                    conn.commit()
                                    st.rerun()

                    with t_notlar:
                        st.markdown("##### ➕ Yeni Not Ekle")
                        with st.form(f"form_not_add_{secili_id}"):
                            cn1, cn2 = st.columns([1, 3])
                            with cn1:
                                n_date = st.date_input("Not Tarihi", value=date.today(), key=f"new_not_date_{secili_id}")
                            with cn2:
                                n_text = st.text_area("İcra Notu / Borçlu Taahhüdü", height=70, placeholder="Örn: Borçlu ile görüşüldü, Cuma gününe kadar 50.000 TL ödeme taahhüdünde bulundu.", key=f"new_not_text_{secili_id}")
                            if st.form_submit_button("💾 Notu Kaydet", type="primary"):
                                if n_text.strip():
                                    cursor.execute("INSERT INTO dosya_notlari (dosya_id, tarih, not_icerik) VALUES (?, ?, ?)", (secili_id, str(n_date), n_text.strip()))
                                    conn.commit()
                                    st.success("Not başarıyla kaydedildi!")
                                    st.rerun()
                                else:
                                    st.warning("Lütfen bir not metni girin.")

                        st.markdown("---")
                        st.markdown("##### 📋 Kayıtlı Dosya Notları")
                        if not notlar_df.empty:
                            goster_notlar = notlar_df[["id", "tarih", "not_icerik"]].copy()
                            goster_notlar.columns = ["Kayıt No", "Tarih", "Not İçeriği"]
                            st.dataframe(goster_notlar, use_container_width=True, hide_index=True)

                            st.markdown("##### ✏️ Not Düzenle veya Sil")
                            not_dict = {f"#{r['id']} | {r['tarih']} - {str(r['not_icerik'])[:55]}...": r['id'] for _, r in notlar_df.iterrows()}
                            sel_not_label = st.selectbox("İşlem Yapılacak Notu Seçin", list(not_dict.keys()), key=f"sel_not_box_{secili_id}")
                            sel_not_id = not_dict[sel_not_label]
                            sel_not_row = notlar_df[notlar_df['id'] == sel_not_id].iloc[0]

                            try:
                                def_not_date = datetime.strptime(str(sel_not_row['tarih']), "%Y-%m-%d").date()
                            except Exception:
                                def_not_date = date.today()

                            ed_nc1, ed_nc2 = st.columns([1, 3])
                            with ed_nc1:
                                edt_n_date = st.date_input("Tarih Düzenle", value=def_not_date, key=f"edt_date_{sel_not_id}")
                            with ed_nc2:
                                edt_n_text = st.text_area("Not Metni Düzenle", value=str(sel_not_row['not_icerik']), height=80, key=f"edt_text_{sel_not_id}")

                            btn_n_col1, btn_n_col2 = st.columns(2)
                            with btn_n_col1:
                                if st.button("💾 Notu Güncelle", key=f"btn_upd_note_{sel_not_id}", type="primary", use_container_width=True):
                                    if edt_n_text.strip():
                                        cursor.execute("UPDATE dosya_notlari SET tarih = ?, not_icerik = ? WHERE id = ?", (str(edt_n_date), edt_n_text.strip(), sel_not_id))
                                        conn.commit()
                                        st.success("Not başarıyla güncellendi!")
                                        st.rerun()
                                    else:
                                        st.warning("Not içeriği boş bırakılamaz.")
                            with btn_n_col2:
                                if st.button("🗑️ Bu Notu Sil", key=f"btn_del_note_{sel_not_id}", use_container_width=True):
                                    cursor.execute("DELETE FROM dosya_notlari WHERE id = ?", (sel_not_id,))
                                    conn.commit()
                                    st.success("Not silindi!")
                                    st.rerun()
                        else:
                            st.info("Bu dosyaya ait henüz kayıtlı bir not bulunmuyor.")

                    with t_rapor:
                        st.markdown("##### 📑 Executive Müvekkil Sunum Raporu (.xlsx)")
                        st.caption("Doğrudan müvekkilinize sunabileceğiniz renk kodlu, antetli ve resmi icra döküm cetveli üretin.")
                        
                        rc1, rc2 = st.columns(2)
                        with rc1:
                            c_genel = st.checkbox("Dosya & Taraf Bilgileri", value=True, key="c_g")
                            c_finans = st.checkbox("Mali Hesap Cetveli (Harçlar Dahil)", value=True, key="c_f")
                            c_tahsil = st.checkbox("Mahsup & Tahsilat Dökümü", value=True, key="c_t")
                        with rc2:
                            c_masraf = st.checkbox("Masraf ve İade Tablosu", value=True, key="c_m")
                            c_not = st.checkbox("Tarihli Dosya Notları", value=True, key="c_n")

                        rapor_veri_paketi = {
                            "alacakli": secili_dosya['alacakli'],
                            "borclu": secili_dosya['borclu'],
                            "takip_turu": secili_dosya['takip_turu'],
                            "icra_dairesi": secili_dosya['icra_dairesi'],
                            "dosya_no": secili_dosya['dosya_no'],
                            "takip_tarihi": secili_dosya['takip_tarihi'],
                            "durum": secili_dosya['durum'],
                            "İtiraz": secili_dosya['İtiraz'],
                            "ana_para": float(secili_dosya['ana_para']),
                            "t_oncesi_faiz": float(secili_dosya['t_oncesi_faiz']),
                            "rem_pre_i": rem_pre_i,
                            "rem_post_i": rem_post_i,
                            "takip_cikisi": float(secili_dosya['takip_cikisi']),
                            "vekalet_ucreti": float(secili_dosya['vekalet_ucreti']),
                            "faiz_orani": float(secili_dosya['faiz_orani']),
                            "rem_p": rem_p,
                            "rem_i": rem_i,
                            "top_masraf": top_masraf,
                            "top_iade": top_iade,
                            "net_masraf": net_masraf,
                            "tahsil_harci": tahsil_harci_tutar,
                            "cezaevi_harci": cezaevi_harci_tutar,
                            "tahsil_harci_safhasi": str(secili_dosya.get('tahsil_harci_safhasi', 'Standart')),
                            "tahsil_harci_orani": s_th_oran,
                            "cezaevi_harci_orani": s_ch_oran,
                            "tot_pay": tot_pay,
                            "kalan_toplam_dosya_borcu": kalan_toplam_dosya_borcu
                        }

                        secenek_paketi = {
                            "genel": c_genel,
                            "finans": c_finans,
                            "tahsilat": c_tahsil,
                            "masraf": c_masraf,
                            "notlar": c_not
                        }

                        excel_bytes = build_executive_excel(rapor_veri_paketi, mahsup_list, masraf_df, notlar_df, secenek_paketi)

                        st.download_button(
                            "📥 Kurumsal Excel Raporunu İndir (.xlsx)",
                            data=excel_bytes,
                            file_name=f"{secili_dosya['borclu'][:20]}_Hesap_Cetveli.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            type="primary"
                        )

                    with t_ayar:
                        st.markdown("##### ⚙️ Dosya Parametrelerini Güncelle")
                        p_parca = str(secili_dosya['dosya_no']).replace(" E.", "").split("/")
                        v_yil = p_parca[0] if len(p_parca) == 2 and p_parca[0] in YILLAR_LISTESI else "2026"
                        v_sira = p_parca[1] if len(p_parca) == 2 else str(secili_dosya['dosya_no'])

                        ed_c1, ed_c2 = st.columns(2)
                        with ed_c1:
                            e_tur = st.selectbox("Takip Türü", TAKIP_TURLERI, index=TAKIP_TURLERI.index(secili_dosya['takip_turu']) if secili_dosya['takip_turu'] in TAKIP_TURLERI else 0)
                            e_il = st.selectbox("İl", list(TURKIYE_IL_ILCE.keys()), index=list(TURKIYE_IL_ILCE.keys()).index(secili_dosya['il']) if secili_dosya['il'] in TURKIYE_IL_ILCE else 0)
                            e_ilce = st.selectbox("İlçe", TURKIYE_IL_ILCE.get(e_il, ["Merkez"]))
                            e_daire = st.selectbox("İcra Dairesi", ICRA_DAIRE_LISTESI, index=ICRA_DAIRE_LISTESI.index(secili_dosya['icra_dairesi']) if secili_dosya['icra_dairesi'] in ICRA_DAIRE_LISTESI else 0)
                            
                            sub_y1, sub_y2 = st.columns([1, 2])
                            with sub_y1:
                                e_yil = st.selectbox("Yıl", YILLAR_LISTESI, index=YILLAR_LISTESI.index(v_yil))
                            with sub_y2:
                                e_sira = st.text_input("Esas No", value=v_sira)
                            e_tam_no = f"{e_yil}/{e_sira} E."
                            e_tarih = st.date_input("Takip Tarihi", value=datetime.strptime(str(secili_dosya['takip_tarihi']), "%Y-%m-%d").date())

                        with ed_c2:
                            e_alacakli = st.selectbox("Alacaklı", taraflar_list, index=taraflar_list.index(secili_dosya['alacakli']) if secili_dosya['alacakli'] in taraflar_list else 0)
                            m_borclular = [b.strip() for b in str(secili_dosya['borclu']).split(",") if b.strip() in taraflar_list]
                            e_borclular = st.multiselect("Borçlular", taraflar_list, default=m_borclular)
                            e_b_str = ", ".join(e_borclular) if e_borclular else secili_dosya['borclu']
                            
                            e_anapara = parse_tr_money(st.text_input("Asıl Alacak", value=str(secili_dosya['ana_para']).replace(".", ",")))
                            e_toncesi = parse_tr_money(st.text_input("Takip Öncesi Faiz", value=str(secili_dosya['t_oncesi_faiz']).replace(".", ",")))
                            
                            cur_faiz_turu = str(secili_dosya.get('faiz_turu', 'Ticari Avans Faizi (%48.00)'))
                            fz_idx = FAIZ_TURLERI_LISTESI.index(cur_faiz_turu) if cur_faiz_turu in FAIZ_TURLERI_LISTESI else 0
                            e_faiz_tipi = st.selectbox("Faiz Türü", FAIZ_TURLERI_LISTESI, index=fz_idx)
                            if e_faiz_tipi == "Ticari Avans Faizi (%48.00)":
                                e_oran = 48.0
                            elif e_faiz_tipi == "TCMB Reeskont Faizi (%39.75)":
                                e_oran = 39.75
                            elif "Yasal Faiz" in e_faiz_tipi:
                                e_oran = 31.0
                            elif e_faiz_tipi == "Faizsiz":
                                e_oran = 0.0
                            else:
                                e_oran = st.number_input("Faiz Oranı (%)", value=float(secili_dosya['faiz_orani']), step=0.5)

                            st.markdown("---")
                            st.markdown("##### ⚖️ Harç Parametreleri")
                            cur_safha = str(secili_dosya.get('tahsil_harci_safhasi', 'Ödeme Emri Tebliğinden Sonra, Hacizden Önce (%9.10)'))
                            th_keys = list(TAHSIL_HARCI_SECENEKLERI.keys())
                            th_idx = th_keys.index(cur_safha) if cur_safha in th_keys else 0
                            e_th_secim = st.selectbox("Tahsil Harcı Safhası", th_keys, index=th_idx, key="edit_th_secim")
                            
                            if TAHSIL_HARCI_SECENEKLERI[e_th_secim] == -1.0:
                                e_th_oran = st.number_input("Özel Tahsil Harcı Oranı (%)", value=float(secili_dosya.get('tahsil_harci_orani', 9.10)), step=0.1, key="edit_th_custom")
                            else:
                                e_th_oran = TAHSIL_HARCI_SECENEKLERI[e_th_secim]

                            cur_ch_oran = float(secili_dosya.get('cezaevi_harci_orani', 2.00) if pd.notnull(secili_dosya.get('cezaevi_harci_orani')) else 2.00)
                            ch_keys = list(CEZAEVI_HARCI_SECENEKLERI.keys())
                            ch_idx = 0 if cur_ch_oran > 0 else 1
                            e_ch_secim = st.selectbox("Cezaevi Harcı", ch_keys, index=ch_idx, key="edit_ch_secim")
                            e_ch_oran = CEZAEVI_HARCI_SECENEKLERI[e_ch_secim]

                        e_cikis = e_anapara + e_toncesi
                        e_vekalet = hesapla_icra_vekalet_ucreti(e_cikis)

                        if st.button("Bilgileri Güncelle", type="primary"):
                            if e_faiz_tipi != "Özel Oran":
                                final_e_oran = get_faiz_default_rate(e_faiz_tipi)
                            else:
                                final_e_oran = float(e_oran)

                            cursor.execute("SELECT COUNT(*), SUM(tutar), SUM(t_oncesi_faiz) FROM alacak_kalemleri WHERE dosya_id = ?", (secili_id,))
                            k_cnt, sum_t, sum_f = cursor.fetchone()
                            
                            # Eğer alacak kalemleri varsa
                            if k_cnt and k_cnt > 0:
                                cursor.execute("""
                                UPDATE alacak_kalemleri 
                                SET faiz_turu = ?, faiz_orani = ? 
                                WHERE dosya_id = ? AND faiz_turu != 'Faizsiz'
                                """, (e_faiz_tipi, final_e_oran, secili_id))

                                if k_cnt == 1:
                                    cursor.execute("UPDATE alacak_kalemleri SET tutar = ?, t_oncesi_faiz = ? WHERE dosya_id = ?", (e_anapara, e_toncesi, secili_id))
                                    tot_p = e_anapara
                                    tot_i = e_toncesi
                                else:
                                    tot_p = sum_t or 0.0
                                    tot_i = sum_f or 0.0
                            else:
                                tot_p = e_anapara
                                tot_i = e_toncesi

                            e_cikis = tot_p + tot_i
                            e_vekalet = hesapla_icra_vekalet_ucreti(e_cikis)

                            cursor.execute("""
                            UPDATE dosyalar 
                            SET il = ?, ilce = ?, icra_dairesi = ?, dosya_no = ?, alacakli = ?, borclu = ?, takip_turu = ?, takip_tarihi = ?, 
                                ana_para = ?, t_oncesi_faiz = ?, takip_cikisi = ?, vekalet_ucreti = ?, faiz_turu = ?, faiz_orani = ?,
                                tahsil_harci_safhasi = ?, tahsil_harci_orani = ?, cezaevi_harci_orani = ?
                            WHERE id = ?
                            """, (e_il, e_ilce, e_daire, e_tam_no, e_alacakli, e_b_str, e_tur, str(e_tarih), tot_p, tot_i, e_cikis, e_vekalet, e_faiz_tipi, final_e_oran, e_th_secim, e_th_oran, e_ch_oran, secili_id))

                            conn.commit()
                            st.success("Dosya bilgileri, faiz oranları ve alacak toplamları başarıyla güncellendi!")
                            st.rerun()

                        st.write("")
                        if st.button("🗑️ Dosyayı Kalıcı Olarak Sil"):
                            cursor.execute("DELETE FROM dosyalar WHERE id = ?", (secili_id,))
                            cursor.execute("DELETE FROM tahsilatlar WHERE dosya_id = ?", (secili_id,))
                            cursor.execute("DELETE FROM masraflar WHERE dosya_id = ?", (secili_id,))
                            cursor.execute("DELETE FROM dosya_notlari WHERE dosya_id = ?", (secili_id,))
                            conn.commit()
                            st.session_state["aktif_dosya_id"] = None
                            st.rerun()

                # SAĞ: CANLI MALİ CETVEL
                with col_sag:
                    # Anlık Tahsil Harcı Safhası Değiştirme (Hızlı Geçiş)
                    st.markdown("##### ⚡ Harç Safhası Seçimi")
                    cur_th_safha = str(secili_dosya.get('tahsil_harci_safhasi', 'Ödeme Emri Tebliğinden Sonra, Hacizden Önce (%9.10)'))
                    th_list_keys = list(TAHSIL_HARCI_SECENEKLERI.keys())
                    th_idx_live = th_list_keys.index(cur_th_safha) if cur_th_safha in th_list_keys else 0
                    
                    secilen_hizli_safha = st.selectbox(
                        "Tahsil Harcı Safhası",
                        th_list_keys,
                        index=th_idx_live,
                        key=f"quick_th_safha_{secili_id}",
                        label_visibility="collapsed"
                    )

                    # Eğer kullanıcı sağ panelden safhayı değiştirirse anında veritabanına kaydet
                    if secilen_hizli_safha != cur_th_safha:
                        yeni_oran_hizli = TAHSIL_HARCI_SECENEKLERI[secilen_hizli_safha]
                        if yeni_oran_hizli != -1.0:
                            cursor.execute("UPDATE dosyalar SET tahsil_harci_safhasi = ?, tahsil_harci_orani = ? WHERE id = ?", (secilen_hizli_safha, yeni_oran_hizli, secili_id))
                            conn.commit()
                            st.rerun()

                    # Cezaevi Harcı Hızlı Aç/Kapat
                    ch_live_tog = st.toggle("🚫 Cezaevi Harcını Hariç Tut (%2)", value=ch_is_haric, key=f"col_sag_ch_{secili_id}")
                    if ch_live_tog != ch_is_haric:
                        st.session_state[f"ch_haric_{secili_id}"] = ch_live_tog
                        st.rerun()

                    gosterim_orani = secili_dosya['faiz_orani']
                    if not ak_df.empty and not ak_df[ak_df['faiz_turu'] != 'Faizsiz'].empty:
                        gosterim_orani = float(ak_df[ak_df['faiz_turu'] != 'Faizsiz']['faiz_orani'].iloc[0])

                    if is_infaz:
                        badge_durum = f"🔒 {secili_dosya['durum']}"
                        borc_box_html = f"""<div class="financial-total-box" style="background: linear-gradient(135deg, #059669 0%, #10B981 100%);">
<div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #FFFFFF; font-weight: 600;">DOSYA İNFAZ EDİLDİ / KAPANDI</div>
<div style="font-size: 22px; font-weight: 700; color: #FFFFFF; margin-top: 2px;">0,00 TL</div>
</div>"""
                        kalan_vekalet_str = "0,00 TL (Tahsil Edildi)"
                        kalan_th_str = "0,00 TL (Tahsil Edildi)"
                        cezaevi_row = f'<div class="financial-row" style="color: #94A3B8;"><span>Cezaevi Harcı (%{s_ch_oran:.2f}):</span><strong>0,00 TL (Tahsil Edildi)</strong></div>'
                    else:
                        badge_durum = str(secili_dosya['durum'])
                        toplam_etiket = "GÜNCEL TOPLAM BORÇ (CEZAEVİ HARİÇ)" if ch_is_haric else "GÜNCEL TOPLAM BORÇ (HARÇLAR DAHİL)"
                        borc_box_html = f"""<div class="financial-total-box">
<div style="font-size: 11px; text-transform: uppercase; letter-spacing: 0.5px; color: #FFFFFF; font-weight: 600;">{toplam_etiket}</div>
<div style="font-size: 20px; font-weight: 700; color: #FFFFFF; margin-top: 2px;">{format_tr_money(kalan_toplam_dosya_borcu)}</div>
</div>"""
                        kalan_vekalet_str = format_tr_money(kalan_vekalet)
                        kalan_th_str = format_tr_money(kalan_th)
                        cezaevi_row = f'<div class="financial-row" style="color: #94A3B8;"><span>Cezaevi Harcı (%{s_ch_oran:.2f}) [Hariç]:</span><strong>0,00 TL</strong></div>' if ch_is_haric else f'<div class="financial-row"><span>Kalan Cezaevi Harcı (%{s_ch_oran:.2f}):</span><strong>{format_tr_money(kalan_ch)}</strong></div>'

                    html_content = f"""<div class="financial-card">
<div class="financial-card-header">
<span style="font-weight: 600; font-size: 13.5px; color: {accent_green};">📊 Canlı Dosya Hesabı</span>
<span style="font-size: 11px; background-color: {card_border}; padding: 2px 6px; border-radius: 4px; color: {text_main}; font-weight: 600;">{badge_durum}</span>
</div>
<div class="financial-row"><span>Takip Açılış Tarihi:</span><strong style="color:{accent_green};">📅 {secili_dosya['takip_tarihi']}</strong></div>
<div class="financial-row"><span>Asıl Alacak:</span><strong>{format_tr_money(secili_dosya['ana_para'])}</strong></div>
<div class="financial-row"><span>Kalan Takip Öncesi Faiz:</span><strong>{format_tr_money(rem_pre_i)}</strong></div>
<div class="financial-row"><span>Takip Açılış Çıkışı:</span><strong>{format_tr_money(secili_dosya['takip_cikisi'])}</strong></div>
<div class="financial-row"><span>Kalan Vekalet Ücreti:</span><strong>{kalan_vekalet_str}</strong></div>
<div class="financial-row" style="background-color: {card_bg};"><span>Takip Sonrası İşlemiş Faiz (%{float(gosterim_orani):.2f}):</span><strong style="color:{accent_green};">{format_tr_money(rem_post_i)}</strong></div>
<div class="financial-row"><span>Kalan Ana Para:</span><strong>{format_tr_money(rem_p)}</strong></div>
<div class="financial-row"><span>Toplam Yapılan Masraf:</span><strong>{format_tr_money(top_masraf)}</strong></div>
<div class="financial-row"><span>Masraf İadeleri (-):</span><strong>{format_tr_money(top_iade)}</strong></div>
<div class="financial-row"><span>Net Masraf Bakiyesi:</span><strong>{format_tr_money(net_masraf)}</strong></div>
<div class="financial-row"><span>Kalan Tahsil Harcı (%{s_th_oran:.2f}):</span><strong>{kalan_th_str}</strong></div>
{cezaevi_row}
<div class="financial-row" style="color: {accent_green};"><span>Toplam Tahsil Edilen (-):</span><strong style="color: {accent_green};">{format_tr_money(tot_pay)}</strong></div>
{borc_box_html}
</div>"""
                    st.markdown(html_content, unsafe_allow_html=True)
    else:
        st.info("Kriterlere uygun icra dosyası bulunamadı.")

# -------------------------------------------------------------
# 9. MODÜL 2: MÜVEKKİL CARİ PORTFÖY RAPORU
# -------------------------------------------------------------
elif menu == "Müvekkil Portföy & Raporlama":
    st.markdown(f"<h2 style='color:{accent_green};'>🏢 Müvekkil Cari Portföy & Konsolide Özet Rapor</h2>", unsafe_allow_html=True)
    st.caption("Seçilen müvekkilin tüm dosyalarını tek sayfada; toplam alacak, toplam tahsilat ve son notlar dahil olacak şekilde özetleyin.")

    alacaklilar = pd.read_sql_query("SELECT DISTINCT alacakli FROM dosyalar WHERE alacakli IS NOT NULL AND alacakli != '' ORDER BY alacakli", conn)['alacakli'].tolist()

    if not alacaklilar:
        st.info("Sistemde henüz kayıtlı bir dosya bulunmuyor.")
    else:
        secilen_muvekkil = st.selectbox("Raporlanacak Müvekkil Cari Seçin", alacaklilar)
        m_dosyalar = pd.read_sql_query("SELECT * FROM dosyalar WHERE alacakli = ? ORDER BY id DESC", conn, params=[secilen_muvekkil])

        st.markdown(f"**{secilen_muvekkil}** cari kartına bağlı toplam **{len(m_dosyalar)}** adet icra dosyası tespit edildi.")

        m_ids = f"({','.join(map(str, m_dosyalar['id'].tolist()))})"
        m_all_t = pd.read_sql_query(f"SELECT * FROM tahsilatlar WHERE dosya_id IN {m_ids} ORDER BY tarih ASC", conn)
        m_all_m = pd.read_sql_query(f"SELECT * FROM masraflar WHERE dosya_id IN {m_ids} ORDER BY tarih ASC", conn)
        m_all_n = pd.read_sql_query(f"SELECT * FROM dosya_notlari WHERE dosya_id IN {m_ids} ORDER BY tarih DESC", conn)
        m_all_ak = pd.read_sql_query(f"SELECT * FROM alacak_kalemleri WHERE dosya_id IN {m_ids}", conn)

        m_t_grp = dict(tuple(m_all_t.groupby("dosya_id"))) if not m_all_t.empty else {}
        m_m_grp = dict(tuple(m_all_m.groupby("dosya_id"))) if not m_all_m.empty else {}
        m_n_grp = dict(tuple(m_all_n.groupby("dosya_id"))) if not m_all_n.empty else {}
        m_ak_grp = dict(tuple(m_all_ak.groupby("dosya_id"))) if not m_all_ak.empty else {}

        m_emp_t = pd.DataFrame(columns=["id", "dosya_id", "tarih", "tutar", "aciklama"])
        m_emp_m = pd.DataFrame(columns=["id", "dosya_id", "tarih", "aciklama", "masraf_tutari", "iade_tutari"])
        m_emp_n = pd.DataFrame(columns=["id", "dosya_id", "tarih", "not_icerik"])
        m_emp_ak = pd.DataFrame(columns=["id", "dosya_id", "kalem_adi", "tutar", "t_oncesi_faiz", "faiz_turu", "faiz_orani", "kalem_turu", "sorumlu_borclular"])

        rapor_satirlari = []
        for _, d_row in m_dosyalar.iterrows():
            d_id = int(d_row['id'])
            t_df = m_t_grp.get(d_id, m_emp_t)
            m_df = m_m_grp.get(d_id, m_emp_m)
            n_df = m_n_grp.get(d_id, m_emp_n)
            m_ak_df = m_ak_grp.get(d_id, m_emp_ak)

            rem_p, rem_i, tot_pay, *_ = hesapla_kademeli_dosya_hesabi(
                d_row['ana_para'], d_row['faiz_orani'], d_row['takip_tarihi'], d_row['t_oncesi_faiz'], t_df,
                faiz_turu=d_row.get('faiz_turu', 'Özel Oran'),
                masraflar_df=m_df,
                alacak_kalemleri_df=m_ak_df
            )

            is_infaz = bool(re.search(r"Kapatıldı|İnfaz|Kapalı", str(d_row.get('durum', '')), re.I))
            kalan_alacak_goster = 0.0 if is_infaz else float(rem_p)

            not_metinleri = [nr['not_icerik'] for _, nr in n_df.iterrows()]
            son_not = not_metinleri[0] if not_metinleri else "İşlem aşamasında."

            rapor_satirlari.append({
                "dosya_id": d_id,
                "Dosya No / Daire": f"{d_row['il']} {d_row['icra_dairesi']} {d_row['dosya_no']}",
                "Borçlu(lar)": str(d_row['borclu']),
                "Takip Türü": str(d_row.get('takip_turu', 'Örnek No: 7')),
                "Başlangıç Asıl Alacak": float(d_row['ana_para']),
                "Tahsil Edilen": float(tot_pay),
                "Kalan Asıl Alacak": kalan_alacak_goster,
                "Dosya Statüsü": f"{d_row['durum']} ({'İtirazlı' if d_row['itiraz_edildi']==1 else 'Normal'})",
                "Müvekkile Rapor Notu": son_not
            })

        df_rapor = pd.DataFrame(rapor_satirlari)

        st.write("")
        st.markdown(f"#### 📝 {secilen_muvekkil} - Düzenlenebilir Durum Raporu")
        st.caption("Tablodaki hücrelere doğrudan tıklayarak açıklamaları, statüleri veya tutarları müvekkile sunmadan önce dilediğiniz gibi düzenleyebilirsiniz. Yapılan düzenlemeler Excel çıktısına birebir yansır.")

        editor_key = f"rapor_editor_{secilen_muvekkil}"
        edited_report = st.data_editor(
            df_rapor,
            key=editor_key,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "dosya_id": None,
                "Başlangıç Asıl Alacak": st.column_config.NumberColumn(format="%.2f TL"),
                "Tahsil Edilen": st.column_config.NumberColumn(format="%.2f TL"),
                "Kalan Asıl Alacak": st.column_config.NumberColumn(format="%.2f TL"),
                "Müvekkile Rapor Notu": st.column_config.TextColumn(width="large")
            }
        )

        col_save_rep_btn, _ = st.columns([1, 1])
        with col_save_rep_btn:
            if st.button("💾 Düzenlenen Rapor Notlarını Dosya Geçmişine Kalıcı Kaydet", key=f"btn_save_report_notes_{secilen_muvekkil}"):
                kaydedilen = 0
                for _, r_item in edited_report.iterrows():
                    d_id_val = r_item.get("dosya_id")
                    cur_not_txt = str(r_item.get("Müvekkile Rapor Notu", "")).strip()
                    if d_id_val and cur_not_txt:
                        cursor.execute("INSERT INTO dosya_notlari (dosya_id, tarih, not_icerik) VALUES (?, ?, ?)", (int(d_id_val), str(date.today()), cur_not_txt))
                        kaydedilen += 1
                conn.commit()
                st.success(f"✅ {kaydedilen} dosyanın rapor notu dosya geçmişine başarıyla kaydedildi!")
                st.rerun()

        top_baslangic = float(edited_report["Başlangıç Asıl Alacak"].sum()) if not edited_report.empty else 0.0
        top_tahsilat = float(edited_report["Tahsil Edilen"].sum()) if not edited_report.empty else 0.0
        top_kalan = float(edited_report["Kalan Asıl Alacak"].sum()) if not edited_report.empty else 0.0

        st.write("")
        rk1, rk2, rk3, rk4 = st.columns(4)
        rk1.metric("Toplam Dosya", f"{len(edited_report)} Adet")
        rk2.metric("Portföy Asıl Alacak", format_tr_money(top_baslangic))
        rk3.metric("Tahsil Edilen Tutar", format_tr_money(top_tahsilat))
        rk4.metric("Kalan Müvekkil Alacağı", format_tr_money(top_kalan))

        # Excel Export of the Edited Data
        wb_c = openpyxl.Workbook()
        ws_c = wb_c.active
        ws_c.title = "Müvekkil Durum Özeti"
        ws_c.views.sheetView[0].showGridLines = True

        fill_header = PatternFill(start_color="084840", end_color="084840", fill_type="solid")
        fill_sub = PatternFill(start_color="1F2421", end_color="1F2421", fill_type="solid")
        fill_zebra = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
        fill_total = PatternFill(start_color="084840", end_color="084840", fill_type="solid")

        font_title = Font(name="Arial", size=13, bold=True, color="FFFFFF")
        font_sub = Font(name="Arial", size=10, bold=True, color="FFFFFF")
        font_reg = Font(name="Arial", size=10, color="000000")
        font_total = Font(name="Arial", size=11, bold=True, color="FFFFFF")

        thin_border = Border(
            left=Side(style='thin', color='D1D5DB'), right=Side(style='thin', color='D1D5DB'),
            top=Side(style='thin', color='D1D5DB'), bottom=Side(style='thin', color='D1D5DB')
        )

        ws_c.merge_cells("A1:H1")
        ws_c["A1"] = f"JUS LEGAL | {secilen_muvekkil.upper()} İCRA PORTFÖYÜ DURUM RAPORU"
        ws_c["A1"].font = font_title
        ws_c["A1"].fill = fill_header
        ws_c["A1"].alignment = Alignment(horizontal="center", vertical="center")
        ws_c.row_dimensions[1].height = 36

        ws_c.merge_cells("A2:H2")
        ws_c["A2"] = f"Rapor Tarihi: {datetime.now().strftime('%d.%m.%Y')} | Toplam Dosya: {len(edited_report)}"
        ws_c["A2"].font = Font(name="Arial", size=9, italic=True, color="334155")
        ws_c["A2"].alignment = Alignment(horizontal="center", vertical="center")
        ws_c.row_dimensions[2].height = 20

        headers_c = [
            "Dosya No / İcra Dairesi", 
            "Borçlu Firma / Kişi", 
            "Takip Türü", 
            "Asıl Alacak", 
            "Tahsil Edilen", 
            "Kalan Asıl Alacak", 
            "Dosya Statüsü", 
            "Müvekkile Rapor Notu / Son Durum"
        ]

        for c_i, h_txt in enumerate(headers_c, start=1):
            c = ws_c.cell(row=4, column=c_i, value=h_txt)
            c.fill = fill_sub
            c.font = font_sub
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = thin_border
        ws_c.row_dimensions[4].height = 26

        row_p = 5
        for _, row_data in edited_report.iterrows():
            vals = [
                str(row_data["Dosya No / Daire"]),
                str(row_data["Borçlu(lar)"]),
                str(row_data["Takip Türü"]),
                float(row_data["Başlangıç Asıl Alacak"]),
                float(row_data["Tahsil Edilen"]),
                float(row_data["Kalan Asıl Alacak"]),
                str(row_data["Dosya Statüsü"]),
                str(row_data["Müvekkile Rapor Notu"])
            ]
            for col_idx, val in enumerate(vals, start=1):
                cell = ws_c.cell(row=row_p, column=col_idx, value=val)
                cell.font = font_reg
                cell.border = thin_border
                if isinstance(val, (float, int)) and col_idx in [4, 5, 6]:
                    cell.number_format = '#,##0.00 "TL"'
                    cell.alignment = Alignment(horizontal="right", vertical="top")
                else:
                    cell.alignment = Alignment(horizontal="center" if col_idx in [1, 3, 7] else "left", vertical="top", wrap_text=(col_idx == 8))
                if row_p % 2 == 1:
                    cell.fill = fill_zebra
            ws_c.row_dimensions[row_p].height = 36
            row_p += 1

        ws_c.cell(row=row_p, column=1, value="TOPLAM PORTFÖY ÖZETİ").font = font_total
        ws_c.merge_cells(start_row=row_p, start_column=1, end_row=row_p, end_column=3)

        totals_map = {
            4: top_baslangic,
            5: top_tahsilat,
            6: top_kalan
        }

        for col_idx in range(1, 9):
            c_tot = ws_c.cell(row=row_p, column=col_idx)
            c_tot.fill = fill_total
            c_tot.font = font_total
            c_tot.border = thin_border
            if col_idx in totals_map:
                c_tot.value = totals_map[col_idx]
                c_tot.number_format = '#,##0.00 "TL"'
                c_tot.alignment = Alignment(horizontal="right", vertical="center")
        ws_c.row_dimensions[row_p].height = 28

        ws_c.column_dimensions["A"].width = 28
        ws_c.column_dimensions["B"].width = 26
        ws_c.column_dimensions["C"].width = 24
        ws_c.column_dimensions["D"].width = 20
        ws_c.column_dimensions["E"].width = 20
        ws_c.column_dimensions["F"].width = 20
        ws_c.column_dimensions["G"].width = 20
        ws_c.column_dimensions["H"].width = 50

        buf_c = io.BytesIO()
        wb_c.save(buf_c)
        buf_c.seek(0)

        st.write("")
        st.download_button(
            label="📥 Düzenlenmiş Müvekkil Raporunu İndir (.xlsx)",
            data=buf_c,
            file_name=f"{secilen_muvekkil}_Muvakkil_Durum_Raporu.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
            use_container_width=True
        )

# -------------------------------------------------------------
# 10. MODÜL 3: YENİ DOSYA AÇILIŞI
# -------------------------------------------------------------
elif menu == "Yeni Dosya Açılışı":
    st.markdown(f"<h2 style='color:{accent_green};'>📁 Yeni İcra Dosyası Oluştur</h2>", unsafe_allow_html=True)
    st.caption("Aşağıdaki formu elle doldurabilir veya UYAP'tan indirdiğiniz Takip Talebi / Ödeme Emri (.udf) dosyasını yükleyerek tüm bilgilerin saniyeler içinde otomatik dolmasını sağlayabilirsiniz.")

    # -------------------------------------------------------------
    # UYAP UDF SÜRÜKLE-BIRAK ENTEGRASYONU
    # -------------------------------------------------------------
    with st.container():
        udf_c1, udf_c2 = st.columns([3, 1])
        with udf_c1:
            yuklenen_udfler = st.file_uploader(
                "📂 UYAP .udf Dosyalarını Sürükleyip Bırakın (Ödeme Emri, Takip Talebi vb.)",
                type=["udf"],
                accept_multiple_files=True,
                help="Ödeme Emri ve Takip Talebini birlikte veya tek tek yükleyebilirsiniz. İkisi birlikte yüklendiğinde; Daire ve Esas No Ödeme Emrinden, Takip Açılış Tarihi Takip Talebinden alınarak harmanlanır."
            )
        with udf_c2:
            st.write("")
            st.write("")
            if st.button("🗑️ Formu Temizle / Sıfırla", use_container_width=True):
                st.session_state["udf_data"] = None
                st.session_state["son_yuklenen_udf_ad"] = None
                st.session_state["form_kalemler_list"] = None
                st.rerun()

        if yuklenen_udfler:
            imza_adlari = "+".join(sorted([f.name for f in yuklenen_udfler]))
            if ("son_yuklenen_udf_ad" not in st.session_state or st.session_state["son_yuklenen_udf_ad"] != imza_adlari):
                p_data, p_err = parse_udf_files(yuklenen_udfler)
                if p_err:
                    st.error(f"❌ {p_err}")
                elif p_data:
                    st.session_state["son_yuklenen_udf_ad"] = imza_adlari
                    st.session_state["udf_data"] = p_data
                    
                    # Otomatik Taraf Tanımlama (Cari yoksa hemen ekle veya VKN güncelle)
                    alc = p_data.get("alacakli", "").strip()
                    alc_vkn = p_data.get("alacakli_vkn", "").strip()
                    if alc:
                        cursor.execute("SELECT id, tc_vkn FROM taraflar WHERE ad_unvan = ?", (alc,))
                        row = cursor.fetchone()
                        if not row:
                            alc_tip = "Tüzel Kişi (Şirket/Kurum)" if any(k in alc.upper() for k in ["A.Ş", "LTD", "ŞTİ", "TİC", "SAN", "BANKA"]) else "Gerçek Kişi (Şahıs)"
                            cursor.execute("INSERT INTO taraflar (tip, ad_unvan, tc_vkn) VALUES (?, ?, ?)", (alc_tip, alc, alc_vkn))
                            conn.commit()
                        elif alc_vkn and not row[1]:
                            cursor.execute("UPDATE taraflar SET tc_vkn = ? WHERE id = ?", (alc_vkn, row[0]))
                            conn.commit()

                    for b in p_data.get("borclular", []):
                        b_name = b.get("ad_unvan", "").strip()
                        b_vkn = b.get("tc_vkn", "").strip()
                        if b_name:
                            cursor.execute("SELECT id, tc_vkn FROM taraflar WHERE ad_unvan = ?", (b_name,))
                            row = cursor.fetchone()
                            if not row:
                                b_tip = "Tüzel Kişi (Şirket/Kurum)" if any(k in b_name.upper() for k in ["A.Ş", "LTD", "ŞTİ", "TİC", "SAN", "BANKA"]) else "Gerçek Kişi (Şahıs)"
                                cursor.execute("INSERT INTO taraflar (tip, ad_unvan, tc_vkn) VALUES (?, ?, ?)", (b_tip, b_name, b_vkn))
                                conn.commit()
                            elif b_vkn and not row[1]:
                                cursor.execute("UPDATE taraflar SET tc_vkn = ? WHERE id = ?", (b_vkn, row[0]))
                                conn.commit()

                    st.success(f"✅ UDF Başarıyla Ayrıştırıldı: **{p_data.get('dosya_no', 'Dosya')}** | {len(p_data.get('borclular', []))} Borçlu ve Müvekkil sisteme işlendi.")
                    st.rerun()

    udf_aktif = st.session_state.get("udf_data", None)

    if udf_aktif:
        udf_dup_file = check_existing_dosya(
            cursor, 
            udf_aktif.get("il"), 
            udf_aktif.get("ilce"), 
            udf_aktif.get("icra_dairesi"), 
            udf_aktif.get("yil"), 
            udf_aktif.get("sira_no")
        )
        if udf_dup_file:
            st.markdown(f"""
            <div style="background: rgba(239, 68, 68, 0.12); border: 2px solid #EF4444; border-radius: 8px; padding: 12px 16px; margin-bottom: 14px;">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                    <span style="font-weight: 700; color: #EF4444; font-size: 14px;">⚠️ MÜKERRER DOSYA UYARISI: Bu Belge Sistemde Zaten Kayıtlı!</span>
                    <span style="font-size: 11.5px; font-weight: 600; color: #EF4444; background: rgba(239, 68, 68, 0.18); padding: 2px 8px; border-radius: 4px;">Kayıt No: #{udf_dup_file['id']}</span>
                </div>
                <div style="font-size: 12.5px; line-height: 1.6;">
                    Yüklenen UDF belgesi (<b>{udf_dup_file['il']} {udf_dup_file['ilce']} / {udf_dup_file['icra_dairesi']} - {udf_dup_file['dosya_no']}</b>) sistemde mevcuttur.<br>
                    👤 <b>Mevcut Alacaklı:</b> {udf_dup_file['alacakli']} &nbsp;|&nbsp; 👥 <b>Borçlu:</b> {udf_dup_file['borclu']}<br>
                    📅 <b>Takip Açılışı:</b> {udf_dup_file['takip_tarihi']} &nbsp;|&nbsp; 💰 <b>Takip Çıkışı:</b> {format_tr_money(udf_dup_file['takip_cikisi'])}
                </div>
            </div>
            """, unsafe_allow_html=True)
            col_u_dup1, col_u_dup2 = st.columns([1, 2])
            with col_u_dup1:
                if st.button("🔍 Kayıtlı Dosyaya Git & İncele", key="btn_goto_udf_dup", use_container_width=True, type="primary"):
                    st.session_state["nav_menu_radio"] = "Dosya Arama & Çalışma Masası"
                    st.session_state["dosya_tab_filtre"] = "Tümü"
                    st.session_state["aktif_dosya_id"] = udf_dup_file["id"]
                    st.rerun()
            with col_u_dup2:
                st.caption("ℹ️ Dosya numarasını veya icra dairesini değiştirerek devam edebilir veya mevcut dosyayı açabilirsiniz.")

        st.markdown(f"""
        <div style="background: rgba(16, 185, 129, 0.08); border: 1.5px solid #10B981; border-radius: 8px; padding: 12px 16px; margin-bottom: 18px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px;">
                <span style="font-weight: 700; color: #10B981; font-size: 14px;">📋 Otomatik UDF Harmanlama Özeti</span>
                <span style="font-size: 11.5px; color: #9CA3AF;">Belgeler: {len(udf_aktif.get('yuklenen_dosyalar', []))} dosya</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px; font-size: 12px;">
                <div>📍 <strong>Daire & Dosya:</strong> {udf_aktif.get('il', '')} / {udf_aktif.get('ilce', '')} - <b>{udf_aktif.get('dosya_no', '')}</b></div>
                <div>📅 <strong>Takip Açılışı:</strong> {udf_aktif.get('takip_tarihi', '').strftime('%d.%m.%Y') if hasattr(udf_aktif.get('takip_tarihi'), 'strftime') else str(udf_aktif.get('takip_tarihi', ''))} <i>(Takip Talebi)</i></div>
                <div>⚖️ <strong>Takip Türü:</strong> {udf_aktif.get('takip_turu', '')}</div>
                <div>👤 <strong>Alacaklı:</strong> {udf_aktif.get('alacakli', '')} {f"<i>(VKN: {udf_aktif.get('alacakli_vkn')})</i>" if udf_aktif.get('alacakli_vkn') else ''}</div>
                <div>👥 <strong>Borçlular ({len(udf_aktif.get('borclular', []))} Taraf):</strong> {", ".join([f"{b['ad_unvan']} (VKN: {b['tc_vkn']})" if b.get('tc_vkn') else b['ad_unvan'] for b in udf_aktif.get('borclular', [])])}</div>
                <div>💰 <strong>Asıl Alacak:</strong> {format_tr_money(udf_aktif.get('ana_para', 0.0))} | <strong>İşlemiş Faiz:</strong> {format_tr_money(udf_aktif.get('t_oncesi_faiz', 0.0))} | <strong>Takip Çıkışı:</strong> {format_tr_money(udf_aktif.get('takip_cikisi', 0.0))}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    taraflar_list = get_cached_taraflar_list()

    if not taraflar_list:
        st.warning("⚠️ Dosya açabilmek için önce 'Taraf Yönetimi' sekmesinden en az bir müvekkil ve borçlu tanımlamalı veya yukarıya UDF yüklemelisiniz.")
    else:
        # Form varsayılan değerlerini UDF'e göre belirle
        def_il = udf_aktif.get("il", "İzmir") if udf_aktif else "İzmir"
        if def_il not in TURKIYE_IL_ILCE:
            def_il = "İzmir"
        il_keys = list(TURKIYE_IL_ILCE.keys())
        idx_il = il_keys.index(def_il) if def_il in il_keys else 0

        def_ilce = udf_aktif.get("ilce", "Merkez") if udf_aktif else "Merkez"
        ilceler_list = TURKIYE_IL_ILCE.get(def_il, ["Merkez"])
        idx_ilce = ilceler_list.index(def_ilce) if def_ilce in ilceler_list else 0

        def_daire = udf_aktif.get("icra_dairesi", "İcra Dairesi") if udf_aktif else "İcra Dairesi"
        idx_daire = ICRA_DAIRE_LISTESI.index(def_daire) if def_daire in ICRA_DAIRE_LISTESI else 0

        def_yil = udf_aktif.get("yil", "2026") if udf_aktif else "2026"
        idx_yil = YILLAR_LISTESI.index(def_yil) if def_yil in YILLAR_LISTESI else YILLAR_LISTESI.index("2026")
        def_sira = udf_aktif.get("sira_no", "") if udf_aktif else ""

        def_takip_turu = udf_aktif.get("takip_turu", "Örnek No: 7 (İlamsız Takip - Para/Teminat)") if udf_aktif else "Örnek No: 7 (İlamsız Takip - Para/Teminat)"
        idx_tur = TAKIP_TURLERI.index(def_takip_turu) if def_takip_turu in TAKIP_TURLERI else 0

        def_tarih = udf_aktif.get("takip_tarihi", date.today()) if udf_aktif else date.today()

        def_alacakli = udf_aktif.get("alacakli", "") if udf_aktif else ""
        idx_alc = taraflar_list.index(def_alacakli) if def_alacakli in taraflar_list else 0

        if udf_aktif and udf_aktif.get("borclu_adlari"):
            def_borclu_raw = [b for b in udf_aktif.get("borclu_adlari", []) if b in taraflar_list]
        elif udf_aktif and udf_aktif.get("borclu"):
            def_borclu_raw = [b.strip() for b in udf_aktif.get("borclu", "").split(",") if b.strip() in taraflar_list]
        else:
            def_borclu_raw = []

        def_anapara = f"{udf_aktif.get('ana_para', 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if udf_aktif else "0,00"
        def_toncesi = f"{udf_aktif.get('t_oncesi_faiz', 0.0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if udf_aktif else "0,00"

        def_faiz_turu = udf_aktif.get("faiz_turu", "TCMB Reeskont Faizi (%39.75)") if udf_aktif else "TCMB Reeskont Faizi (%39.75)"
        idx_ftur = FAIZ_TURLERI_LISTESI.index(def_faiz_turu) if def_faiz_turu in FAIZ_TURLERI_LISTESI else 0
        def_oran = float(udf_aktif.get("faiz_orani", 39.75)) if udf_aktif else 39.75

        c1, c2 = st.columns(2)
        with c1:
            takip_turu = st.selectbox("İcra Takip Yolu (Örnek No)", TAKIP_TURLERI, index=idx_tur)
            secilen_il = st.selectbox("İl", il_keys, index=idx_il)
            secilen_ilce = st.selectbox("İlçe", TURKIYE_IL_ILCE.get(secilen_il, ["Merkez"]), index=min(idx_ilce, len(TURKIYE_IL_ILCE.get(secilen_il, ["Merkez"])) - 1))
            secilen_daire = st.selectbox("İcra Dairesi", ICRA_DAIRE_LISTESI, index=idx_daire)
            
            sub_y1, sub_y2 = st.columns([1, 2])
            with sub_y1:
                secilen_yil = st.selectbox("Takip Yılı", YILLAR_LISTESI, index=idx_yil)
            with sub_y2:
                esas_sira_no = st.text_input("Esas Sıra No", value=def_sira, placeholder="Örn: 4644")
            
            tam_dosya_no = f"{secilen_yil}/{esas_sira_no} E." if esas_sira_no else ""
            takip_tarihi = st.date_input("Takip Açılış Tarihi", value=def_tarih)

            existing_file = check_existing_dosya(cursor, secilen_il, secilen_ilce, secilen_daire, secilen_yil, esas_sira_no)
            if existing_file:
                st.markdown(f"""
                <div style="background: rgba(239, 68, 68, 0.12); border: 1.5px solid #EF4444; border-radius: 6px; padding: 8px 12px; margin-top: 8px; margin-bottom: 8px;">
                    <span style="font-weight: 700; color: #EF4444; font-size: 12px;">⚠️ Bu dosya sistemde zaten kayıtlı (#{existing_file['id']})</span>
                    <div style="font-size: 11px; margin-top: 2px;">
                        <b>{existing_file['dosya_no']}</b> - {existing_file['icra_dairesi']}<br>
                        {existing_file['alacakli'][:30]}... / {existing_file['borclu'][:30]}...
                    </div>
                </div>
                """, unsafe_allow_html=True)

        with c2:
            alacakli = st.selectbox("Alacaklı (Müvekkil Cari)", taraflar_list, index=idx_alc)
            secilen_borclular = st.multiselect("Borçlu Firma / Kişiler (Çoklu Seçilebilir)", taraflar_list, default=def_borclu_raw)
            borclu_metni = ", ".join(secilen_borclular) if secilen_borclular else ""
            
            st.markdown("##### ⚖️ Harç Seçenekleri")
            yeni_th_secim = st.selectbox("Tahsil Harcı Safhası", list(TAHSIL_HARCI_SECENEKLERI.keys()), index=0, key="new_th_secim")
            if TAHSIL_HARCI_SECENEKLERI[yeni_th_secim] == -1.0:
                yeni_th_oran = st.number_input("Özel Tahsil Harcı Oranı (%)", value=9.10, step=0.1, key="new_th_custom")
            else:
                yeni_th_oran = TAHSIL_HARCI_SECENEKLERI[yeni_th_secim]

            yeni_ch_secim = st.selectbox("Cezaevi Harcı", list(CEZAEVI_HARCI_SECENEKLERI.keys()), index=0, key="new_ch_secim")
            yeni_ch_oran = CEZAEVI_HARCI_SECENEKLERI[yeni_ch_secim]

        st.markdown("---")
        st.markdown("##### ⚖️ Alacak Kalemleri (Takip Talebi Kalem Dökümü)")
        st.caption("Aşağıdaki tabloda her bir alacak kalemini (asıl alacak, çek tazminatı, işlemiş faiz vb.), kendi faiz türü ve sorumlu borçlusu ile birlikte düzenleyebilir veya yeni satır ekleyebilirsiniz.")

        col_fz1, col_fz2 = st.columns([2, 1])
        with col_fz1:
            secilen_toplu_faiz = st.selectbox(
                "⚡ Kalemlere Uygulanacak Takip Sonrası Faiz Türü",
                FAIZ_TURLERI_LISTESI,
                index=idx_ftur,
                key="yeni_dosya_toplu_faiz_secimi"
            )
        with col_fz2:
            if secilen_toplu_faiz == "Özel Oran":
                secilen_toplu_oran = st.number_input("Faiz Oranı (%)", value=def_oran, step=0.5, key="yeni_dosya_toplu_oran")
            else:
                secilen_toplu_oran = get_faiz_default_rate(secilen_toplu_faiz)
                st.text_input("Uygulanan Oran", value=f"%{secilen_toplu_oran:.2f}", disabled=True)

        # Session state için alacak kalemleri listesini hazırla
        udf_kalemleri = udf_aktif.get("alacak_kalemleri", []) if udf_aktif else []
        if "form_kalemler_list" not in st.session_state or st.session_state.get("last_udf_source") != st.session_state.get("son_yuklenen_udf_ad"):
            if udf_kalemleri:
                st.session_state["form_kalemler_list"] = udf_kalemleri
            else:
                st.session_state["form_kalemler_list"] = [
                    {"kalem_adi": "Asıl Alacak", "kalem_turu": "Asıl Alacak", "tutar": 0.0, "t_oncesi_faiz": 0.0, "faiz_turu": secilen_toplu_faiz, "faiz_orani": secilen_toplu_oran, "sorumlu_borclular": "Tüm Borçlular"}
                ]
            st.session_state["last_udf_source"] = st.session_state.get("son_yuklenen_udf_ad")
            st.session_state["prev_toplu_faiz_choice"] = secilen_toplu_faiz

        # Eğer kullanıcı yukarıdaki açılır kutudan faiz türünü değiştirdiyse tabloyu ve session state'i senkronize et
        if st.session_state.get("prev_toplu_faiz_choice") != secilen_toplu_faiz:
            st.session_state["prev_toplu_faiz_choice"] = secilen_toplu_faiz
            st.session_state["kalem_editor_key_version"] = st.session_state.get("kalem_editor_key_version", 0) + 1
            if "form_kalemler_list" in st.session_state and st.session_state["form_kalemler_list"]:
                for itm in st.session_state["form_kalemler_list"]:
                    if str(itm.get("faiz_turu")) != "Faizsiz":
                        itm["faiz_turu"] = secilen_toplu_faiz
                        itm["faiz_orani"] = secilen_toplu_oran

        df_kalemler = pd.DataFrame(st.session_state["form_kalemler_list"])
        for c_req, def_v in [("kalem_adi", "Alacak"), ("kalem_turu", "Asıl Alacak"), ("tutar", 0.0), ("t_oncesi_faiz", 0.0), ("faiz_turu", secilen_toplu_faiz), ("faiz_orani", secilen_toplu_oran), ("sorumlu_borclular", "Tüm Borçlular")]:
            if c_req not in df_kalemler.columns:
                df_kalemler[c_req] = def_v

        # Tablodaki tüm kalemlerin faiz oranını türüne göre doğrula
        for idx_k in df_kalemler.index:
            cur_k_ftur = str(df_kalemler.at[idx_k, "faiz_turu"]).strip()
            if cur_k_ftur == "Faizsiz":
                df_kalemler.at[idx_k, "faiz_orani"] = 0.0
            elif cur_k_ftur != "Özel Oran":
                df_kalemler.at[idx_k, "faiz_orani"] = get_faiz_default_rate(cur_k_ftur)

        ed_ver = st.session_state.get("kalem_editor_key_version", 0)
        edited_kalemler_df = st.data_editor(
            df_kalemler,
            num_rows="dynamic",
            use_container_width=True,
            column_config={
                "kalem_adi": st.column_config.TextColumn("Alacak Kalemi Adı", required=True),
                "kalem_turu": st.column_config.SelectboxColumn("Kalem Türü", options=["Asıl Alacak", "Tazminat", "Takip Öncesi Faiz", "Masraf/Komisyon", "Diğer"], required=True),
                "tutar": st.column_config.NumberColumn("Asıl Tutar (TL)", min_value=0.0, format="%.2f TL", required=True),
                "t_oncesi_faiz": st.column_config.NumberColumn("Takip Öncesi Faiz (TL)", min_value=0.0, format="%.2f TL"),
                "faiz_turu": st.column_config.SelectboxColumn("Takip Sonrası Faiz Türü", options=FAIZ_TURLERI_LISTESI, required=True),
                "faiz_orani": st.column_config.NumberColumn("Faiz Oranı (%)", min_value=0.0, max_value=100.0, format="%.2f"),
                "sorumlu_borclular": st.column_config.TextColumn("Sorumlu Borçlu(lar)", help="Örn: Tüm Borçlular veya Keşideci")
            },
            key=f"editor_yeni_dosya_kalemler_{ed_ver}"
        )

        # Tablodan satır bazlı faiz türü değiştirildiyse oranını senkronize et
        for idx_k in edited_kalemler_df.index:
            cur_k_ftur = str(edited_kalemler_df.at[idx_k, "faiz_turu"]).strip()
            if cur_k_ftur == "Faizsiz":
                edited_kalemler_df.at[idx_k, "faiz_orani"] = 0.0
            elif cur_k_ftur != "Özel Oran":
                edited_kalemler_df.at[idx_k, "faiz_orani"] = get_faiz_default_rate(cur_k_ftur)

        # Dinamik toplamlar
        calc_anapara = float(edited_kalemler_df["tutar"].sum()) if not edited_kalemler_df.empty else 0.0
        calc_toncesi = float(edited_kalemler_df["t_oncesi_faiz"].sum()) if not edited_kalemler_df.empty else 0.0
        takip_cikisi_hesap = calc_anapara + calc_toncesi
        hesaplanan_vekalet = hesapla_icra_vekalet_ucreti(takip_cikisi_hesap)
        tahsil_harci_tahmini = round(takip_cikisi_hesap * (yeni_th_oran / 100.0), 2)
        cezaevi_harci_tahmini = round(takip_cikisi_hesap * (yeni_ch_oran / 100.0), 2)

        st.info(f"📊 **Toplam Asıl Alacak:** {format_tr_money(calc_anapara)} | **Takip Öncesi Faiz:** {format_tr_money(calc_toncesi)} | **Takip Çıkışı:** {format_tr_money(takip_cikisi_hesap)} | **Sabit İcra Vekalet:** {format_tr_money(hesaplanan_vekalet)} | **Tahsil Harcı:** {format_tr_money(tahsil_harci_tahmini)} (%{yeni_th_oran:.2f})")

        allow_duplicate_save = False
        if existing_file:
            st.error(
                f"🚨 **DİKKAT: MÜKERRER DOSYA TESPİT EDİLDİ!**\n\n"
                f"**{existing_file['il']} {existing_file['ilce']} / {existing_file['icra_dairesi']} - {existing_file['dosya_no']}** esas sayılı dosya sistemde zaten mevcuttur.\n\n"
                f"• **Kayıtlı Alacaklı:** {existing_file['alacakli']}\n\n"
                f"• **Kayıtlı Borçlu:** {existing_file['borclu']}\n\n"
                f"• **Takip Açılış:** {existing_file['takip_tarihi']} &nbsp;|&nbsp; **Takip Çıkışı:** {format_tr_money(existing_file['takip_cikisi'])}"
            )
            col_dup1, col_dup2 = st.columns([1, 2])
            with col_dup1:
                if st.button("🔍 Mevcut Dosyayı Aç & Çalış", key="btn_goto_existing_form", use_container_width=True, type="primary"):
                    st.session_state["nav_menu_radio"] = "Dosya Arama & Çalışma Masası"
                    st.session_state["dosya_tab_filtre"] = "Tümü"
                    st.session_state["aktif_dosya_id"] = existing_file["id"]
                    st.rerun()
            with col_dup2:
                allow_duplicate_save = st.checkbox(
                    "⚠️ Mükerrer kayda izin ver (Aynı esas no ile yeni dosya açmak istiyorum)",
                    value=False,
                    key="chk_allow_duplicate_save",
                    help="İstisnai bir durumda aynı esas numarası ve daire ile mükerrer dosya kaydetmek istiyorsanız bu kutucuğu işaretleyin."
                )

        st.write("")
        btn_label = "💾 Dosyayı ve Kalemleri Kaydet"
        btn_type = "primary"
        if existing_file and not allow_duplicate_save:
            btn_label = "🚫 Mükerrer Dosya - Kayıt Engellendi"
            btn_type = "secondary"

        if st.button(btn_label, type=btn_type, use_container_width=True):
            if existing_file and not allow_duplicate_save:
                st.error(f"⛔ Mükerrer dosya kaydı engellendi! '{existing_file['dosya_no']}' esas numarası ile '{existing_file['icra_dairesi']}' dairesinde zaten kayıtlı bir dosya bulunmaktadır. Dosyayı görüntülemek için 'Mevcut Dosyayı Aç & Çalış' butonuna tıklayabilir veya istisnai bir durum varsa yukarıdaki onay kutucuğunu işaretleyebilirsiniz.")
            elif esas_sira_no and borclu_metni and takip_cikisi_hesap > 0:
                primary_faiz_turu = secilen_toplu_faiz
                primary_faiz_orani = secilen_toplu_oran

                cursor.execute("""
                INSERT INTO dosyalar (il, ilce, icra_dairesi, dosya_no, alacakli, borclu, takip_turu, takip_tarihi, ana_para, t_oncesi_faiz, takip_cikisi, vekalet_ucreti, faiz_turu, faiz_orani, tahsil_harci_safhasi, tahsil_harci_orani, cezaevi_harci_orani)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (secilen_il, secilen_ilce, secilen_daire, tam_dosya_no, alacakli, borclu_metni, takip_turu, str(takip_tarihi), calc_anapara, calc_toncesi, takip_cikisi_hesap, hesaplanan_vekalet, primary_faiz_turu, primary_faiz_orani, yeni_th_secim, yeni_th_oran, yeni_ch_oran))
                new_dosya_id = cursor.lastrowid

                # Kalemleri alacak_kalemleri tablosuna satır satır kaydet
                for _, k_row in edited_kalemler_df.iterrows():
                    k_name = str(k_row.get("kalem_adi", "Asıl Alacak")).strip()
                    k_tur = str(k_row.get("kalem_turu", "Asıl Alacak"))
                    k_tut = float(k_row.get("tutar", 0.0))
                    k_fai = float(k_row.get("t_oncesi_faiz", 0.0))
                    k_ftur = str(k_row.get("faiz_turu", secilen_toplu_faiz)).strip()
                    if k_ftur == "Faizsiz":
                        k_foran = 0.0
                    elif k_ftur != "Özel Oran":
                        k_foran = get_faiz_default_rate(k_ftur)
                    else:
                        k_foran = float(k_row.get("faiz_orani", secilen_toplu_oran))
                    k_srm = str(k_row.get("sorumlu_borclular", "Tüm Borçlular"))
                    
                    if k_name and (k_tut > 0 or k_fai > 0):
                        cursor.execute("""
                        INSERT INTO alacak_kalemleri (dosya_id, kalem_adi, kalem_turu, tutar, t_oncesi_faiz, faiz_turu, faiz_orani, sorumlu_borclular)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (new_dosya_id, k_name, k_tur, k_tut, k_fai, k_ftur, k_foran, k_srm))
                        if k_ftur != "Faizsiz":
                            primary_faiz_turu = k_ftur
                            primary_faiz_orani = k_foran

                # Ana dosya tablosunun faiz türü ve oranını da asıl kalemin faizine göre güncelle
                cursor.execute("""
                    UPDATE dosyalar SET faiz_turu = ?, faiz_orani = ? WHERE id = ?
                """, (primary_faiz_turu, primary_faiz_orani, new_dosya_id))

                conn.commit()
                st.session_state["udf_data"] = None
                st.session_state["son_yuklenen_udf_ad"] = None
                st.session_state["form_kalemler_list"] = None
                st.success(f"{tam_dosya_no} esas sayılı dosya ve {len(edited_kalemler_df)} alacak kalemi başarıyla kaydedildi!")
                st.rerun()
            elif takip_cikisi_hesap <= 0:
                st.warning("Lütfen alacak kalemleri tablosuna en az bir geçerli tutar girin.")
            else:
                st.warning("Lütfen Esas Numarası ve en az bir Borçlu seçin.")

# -------------------------------------------------------------
# 11. MODÜL 4: TARAF (CARİ) YÖNETİMİ
# -------------------------------------------------------------
elif menu == "Taraf (Cari) Yönetimi":
    st.markdown(f"<h2 style='color:{accent_green};'>👥 Taraf (Cari Kart) Yönetimi</h2>", unsafe_allow_html=True)
    t_add, t_edit = st.tabs(["➕ Yeni Cari Kartı", "✏️ Kayıtlı Tarafları Düzenle"])

    with t_add:
        with st.form("form_taraf_add"):
            c1, c2 = st.columns(2)
            with c1:
                taraf_tipi = st.radio("Taraf Statüsü", ["Tüzel Kişi (Şirket/Kurum)", "Gerçek Kişi (Şahıs)"], horizontal=True)
                ad_unvan = st.text_input("Ticaret Unvanı / Ad Soyad *")
                tc_vkn = st.text_input("Vergi Kimlik No / TCKN")
            with c2:
                vergi_dairesi = st.text_input("Vergi Dairesi")
                telefon = st.text_input("Telefon Numarası")
                adres = st.text_area("Tebligat Adresi", height=70)

            if st.form_submit_button("Tarafı Sisteme Kaydet", type="primary"):
                if ad_unvan.strip():
                    try:
                        cursor.execute("""
                        INSERT INTO taraflar (tip, ad_unvan, tc_vkn, vergi_dairesi, telefon, adres)
                        VALUES (?, ?, ?, ?, ?, ?)
                        """, (taraf_tipi, ad_unvan.strip(), tc_vkn.strip(), vergi_dairesi.strip(), telefon.strip(), adres.strip()))
                        conn.commit()
                        st.success(f"'{ad_unvan}' cari kartı oluşturuldu!")
                        st.rerun()
                    except (sqlite3.IntegrityError, IntegrityError):
                        st.error("Bu isimle kayıtlı bir taraf zaten mevcut.")
                else:
                    st.warning("Unvan/Ad Soyad zorunludur.")

    with t_edit:
        taraflar_df = pd.read_sql_query("SELECT id, tip, ad_unvan, tc_vkn, vergi_dairesi, telefon, adres FROM taraflar ORDER BY ad_unvan ASC", conn)
        if not taraflar_df.empty:
            t_dict = {f"{r['ad_unvan']} ({r['tip']})": r['id'] for _, r in taraflar_df.iterrows()}
            s_id = t_dict[st.selectbox("Düzenlenecek Cari Kart", list(t_dict.keys()))]
            cur_t = taraflar_df[taraflar_df['id'] == s_id].iloc[0]

            c1, c2 = st.columns(2)
            with c1:
                e_tip = st.radio("Statü", ["Tüzel Kişi (Şirket/Kurum)", "Gerçek Kişi (Şahıs)"], index=0 if "Tüzel" in cur_t['tip'] else 1)
                e_ad = st.text_input("Unvan / İsim", value=str(cur_t['ad_unvan']))
                e_vkn = st.text_input("VKN / TCKN", value=str(cur_t['tc_vkn'] or ''))
            with c2:
                e_vd = st.text_input("V.D.", value=str(cur_t['vergi_dairesi'] or ''))
                e_tel = st.text_input("Tel", value=str(cur_t['telefon'] or ''))
                e_adr = st.text_area("Adres", value=str(cur_t['adres'] or ''), height=70)

            b1, b2 = st.columns(2)
            with b1:
                if st.button("Cari Bilgilerini Güncelle"):
                    cursor.execute("UPDATE taraflar SET tip = ?, ad_unvan = ?, tc_vkn = ?, vergi_dairesi = ?, telefon = ?, adres = ? WHERE id = ?", (e_tip, e_ad.strip(), e_vkn.strip(), e_vd.strip(), e_tel.strip(), e_adr.strip(), s_id))
                    conn.commit()
                    st.success("Güncellendi!")
                    st.rerun()
            with b2:
                if st.button("🗑️ Cari Kartı Sil"):
                    cursor.execute("DELETE FROM taraflar WHERE id = ?", (s_id,))
                    conn.commit()
                    st.rerun()

# -------------------------------------------------------------
# 12. MODÜL 5: MASRAF & AVANS YÖNETİMİ
# -------------------------------------------------------------
elif menu == "Masraf & Avans Kaydı":
    st.markdown(f"<h2 style='color:{accent_green};'>💸 İcra Masraf & Avans Yönetimi</h2>", unsafe_allow_html=True)
    dosyalar_df = pd.read_sql_query("SELECT id, dosya_no, borclu FROM dosyalar", conn)
    
    if not dosyalar_df.empty:
        d_dict = {f"{r['dosya_no']} - {r['borclu']}": r['id'] for _, r in dosyalar_df.iterrows()}
        s_id = d_dict[st.selectbox("İşlem Yapılacak Dosya", list(d_dict.keys()))]

        m_add, m_view = st.tabs(["➕ Yeni Masraf / İade Ekle", "📜 Geçmiş Masraf Hareketleri"])

        with m_add:
            c1, c2, c3 = st.columns(3)
            with c1:
                m_date = st.date_input("İşlem Tarihi", value=date.today())
                m_tur = st.radio("Hareket Türü", ["Masraf", "İade (Avans/Yolluk İadesi)"], horizontal=True)
            with c2:
                m_amt = parse_tr_money(st.text_input("Tutar (TL)", value="0,00"))
                st.caption(f"Tutar: **{format_tr_money(m_amt)}**")
            with c3:
                m_desc = st.text_input("Açıklama", placeholder="Örn: Tebligat, Baro Pulu, Haciz Harcı")

            if st.button("Masraf Kalemini Kaydet", type="primary"):
                if m_amt > 0:
                    v_masraf = m_amt if "Masraf" in m_tur else 0.0
                    v_iade = m_amt if "İade" in m_tur else 0.0
                    cursor.execute("INSERT INTO masraflar (dosya_id, tarih, aciklama, masraf_tutari, iade_tutari) VALUES (?, ?, ?, ?, ?)", (s_id, str(m_date), m_desc, v_masraf, v_iade))
                    conn.commit()
                    st.success("Kayıt işlendi!")
                    st.rerun()

        with m_view:
            kayitlar = pd.read_sql_query("SELECT id, tarih, aciklama, masraf_tutari, iade_tutari FROM masraflar WHERE dosya_id = ? ORDER BY id DESC", conn, params=[s_id])
            if not kayitlar.empty:
                g_kayitlar = pd.DataFrame({
                    "Tarih": kayitlar["tarih"],
                    "Açıklama": kayitlar["aciklama"],
                    "Masraf Tutarı": kayitlar["masraf_tutari"].apply(format_tr_money),
                    "İade Tutarı": kayitlar["iade_tutari"].apply(format_tr_money)
                })
                st.dataframe(g_kayitlar, use_container_width=True, hide_index=True)
            else:
                st.info("Bu dosyada masraf kaydı bulunmuyor.")
    else:
        st.info("İşlem yapabilmek için önce bir dosya açmalısınız.")

# -------------------------------------------------------------
# 13. MODÜL: YASAL & TCMB FAİZ CETVELİ YÖNETİMİ
# -------------------------------------------------------------
elif menu == "Yasal Faiz Cetveli":
    st.markdown(f"<h2 style='color:{accent_green};'>⚖️ Yasal & TCMB Faiz Oranları Cetveli</h2>", unsafe_allow_html=True)
    st.caption("Resmi Gazete ve TCMB kararları uyarınca kademeli faiz dilimlerini görüntüleyin veya yeni yasal oran ekleyin.")

    tab_fz_sync, tab_fz_list, tab_fz_add = st.tabs([
        "🌐 Akıllı Senkronizasyon & Güncelleme",
        "📜 Yürürlükteki Faiz Dilimleri",
        "➕ Yeni Faiz Oranı Ekle"
    ])

    with tab_fz_sync:
        st.markdown("##### 🌐 Resmi Gazete & TCMB Otomatik Faiz Senkronizasyonu")
        st.caption("Bu modül internet ve yerel master kaynakları üzerinden TCMB ve 3095 s.K. faiz değişikliklerini denetler, onayınızla tüm icra dosyalarına anında uygular.")

        # Son kontrol zamanı
        cursor.execute("CREATE TABLE IF NOT EXISTS sistem_ayarlari (anahtar TEXT PRIMARY KEY, deger TEXT)")
        cursor.execute("SELECT deger FROM sistem_ayarlari WHERE anahtar = 'son_faiz_kontrol'")
        r_son = cursor.fetchone()
        son_kontrol_str = r_son[0] if r_son else "Henüz denetlenmedi"

        cursor.execute("SELECT deger FROM sistem_ayarlari WHERE anahtar = 'son_faiz_guncelleme'")
        r_gun = cursor.fetchone()
        son_guncelleme_str = r_gun[0] if r_gun else "15.10.2026 (İlk Kurulum)"

        sc1, sc2, sc3 = st.columns(3)
        with sc1:
            st.metric("Son Güncelleme Tarihi", son_guncelleme_str)
        with sc2:
            st.metric("Son Denetleme Tarihi", son_kontrol_str)
        with sc3:
            fz_st = st.session_state.get("faiz_sync_status", {})
            st_text = "🟢 Oranlar Güncel" if fz_st.get("durum") != "GUNCELLEME_VAR" else "🔔 Güncelleme Var"
            st.metric("Sistem Durumu", st_text)

        st.write("")
        col_btn1, col_btn2 = st.columns([1, 2])
        with col_btn1:
            if st.button("🔍 Şimdi Güncellemeleri Denetle", type="primary", use_container_width=True):
                yeni_st = kontrol_et_faiz_guncellemeleri(conn)
                st.session_state["faiz_sync_status"] = yeni_st
                cursor.execute("INSERT OR REPLACE INTO sistem_ayarlari (anahtar, deger) VALUES ('son_faiz_kontrol', ?)", (datetime.now().strftime("%d.%m.%Y %H:%M"),))
                conn.commit()
                st.rerun()

        fz_st = st.session_state.get("faiz_sync_status", {})
        if fz_st.get("durum") == "GUNCELLEME_VAR":
            st.warning(f"📢 **{fz_st.get('mesaj')}**")
            st.markdown("##### 📋 Tespit Edilen Yeni / Revize Edilen Faiz Oranları:")
            fark_df = pd.DataFrame(fz_st.get("farklar", []))
            if not fark_df.empty:
                fark_df["oran"] = fark_df["oran"].apply(lambda x: f"%{float(x):.2f}")
                fark_df.rename(columns={
                    "faiz_turu": "Faiz Türü",
                    "baslangic_tarihi": "Başlangıç Tarihi",
                    "bitis_tarihi": "Bitiş Tarihi",
                    "oran": "Yıllık Oran",
                    "aciklama": "Yasal Dayanak / Resmi Gazete"
                }, inplace=True)
                st.dataframe(fark_df, use_container_width=True, hide_index=True)

            st.write("")
            if st.button("🚀 Tüm Yeni Oranları Onayla ve Dosyalara Uygula", type="primary", use_container_width=True):
                ok, msg = uygula_faiz_guncellemesi(conn, fz_st.get("farklar", []))
                if ok:
                    st.session_state["faiz_sync_status"] = kontrol_et_faiz_guncellemeleri(conn)
                    st.success(f"✅ {msg}")
                    st.rerun()
                else:
                    st.error(f"❌ {msg}")
        elif fz_st.get("durum") == "GUNCEL":
            st.success(f"✅ {fz_st.get('mesaj', 'Sistemdeki tüm faiz oranları günceldir.')}")
        elif fz_st.get("durum") == "HATA":
            st.error(f"⚠️ {fz_st.get('mesaj')}")

        with st.expander("⚙️ Gelişmiş Senkronizasyon ve Ağ Kaynak Ayarları"):
            st.caption("Büro ortak sunucunuzda paylaşılan veya özel bir URL üzerinden faiz cetvelini otomatik dağıtmak için özel kaynak tanımlayabilirsiniz.")
            ozel_kaynak = st.text_input("Özel Master JSON URL / Yerel Yol", placeholder="Örn: http://192.168.1.50/faiz_oranlari.json veya C:\\Ofis\\faiz.json")
            if st.button("Kaynaktan Test Et"):
                if ozel_kaynak.strip():
                    test_st = kontrol_et_faiz_guncellemeleri(conn, source_url=ozel_kaynak.strip())
                    st.json(test_st)
                else:
                    st.info("Lütfen bir URL veya dosya yolu girin.")

    with tab_fz_list:
        fz_df = pd.read_sql_query("""
            SELECT id, faiz_turu, baslangic_tarihi, bitis_tarihi, oran, aciklama 
            FROM faiz_oranlari 
            ORDER BY faiz_turu, baslangic_tarihi DESC
        """, conn)

        if not fz_df.empty:
            fz_goster = fz_df.copy()
            fz_goster["oran"] = fz_goster["oran"].apply(lambda x: f"%{x:.2f}")
            fz_goster.rename(columns={
                "id": "ID",
                "faiz_turu": "Faiz Türü",
                "baslangic_tarihi": "Başlangıç Tarihi",
                "bitis_tarihi": "Bitiş Tarihi",
                "oran": "Yıllık Oran",
                "aciklama": "Yasal Dayanak / Açıklama"
            }, inplace=True)
            st.dataframe(fz_goster, use_container_width=True, hide_index=True)

            st.write("")
            st.markdown("##### 🗑️ Faiz Dilimi Sil / Düzelt")
            col_d1, col_d2 = st.columns([3, 1])
            with col_d1:
                silinecek_secim = {f"ID: {r['id']} | {r['faiz_turu']} ({r['baslangic_tarihi']} - {r['bitis_tarihi']}): %{r['oran']}": r['id'] for _, r in fz_df.iterrows()}
                secili_fz_id = silinecek_secim[st.selectbox("İşlem Yapılacak Kayıt", list(silinecek_secim.keys()))]
            with col_d2:
                st.write("")
                st.write("")
                if st.button("🗑️ Oranı Sil", use_container_width=True):
                    cursor.execute("DELETE FROM faiz_oranlari WHERE id = ?", (secili_fz_id,))
                    conn.commit()
                    st.success("Faiz dilimi silindi!")
                    st.rerun()
        else:
            st.info("Kayıtlı faiz dilimi bulunamadı.")

    with tab_fz_add:
        with st.form("form_yeni_faiz"):
            c_f1, c_f2 = st.columns(2)
            with c_f1:
                yeni_ftur = st.selectbox("Faiz Türü", ["Ticari Avans Faizi", "Reeskont Faizi", "Yasal Faiz", "Diğer Yasal Faiz"])
                yeni_fbaslangic = st.date_input("Yürürlük Başlangıç Tarihi", value=date.today())
                yeni_fbitis = st.date_input("Yürürlük Bitiş Tarihi", value=date(2099, 12, 31))
            with c_f2:
                yeni_foran = st.number_input("Yıllık Faiz Oranı (%)", min_value=0.0, max_value=200.0, value=48.0, step=0.25)
                yeni_faciklama = st.text_input("Yasal Dayanak / R.G. Sayısı", placeholder="Örn: 2026/.. sayılı TCMB Tebliği")

            st.caption("ℹ️ Yeni oran eklendiğinde, bu faiz türünü kullanan tüm icra dosyalarının faizleri ilgili tarih aralığı için otomatik güncellenir.")

            if st.form_submit_button("Yeni Faiz Oranını Kaydet", type="primary"):
                cursor.execute("""
                    INSERT INTO faiz_oranlari (faiz_turu, baslangic_tarihi, bitis_tarihi, oran, aciklama)
                    VALUES (?, ?, ?, ?, ?)
                """, (yeni_ftur, str(yeni_fbaslangic), str(yeni_fbitis), yeni_foran, yeni_faciklama.strip()))
                conn.commit()
                st.success("Yeni faiz oranı yürürlüğe girdi ve başarıyla kaydedildi!")
                st.rerun()

# -------------------------------------------------------------
# 14. MODÜL: YEDEKLEME & SİSTEM YÖNETİMİ
# -------------------------------------------------------------
elif menu == "Yedekleme & Sistem":
    st.markdown(f"<h2 style='color:{accent_green};'>💾 Sistem Yedekleme ve Veritabanı Merkezi</h2>", unsafe_allow_html=True)
    st.caption("Bulutta çalışan sisteminizin anlık veritabanı yedeğini tek tıkla bilgisayarınıza indirin.")

    col_yb1, col_yb2 = st.columns(2)

    with col_yb1:
        st.markdown(f"""
            <div style="background-color: {card_bg}; border: 1.5px solid {card_border}; padding: 20px; border-radius: 12px;">
                <h4 style="margin-top:0; color:{accent_green};">📦 SQLite Veritabanı Yedeği (.db)</h4>
                <p style="font-size:13.5px; color:{text_muted};">
                    Tüm dosyalarınızı, tahsilatlarınızı, notlarınızı ve cari kartlarınızı içeren ham veritabanı dosyasını doğrudan bilgisayarınıza indirir.
                </p>
            </div>
        """, unsafe_allow_html=True)
        
        st.write("")
        if os.path.exists("tahsilat_pro.db"):
            with open("tahsilat_pro.db", "rb") as db_file:
                db_bytes = db_file.read()
            st.download_button(
                label="📥 Veritabanı Dosyasını İndir (.db)",
                data=db_bytes,
                file_name=f"tahsilat_pro_yedek_{datetime.now().strftime('%Y%m%d_%H%M')}.db",
                mime="application/octet-stream",
                type="primary"
            )
        else:
            st.warning("Veritabanı dosyası henüz oluşturulmadı.")

    with col_yb2:
        st.markdown(f"""
            <div style="background-color: {card_bg}; border: 1.5px solid {card_border}; padding: 20px; border-radius: 12px;">
                <h4 style="margin-top:0; color:{accent_green};">ℹ️ Güvenlik Bilgisi</h4>
                <p style="font-size:13.5px; color:{text_muted};">
                    • Bu işlem buluttaki verilerinizin yedeğini lokal bilgisayarınıza almanızı sağlar.<br>
                    • Haftada bir kez bu yedeği almanız ofis güvenliği için tavsiye edilir.<br>
                    • Oturum Kapatma: İşiniz bittiğinde sol alttan çıkış yapabilirsiniz.
                </p>
            </div>
        """, unsafe_allow_html=True)