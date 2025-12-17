import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime
import time
import io
import os
from fpdf import FPDF

# =========================================================
# 1. AYARLAR VE TASARIM (MODERN UI)
# =========================================================
st.set_page_config(
    page_title="Uzman Otomotiv",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS SİHİRLERİ ---
# Not: Bu ayarlar kullanıcı Dark Mode kullansa bile uygulamayı
# Kurumsal (Beyaz/Yeşil) temada sabitler.
st.markdown("""
<style>
    /* 1. GENEL SAYFA YAPISI (Zorunlu Beyaz Zemin) */
    .stApp {
        background-color: #f8f9fa; /* Çok açık gri (göz yormaz) */
        color: #212529; /* Koyu antrasit yazı */
    }
    
    /* 2. SOL MENÜ (SIDEBAR) - UZMAN YEŞİLİ */
    [data-testid="stSidebar"] {
        background-color: #004D40;
        background-image: linear-gradient(180deg, #004D40 0%, #00251a 100%);
        border-right: 1px solid #00251a;
    }
    [data-testid="stSidebar"] * {
        color: #ffffff !important; /* Menüdeki her şey beyaz olsun */
    }
    
    /* MENÜ KAPATMA OKU (Düzeltildi) */
    [data-testid="stSidebarCollapsedControl"] {
        color: #004D40 !important;
        background-color: white;
        border-radius: 50%;
        border: 1px solid #004D40;
        top: 1rem;
        left: 1rem;
        z-index: 99999;
    }
    
    /* 3. KARTLAR VE METRİKLER (Gölgeli ve Modern) */
    div[data-testid="stMetric"], .stMetric {
        background-color: #ffffff !important;
        padding: 20px;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border: 1px solid #e9ecef;
        border-left: 6px solid #E67E22; /* Turuncu vurgu */
        transition: transform 0.2s;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
    }
    
    /* Metrik Yazı Renklerini Zorla (Dark Mode override) */
    div[data-testid="stMetricLabel"] p { color: #6c757d !important; font-size: 0.9rem !important; font-weight: 600 !important; }
    div[data-testid="stMetricValue"] div { color: #212529 !important; font-weight: 700 !important; }

    /* 4. TABLOLAR (Temiz Görünüm) */
    [data-testid="stDataFrame"] {
        border: 1px solid #dee2e6;
        border-radius: 10px;
        overflow: hidden;
        background-color: white;
    }
    
    /* 5. INPUT ALANLARI VE FORMLAR */
    .stTextInput input, .stNumberInput input, .stSelectbox div[data-baseweb="select"] {
        background-color: #ffffff !important;
        color: #212529 !important;
        border: 1px solid #ced4da;
        border-radius: 8px;
    }
    
    /* 6. BUTONLAR (Canlı Turuncu) */
    .stButton > button {
        background: linear-gradient(45deg, #E67E22, #D35400);
        color: white !important;
        border: none;
        font-weight: 600;
        padding: 0.5rem 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        transition: all 0.3s ease;
        width: 100%;
    }
    .stButton > button:hover {
        box-shadow: 0 4px 8px rgba(230, 126, 34, 0.4);
        transform: translateY(-1px);
    }
    
    /* 7. ÖZEL FİŞ KUTUSU */
    .fiş-kutusu {
        background-color: #e3f2fd;
        padding: 25px;
        border-radius: 15px;
        border: 2px dashed #1565C0;
        text-align: center;
        margin: 20px 0;
    }
    .fiş-baslik { color: #1565C0; font-weight: bold; letter-spacing: 1px; font-size: 1.1rem; }
    .fiş-tutar { color: #0d47a1; font-weight: 900; font-size: 2.8rem; margin: 10px 0; font-family: 'Arial', sans-serif; }
    .fiş-detay { color: #546e7a; font-size: 0.95rem; font-family: monospace; }

    /* Gereksiz header'ı gizle ama menü butonuna dokunma */
    header[data-testid="stHeader"] { background: transparent; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    
</style>
""", unsafe_allow_html=True)

# =========================================================
# 2. VERİTABANI BAĞLANTISI
# =========================================================
DB_FILE = 'Uzman_Dat.db'

def get_connection():
    return sqlite3.connect(DB_FILE, timeout=10)

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        
        cursor.execute('''CREATE TABLE IF NOT EXISTS stoklar (
            StokKodu TEXT PRIMARY KEY, UrunAdi TEXT, Barkod TEXT, Kategori TEXT, 
            ModelUyumluluk TEXT, RafYeri TEXT, Birim TEXT, PacalMaliyet REAL, 
            SonAlisFiyati REAL, SatisFiyati REAL, SatisFiyatiNet REAL, 
            KritikLimit INTEGER, MevcutStok INTEGER, Segment TEXT, SonGuncelleme TIMESTAMP)''')
            
        cursor.execute('''CREATE TABLE IF NOT EXISTS hareketler (
            id INTEGER PRIMARY KEY AUTOINCREMENT, Tarih TIMESTAMP, EvrakNo TEXT, 
            IslemTipi TEXT, UrunAdi TEXT, Cari TEXT, Personel TEXT, Miktar INTEGER, 
            BirimFiyat REAL, KDVOrani INTEGER, KDVTutari REAL, GenelToplam REAL, IslemZamani TIMESTAMP)''')
            
        cursor.execute('''CREATE TABLE IF NOT EXISTS tanimlar (
            Kategori TEXT, Birim TEXT, KDV INTEGER, Cari TEXT, Personel TEXT)''')
            
        cursor.execute('''CREATE TABLE IF NOT EXISTS admin (
            kullanici TEXT PRIMARY KEY, sifre TEXT)''')

        cursor.execute("SELECT Count(*) FROM tanimlar")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO tanimlar (Personel, Cari, Kategori) VALUES (?,?,?)", 
                           ("Genel Personel", "Peşin Müşteri", "Genel Parça"))
        
        cursor.execute("SELECT Count(*) FROM admin")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO admin (kullanici, sifre) VALUES (?,?)", ("admin", "1234"))
            
        conn.commit()

