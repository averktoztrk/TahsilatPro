# -*- coding: utf-8 -*-
"""
TahsilatPro / JusLegal Dava Takip ve Mahkeme Yönetim Motoru
- UDF (UYAP XML) ve PDF Belge Ayrıştırıcı
- Tensip Zaptı / Tevzi Formu Analiz Motoru
- Gerekçeli Karar Hüküm Analizi ve Çift Yönlü İcra Entegrasyonu
- iCalendar (.ics) Duruşma / Süre Dışa Aktarımı
"""

import os
import re
import io
import zipfile
import xml.etree.ElementTree as ET
from datetime import datetime, date, timedelta

# -------------------------------------------------------------
# 1. VERİTABANI TABLOLARINI HAZIRLAMA (DDL)
# -------------------------------------------------------------
def init_dava_tables(cursor, conn):
    """
    Davalar, Dava Notları ve Dava Süreleri tablolarını veritabanında oluşturur.
    PostgreSQL (Supabase) ve SQLite uyumludur.
    """
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS davalar (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        mahkeme_il TEXT,
        mahkeme_ilce TEXT,
        mahkeme_adi TEXT,
        dosya_no TEXT,
        karar_no TEXT,
        dava_turu TEXT DEFAULT 'İtirazın İptali',
        dava_tarihi TEXT,
        alacakli TEXT,
        borclu TEXT,
        karsi_vekil TEXT,
        dava_degeri REAL DEFAULT 0,
        durum TEXT DEFAULT 'Derdest',
        asama TEXT DEFAULT 'Ön İnceleme',
        sonraki_durusma_tarihi TEXT,
        durusma_saati TEXT DEFAULT '09:30',
        durusma_aciklamasi TEXT,
        bagli_icra_id INTEGER,
        lehe_alacak REAL DEFAULT 0,
        lehe_tazminat REAL DEFAULT 0,
        lehe_vekalet REAL DEFAULT 0,
        lehe_gider REAL DEFAULT 0,
        aleyhe_vekalet REAL DEFAULT 0,
        aleyhe_gider REAL DEFAULT 0,
        karar_ozeti TEXT,
        olusturma_tarihi TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dava_notlari (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dava_id INTEGER,
        tarih TEXT,
        not_icerik TEXT,
        FOREIGN KEY(dava_id) REFERENCES davalar(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS dava_sureleri (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dava_id INTEGER,
        baslik TEXT,
        teblig_tarihi TEXT,
        son_gun TEXT,
        aciklama TEXT,
        durum TEXT DEFAULT 'Bekliyor',
        FOREIGN KEY(dava_id) REFERENCES davalar(id)
    )
    """)

    # Eğer eski tablolarda bazı sütunlar eksikse ekle
    try:
        cursor.execute("ALTER TABLE davalar ADD COLUMN aleyhe_vekalet REAL DEFAULT 0;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE davalar ADD COLUMN aleyhe_gider REAL DEFAULT 0;")
    except Exception:
        pass
    try:
        cursor.execute("ALTER TABLE davalar ADD COLUMN karar_ozeti TEXT;")
    except Exception:
        pass

    conn.commit()


# -------------------------------------------------------------
# 2. METİN VE SAYI YARDIMCILARI
# -------------------------------------------------------------
def parse_tr_float(val_str):
    if not val_str:
        return 0.0
    cleaned = str(val_str).replace("TL", "").replace("tl", "").replace("TRY", "").strip()
    cleaned = re.sub(r"[^\d.,]", "", cleaned)
    if "." in cleaned and "," in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")
    try:
        return float(cleaned)
    except Exception:
        return 0.0


# -------------------------------------------------------------
# 3. UYAP (.udf) VE PDF BELGE OKUYUCU
# -------------------------------------------------------------
def extract_text_from_udf(file_bytes):
    """
    UYAP Doküman Editörü (.udf) dosyalarını okur.
    UDF aslında content.xml barındıran bir ZIP arşividir.
    Şablon bazlı belgelerde (Tevzi Formu vb.) XML etiketlerini CDATA şablonuyla
    birleştirerek eksiksiz ve temiz metin üretir.
    """
    try:
        with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as zf:
            if 'content.xml' in zf.namelist():
                xml_data = zf.read('content.xml')
                decoded_xml = None
                for enc in ['utf-8', 'windows-1254', 'iso-8859-9']:
                    try:
                        decoded_xml = xml_data.decode(enc)
                        break
                    except Exception:
                        pass
                if not decoded_xml:
                    decoded_xml = xml_data.decode('utf-8', errors='ignore')

                root = ET.fromstring(decoded_xml)
                
                # 1. CDATA içeriğini al
                cdata = ""
                c_m = re.search(r'<content><!\[CDATA\[(.*?)\]\]></content>', decoded_xml, re.DOTALL)
                if c_m:
                    cdata = c_m.group(1)

                # 2. Tüm etiketleri topla
                tag_map = {}
                for elem in root.iter():
                    if elem.text and elem.text.strip():
                        tag_map.setdefault(elem.tag, []).append(elem.text.strip())

                # 3. Eğer CDATA şablon etiketleri içeriyorsa (Tevzi Formu gibi)
                if cdata and ("ilIlceMahkemeAdi" in cdata or "davaciAdSoyad" in cdata or "kayitNo" in cdata):
                    rendered = cdata
                    for tag, vals in tag_map.items():
                        if tag not in ['content', 'taraf', 'tarafAdiSoyadi', 'harcMasrafTip', 'harcMasrafMiktari']:
                            rendered = rendered.replace(tag, vals[0] if vals else '')

                    # Tarafları satır satır yerleştir
                    t_roller = tag_map.get('taraf', [])
                    t_adlar = tag_map.get('tarafAdiSoyadi', [])
                    t_lines = [f"{r} : {a}" for r, a in zip(t_roller, t_adlar)]
                    if t_lines:
                        rendered = re.sub(r'taraf\s*:\s*tarafAdiSoyadi', '\n'.join(t_lines), rendered)

                    # Harç/Masrafları yerleştir
                    m_tipler = tag_map.get('harcMasrafTip', [])
                    m_tutarlar = tag_map.get('harcMasrafMiktari', [])
                    m_lines = [f"{t} : {u}" for t, u in zip(m_tipler, m_tutarlar)]
                    if m_lines:
                        rendered = re.sub(r'harcMasrafTip\s*:\s*harcMasrafMiktari', '\n'.join(m_lines), rendered)

                    return rendered

                # Normal dokümanda (Tensip Zaptı, Karar vb.) CDATA varsa ve doluysa döndür
                if cdata and len(cdata.strip()) > 50:
                    return cdata

                # Fallback: Tüm element metinlerini birleştir
                texts = []
                for elem in root.iter():
                    if elem.text and elem.text.strip() and elem.tag != 'content':
                        texts.append(elem.text.strip())
                return "\n".join(texts)
    except Exception:
        pass
    
    # Eğer doğrudan xml veya metin ise
    try:
        return file_bytes.decode('utf-8', errors='ignore')
    except Exception:
        return ""


def extract_text_from_pdf(file_bytes):
    """
    PDF dosyalarından metin katmanını okur (pypdf veya fitz).
    """
    # 1. pypdf denemesi
    try:
        import pypdf
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        texts = [page.extract_text() or "" for page in reader.pages]
        full_text = "\n".join(texts).strip()
        if full_text:
            return full_text
    except Exception:
        pass

    # 2. PyMuPDF (fitz) fallback
    try:
        import fitz
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        texts = [page.get_text() for page in doc]
        return "\n".join(texts).strip()
    except Exception:
        pass

    return ""


def extract_text_from_uploaded_file(file_name, file_bytes):
    """
    Dosya uzantısına göre en uygun metin çıkarıcıyı çalıştırır.
    """
    lower_name = file_name.lower()
    if lower_name.endswith(".udf"):
        return extract_text_from_udf(file_bytes)
    elif lower_name.endswith(".pdf"):
        return extract_text_from_pdf(file_bytes)
    elif lower_name.endswith(".txt"):
        try:
            return file_bytes.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    return ""


# -------------------------------------------------------------
# 4. TENSİP ZAPTI / TEVZİ FORMU ANALİZ MOTORU
# -------------------------------------------------------------
def analyze_tensip_or_tevzi_text(text):
    """
    Tensip zaptı veya tevzi formundan temel dava bilgilerini çıkarır.
    """
    data = {
        "mahkeme_adi": "",
        "dosya_no": "",
        "dava_turu": "İtirazın İptali",
        "dava_tarihi": str(date.today()),
        "alacakli": "",
        "borclu": "",
        "karsi_vekil": "",
        "dava_degeri": 0.0,
        "durusma_tarihi": "",
        "durusma_saati": "09:30",
        "asama": "Ön İnceleme",
        "bagli_icra_no": "",
        "bagli_icra_daire": "",
        "raw_text": text
    }

    if not text:
        return data

    # 1. Mahkeme Adı (Satır bazlı arama, önceki satırlardaki saat/sayı artık karışmaz)
    m_mahk = re.search(r"(?:T\.C\.\s*)?([^\r\n]*?(?:MAHKEMES[İI]|HAK[İI]ML[İI]Ğ[İI]))", text, re.I)
    if m_mahk:
        raw_m = m_mahk.group(1).strip()
        clean_m = re.sub(r"^[\s\(\)\[\]\{\}\d\.\,\:\-]+", "", raw_m).strip()
        if clean_m:
            data["mahkeme_adi"] = clean_m

    # 2. Esas / Kayıt No
    m_esas = re.search(r"(?:ESAS\s*NO|KAYIT\s*NO|DOSYA\s*NO)\s*[:\t ]*(\d{4}\s*/\s*\d+)", text, re.I)
    if not m_esas:
        m_esas = re.search(r"\b(\d{4}\s*/\s*\d+)\s*(?:ESAS|E\.)\b", text, re.I)
    if m_esas:
        kno = m_esas.group(1).replace(" ", "")
        data["dosya_no"] = kno if (kno.endswith("E.") or kno.endswith("ESAS")) else f"{kno} E."

    # 3. Dava Türü
    m_tur = re.search(r"DAVA\s*(?:TÜRÜ)?\s*[:\t ]*([^\r\n]+)", text, re.I)
    if m_tur:
        dtur_cand = m_tur.group(1).strip().strip(".-")
        if dtur_cand.lower() not in ["davatarz", "davatarzi", "davatarzi"]:
            data["dava_turu"] = dtur_cand

    # 4. Dava Tarihi
    m_dt = re.search(r"(?:DAVA\s*TARİHİ|AÇILIŞ\s*TARİHİ)\s*[:\t ]*(\d{2}[./]\d{2}[./]\d{4})", text, re.I)
    if m_dt:
        raw_d = m_dt.group(1).replace("/", ".")
        try:
            data["dava_tarihi"] = datetime.strptime(raw_d, "%d.%m.%Y").strftime("%Y-%m-%d")
        except Exception:
            data["dava_tarihi"] = raw_d

    # 5. Taraflar (Müvekkil Davacı / Karşı Taraf Davalı)
    m_davaci = re.search(r"(?:^|\n)\s*DAVACI\s*[:\t ]*([^\r\n]+)", text, re.I)
    if m_davaci:
        cand_a = re.split(r"VEKİLİ|TC|VKN|-", m_davaci.group(1), flags=re.I)[0].strip().strip(".-")
        if cand_a.lower() not in ["davaciadsoyad", "tarafadisoyadi", "davaci", "adsoyad", ""]:
            data["alacakli"] = cand_a

    m_davali = re.search(r"(?:^|\n)\s*DAVALI\s*[:\t ]*([^\r\n]+)", text, re.I)
    if m_davali:
        cand_b = re.split(r"VEKİLİ|TC|VKN|-", m_davali.group(1), flags=re.I)[0].strip().strip(".-")
        if cand_b.lower() not in ["tarafadisoyadi", "davali", "adsoyad", ""]:
            data["borclu"] = cand_b

    m_kvekil = re.search(r"(?:DAVALI\s*VEKİLİ|VEKİLİ)\s*[:\t ]*(Av\.[^\r\n]+)", text, re.I)
    if m_kvekil:
        data["karsi_vekil"] = m_kvekil.group(1).strip().strip(".-")

    # 6. Dava Değeri (Müddeabih / Dava Esas Değeri)
    m_deg = re.search(r"(?:DAVA\s*(?:ESAS\s*)?DEĞER[İI]|MÜDDEAB[İI]H|TALEP\s*SONUCU)\s*[:\t ]*([0-9.,]+)", text, re.I)
    if m_deg:
        data["dava_degeri"] = parse_tr_float(m_deg.group(1))

    # 7. İlk Duruşma Tarihi ve Saati
    m_dur = re.search(r"(?:duruşma(?:nın)?|ön\s*inceleme)\s*(?:günü|tarihi)?\s*(?:olarak\s*)?[:\t ]*(\d{2}[./]\d{2}[./]\d{4})", text, re.I)
    if m_dur:
        raw_dur = m_dur.group(1).replace("/", ".")
        try:
            data["durusma_tarihi"] = datetime.strptime(raw_dur, "%d.%m.%Y").strftime("%Y-%m-%d")
        except Exception:
            data["durusma_tarihi"] = raw_dur

    m_saat = re.search(r"(?:saat\s*[:\s]*|saatinde\s*)(\d{1,2}[:.]\d{2})", text, re.I)
    if m_saat:
        saat_txt = m_saat.group(1).replace(".", ":")
        if len(saat_txt) == 4:
            saat_txt = "0" + saat_txt
        data["durusma_saati"] = saat_txt

    # 8. İcra Dosya Bilgileri (Tevzi formundan)
    m_icra = re.search(r"İCRA\s*DOSYA\s*(?:BİLGİLERİ)?\s*[:\t ]*([^\r\n]+)", text, re.I)
    if m_icra:
        ic_txt = m_icra.group(1).strip()
        m_ic_no = re.search(r"(\d{4}\s*/\s*\d+)", ic_txt)
        if m_ic_no:
            data["bagli_icra_no"] = m_ic_no.group(1).replace(" ", "")

    return data


def analyze_tensip_or_tevzi_file(file_name, file_bytes):
    """
    Yüklenen dosyanın türüne göre (UDF veya PDF/TXT) en yüksek doğrulukla
    mahkeme, esas, taraflar ve dava bilgilerini analiz eder.
    UDF dosyalarında XML etiketlerinden doğrudan yararlanarak 100% kesinlik sağlar.
    """
    raw_text = extract_text_from_uploaded_file(file_name, file_bytes)
    data = analyze_tensip_or_tevzi_text(raw_text)

    # UDF ise doğrudan XML etiketlerini de tara ve boş/hatalı kalan alanları tamamla
    lower_name = file_name.lower()
    if lower_name.endswith(".udf"):
        try:
            with zipfile.ZipFile(io.BytesIO(file_bytes), 'r') as zf:
                if 'content.xml' in zf.namelist():
                    xml_data = zf.read('content.xml')
                    decoded_xml = None
                    for enc in ['utf-8', 'windows-1254', 'iso-8859-9']:
                        try:
                            decoded_xml = xml_data.decode(enc)
                            break
                        except Exception:
                            pass
                    if not decoded_xml:
                        decoded_xml = xml_data.decode('utf-8', errors='ignore')

                    root = ET.fromstring(decoded_xml)
                    tag_map = {}
                    for elem in root.iter():
                        if elem.text and elem.text.strip():
                            tag_map.setdefault(elem.tag, []).append(elem.text.strip())

                    # Mahkeme Adı
                    if tag_map.get("ilIlceMahkemeAdi"):
                        raw_m = tag_map["ilIlceMahkemeAdi"][0]
                        clean_m = re.sub(r"^[\s\(\)\[\]\{\}\d\.\,\:\-]+", "", raw_m).strip()
                        if clean_m:
                            data["mahkeme_adi"] = clean_m

                    # Esas No
                    if tag_map.get("kayitNo"):
                        kno = tag_map["kayitNo"][0].replace(" ", "").strip()
                        if kno:
                            data["dosya_no"] = kno if (kno.endswith("E.") or kno.endswith("ESAS")) else f"{kno} E."

                    # Dava Türü
                    if tag_map.get("davaTuru"):
                        data["dava_turu"] = tag_map["davaTuru"][0].strip()

                    # Davacı
                    if tag_map.get("davaciAdSoyad"):
                        data["alacakli"] = tag_map["davaciAdSoyad"][0].strip()

                    # Taraflar (Davacı / Davalı)
                    t_roller = tag_map.get("taraf", [])
                    t_adlar = tag_map.get("tarafAdiSoyadi", [])
                    for r, a in zip(t_roller, t_adlar):
                        r_low = r.lower()
                        if "davacı" in r_low or "davaci" in r_low:
                            data["alacakli"] = a.strip()
                        elif "davalı" in r_low or "davali" in r_low:
                            data["borclu"] = a.strip()

                    # Dava Değeri (Müddeabih)
                    if tag_map.get("davaEsasDegeri"):
                        data["dava_degeri"] = parse_tr_float(tag_map["davaEsasDegeri"][0])

                    # Açılış Tarihi
                    if tag_map.get("acilisTarihi"):
                        m_ac = re.search(r"(\d{2}[./]\d{2}[./]\d{4})", tag_map["acilisTarihi"][0])
                        if m_ac:
                            try:
                                data["dava_tarihi"] = datetime.strptime(m_ac.group(1).replace("/", "."), "%d.%m.%Y").strftime("%Y-%m-%d")
                            except Exception:
                                pass

                    # İcra Dosyası Bilgileri
                    if tag_map.get("icraDosyasi"):
                        m_ic = re.search(r"(\d{4}\s*/\s*\d+)", tag_map["icraDosyasi"][0])
                        if m_ic:
                            data["bagli_icra_no"] = m_ic.group(1).replace(" ", "")
                    if tag_map.get("icraMudurlugu"):
                        data["bagli_icra_daire"] = tag_map["icraMudurlugu"][0].strip()
        except Exception:
            pass

    return data


# -------------------------------------------------------------
# 5. GEREKÇELİ KARAR VE HÜKÜM ANALİZ MOTORU
# -------------------------------------------------------------
def analyze_karar_text(text):
    """
    Gerekçeli kararın hüküm fıkrasını analiz ederek lehe ve aleyhe kalemleri çıkarır.
    """
    data = {
        "mahkeme_adi": "",
        "dosya_no": "",
        "karar_no": "",
        "karar_tarihi": str(date.today()),
        "sonuc_turu": "Kabul", # Kabul, Kısmen Kabul, Ret
        "lehe_alacak": 0.0,
        "lehe_tazminat": 0.0,
        "lehe_vekalet": 0.0,
        "lehe_gider": 0.0,
        "aleyhe_vekalet": 0.0,
        "aleyhe_gider": 0.0,
        "hukum_metni": "",
        "kalemler_listesi": []
    }

    if not text:
        return data

    # 1. Mahkeme, Esas, Karar No
    m_mahk = re.search(r"(?:T\.C\.\s*)?([^\r\n]*?(?:MAHKEMES[İI]|HAK[İI]ML[İI]Ğ[İI]))", text, re.I)
    if m_mahk:
        raw_m = m_mahk.group(1).strip()
        clean_m = re.sub(r"^[\s\(\)\[\]\{\}\d\.\,\:\-]+", "", raw_m).strip()
        if clean_m:
            data["mahkeme_adi"] = clean_m

    m_esas = re.search(r"ESAS\s*NO\s*[:\s]+(\d{4}\s*/\s*\d+)", text, re.I)
    if m_esas:
        data["dosya_no"] = m_esas.group(1).replace(" ", "") + " E."

    m_karar = re.search(r"KARAR\s*NO\s*[:\s]+(\d{4}\s*/\s*\d+)", text, re.I)
    if m_karar:
        data["karar_no"] = m_karar.group(1).replace(" ", "") + " K."

    m_kt = re.search(r"KARAR\s*TARİHİ\s*[:\s]+(\d{2}[./]\d{2}[./]\d{4})", text, re.I)
    if m_kt:
        raw_k = m_kt.group(1).replace("/", ".")
        try:
            data["karar_tarihi"] = datetime.strptime(raw_k, "%d.%m.%Y").strftime("%Y-%m-%d")
        except Exception:
            data["karar_tarihi"] = raw_k

    # 2. HÜKÜM fıkrasını yakala
    m_hukum = re.search(r"(?:H\s*Ü\s*K\s*Ü\s*M\s*:|GEREĞİ\s+DÜŞÜNÜLDÜ\s*:)([\s\S]+?)(?:Gerekçeli\s+kararın|Katip|Hakim|\Z)", text, re.I)
    hukum_str = m_hukum.group(1).strip() if m_hukum else text
    data["hukum_metni"] = hukum_str

    # 3. Sonuç Türü (Kabul, Kısmen Kabul, Ret)
    if re.search(r"kısmen\s+kabul", hukum_str, re.I):
        data["sonuc_turu"] = "Kısmen Kabul"
    elif re.search(r"davanın\s+kabulüne", hukum_str, re.I):
        data["sonuc_turu"] = "Kabul"
    elif re.search(r"davanın\s+reddine", hukum_str, re.I):
        data["sonuc_turu"] = "Ret"

    # 4. Asıl Alacak / İptal Tutarı
    m_asl = re.search(r"([0-9.,]+)\s*TL\s*(?:asıl\s*alacak|alacak|asıl\s*borç)", hukum_str, re.I)
    if not m_asl:
        m_asl = re.search(r"(?:kabulü\s+ile|itirazın\s+iptali\s+ile)[^0-9]*?([0-9.,]+)\s*TL", hukum_str, re.I)
    if m_asl:
        data["lehe_alacak"] = parse_tr_float(m_asl.group(1))

    # 5. İcra İnkar Tazminatı
    m_inkar = re.search(r"([0-9.,]+)\s*TL\s*(?:icra\s*ink[aâ]r\s*tazminat|tazminat)", hukum_str, re.I)
    if m_inkar:
        data["lehe_tazminat"] = parse_tr_float(m_inkar.group(1))
    elif data["lehe_alacak"] > 0 and re.search(r"%20|yüzde\s*yirmi", hukum_str, re.I):
        data["lehe_tazminat"] = round(data["lehe_alacak"] * 0.20, 2)

    # 6. Vekalet Ücretleri
    # Davacı lehine
    m_vek_davaci = re.search(r"([0-9.,]+)\s*TL\s*(?:nisbi\s+|maktu\s+)?vekalet\s*ücretinin\s+davalıdan\s+alınarak\s+davacıya", hukum_str, re.I)
    if not m_vek_davaci:
        m_vek_davaci = re.search(r"(?:davacı\s+(?:ve\s+kendisini\s+vekil\s+ile\s+temsil\s+ettiren\s+)?(?:lehine|tarafından)?)[^0-9]*?([0-9.,]+)\s*TL\s*(?:nisbi\s+|maktu\s+)?vekalet\s*ücreti", hukum_str, re.I)
    if m_vek_davaci:
        data["lehe_vekalet"] = parse_tr_float(m_vek_davaci.group(1))

    # Davalı lehine (Aleyhe vekalet)
    m_vek_davali = re.search(r"([0-9.,]+)\s*TL\s*(?:nisbi\s+|maktu\s+)?vekalet\s*ücretinin\s+davacıdan\s+alınarak\s+davalıya", hukum_str, re.I)
    if not m_vek_davali:
        m_vek_davali = re.search(r"(?:davalı\s+(?:ve\s+kendisini\s+vekil\s+ile\s+temsil\s+ettiren\s+)?(?:lehine)?)[^0-9]*?([0-9.,]+)\s*TL\s*(?:nisbi\s+|maktu\s+)?vekalet\s*ücreti", hukum_str, re.I)
    if m_vek_davali:
        data["aleyhe_vekalet"] = parse_tr_float(m_vek_davali.group(1))

    # 7. Yargılama Giderleri
    m_gid_davaci = re.search(r"(?:davacı\s+(?:tarafından\s+yapılan|için)?)[^0-9]*?([0-9.,]+)\s*TL\s*(?:yargılama\s+gideri|harç)", hukum_str, re.I)
    if m_gid_davaci:
        data["lehe_gider"] = parse_tr_float(m_gid_davaci.group(1))

    m_gid_davali = re.search(r"(?:davalı\s+(?:tarafından\s+yapılan)?)[^0-9]*?([0-9.,]+)\s*TL\s*(?:yargılama\s+gideri)", hukum_str, re.I)
    if m_gid_davali:
        data["aleyhe_gider"] = parse_tr_float(m_gid_davali.group(1))

    return data


# -------------------------------------------------------------
# 6. DAVA KARARINI İCRA DOSYASINA ENTEGRE ETME MOTORU
# -------------------------------------------------------------
def sync_dava_karari_to_icra(cursor, conn, icra_id, dava_data, takas_mahsup_et=False):
    """
    Mahkeme kararındaki lehe ve aleyhe kalemleri ilgili icra dosyasına aktarır:
    - İcra inkar tazminatı -> alacak_kalemleri tablosuna
    - Mahkeme ilam vekalet ücreti -> alacak_kalemleri tablosuna
    - Yargılama gideri -> masraflar tablosuna (masraf_tutari)
    - Eğer takas_mahsup_et=True ise aleyhe vekalet ücreti masraflar iade_tutari veya indirim olarak işlenir.
    - dosya_notlari tablosuna mahkeme ilamı işleme notu eklenir.
    """
    dava_etiketi = f"{dava_data.get('mahkeme_adi', 'Mahkeme')} {dava_data.get('dosya_no', '')} K: {dava_data.get('karar_no', '')}"
    eklenen_kalem_sayisi = 0

    # 1. İcra İnkar Tazminatı
    lehe_tazm = float(dava_data.get("lehe_tazminat", 0.0) or 0.0)
    if lehe_tazm > 0:
        cursor.execute("""
            INSERT INTO alacak_kalemleri (dosya_id, kalem_adi, tutar, t_oncesi_faiz, faiz_turu, faiz_orani)
            VALUES (?, ?, ?, 0, 'Faizsiz', 0.0)
        """, (icra_id, f"İcra İnkar Tazminatı ({dava_etiketi})", lehe_tazm))
        eklenen_kalem_sayisi += 1

    # 2. Mahkeme İlam Vekalet Ücreti
    lehe_vek = float(dava_data.get("lehe_vekalet", 0.0) or 0.0)
    if lehe_vek > 0:
        cursor.execute("""
            INSERT INTO alacak_kalemleri (dosya_id, kalem_adi, tutar, t_oncesi_faiz, faiz_turu, faiz_orani)
            VALUES (?, ?, ?, 0, 'Yasal Faiz (%31.00)', 31.0)
        """, (icra_id, f"Mahkeme İlam Vekalet Ücreti ({dava_etiketi})", lehe_vek))
        eklenen_kalem_sayisi += 1

    # 3. Yargılama Gideri
    lehe_gid = float(dava_data.get("lehe_gider", 0.0) or 0.0)
    if lehe_gid > 0:
        cursor.execute("""
            INSERT INTO masraflar (dosya_id, tarih, aciklama, masraf_tutari, iade_tutari)
            VALUES (?, ?, ?, ?, 0)
        """, (icra_id, str(date.today()), f"Mahkeme Yargılama Gideri İlamı ({dava_etiketi})", lehe_gid))
        eklenen_kalem_sayisi += 1

    # 4. Aleyhe Vekalet Ücreti (Takas/Mahsup seçildiyse)
    aleyhe_vek = float(dava_data.get("aleyhe_vekalet", 0.0) or 0.0)
    if aleyhe_vek > 0 and takas_mahsup_et:
        cursor.execute("""
            INSERT INTO masraflar (dosya_id, tarih, aciklama, masraf_tutari, iade_tutari)
            VALUES (?, ?, ?, 0, ?)
        """, (icra_id, str(date.today()), f"Karşı Taraf Vekalet Ücreti Mahsubu / Takas ({dava_etiketi})", aleyhe_vek))
        eklenen_kalem_sayisi += 1

    # 5. Dosya Notu Ekle
    not_ozet = f"⚖️ {dava_etiketi} sayılı ilamı icra hesabına işlendi. Lehe Tazminat: {lehe_tazm:,.2f} TL | İlam Vekaleti: {lehe_vek:,.2f} TL | Yargılama Gideri: {lehe_gid:,.2f} TL."
    if aleyhe_vek > 0:
        not_ozet += f" [⚠️ Davalı vekili lehine {aleyhe_vek:,.2f} TL vekalet ücreti borcu doğdu - Takas: {'Uygulandı' if takas_mahsup_et else 'Beklemede'}]."
    
    cursor.execute("""
        INSERT INTO dosya_notlari (dosya_id, tarih, not_icerik)
        VALUES (?, ?, ?)
    """, (icra_id, str(date.today()), not_ozet))

    # İcra dosyasının durumunu güncelle (İtiraz kaldırıldı / kesinleşti)
    if "iptal" in str(dava_data.get("dava_turu", "")).lower() or "kabul" in str(dava_data.get("sonuc_turu", "")).lower():
        cursor.execute("""
            UPDATE dosyalar 
            SET itiraz_edildi = 0, kesinlesme_durumu = 1
            WHERE id = ?
        """, (icra_id,))

    conn.commit()
    return eklenen_kalem_sayisi, not_ozet


# -------------------------------------------------------------
# 7. iCALENDAR (.ics) DIŞA AKTARICI
# -------------------------------------------------------------
def generate_ics_content(dava_title, durusma_tarihi_str, durusma_saati_str="09:30", mahkeme_adi="", aciklama=""):
    """
    Duruşma için Google Calendar / Outlook / iPhone uyumlu .ics dosyası metni üretir.
    """
    try:
        d_date = datetime.strptime(durusma_tarihi_str[:10], "%Y-%m-%d").date()
    except Exception:
        d_date = date.today()

    h, m = 9, 30
    if durusma_saati_str and ":" in durusma_saati_str:
        try:
            parts = durusma_saati_str.split(":")
            h = int(parts[0])
            m = int(parts[1])
        except Exception:
            pass

    dt_start = datetime(d_date.year, d_date.month, d_date.day, h, m)
    dt_end = dt_start + timedelta(minutes=30)
    now_utc = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    
    start_fmt = dt_start.strftime("%Y%m%dT%H%M%S")
    end_fmt = dt_end.strftime("%Y%m%dT%H%M%S")

    ics_lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//JusLegal//TahsilatPro Dava ve Durusma Takvimi//TR",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        "BEGIN:VEVENT",
        f"UID:durusma-{now_utc}-{start_fmt}@juslegal.com",
        f"DTSTAMP:{now_utc}",
        f"DTSTART:{start_fmt}",
        f"DTEND:{end_fmt}",
        f"SUMMARY:DURUŞMA: {dava_title}",
        f"LOCATION:{mahkeme_adi}",
        f"DESCRIPTION:JusLegal Dava Takip | {dava_title}\\nMahkeme: {mahkeme_adi}\\nNot: {aciklama}",
        "STATUS:CONFIRMED",
        "BEGIN:VALARM",
        "TRIGGER:-PT1D",
        "ACTION:DISPLAY",
        "DESCRIPTION:Yarın Duruşmanız Var!",
        "END:VALARM",
        "BEGIN:VALARM",
        "TRIGGER:-PT2H",
        "ACTION:DISPLAY",
        "DESCRIPTION:2 Saat Sonra Duruşmanız Var!",
        "END:VALARM",
        "END:VEVENT",
        "END:VCALENDAR"
    ]
    return "\r\n".join(ics_lines)
