import json
import os
import sqlite3
import urllib.request
from datetime import datetime, date

DEFAULT_ONLINE_SOURCE = "https://raw.githubusercontent.com/juslegal/faiz-cetveli/main/faiz_oranlari.json"

def get_db_connection(db_path=None):
    if not db_path:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        db_path = os.path.join(base_dir, "tahsilat_pro.db")
    return sqlite3.connect(db_path, check_same_thread=False)

def fetch_master_rates(source_url=None):
    """
    Öncelikle verilen internet URL'sinden, olmazsa yerel/ağ üzerindeki
    master json dosyasından güncel faiz cetvelini okur.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    local_master = os.path.join(base_dir, "faiz_cetveli_master.json")
    
    # 1. İnternet kaynağından dene
    if source_url and source_url.startswith("http"):
        try:
            req = urllib.request.Request(source_url, headers={"User-Agent": "JusTahsilat/1.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    return data.get("oranlar", []), "ONLINE", data.get("versiyon", "Güncel")
        except Exception:
            pass

    # 2. Yerel master json dosyasından dene
    if os.path.exists(local_master):
        try:
            with open(local_master, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("oranlar", []), "LOCAL_MASTER", data.get("versiyon", "Yerel Master")
        except Exception as e:
            pass

    return [], "NONE", "Bilinmiyor"

def kontrol_et_faiz_guncellemeleri(conn, source_url=None):
    """
    Mevcut veritabanındaki oranlar ile master kaynaktaki oranları karşılaştırır.
    Farklı veya eksik oranlar varsa listeler.
    """
    master_rates, source_type, version_info = fetch_master_rates(source_url)
    if not master_rates:
        return {
            "durum": "HATA",
            "mesaj": "Faiz güncelleme kaynağına (internet/yerel master) ulaşılamadı.",
            "farklar": [],
            "kaynak": source_type,
            "versiyon": version_info
        }

    cur = conn.cursor()
    cur.execute("SELECT faiz_turu, baslangic_tarihi, bitis_tarihi, oran FROM faiz_oranlari")
    db_records = set((r[0], r[1], r[2], float(r[3])) for r in cur.fetchall())

    yeni_dilimler = []
    for itm in master_rates:
        tup = (itm["faiz_turu"], itm["baslangic_tarihi"], itm["bitis_tarihi"], float(itm["oran"]))
        if tup not in db_records:
            yeni_dilimler.append(itm)

    if not yeni_dilimler:
        return {
            "durum": "GUNCEL",
            "mesaj": f"Tüm faiz oranları günceldir. (Master Versiyon: {version_info})",
            "farklar": [],
            "kaynak": source_type,
            "versiyon": version_info
        }

    return {
        "durum": "GUNCELLEME_VAR",
        "mesaj": f"{len(yeni_dilimler)} adet yeni/güncellenmiş faiz dilimi tespit edildi! (Versiyon: {version_info})",
        "farklar": yeni_dilimler,
        "kaynak": source_type,
        "versiyon": version_info
    }

def uygula_faiz_guncellemesi(conn, farklar):
    """
    Tespit edilen yeni oranları veritabanına ekler veya günceller.
    """
    if not farklar:
        return False, "Eklenecek yeni faiz dilimi bulunamadı."

    cur = conn.cursor()
    eklenen_sayisi = 0
    guncellenen_sayisi = 0

    try:
        for itm in farklar:
            f_tur = itm["faiz_turu"]
            b_tar = itm["baslangic_tarihi"]
            e_tar = itm["bitis_tarihi"]
            oran = float(itm["oran"])
            aciklama = itm.get("aciklama", "Otomatik Güncelleme")

            # Aynı tür ve başlangıç tarihi varsa oran ve bitişi güncelle
            cur.execute("""
                SELECT id FROM faiz_oranlari 
                WHERE faiz_turu = ? AND baslangic_tarihi = ?
            """, (f_tur, b_tar))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE faiz_oranlari 
                    SET bitis_tarihi = ?, oran = ?, aciklama = ?
                    WHERE id = ?
                """, (e_tar, oran, aciklama, existing[0]))
                guncellenen_sayisi += 1
            else:
                # Yeni bir dilim eklemeden önce, aynı türün önceki açık dilimini kapat
                cur.execute("""
                    UPDATE faiz_oranlari
                    SET bitis_tarihi = date(?, '-1 day')
                    WHERE faiz_turu = ? AND bitis_tarihi >= '2099-01-01'
                """, (b_tar, f_tur))

                cur.execute("""
                    INSERT INTO faiz_oranlari (faiz_turu, baslangic_tarihi, bitis_tarihi, oran, aciklama)
                    VALUES (?, ?, ?, ?, ?)
                """, (f_tur, b_tar, e_tar, oran, aciklama))
                eklenen_sayisi += 1

        # Sistem ayarlarında son güncelleme zamanını kaydet
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sistem_ayarlari (
                anahtar TEXT PRIMARY KEY,
                deger TEXT
            )
        """)
        now_str = datetime.now().strftime("%d.%m.%Y %H:%M")
        cur.execute("INSERT OR REPLACE INTO sistem_ayarlari (anahtar, deger) VALUES ('son_faiz_guncelleme', ?)", (now_str,))
        cur.execute("INSERT OR REPLACE INTO sistem_ayarlari (anahtar, deger) VALUES ('son_faiz_kontrol', ?)", (now_str,))

        conn.commit()
        return True, f"Başarıyla güncellendi: {eklenen_sayisi} yeni dilim eklendi, {guncellenen_sayisi} dilim revize edildi."
    except Exception as e:
        conn.rollback()
        return False, f"Güncelleme sırasında hata oluştu: {str(e)}"