init_db()

# =========================================================
# 3. YARDIMCI FONKSİYONLAR
# =========================================================
def show_logo():
    """Logo varsa gösterir, yoksa online bir ikon gösterir."""
    # GitHub'da dosya adı 'Uzman.png' ise (büyük küçük harf duyarlı) çalışır.
    if os.path.exists("Uzman.png"):
        return st.image("Uzman.png", width=180)
    elif os.path.exists("uzman.png"):
        return st.image("uzman.png", width=180)
    else:
        # Logo yoksa şık bir Renault/Oto ikonu
        st.markdown("""
            <div style="text-align: center; margin-bottom: 20px;">
                <div style="font-size: 60px;">🚘</div>
                <h3 style="color: white; margin:0;">UZMAN<br>OTOMOTİV</h3>
            </div>
        """, unsafe_allow_html=True)

def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            # Login ekranı logosu
            if os.path.exists("Uzman.png"):
                st.image("Uzman.png", width=200)
            else:
                st.markdown("<h1 style='text-align: center;'>🚘</h1>", unsafe_allow_html=True)
                
            st.markdown("<h2 style='text-align: center; color: #333;'>YÖNETİM PANELİ GİRİŞ</h2>", unsafe_allow_html=True)
            
            with st.form("login_form"):
                user = st.text_input("Kullanıcı Adı")
                pw = st.text_input("Şifre", type="password")
                btn = st.form_submit_button("GÜVENLİ GİRİŞ")
                
                if btn:
                    with get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT * FROM admin WHERE kullanici=? AND sifre=?", (user, pw))
                        if cur.fetchone():
                            st.session_state["logged_in"] = True
                            st.success("Giriş Başarılı!")
                            time.sleep(0.5)
                            st.rerun()
                        else: st.error("Hatalı kullanıcı adı veya şifre!")
        return False
    return True

def backup_db():
    try:
        with open(DB_FILE, "rb") as f: return f.read()
    except: return None

