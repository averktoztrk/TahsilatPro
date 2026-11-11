# -*- coding: utf-8 -*-
"""
TahsilatPro / JusLegal Dava Takip & Mahkeme Masası Görünüm Bileşeni (UI Module)
- Dava Listesi & Çalışma Masası
- Akıllı Duruşma & Süre Ajandası
- Tensip / Tevzi ile Dava Kaydı
- Karar Analiz & Çift Yönlü İcra Entegrasyonu
- İcra Dosyası İçi Bağlı Dava Sekmesi
"""

import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
import dava_engine

def format_money(val):
    try:
        f = float(val or 0.0)
        return f"{f:,.2f} TL".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "0,00 TL"

def render_dava_modulu(conn, cursor, theme_vars):
    accent_green = theme_vars.get("accent_green", "#10B981")
    card_bg = theme_vars.get("card_bg", "#1F2937")
    card_border = theme_vars.get("card_border", "#374151")
    text_main = theme_vars.get("text_main", "#F9FAFB")
    text_muted = theme_vars.get("text_muted", "#9CA3AF")

    # Tabloları garantiye al
    dava_engine.init_dava_tables(cursor, conn)

    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 12px; margin-bottom: 8px;">
            <div style="font-size: 28px;">⚖️</div>
            <div>
                <h2 style="margin: 0; color: {accent_green}; font-weight: 800; font-size: 24px;">Dava Takip & Mahkeme Masası</h2>
                <p style="margin: 2px 0 0 0; color: {text_muted}; font-size: 13px;">
                    Mahkeme dava dosyalarını, duruşma ve hak düşürücü süre ajandasını takip edin; tensip zaptı ve gerekçeli kararları yapay zeka ile icra takipleriyle senkronize edin.
                </p>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # Verileri Çek
    df_davalar = pd.read_sql_query("SELECT * FROM davalar ORDER BY id DESC", conn)

    # Üst Özet Metrikleri
    tot_dava = len(df_davalar)
    derdest_dava = len(df_davalar[df_davalar["durum"] == "Derdest"]) if not df_davalar.empty and "durum" in df_davalar.columns else 0
    karar_dava = len(df_davalar[df_davalar["durum"] != "Derdest"]) if not df_davalar.empty and "durum" in df_davalar.columns else 0
    top_muddeabih = float(df_davalar["dava_degeri"].sum()) if not df_davalar.empty and "dava_degeri" in df_davalar.columns else 0.0

    # Yaklaşan duruşma sayısı (önümüzdeki 15 gün)
    bugun_str = str(date.today())
    onbes_gun_sonra_str = str(date.today() + timedelta(days=15))
    cursor.execute("""
        SELECT COUNT(*) FROM davalar 
        WHERE sonraki_durusma_tarihi >= ? AND sonraki_durusma_tarihi <= ? AND durum = 'Derdest'
    """, (bugun_str, onbes_gun_sonra_str))
    yaklasan_durusma_cnt = cursor.fetchone()[0]

    st.write("")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Toplam Dava Dosyası", f"{tot_dava} Adet")
    m2.metric("Derdest (Açık) Dava", f"{derdest_dava} Dosya")
    m3.metric("🔔 Yaklaşan Duruşma (15 Gün)", f"{yaklasan_durusma_cnt} Duruşma")
    m4.metric("Toplam Dava Değeri", format_money(top_muddeabih))

    st.write("")

    # Ana Sekmeler
    t_liste, t_ajanda, t_yeni, t_karar = st.tabs([
        "📋 Dava Listesi & Çalışma Masası",
        "📅 Akıllı Duruşma & Süre Ajandası",
        "➕ Akıllı Dava Kaydı (Tensip / Tevzi)",
        "⚖️ Karar Analiz & İcraya Aktarım Merkezi"
    ])

    # -------------------------------------------------------------
    # TAB 1: DAVA LİSTESİ & ÇALIŞMA MASASI
    # -------------------------------------------------------------
    with t_liste:
        if df_davalar.empty:
            st.info("💡 Sistemde henüz kayıtlı bir dava dosyası bulunmuyor. '➕ Akıllı Dava Kaydı' sekmesinden Tensip Zaptı yükleyerek ilk davanızı anında açabilirsiniz.")
        else:
            fc1, fc2, fc3, fc4 = st.columns(4)
            with fc1:
                muv_list = ["Tümü"] + sorted(list(set([str(x) for x in df_davalar["alacakli"].dropna().unique() if str(x).strip()])))
                sec_muv = st.selectbox("Müvekkil Filtresi", muv_list, key="dava_filter_muv")
            with fc2:
                durum_list = ["Tümü", "Derdest", "Karara Çıktı", "İstinafta", "Yargıtay'da", "Kesinleşti", "Feragat / Sulh"]
                sec_durum = st.selectbox("Durum Filtresi", durum_list, key="dava_filter_durum")
            with fc3:
                tur_list = ["Tümü"] + sorted(list(set([str(x) for x in df_davalar["dava_turu"].dropna().unique() if str(x).strip()])))
                sec_tur = st.selectbox("Dava Türü", tur_list, key="dava_filter_tur")
            with fc4:
                arama_kelimesi = st.text_input("🔍 Hızlı Ara (Esas, Mahkeme, Borçlu)", placeholder="Örn: 2024/782 veya Asliye", key="dava_quick_search")

            filtrelenmis_df = df_davalar.copy()
            if sec_muv != "Tümü":
                filtrelenmis_df = filtrelenmis_df[filtrelenmis_df["alacakli"] == sec_muv]
            if sec_durum != "Tümü":
                filtrelenmis_df = filtrelenmis_df[filtrelenmis_df["durum"] == sec_durum]
            if sec_tur != "Tümü":
                filtrelenmis_df = filtrelenmis_df[filtrelenmis_df["dava_turu"] == sec_tur]
            if arama_kelimesi.strip():
                q = arama_kelimesi.strip().lower()
                filtrelenmis_df = filtrelenmis_df[
                    filtrelenmis_df["dosya_no"].str.lower().str.contains(q, na=False) |
                    filtrelenmis_df["mahkeme_adi"].str.lower().str.contains(q, na=False) |
                    filtrelenmis_df["borclu"].str.lower().str.contains(q, na=False) |
                    filtrelenmis_df["alacakli"].str.lower().str.contains(q, na=False)
                ]

            st.caption(f"⚡ Listelenen: **{len(filtrelenmis_df)} dava dosyası**")

            # Hızlı Seçici
            dava_dict = {f"[{r['id']}] {r['dosya_no']} | {r['mahkeme_adi']} - {r['borclu']}": int(r['id']) for _, r in filtrelenmis_df.iterrows()}
            dava_keys = ["-- Dosya Seçin veya Aşağıdaki Tablodan İnceleyin --"] + list(dava_dict.keys())
            secili_dava_label = st.selectbox("🎯 İncelenecek Dava Dosyasını Seçin:", dava_keys, key="dava_picker_select")

            aktif_dava_id = None
            if secili_dava_label != "-- Dosya Seçin veya Aşağıdaki Tablodan İnceleyin --":
                aktif_dava_id = dava_dict[secili_dava_label]

            # Tablo Gösterimi
            gosterim_tablosu = pd.DataFrame({
                "ID": filtrelenmis_df["id"],
                "Mahkeme": filtrelenmis_df["mahkeme_adi"],
                "Esas No": filtrelenmis_df["dosya_no"],
                "Dava Türü": filtrelenmis_df["dava_turu"],
                "Müvekkil": filtrelenmis_df["alacakli"],
                "Karşı Taraf": filtrelenmis_df["borclu"],
                "Dava Değeri": filtrelenmis_df["dava_degeri"].apply(format_money),
                "Durum": filtrelenmis_df["durum"],
                "Aşama": filtrelenmis_df["asama"],
                "Sonraki Duruşma": filtrelenmis_df["sonraki_durusma_tarihi"].fillna("-")
            })

            st.dataframe(gosterim_tablosu, use_container_width=True, hide_index=True)

            # Seçili Dava Detayı
            if aktif_dava_id:
                row_sel = df_davalar[df_davalar["id"] == aktif_dava_id].iloc[0]
                st.markdown("---")
                
                det_col1, det_col2 = st.columns([1.6, 1.0])
                with det_col1:
                    st.markdown(f"#### 🏛️ {row_sel['mahkeme_adi']} - `{row_sel['dosya_no']}`")
                    st.caption(f"**Dava Türü:** {row_sel['dava_turu']} | **Açılış Tarihi:** `{row_sel['dava_tarihi']}` | **Aşama:** `{row_sel['asama']}` | **Durum:** `{row_sel['durum']}`")

                    # Bağlı İcra Dosyası Bilgisi
                    bagli_icra_id = row_sel.get("bagli_icra_id")
                    if bagli_icra_id and pd.notnull(bagli_icra_id):
                        cursor.execute("SELECT dosya_no, icra_dairesi, il, borclu FROM dosyalar WHERE id = ?", (int(bagli_icra_id),))
                        icra_row = cursor.fetchone()
                        if icra_row:
                            st.success(f"🔗 **Bağlı İcra Takibi:** {icra_row[2]} {icra_row[1]} `{icra_row[0]}` (Borçlu: {icra_row[3]})")
                        else:
                            st.info("🔗 Bağlı İcra ID: #" + str(bagli_icra_id))
                    else:
                        st.info("ℹ️ Bu dava şu anda hiçbir icra dosyasına bağlı değil.")

                    # Dava Notları
                    st.markdown("##### 📝 Dava Notları")
                    df_notlar = pd.read_sql_query("SELECT id, tarih, not_icerik FROM dava_notlari WHERE dava_id = ? ORDER BY tarih DESC, id DESC", conn, params=[aktif_dava_id])
                    if not df_notlar.empty:
                        for _, n_r in df_notlar.iterrows():
                            st.markdown(f"- **`{n_r['tarih']}`**: {n_r['not_icerik']}")
                    else:
                        st.caption("Henüz not eklenmemiş.")

                    with st.expander("➕ Yeni Not Ekle", expanded=False):
                        with st.form(f"form_dava_not_{aktif_dava_id}"):
                            n_date = st.date_input("Not Tarihi", value=date.today())
                            n_txt = st.text_area("Not Açıklaması", placeholder="Duruşmada alınan ara karar, müzekkere cevabı vb.")
                            if st.form_submit_button("💾 Notu Kaydet", type="primary"):
                                if n_txt.strip():
                                    cursor.execute("INSERT INTO dava_notlari (dava_id, tarih, not_icerik) VALUES (?, ?, ?)", (aktif_dava_id, str(n_date), n_txt.strip()))
                                    conn.commit()
                                    st.success("Not kaydedildi!")
                                    st.rerun()

                with det_col2:
                    # Duruşma ve Mali Özet Kartı
                    durusma_tarihi_str = str(row_sel.get("sonraki_durusma_tarihi") or "")
                    durusma_saati_str = str(row_sel.get("durusma_saati") or "09:30")
                    
                    st.markdown(f"""
                        <div style="background: {card_bg}; border: 1.5px solid {accent_green}; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
                            <div style="font-size: 11px; text-transform: uppercase; color: {accent_green}; font-weight: 700;">DAVA FİNANSAL DEĞERİ</div>
                            <div style="font-size: 22px; font-weight: 800; color: {text_main}; margin-top: 3px;">{format_money(row_sel['dava_degeri'])}</div>
                        </div>
                    """, unsafe_allow_html=True)

                    if durusma_tarihi_str and durusma_tarihi_str != "None":
                        try:
                            d_obj = datetime.strptime(durusma_tarihi_str[:10], "%Y-%m-%d").date()
                            kalan_gun = (d_obj - date.today()).days
                            if kalan_gun > 0:
                                gun_badge = f"<span style='background:#0284C7; color:#fff; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:700;'>{kalan_gun} GÜN KALDI</span>"
                            elif kalan_gun == 0:
                                gun_badge = "<span style='background:#EF4444; color:#fff; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:700;'>🚨 BUGÜN!</span>"
                            else:
                                gun_badge = f"<span style='background:#64748B; color:#fff; padding:3px 8px; border-radius:6px; font-size:11px; font-weight:700;'>{abs(kalan_gun)} Gün Önce Yapıldı</span>"
                        except Exception:
                            gun_badge = ""

                        st.markdown(f"""
                            <div style="background: {card_bg}; border: 1.5px solid {card_border}; border-radius: 10px; padding: 14px; margin-bottom: 12px;">
                                <div style="display:flex; justify-content:space-between; align-items:center;">
                                    <span style="font-size: 11px; text-transform: uppercase; color: #38BDF8; font-weight: 700;">📅 SONRAKİ DURUŞMA</span>
                                    {gun_badge}
                                </div>
                                <div style="font-size: 18px; font-weight: 800; color: {text_main}; margin-top: 6px;">
                                    {durusma_tarihi_str} - {durusma_saati_str}
                                </div>
                                <div style="font-size: 12px; color: {text_muted}; margin-top: 4px;">{row_sel.get('durusma_aciklamasi', '') or 'Duruşma safhasında.'}</div>
                            </div>
                        """, unsafe_allow_html=True)

                        # iCalendar (.ics) İndirme Butonu
                        ics_text = dava_engine.generate_ics_content(
                            f"{row_sel['mahkeme_adi']} {row_sel['dosya_no']} Duruşması",
                            durusma_tarihi_str,
                            durusma_saati_str,
                            row_sel['mahkeme_adi'],
                            f"Borçlu: {row_sel['borclu']} | Dava Türü: {row_sel['dava_turu']}"
                        )
                        st.download_button(
                            label="📲 Duruşmayı Takvime Ekle (.ics)",
                            data=ics_text.encode("utf-8"),
                            file_name=f"durusma_{row_sel['dosya_no'].replace('/', '_')}.ics",
                            mime="text/calendar",
                            use_container_width=True,
                            key=f"btn_ics_{aktif_dava_id}"
                        )

                    # Duruşma Tarihini Hızlı Güncelle
                    with st.expander("🔄 Duruşma Tarihi / Aşama Güncelle", expanded=False):
                        with st.form(f"form_upd_durusma_{aktif_dava_id}"):
                            y_tarih = st.date_input("Yeni Duruşma Tarihi", value=date.today() + timedelta(days=30))
                            y_saat = st.text_input("Duruşma Saati", value=durusma_saati_str)
                            asamalar = ["Dilekçeler Teatisi", "Ön İnceleme", "Tahkikat", "Bilirkişi İncelemesi", "Karar", "İstinaf / Temyiz"]
                            cur_asama = row_sel.get("asama", "Ön İnceleme")
                            as_idx = asamalar.index(cur_asama) if cur_asama in asamalar else 1
                            y_asama = st.selectbox("Dava Aşaması", asamalar, index=as_idx)
                            y_aciklama = st.text_input("Duruşma Açıklaması", value=str(row_sel.get("durusma_aciklamasi", "") or ""))

                            if st.form_submit_button("💾 Duruşmayı Güncelle", type="primary"):
                                cursor.execute("""
                                    UPDATE davalar 
                                    SET sonraki_durusma_tarihi = ?, durusma_saati = ?, asama = ?, durusma_aciklamasi = ?
                                    WHERE id = ?
                                """, (str(y_tarih), y_saat, y_asama, y_aciklama, aktif_dava_id))
                                conn.commit()
                                st.success("Duruşma bilgisi güncellendi!")
                                st.rerun()

                    # Davayı Sil Butonu
                    if st.button("🗑️ Davayı Sistemden Sil", key=f"btn_del_dava_{aktif_dava_id}"):
                        cursor.execute("DELETE FROM davalar WHERE id = ?", (aktif_dava_id,))
                        cursor.execute("DELETE FROM dava_notlari WHERE dava_id = ?", (aktif_dava_id,))
                        cursor.execute("DELETE FROM dava_sureleri WHERE dava_id = ?", (aktif_dava_id,))
                        conn.commit()
                        st.warning("Dava dosyası silindi.")
                        st.rerun()

    # -------------------------------------------------------------
    # TAB 2: AKILLI DURUŞMA & SÜRE AJANDASI
    # -------------------------------------------------------------
    with t_ajanda:
        st.markdown("##### 📅 Duruşma Takvimi & Hak Düşürücü Süre Ajandası")
        st.caption("Önümüzdeki duruşmalarınızı gün sayacıyla izleyin, tek tıkla cep telefonunuza veya bilgisayar takviminize aktarın.")

        cursor.execute("""
            SELECT id, mahkeme_adi, dosya_no, alacakli, borclu, dava_turu, sonraki_durusma_tarihi, durusma_saati, durusma_aciklamasi
            FROM davalar
            WHERE sonraki_durusma_tarihi IS NOT NULL AND sonraki_durusma_tarihi != '' AND durum = 'Derdest'
            ORDER BY sonraki_durusma_tarihi ASC
        """)
        durusma_rows = cursor.fetchall()

        if not durusma_rows:
            st.info("🟢 Yaklaşan planlı bir duruşmanız bulunmuyor.")
        else:
            for d_id, mahk, d_no, alac, borc, tur, d_tarih, d_saat, acik in durusma_rows:
                try:
                    d_obj = datetime.strptime(d_tarih[:10], "%Y-%m-%d").date()
                    kalan = (d_obj - date.today()).days
                except Exception:
                    kalan = 0

                if kalan > 7:
                    b_color = "#0284C7"
                    b_txt = f"{kalan} Gün Kaldı"
                elif 0 <= kalan <= 7:
                    b_color = "#EAB308"
                    b_txt = f"⚠️ {kalan} Gün Kaldı (Yaklaşıyor)"
                else:
                    b_color = "#64748B"
                    b_txt = f"{abs(kalan)} Gün Önceydi"

                c_d1, c_d2 = st.columns([3.5, 1.2])
                with c_d1:
                    st.markdown(f"""
                        <div style="background:{card_bg}; border:1px solid {card_border}; border-left: 4px solid {b_color}; border-radius:8px; padding:10px 14px; margin-bottom:8px;">
                            <div style="display:flex; justify-content:space-between;">
                                <strong style="font-size:15px; color:{text_main};">{mahk} - {d_no}</strong>
                                <span style="background:{b_color}; color:#fff; font-size:11px; font-weight:700; padding:2px 8px; border-radius:4px;">{b_txt}</span>
                            </div>
                            <div style="font-size:12px; color:{accent_green}; margin-top:3px;">
                                📅 <b>{d_tarih} - Saat {d_saat or '09:30'}</b> | Dava: {tur}
                            </div>
                            <div style="font-size:12px; color:{text_muted}; margin-top:2px;">
                                Müvekkil: <b>{alac}</b> | Karşı Taraf: <b>{borc}</b> {f'— <i>({acik})</i>' if acik else ''}
                            </div>
                        </div>
                    """, unsafe_allow_html=True)
                with c_d2:
                    ics_content = dava_engine.generate_ics_content(
                        f"Duruşma: {mahk} {d_no}",
                        d_tarih,
                        d_saat or "09:30",
                        mahk,
                        f"Müvekkil: {alac} | Borçlu: {borc}"
                    )
                    st.download_button(
                        label="📲 Takvime Ekle (.ics)",
                        data=ics_content.encode("utf-8"),
                        file_name=f"durusma_{d_id}.ics",
                        mime="text/calendar",
                        key=f"btn_agenda_ics_{d_id}",
                        use_container_width=True
                    )

    # -------------------------------------------------------------
    # TAB 3: AKILLI DAVA KAYDI (TENSİP / TEVZİ VEYA MANUEL)
    # -------------------------------------------------------------
    with t_yeni:
        st.markdown("##### ➕ Akıllı Dava Kaydı (Tensip Zaptı / Tevzi Formu ile veya Manuel)")
        st.caption("UYAP'tan indirdiğiniz Tensip Zaptını veya Tevzi Formunu (`.udf` veya `.pdf`) yükleyin; sistem mahkeme, esas, taraflar ve duruşma gününü otomatik doldursun.")

        uploaded_belge = st.file_uploader(
            "📄 Tensip Zaptı veya Tevzi Formu Yükleyin (Opsiyonel - Otomatik Doldurma İçin):",
            type=["udf", "pdf", "txt"],
            key="upl_tensip_form"
        )

        parsed_data = {}
        if uploaded_belge is not None:
            file_bytes = uploaded_belge.read()
            parsed_data = dava_engine.analyze_tensip_or_tevzi_file(uploaded_belge.name, file_bytes)
            if parsed_data.get("mahkeme_adi") or parsed_data.get("dosya_no") or parsed_data.get("alacakli"):
                m_info = f"Mahkeme: **{parsed_data.get('mahkeme_adi')}**" if parsed_data.get('mahkeme_adi') else ""
                e_info = f"Esas: **{parsed_data.get('dosya_no')}**" if parsed_data.get('dosya_no') else ""
                d_info = f"Müvekkil: **{parsed_data.get('alacakli')}**" if parsed_data.get('alacakli') else ""
                st.success(f"✨ **Belge Başarıyla Okundu!** {m_info} | {e_info} | {d_info}")
            else:
                st.warning("Belge metni çıkarılamadı veya boş. Lütfen form alanlarını elle doldurunuz.")

        # İcra dosyaları listesini hazırla (Bağlantı için)
        cursor.execute("SELECT id, il, icra_dairesi, dosya_no, borclu FROM dosyalar ORDER BY id DESC")
        icra_listesi = cursor.fetchall()
        icra_dict = {"-- Bağlı İcra Dosyası Yok (Müstakil Dava) --": None}
        for ic_id, ic_il, ic_d, ic_no, ic_b in icra_listesi:
            icra_dict[f"[{ic_id}] {ic_il} {ic_d} {ic_no} | {ic_b}"] = ic_id

        # Otomatik İcra Dosyası Eşleştirme (Tevzi Formundan gelen icra dosya numarasına göre)
        auto_icra_idx = 0
        bagli_ic_no = parsed_data.get("bagli_icra_no", "")
        if bagli_ic_no:
            for idx, key in enumerate(icra_dict.keys()):
                if bagli_ic_no in key:
                    auto_icra_idx = idx
                    break

        if auto_icra_idx > 0:
            st.info(f"🔗 **Tevzi Formundaki İcra Dosyası Tespit Edildi:** Otomatik eşleştirildi ({list(icra_dict.keys())[auto_icra_idx]}).")

        with st.form("form_yeni_dava_kaydi"):
            f_c1, f_c2 = st.columns(2)
            with f_c1:
                def_mahkeme = parsed_data.get("mahkeme_adi", "")
                i_mahkeme = st.text_input("Mahkeme Adı", value=def_mahkeme, placeholder="Örn: İzmir 3. Asliye Ticaret Mahkemesi")
                
                def_esas = parsed_data.get("dosya_no", "")
                i_esas = st.text_input("Esas No", value=def_esas, placeholder="Örn: 2024/782 E.")

                dava_turleri = [
                    "İtirazın İptali (İİK m. 67)",
                    "İtirazın Kaldırılması (İİK m. 68)",
                    "Menfi Tespit (İİK m. 72)",
                    "İstirdat Davası (İİK m. 72/son)",
                    "Tasarrufun İptali (İİK m. 277 vd.)",
                    "İstihkak Davası",
                    "İcra Ceza / Taahhüdü İhlal",
                    "Alacak / Tazminat Davası",
                    "İşçilik Alacakları Davası",
                    "Diğer Hukuk Davası"
                ]
                cur_dtur = parsed_data.get("dava_turu", "İtirazın İptali (İİK m. 67)")
                d_idx = 0
                for idx, dt in enumerate(dava_turleri):
                    if "itirazın iptali" in cur_dtur.lower() and "itirazın iptali" in dt.lower():
                        d_idx = idx
                        break
                    elif dt.split()[0].lower() in cur_dtur.lower():
                        d_idx = idx
                        break
                i_tur = st.selectbox("Dava Türü", dava_turleri, index=d_idx)

                def_dtarih = parsed_data.get("dava_tarihi", str(date.today()))
                try:
                    def_dtarih_val = datetime.strptime(def_dtarih[:10], "%Y-%m-%d").date()
                except Exception:
                    def_dtarih_val = date.today()
                i_dtarih = st.date_input("Dava Açılış Tarihi", value=def_dtarih_val)

                def_deger = float(parsed_data.get("dava_degeri", 0.0) or 0.0)
                i_deger = st.number_input("Dava Değeri / Müddeabih (TL)", value=def_deger, step=1000.0, format="%.2f")

            with f_c2:
                def_alacakli = parsed_data.get("alacakli", "")
                i_alacakli = st.text_input("Müvekkil (Davacı / Davalı)", value=def_alacakli, placeholder="Örn: Kulalılar İnşaat A.Ş.")

                def_borclu = parsed_data.get("borclu", "")
                i_borclu = st.text_input("Karşı Taraf (Davalı / Davacı)", value=def_borclu, placeholder="Örn: Demirtaş Metal Ltd. Şti.")

                def_kvekil = parsed_data.get("karsi_vekil", "")
                i_kvekil = st.text_input("Karşı Taraf Vekili", value=def_kvekil, placeholder="Örn: Av. Ahmet Yılmaz")

                i_bagli_icra = st.selectbox("🔗 Bağlı İcra Dosyası Seç (Varsa)", list(icra_dict.keys()), index=auto_icra_idx)

                # Duruşma Bilgisi
                def_dur_t = parsed_data.get("durusma_tarihi", "")
                try:
                    def_dur_val = datetime.strptime(def_dur_t[:10], "%Y-%m-%d").date() if def_dur_t else None
                except Exception:
                    def_dur_val = None
                
                has_dur = st.checkbox("Duruşma / Ön İnceleme Tarihi Belirlendi", value=bool(def_dur_val))
                if has_dur:
                    i_durtarih = st.date_input("İlk Duruşma Tarihi", value=def_dur_val if def_dur_val else date.today() + timedelta(days=30))
                    i_dursaati = st.text_input("Duruşma Saati", value=parsed_data.get("durusma_saati", "09:30"))
                else:
                    i_durtarih = None
                    i_dursaati = "09:30"

            if st.form_submit_button("💾 Dava Dosyasını Kaydet", type="primary"):
                if not i_mahkeme.strip() or not i_esas.strip():
                    st.error("Mahkeme Adı ve Esas No alanları zorunludur.")
                else:
                    secili_icra_id = icra_dict[i_bagli_icra]
                    cursor.execute("""
                        INSERT INTO davalar (
                            mahkeme_adi, dosya_no, dava_turu, dava_tarihi, alacakli, borclu, karsi_vekil,
                            dava_degeri, durum, asama, sonraki_durusma_tarihi, durusma_saati, bagli_icra_id, olusturma_tarihi
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'Derdest', 'Ön İnceleme', ?, ?, ?, ?)
                    """, (
                        i_mahkeme.strip(), i_esas.strip(), i_tur, str(i_dtarih), i_alacakli.strip(), i_borclu.strip(),
                        i_kvekil.strip(), i_deger, str(i_durtarih) if i_durtarih else None, i_dursaati, secili_icra_id, str(date.today())
                    ))
                    conn.commit()
                    st.success("🎉 Dava dosyası başarıyla kaydedildi!")
                    st.rerun()

    # -------------------------------------------------------------
    # TAB 4: KARAR ANALİZ & İCRAYA AKTARIM MERKEZİ
    # -------------------------------------------------------------
    with t_karar:
        st.markdown("##### ⚖️ Gerekçeli Karar Analiz & Çift Yönlü İcra Entegrasyonu")
        st.caption("Mahkemenin Gerekçeli Kararını (`.udf` veya `.pdf`) yükleyin; hüküm fıkrasındaki lehe alacak, tazminat ve vekâlet kalemleri analiz edilerek bağlı icra dosyasına otomatik aktarılsın.")

        if df_davalar.empty:
            st.info("Sistemde henüz bir dava kaydı bulunmuyor.")
        else:
            d_sec_dict = {f"[{r['id']}] {r['dosya_no']} | {r['mahkeme_adi']} ({r['borclu']})": int(r['id']) for _, r in df_davalar.iterrows()}
            k_dava_lbl = st.selectbox("Kararı İşlenecek Dava Dosyasını Seçin:", list(d_sec_dict.keys()), key="karar_dava_select")
            k_dava_id = d_sec_dict[k_dava_lbl]
            cur_dava_row = df_davalar[df_davalar["id"] == k_dava_id].iloc[0]

            karar_belgesi = st.file_uploader("📄 Mahkemenin Gerekçeli Kararını Yükleyin (.udf veya .pdf):", type=["udf", "pdf", "txt"], key="upl_karar_doc")

            if karar_belgesi is not None:
                k_bytes = karar_belgesi.read()
                k_raw_text = dava_engine.extract_text_from_uploaded_file(karar_belgesi.name, k_bytes)
                
                if not k_raw_text:
                    st.error("Karar metni okunamadı. Lütfen geçerli bir metin tabanlı UDF veya PDF yükleyin.")
                else:
                    k_analiz = dava_engine.analyze_karar_text(k_raw_text)
                    st.success(f"⚖️ **Hüküm Fıkrası Tespit Edildi!** Sonuç: **{k_analiz['sonuc_turu']}**")

                    # Çift Kutulu Bilanço
                    st.write("")
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        st.markdown(f"""
                            <div style="background:{card_bg}; border: 1.5px solid #10B981; border-radius:10px; padding:14px;">
                                <div style="font-size:12px; font-weight:800; color:#10B981; text-transform:uppercase;">🟢 MÜVEKKİL LEHİNE HÜKÜM (İCRAYA GİRECEK)</div>
                                <div style="font-size:13px; color:{text_main}; margin-top:8px;">
                                    • Kabul Edilen Alacak: <b>{format_money(k_analiz['lehe_alacak'])}</b><br>
                                    • %20 İcra İnkar Tazminatı: <b>{format_money(k_analiz['lehe_tazminat'])}</b><br>
                                    • Lehe İlam Vekalet Ücreti: <b>{format_money(k_analiz['lehe_vekalet'])}</b><br>
                                    • Lehe Yargılama Gideri: <b>{format_money(k_analiz['lehe_gider'])}</b>
                                </div>
                                <hr style="margin:10px 0; border-color:{card_border};">
                                <div style="font-size:16px; font-weight:800; color:#10B981;">
                                    TOPLAM LEHE: {format_money(k_analiz['lehe_alacak'] + k_analiz['lehe_tazminat'] + k_analiz['lehe_vekalet'] + k_analiz['lehe_gider'])}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                    with b_col2:
                        has_aleyhe = k_analiz['aleyhe_vekalet'] > 0 or k_analiz['aleyhe_gider'] > 0
                        box_border = "#EF4444" if has_aleyhe else card_border
                        st.markdown(f"""
                            <div style="background:{card_bg}; border: 1.5px solid {box_border}; border-radius:10px; padding:14px;">
                                <div style="font-size:12px; font-weight:800; color:#EF4444; text-transform:uppercase;">🔴 MÜVEKKİL ALEYHİNE (BORÇ & RİSK)</div>
                                <div style="font-size:13px; color:{text_main}; margin-top:8px;">
                                    • Davalı Lehine Vekalet: <b>{format_money(k_analiz['aleyhe_vekalet'])}</b><br>
                                    • Karşı Taraf Yargılama Gideri: <b>{format_money(k_analiz['aleyhe_gider'])}</b>
                                </div>
                                <hr style="margin:10px 0; border-color:{card_border};">
                                <div style="font-size:16px; font-weight:800; color:#EF4444;">
                                    TOPLAM ALEYHE: {format_money(k_analiz['aleyhe_vekalet'] + k_analiz['aleyhe_gider'])}
                                </div>
                            </div>
                        """, unsafe_allow_html=True)

                    # Aleyhe Vekalet Varsa Kritik Uyarı
                    if k_analiz['aleyhe_vekalet'] > 0:
                        st.write("")
                        st.markdown(f"""
                            <div style="background: rgba(239, 68, 68, 0.15); border: 1.5px solid #EF4444; border-radius: 8px; padding: 12px 16px;">
                                <strong style="color: #EF4444; font-size: 14px;">🚨 HUKUKİ RİSK & TAKAS UYARISI:</strong><br>
                                <span style="font-size: 13px; color: {text_main};">
                                    Davalı lehine <b>{format_money(k_analiz['aleyhe_vekalet'])}</b> vekâlet ücreti hükmedilmiştir. Karşı vekil bu tutarı aleyhinize icraya koyabilir.
                                </span>
                            </div>
                        """, unsafe_allow_html=True)

                        opt_takas = st.radio(
                            "Karşı Vekalet Ücreti Nasıl İşlensin?",
                            [
                                "🔄 Takas / Mahsup Et: Karşı vekalet ücretini icradaki alacağımızdan doğrudan mahsup et (Düş)",
                                "📌 Müvekkil Cari Borcuna Yaz: İcraya sadece lehimize olan kalemleri yaz, karşı vekaleti müvekkile borç kaydet"
                            ],
                            key="rad_takas_secim"
                        )
                        takas_secildi = "Takas" in opt_takas
                    else:
                        takas_secildi = False

                    # Aktarım Hedefi
                    st.write("")
                    bagli_icra_id = cur_dava_row.get("bagli_icra_id")
                    if bagli_icra_id and pd.notnull(bagli_icra_id):
                        cursor.execute("SELECT id, il, icra_dairesi, dosya_no, borclu FROM dosyalar WHERE id = ?", (int(bagli_icra_id),))
                        linked_icra = cursor.fetchone()
                    else:
                        linked_icra = None

                    if linked_icra:
                        st.info(f"🎯 **Otomatik Hedef:** Karar, bu davanın bağlı olduğu **{linked_icra[1]} {linked_icra[2]} {linked_icra[3]}** sayılı icra dosyasına aktarılacaktır.")
                        btn_aktar_lbl = "⚡ Kararı Bağlı İcra Dosyasına Ekle ve Hesap Motorunu Güncelle"
                    else:
                        st.warning("Bu davanın bağlı olduğu bir icra takibi bulunamadı. Lütfen aktarılacak icra dosyasını aşağıdan seçin:")
                        cursor.execute("SELECT id, il, icra_dairesi, dosya_no, borclu FROM dosyalar ORDER BY id DESC")
                        all_icras = cursor.fetchall()
                        ic_sel_dict = {f"[{r[0]}] {r[1]} {r[2]} {r[3]} ({r[4]})": r[0] for r in all_icras}
                        sec_ic_lbl = st.selectbox("Hedef İcra Dosyası:", list(ic_sel_dict.keys()), key="man_ic_select")
                        linked_icra = [ic_sel_dict[sec_ic_lbl]]
                        btn_aktar_lbl = "⚡ Kararı Seçilen İcra Dosyasına Ekle ve Hesap Motorunu Güncelle"

                    if st.button(btn_aktar_lbl, type="primary", use_container_width=True, key=f"btn_sync_karar_{k_dava_id}"):
                        target_icra_id = linked_icra[0]
                        k_data = {
                            "mahkeme_adi": k_analiz.get("mahkeme_adi") or cur_dava_row["mahkeme_adi"],
                            "dosya_no": k_analiz.get("dosya_no") or cur_dava_row["dosya_no"],
                            "karar_no": k_analiz.get("karar_no") or "2025/Karar",
                            "dava_turu": cur_dava_row["dava_turu"],
                            "sonuc_turu": k_analiz["sonuc_turu"],
                            "lehe_tazminat": k_analiz["lehe_tazminat"],
                            "lehe_vekalet": k_analiz["lehe_vekalet"],
                            "lehe_gider": k_analiz["lehe_gider"],
                            "aleyhe_vekalet": k_analiz["aleyhe_vekalet"]
                        }

                        eklenen, not_msg = dava_engine.sync_dava_karari_to_icra(
                            cursor, conn, target_icra_id, k_data, takas_mahsup_et=takas_secildi
                        )

                        # Dava durumunu güncelle
                        cursor.execute("""
                            UPDATE davalar
                            SET durum = 'Karara Çıktı', karar_no = ?, karar_ozeti = ?,
                                lehe_alacak = ?, lehe_tazminat = ?, lehe_vekalet = ?, lehe_gider = ?,
                                aleyhe_vekalet = ?, aleyhe_gider = ?, bagli_icra_id = ?
                            WHERE id = ?
                        """, (
                            k_data["karar_no"], k_analiz.get("hukum_metni", "")[:1000],
                            k_analiz["lehe_alacak"], k_analiz["lehe_tazminat"], k_analiz["lehe_vekalet"], k_analiz["lehe_gider"],
                            k_analiz["aleyhe_vekalet"], k_analiz["aleyhe_gider"], target_icra_id, k_dava_id
                        ))
                        conn.commit()

                        st.success(f"🎉 **Başarıyla Entegre Edildi!** İcra dosyasına {eklenen} adet kalem eklendi ve takip itirazı kaldırılarak kesinleştirildi.")
                        st.info(f"📌 **Dosya Notu:** {not_msg}")
                        st.rerun()


# -------------------------------------------------------------
# İCRA DOSYASI İÇİNDEKİ BAĞLI DAVALAR SEKME BİLEŞENİ
# -------------------------------------------------------------
def render_bagli_davalar_tab(conn, cursor, secili_id, secili_dosya, theme_vars):
    accent_green = theme_vars.get("accent_green", "#10B981")
    card_bg = theme_vars.get("card_bg", "#1F2937")
    card_border = theme_vars.get("card_border", "#374151")
    text_main = theme_vars.get("text_main", "#F9FAFB")
    text_muted = theme_vars.get("text_muted", "#9CA3AF")

    # Bu icra dosyasına bağlı davaları çek
    cursor.execute("""
        SELECT id, mahkeme_adi, dosya_no, karar_no, dava_turu, dava_tarihi, dava_degeri, durum, asama, 
               sonraki_durusma_tarihi, durusma_saati, durusma_aciklamasi, lehe_vekalet, aleyhe_vekalet, lehe_tazminat
        FROM davalar
        WHERE bagli_icra_id = ?
        ORDER BY id DESC
    """, (secili_id,))
    bagli_rows = cursor.fetchall()

    st.markdown("##### ⚖️ Bu İcra Takibine Bağlı Mahkeme Davaları")
    st.caption("İtirazın iptali, menfi tespit veya tahliye gibi bu icra dosyasından doğan veya bu icraya bağlanan mahkeme süreçleri.")

    if not bagli_rows:
        st.info("ℹ️ Bu icra dosyasına bağlı herhangi bir mahkeme davası bulunmuyor.")
    else:
        for r_id, mahk, d_no, k_no, tur, dt, deg, drm, asama, dur_t, dur_s, dur_acik, l_vek, a_vek, l_tazm in bagli_rows:
            with st.container():
                st.markdown(f"""
                    <div style="background:{card_bg}; border:1.5px solid {accent_green}; border-radius:10px; padding:14px; margin-bottom:12px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <span style="font-size:16px; font-weight:800; color:{text_main};">🏛️ {mahk}</span>
                            <span style="background:#0284C7; color:#fff; font-size:11px; font-weight:700; padding:3px 8px; border-radius:6px;">{drm} - {asama}</span>
                        </div>
                        <div style="font-size:13px; color:{accent_green}; margin-top:4px;">
                            <b>Esas No:</b> {d_no} {f'| <b>Karar No:</b> {k_no}' if k_no else ''} | <b>Dava Türü:</b> {tur}
                        </div>
                        <div style="font-size:12px; color:{text_muted}; margin-top:4px;">
                            Dava Değeri: <b>{format_money(deg)}</b> | Açılış Tarihi: {dt}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

                c_b1, c_b2 = st.columns([2, 1])
                with c_b1:
                    if dur_t and str(dur_t) != "None":
                        st.markdown(f"📅 **Sonraki Duruşma:** `{dur_t} Saat: {dur_s or '09:30'}` *(Not: {dur_acik or 'Planlandı'})*")
                    if a_vek and float(a_vek) > 0:
                        st.markdown(f"<span style='color:#EF4444; font-weight:700;'>⚠️ Karşı Tarafa Ödenecek İlam Vekalet Borcu Riski: {format_money(a_vek)}</span>", unsafe_allow_html=True)
                with c_b2:
                    if dur_t and str(dur_t) != "None":
                        ics_data = dava_engine.generate_ics_content(
                            f"Duruşma: {mahk} {d_no}",
                            dur_t, dur_s or "09:30", mahk, f"İcra Dosyası: #{secili_id}"
                        )
                        st.download_button(
                            label="📲 Takvime Ekle (.ics)",
                            data=ics_data.encode("utf-8"),
                            file_name=f"durusma_{r_id}.ics",
                            mime="text/calendar",
                            key=f"btn_tab_ics_{r_id}",
                            use_container_width=True
                        )