def process_excel_import(uploaded_file):
    try:
        if uploaded_file.name.endswith('.csv'): df = pd.read_csv(uploaded_file)
        else: df = pd.read_excel(uploaded_file)
        
        cols = ['Stok', 'Paçal', 'Alış Fiyat', "Satış Kdv'li", "Satış Kdv'siz"]
        for c in cols:
            if c in df.columns and df[c].dtype == 'object':
                df[c] = pd.to_numeric(df[c].str.replace('.','').str.replace(',','.'), errors='coerce').fillna(0)
        
        if {'Y', 'E', 'R', 'İ'}.issubset(df.columns):
            df['RafYeri'] = df.apply(lambda x: f"{str(x['Y']).replace('.0','')}-{str(x['E']).replace('.0','')}-{str(x['R']).replace('.0','')}-{str(x['İ']).replace('.0','')}", axis=1)
        else: df['RafYeri'] = '-'

        conn = get_connection()
        cursor = conn.cursor()
        updated, inserted = 0, 0
        progress_bar = st.progress(0)
        total = len(df)
        
        for idx, row in df.iterrows():
            if idx % 50 == 0: progress_bar.progress(min(idx / total, 1.0))
            kod = str(row.get('Parça Kodu', '')).strip()
            if not kod: continue
            
            vals = {
                'ad': str(row.get('Parça Adı', '')).strip(), 'kat': str(row.get('Parça Aile', 'Genel')),
                'mod': str(row.get('Parça Tip Adı', '')), 'raf': str(row.get('RafYeri', '')),
                'pacal': float(row.get('Paçal', 0)), 'alis': float(row.get('Alış Fiyat', 0)),
                'satis': float(row.get("Satış Kdv'li", 0)), 
                'satis_net': float(row.get("Satış Kdv'siz", 0)),
                'stok': int(float(row.get('Stok', 0))),
                'seg': str(row.get('Segment', 'C')), 'kod': kod, 'zaman': datetime.now()
            }
            
            cursor.execute("SELECT StokKodu FROM stoklar WHERE StokKodu = ?", (kod,))
            if cursor.fetchone():
                cursor.execute('''UPDATE stoklar SET UrunAdi=:ad, Kategori=:kat, ModelUyumluluk=:mod, RafYeri=:raf, PacalMaliyet=:pacal, SonAlisFiyati=:alis, SatisFiyati=:satis, SatisFiyatiNet=:satis_net, MevcutStok=:stok, Segment=:seg, SonGuncelleme=:zaman WHERE StokKodu=:kod''', vals)
                updated += 1
            else:
                cursor.execute('''INSERT INTO stoklar VALUES (:kod, :ad, :kod, :kat, :mod, :raf, 'ADET', :pacal, :alis, :satis, :satis_net, 5, :stok, :seg, :zaman)''', vals)
                inserted += 1

        if 'Parça Aile' in df.columns:
            kats = df['Parça Aile'].dropna().unique()
            existing = [x[0] for x in cursor.execute("SELECT Kategori FROM tanimlar").fetchall()]
            for k in kats:
                if k not in existing: cursor.execute("INSERT INTO tanimlar (Kategori) VALUES (?)", (k,))
            
        conn.commit()
        conn.close()
        progress_bar.empty()
        return True, f"✅ İşlem Başarılı! {inserted} Yeni, {updated} Güncelleme."
    except Exception as e: return False, str(e)

def create_excel(df):
    output = io.BytesIO()
    # Excel oluştururken xlsxwriter motorunu kullanıyoruz
    with pd.ExcelWriter(output, engine='xlsxwriter') as w: df.to_excel(w, index=False)
    return output.getvalue()

def tr_fix(text):
    mapping = {"ı": "i", "ğ": "g", "ü": "u", "ş": "s", "ö": "o", "ç": "c", "İ": "I", "Ğ": "G", "Ü": "U", "Ş": "S", "Ö": "O", "Ç": "C"}
    text = str(text)
    for c, r in mapping.items(): text = text.replace(c, r)
    return text

def create_pdf(df):
    pdf = FPDF()
    pdf.add_page()
    if os.path.exists("Uzman.png"):
        pdf.image("Uzman.png", 10, 8, 30) 
        pdf.set_xy(45, 10)
    else: pdf.set_xy(10, 10)

    pdf.set_font("Arial", 'B', 14)
    pdf.cell(0, 10, tr_fix("UZMAN OTOMOTIV RAPOR"), ln=True)
    pdf.ln(10)
    pdf.set_font("Arial", size=8)
    cols = df.columns.tolist()[:6]
    for col in cols: pdf.cell(32, 8, tr_fix(col)[:15], 1)
    pdf.ln()
    for _, row in df.iterrows():
        for col in cols: pdf.cell(32, 8, tr_fix(str(row[col]))[:15], 1)
        pdf.ln()
    return pdf.output(dest='S').encode('latin-1', errors='replace')

def indirme_butonlari(df, isim):
    c1, c2, c3 = st.columns(3)
    c1.download_button("📥 Excel İndir", create_excel(df), f"{isim}.xlsx")
    c2.download_button("📄 CSV İndir", df.to_csv(index=False).encode('utf-8'), f"{isim}.csv")
    c3.download_button("📕 PDF İndir", create_pdf(df), f"{isim}.pdf")

# =========================================================
# 4. GİRİŞ KONTROLÜ VE MENÜ
# =========================================================
if check_password():
    # LOGO GÖSTERİMİ (Sidebar)
    with st.sidebar:
        show_logo()
        st.title("YEDEK PARÇA") 
        st.caption("Yönetim Paneli v2.0")
        st.markdown("---")

    menu = st.sidebar.radio("MENÜ", ["📊 Dashboard", "📦 Stok Yönetimi", "📝 Hareket Girişi", "📈 Raporlar & Analiz", "⚙️ Ayarlar"])
    
    if st.sidebar.button("🚪 GÜVENLİ ÇIKIŞ"):
        st.session_state["logged_in"] = False
        st.rerun()

    conn = get_connection()
    df_stok = pd.read_sql("SELECT * FROM stoklar", conn)
    df_har = pd.read_sql("SELECT * FROM hareketler", conn)
    df_tanim = pd.read_sql("SELECT * FROM tanimlar", conn)
    conn.close()

    # --- 1. DASHBOARD ---
    if menu == "📊 Dashboard":
        st.header("🚀 Ana Kontrol Paneli")
        st.markdown("---")
        
        if not df_stok.empty:
            stok_maliyet_net = (df_stok['MevcutStok'] * df_stok['PacalMaliyet']).sum()
            # Net satış fiyatı sütunu yoksa brütten hesapla
            if 'SatisFiyatiNet' in df_stok.columns:
                satis_degeri_net = (df_stok['MevcutStok'] * df_stok['SatisFiyatiNet']).sum()
            else:
                satis_degeri_net = (df_stok['MevcutStok'] * df_stok['SatisFiyati']).sum() / 1.20 
            
            tahmini_kar = satis_degeri_net - stok_maliyet_net
            kritik = len(df_stok[df_stok['MevcutStok'] <= df_stok['KritikLimit']])
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 Stok Maliyeti (NET)", f"{stok_maliyet_net:,.0f} TL", "Paçal Maliyet")
            c2.metric("💵 Satış Değeri (NET)", f"{satis_degeri_net:,.0f} TL", "KDV Hariç")
            c3.metric("📈 Tahmini Brüt Kâr", f"{tahmini_kar:,.0f} TL", "Potansiyel")
            c4.metric("⚠️ Kritik Stok", kritik, "Acil Sipariş", delta_color="inverse")
            
            st.markdown("<br>", unsafe_allow_html=True)
            
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("🔥 En Çok Satan 10 Ürün")
                if not df_har.empty:
                    top = df_har[df_har['IslemTipi'].str.contains('Çıkış')].groupby('UrunAdi')['Miktar'].sum().nlargest(10).reset_index()
                    st.plotly_chart(px.bar(top, x='UrunAdi', y='Miktar', color='Miktar', color_continuous_scale='Oranges'), use_container_width=True)
                else: st.info("Henüz satış verisi yok.")
            
            with g2:
                st.subheader("📍 Depo Doluluk Oranı")
                if 'RafYeri' in df_stok.columns:
                    df_stok['Koridor'] = df_stok['RafYeri'].astype(str).str.split('-').str[0]
                    raf = df_stok[df_stok['Koridor'].str.isnumeric()].groupby('Koridor').size().reset_index(name='Adet')
                    if not raf.empty:
                        st.plotly_chart(px.pie(raf, values='Adet', names='Koridor', hole=0.4), use_container_width=True)
                    else: st.info("Raf verisi düzenlenmemiş.")
                else: st.info("Raf sistemi aktif değil.")
                
        else: st.warning("Veritabanı boş! 'Ayarlar' menüsünden Excel dosyanızı yükleyiniz.")

    # --- 2. STOK YÖNETİMİ ---
    elif menu == "📦 Stok Yönetimi":
        st.header("📦 Stok Yönetimi")
        
        tab_list, tab_ekle = st.tabs(["📋 Stok Listesi", "➕ Ürün Ekle / Düzenle"])
        
        with tab_list:
            with st.expander("🔍 Detaylı Arama", expanded=True):
                c1, c2 = st.columns([3,1])
                search = c1.text_input("Arama Yap", placeholder="Parça adı, kod veya raf yeri yazın...")
                seg = c2.multiselect("Segment Filtresi", df_stok['Segment'].unique())
            
            view = df_stok.copy()
            if search:
                view = view[view.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            if seg:
                view = view[view['Segment'].isin(seg)]
            
            view['Durum'] = view.apply(lambda x: "🔴 KRİTİK" if x['MevcutStok'] <= x['KritikLimit'] else "🟢 YETERLİ", axis=1)
            
            st.dataframe(view[['StokKodu','UrunAdi','RafYeri','MevcutStok','Durum','SatisFiyati']], 
                        use_container_width=True, height=500,
                        column_config={
                            "SatisFiyati": st.column_config.NumberColumn("Fiyat", format="%.2f TL"),
                            "MevcutStok": st.column_config.ProgressColumn("Stok", min_value=0, max_value=100, format="%.f"),
                        })

        with tab_ekle:
            st.info("Var olan bir stok kodunu girerseniz ürün GÜNCELLENİR, yeni kod girerseniz EKLENİR.")
            with st.form("stok_form"):
                c1, c2 = st.columns(2)
                kod = c1.text_input("Stok Kodu / Barkod", placeholder="Örn: 8200...")
                ad = c2.text_input("Parça Adı")
                
                c3, c4, c5 = st.columns(3)
                raf = c3.text_input("Raf Yeri", placeholder="Koridor-Sıra...")
                fiyat = c4.number_input("Satış Fiyatı (KDV Dahil)", min_value=0.0)
                stok = c5.number_input("Stok Adedi", min_value=0)
                
                if st.form_submit_button("💾 KAYDET"):
                    if kod and ad:
                        with get_connection() as conn:
                            net_fiyat = fiyat / 1.20
                            try:
                                conn.execute("""
                                    INSERT INTO stoklar (StokKodu, UrunAdi, RafYeri, SatisFiyati, SatisFiyatiNet, MevcutStok, PacalMaliyet, KritikLimit, SonGuncelleme)
                                    VALUES (?, ?, ?, ?, ?, ?, 0, 5, ?)
                                    ON CONFLICT(StokKodu) DO UPDATE SET
                                    UrunAdi=excluded.UrunAdi, RafYeri=excluded.RafYeri, SatisFiyati=excluded.SatisFiyati, 
                                    SatisFiyatiNet=excluded.SatisFiyatiNet, MevcutStok=excluded.MevcutStok, SonGuncelleme=excluded.SonGuncelleme
                                """, (kod, ad, raf, fiyat, net_fiyat, stok, datetime.now()))
                                conn.commit()
                                st.success(f"✅ {ad} başarıyla kaydedildi.")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"Hata: {e}")
                    else: st.warning("Kod ve Ürün Adı zorunludur.")

    # --- 3. HAREKET GİRİŞİ ---
    elif menu == "📝 Hareket Girişi":
        st.header("⚡ Hızlı Satış / Giriş Ekranı")
        
        col_sol, col_sag = st.columns([1, 2])
        
        with col_sol:
            st.markdown("### 📄 İşlem Detayı")
            islem = st.selectbox("İşlem Tipi", ["Stok Çıkış (Satış)", "Stok Giriş (İade/Alım)"])
            evrak = st.text_input("Evrak / Fiş No")
            cari = st.selectbox("Cari Hesap", df_tanim['Cari'].dropna().unique().tolist() or ["Peşin"])
            personel = st.selectbox("Personel", df_tanim['Personel'].dropna().unique().tolist() or ["Genel"])
        
        with col_sag:
            st.markdown("### 🛒 Ürün ve Tutar")
            urun = st.selectbox("Ürün Arama", df_stok['UrunAdi'].unique())
            
            if urun:
                rec = df_stok[df_stok['UrunAdi']==urun].iloc[0]
                st.info(f"📍 Raf: **{rec['RafYeri']}** | 📦 Mevcut: **{rec['MevcutStok']}** | 🏷️ Liste Fiyatı: **{rec['SatisFiyati']} TL**")
                
                r1, r2, r3 = st.columns(3)
                miktar = r1.number_input("Adet", 1, 1000, 1)
                fiyat = r2.number_input("Birim Fiyat", value=float(rec['SatisFiyati']))
                kdv_orani = r3.selectbox("KDV", [0, 1, 10, 20], index=3)
                
                # Hesaplama
                tutar = miktar * fiyat
                kdv_tutari = tutar * (kdv_orani / 100) if islem == "Stok Çıkış (Satış)" else 0 # Basit hesap
                # Burada KDV dahil/hariç karmaşası olmasın diye basit mantık: Fiyat KDV dahil kabul edildi.
                genel_toplam = tutar 
                net_tutar = genel_toplam / (1 + kdv_orani/100)
                kdv_tutari = genel_toplam - net_tutar
                
                st.markdown(f"""
                <div class="fiş-kutusu">
                    <div class="fiş-baslik">TOPLAM TUTAR</div>
                    <div class="fiş-tutar">{genel_toplam:,.2f} TL</div>
                    <div class="fiş-detay">Net: {net_tutar:,.2f} TL | KDV: {kdv_tutari:,.2f} TL</div>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button("✅ İŞLEMİ ONAYLA", use_container_width=True):
                    with get_connection() as conn:
                        # Hareketi kaydet
                        conn.execute("INSERT INTO hareketler (Tarih, EvrakNo, IslemTipi, UrunAdi, Cari, Personel, Miktar, BirimFiyat, KDVOrani, KDVTutari, GenelToplam, IslemZamani) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                     (datetime.now(), evrak, islem, urun, cari, personel, miktar, fiyat, kdv_orani, kdv_tutari, genel_toplam, datetime.now()))
                        
                        # Stoğu düş/arttır
                        yeni_stok = int(rec['MevcutStok']) - miktar if "Çıkış" in islem else int(rec['MevcutStok']) + miktar
                        conn.execute("UPDATE stoklar SET MevcutStok=? WHERE StokKodu=?", (yeni_stok, rec['StokKodu']))
                        conn.commit()
                        
                    st.success("İşlem başarıyla kaydedildi!")
                    time.sleep(1)
                    st.rerun()

    # --- 4. RAPORLAR ---
    elif menu == "📈 Raporlar & Analiz":
        st.header("📈 Rapor Merkezi")
        t1, t2, t3, t4, t5 = st.tabs(["📦 Envanter", "📊 ABC Analizi", "💰 Kârlılık", "🕸️ Ölü Stok", "📝 Hareket Geçmişi"])
        
        with t1:
            st.dataframe(df_stok, use_container_width=True)
            indirme_butonlari(df_stok, "stok_envanter")

        with t2:
            st.subheader("Pareto (ABC) Analizi")
            if not df_har.empty:
                abc = df_har[df_har['IslemTipi'].str.contains('Çıkış')].groupby('UrunAdi')['GenelToplam'].sum().reset_index().sort_values(by='GenelToplam', ascending=False)
                abc['Kumulatif'] = abc['GenelToplam'].cumsum()
                abc['Yuzde'] = (abc['Kumulatif'] / abc['GenelToplam'].sum()) * 100
                abc['Sinif'] = abc['Yuzde'].apply(lambda x: 'A' if x<=80 else ('B' if x<=95 else 'C'))
                st.dataframe(abc, use_container_width=True)
                indirme_butonlari(abc, "abc_analizi")
            else: st.warning("Veri yok.")
            
        with t3:
            if not df_har.empty:
                kar = df_har[df_har['IslemTipi'].str.contains('Çıkış')].groupby('UrunAdi').agg({'Miktar':'sum', 'GenelToplam':'sum'}).reset_index()
                kar = kar.merge(df_stok[['UrunAdi','PacalMaliyet']], on='UrunAdi', how='left')
                kar['TahminiMaliyet'] = kar['Miktar'] * kar['PacalMaliyet']
                kar['BrutKar'] = kar['GenelToplam'] - kar['TahminiMaliyet']
                st.dataframe(kar, use_container_width=True)
                indirme_butonlari(kar, "karlilik_raporu")
            else: st.warning("Veri yok.")
            
        with t4:
            st.subheader("Hareketsiz Ürünler")
            if not df_har.empty:
                satilanlar = df_har['UrunAdi'].unique()
                olu = df_stok[~df_stok['UrunAdi'].isin(satilanlar)]
                st.dataframe(olu, use_container_width=True)
            else: st.info("Henüz hareket yok.")

        with t5:
            st.subheader("Son İşlemler")
            df_log = df_har.sort_values('id', ascending=False)
            st.dataframe(df_log, use_container_width=True)
            indirme_butonlari(df_log, "hareket_dokumu")
            
            st.markdown("---")
            with st.expander("🗑️ Hatalı Kayıt Silme"):
                sid = st.selectbox("Silinecek Kayıt ID", df_log['id'].tolist())
                if st.button("❌ Kaydı Sil ve Stoğu Geri Al"):
                    with get_connection() as conn:
                        r = df_har[df_har['id']==sid].iloc[0]
                        # Stoğu tersine çevir
                        curr = df_stok[df_stok['UrunAdi']==r['UrunAdi']]['MevcutStok'].iloc[0]
                        new_stk = curr + r['Miktar'] if "Çıkış" in r['IslemTipi'] else curr - r['Miktar']
                        conn.execute("UPDATE stoklar SET MevcutStok=? WHERE UrunAdi=?", (new_stk, r['UrunAdi']))
                        conn.execute("DELETE FROM hareketler WHERE id=?", (sid,))
                        conn.commit()
                    st.success("Kayıt silindi, stok düzeltildi.")
                    time.sleep(1)
                    st.rerun()

    # --- 5. AYARLAR ---
    elif menu == "⚙️ Ayarlar":
        st.header("⚙️ Sistem Ayarları")
        t1, t2, t3, t4 = st.tabs(["📥 Stok Yükle", "📝 Tanımlamalar", "🔐 Güvenlik", "💾 Yedekleme"])
        
        with t1:
            st.info("Excel formatı: Parça Kodu | Parça Adı | Stok | Fiyat sütunlarını içermelidir.")
            up = st.file_uploader("Excel Dosyası Seç", type=['xlsx','csv'])
            if up and st.button("Yüklemeyi Başlat"):
                ok, msg = process_excel_import(up)
                if ok: st.success(msg)
                else: st.error(msg)
        
        with t2:
            c1, c2 = st.columns(2)
            with c1:
                st.subheader("Personel Listesi")
                new_p = st.data_editor(df_tanim[['Personel']].dropna(), num_rows="dynamic", key="k1")
            with c2:
                st.subheader("Cari Hesaplar")
                new_c = st.data_editor(df_tanim[['Cari']].dropna(), num_rows="dynamic", key="k2")
            
            if st.button("Tanımları Kaydet"):
                # Basitçe tüm tanımları silip yeniden ekleme mantığı (pratik çözüm)
                l_p = new_p['Personel'].dropna().tolist()
                l_c = new_c['Cari'].dropna().tolist()
                max_len = max(len(l_p), len(l_c))
                # Listeleri eşitle
                l_p += [None] * (max_len - len(l_p))
                l_c += [None] * (max_len - len(l_c))
                
                df_new = pd.DataFrame({'Personel': l_p, 'Cari': l_c, 'Kategori': [None]*max_len, 'Birim': [None]*max_len, 'KDV': [None]*max_len})
                with get_connection() as conn:
                    df_new.to_sql('tanimlar', conn, if_exists='replace', index=False)
                st.success("Tanımlar güncellendi.")

        with t3:
            with st.form("pwd"):
                p1 = st.text_input("Eski Şifre", type="password")
                p2 = st.text_input("Yeni Şifre", type="password")
                if st.form_submit_button("Şifreyi Değiştir"):
                    with get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT * FROM admin WHERE kullanici='admin' AND sifre=?", (p1,))
                        if cur.fetchone():
                            cur.execute("UPDATE admin SET sifre=? WHERE kullanici='admin'", (p2,))
                            conn.commit()
                            st.success("Şifre değişti, lütfen tekrar giriş yapın.")
                            st.session_state["logged_in"] = False
                            time.sleep(2)
                            st.rerun()
                        else: st.error("Eski şifre hatalı.")

        with t4:
            st.write("Veritabanı yedeğini indirip bilgisayarınızda saklayabilirsiniz.")
            data = backup_db()
            if data:
                st.download_button("💾 Yedeği İndir", data, file_name=f"Yedek_{datetime.now().date()}.db")
