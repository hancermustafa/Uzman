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
# 0. ZORUNLU TEMA ENJEKSİYONU (v7.0 BAZ ALINDI)
# =========================================================
def force_light_mode():
    config_dir = ".streamlit"
    config_path = os.path.join(config_dir, "config.toml")
    
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
    
    # Secondary Background GRİ (#F0F2F6) yapıldı (Inputlar bozulmasın diye)
    config_content = """
[theme]
base="light"
primaryColor="#E67E22"
backgroundColor="#FFFFFF"
secondaryBackgroundColor="#F0F2F6"
textColor="#31333F"
font="sans serif"

[server]
headless = true
    """
    
    with open(config_path, "w", encoding="utf-8") as f:
        f.write(config_content.strip())

# Kod çalışmadan önce ayarları enjekte et
force_light_mode()

# =========================================================
# 1. SAYFA AYARLARI
# =========================================================
st.set_page_config(
    page_title="Uzman Otomotiv",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================================================
# 2. CSS SİHİRLERİ (v7.3 - TABLO GÖRÜNÜRLÜK FIX)
# =========================================================
st.markdown("""
<style>
    /* --- 1. KÖK AYARLAR --- */
    :root {
        --primary-color: #E67E22;
        --background-color: #FFFFFF;
        --secondary-background-color: #F0F2F6;
        --text-color: #000000;
        --font: "Source Sans Pro", sans-serif;
    }

    [data-testid="stAppViewContainer"], .stApp {
        background-color: #FFFFFF !important;
        color: #000000 !important;
    }
    
    /* --- 2. YAN MENÜ (KUTSAL VE DOKUNULMAZ ALAN) --- */
    [data-testid="stSidebar"] {
        background-color: #004D40 !important;
        background-image: linear-gradient(180deg, #004D40 0%, #00251a 100%) !important;
        border-right: 4px solid #E67E22 !important;
    }
    /* Yan menü yazıları BEYAZ */
    [data-testid="stSidebar"] *, [data-testid="stSidebar"] p, [data-testid="stSidebar"] label, [data-testid="stSidebar"] span {
        color: #FFFFFF !important;
    }
    
    /* --- 3. MENÜ OKLARI (<< >> ÇALIŞAN HALİ) --- */
    [data-testid="stSidebarCollapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        color: #31333F !important;
        background-color: #FFFFFF !important;
        border: 2px solid #E67E22 !important;
        border-radius: 5px !important;
        z-index: 100000 !important;
    }

    /* --- 4. TABLOLAR (RAPORLARDAKİ BOŞ GÖRÜNME SORUNU ÇÖZÜMÜ) --- */
    /* Tablo çerçevesi */
    .stDataFrame, [data-testid="stDataFrame"] {
        background-color: #FFFFFF !important;
        border: 1px solid #ddd !important;
    }
    
    /* Tablo BAŞLIKLARI (Header) - Yeşil Zemin, Beyaz Yazı */
    [data-testid="stDataFrame"] th {
        background-color: #004D40 !important;
        color: #FFFFFF !important;
    }
    
    /* Tablo HÜCRELERİ (Cells) - Beyaz Zemin, SİYAH Yazı */
    /* Burası çok önemli: Streamlit'in içindeki div, span, p ne varsa hepsini siyaha boyuyoruz */
    [data-testid="stDataFrame"] td, 
    [data-testid="stDataFrame"] td div, 
    [data-testid="stDataFrame"] td span, 
    [data-testid="stDataFrame"] td p {
        color: #000000 !important;
        background-color: #FFFFFF !important;
    }
    
    /* Alternatif Tablo Yapısı (Glide Data Grid) için ek önlem */
    div[data-testid="stDataFrame"] > div {
        color: #000000 !important;
    }

    /* --- 5. LİSTELER VE INPUTLAR --- */
    .stTextInput input, .stNumberInput input, .stSelectbox div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border-color: #ccc !important;
    }
    
    /* Açılır Liste İçi */
    div[data-baseweb="popover"] *, ul[data-testid="stSelectboxVirtualDropdown"] li {
        color: #000000 !important;
        background-color: #FFFFFF !important;
    }
    
    /* --- 6. BUTONLAR --- */
    .stButton > button {
        background-color: #E67E22 !important; 
        color: #FFFFFF !important;
        border: none; border-radius: 8px; font-weight: bold;
    }
    .stButton > button:hover { background-color: #D35400 !important; }
    
    /* Sayı artırma butonları (+ -) */
    [data-testid="stNumberInput"] button {
        color: #000000 !important;
        background: transparent !important;
    }

    /* --- 7. DİĞER GÖRSELLER --- */
    /* Fullscreen butonunu gizle */
    button[title="View fullscreen"] { display: none !important; }
    
    /* Logo */
    [data-testid="stSidebar"] > div:first-child img {
        background-color: #FFFFFF; padding: 10px; border-radius: 10px; margin-bottom: 20px;
    }
    
    /* Kartlar */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-left: 5px solid #E67E22 !important;
        color: #000000 !important;
    }
    div[data-testid="stMetricLabel"] p { color: #555 !important; }
    div[data-testid="stMetricValue"] div { color: #000 !important; }

    /* Genel Yazı */
    h1, h2, h3, h4, p, span, div, label { color: inherit; }
</style>
""", unsafe_allow_html=True)

# =========================================================
# 3. VERİTABANI BAĞLANTISI
# =========================================================
DB_FILE = 'Uzman_Dat.db'

def get_connection():
    return sqlite3.connect(DB_FILE, timeout=10, isolation_level=None)

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
            cursor.execute("INSERT INTO tanimlar (Personel, Cari, Kategori) VALUES (?,?,?)", ("Genel Personel", "Peşin Müşteri", "Genel Parça"))
        cursor.execute("SELECT Count(*) FROM admin")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT INTO admin (kullanici, sifre) VALUES (?,?)", ("admin", "1234"))
        conn.commit()

init_db()

def show_logo():
    if os.path.exists("Uzman.png"):
        st.sidebar.image("Uzman.png", width=250)
    elif os.path.exists("uzman.png"):
        st.sidebar.image("uzman.png", width=250)
    else:
        st.sidebar.markdown("<h2 style='color:white; text-align:center;'>🚘 UZMAN OTO</h2>", unsafe_allow_html=True)

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
    try:
        with pd.ExcelWriter(output, engine='xlsxwriter') as w: df.to_excel(w, index=False)
    except ModuleNotFoundError:
        with pd.ExcelWriter(output, engine='openpyxl') as w: df.to_excel(w, index=False)
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

def backup_db():
    try:
        with open(DB_FILE, "rb") as f: return f.read()
    except: return None

# =========================================================
# 4. GİRİŞ KONTROLÜ
# =========================================================
def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        st.markdown("""<style>[data-testid="stSidebar"] {display: none;}</style>""", unsafe_allow_html=True)
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if os.path.exists("Uzman.png"):
                st.image("Uzman.png", width=200)
            else:
                st.markdown("<h1 style='text-align: center; color:#004D40;'>🚘</h1>", unsafe_allow_html=True)
            st.markdown("<h2 style='text-align: center; color: #333 !important;'>YÖNETİM PANELİ</h2>", unsafe_allow_html=True)
            with st.form("login_form"):
                user = st.text_input("Kullanıcı Adı")
                pw = st.text_input("Şifre", type="password")
                if st.form_submit_button("GİRİŞ YAP"):
                    with get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT * FROM admin WHERE kullanici=? AND sifre=?", (user, pw))
                        if cur.fetchone():
                            st.session_state["logged_in"] = True
                            st.success("Giriş Başarılı!")
                            time.sleep(0.5)
                            st.rerun()
                        else: st.error("Hatalı Giriş!")
        return False
    return True

# =========================================================
# 5. UYGULAMA AKIŞI
# =========================================================
if check_password():
    show_logo()
    st.sidebar.title(" YEDEK PARÇA ") 
    st.sidebar.caption("Yönetim Paneli")
    
    menu = st.sidebar.radio("MENÜ", [
        "📊 Dashboard", 
        "📝 Stok Hareket Girişi", 
        "📦 Stok Kartları", 
        "📈 Raporlar & Analiz", 
        "⚙️ Ayarlar"
    ])

    st.sidebar.markdown("---")
    if st.sidebar.button("🚪 ÇIKIŞ YAP"):
        st.session_state["logged_in"] = False
        st.rerun()

    conn = get_connection()
    df_stok = pd.read_sql("SELECT * FROM stoklar", conn)
    for col in ['MevcutStok', 'PacalMaliyet', 'SatisFiyati', 'SatisFiyatiNet', 'KritikLimit', 'SonAlisFiyati']:
        if col in df_stok.columns:
            df_stok[col] = pd.to_numeric(df_stok[col], errors='coerce').fillna(0)
    
    df_har = pd.read_sql("SELECT * FROM hareketler", conn)
    df_tanim = pd.read_sql("SELECT * FROM tanimlar", conn)
    conn.close()

    # --- 1. DASHBOARD ---
    if menu == "📊 Dashboard":
        st.markdown("## 🚀 Ana Kontrol Paneli")
        st.markdown("---")
        
        if not df_stok.empty:
            maliyet_baz = df_stok['SonAlisFiyati'] if 'SonAlisFiyati' in df_stok.columns else df_stok['PacalMaliyet']
            stok_maliyet_net = (df_stok['MevcutStok'] * maliyet_baz).sum()
            satis_degeri_net = (df_stok['MevcutStok'] * (df_stok['SatisFiyatiNet'] if 'SatisFiyatiNet' in df_stok.columns else df_stok['SatisFiyati']/1.20)).sum()
            tahmini_kar = satis_degeri_net - stok_maliyet_net
            kritik = len(df_stok[df_stok['MevcutStok'] <= df_stok['KritikLimit']])
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 Stok Maliyeti (NET)", f"{stok_maliyet_net:,.0f} TL", "Son Alış Fiyatından")
            c2.metric("💵 Satış Değeri (NET)", f"{satis_degeri_net:,.0f} TL", "KDV Hariç Fiyat")
            c3.metric("📈 Tahmini Brüt Kâr", f"{tahmini_kar:,.0f} TL", "Potansiyel Kazanç")
            c4.metric("⚠️ Kritik Stok", kritik, "Acil", delta_color="inverse")
            
            st.markdown("---")
            g1, g2 = st.columns(2)
            with g1:
                st.subheader("🔥 En Çok Satan 10 Ürün")
                if not df_har.empty:
                    top = df_har[df_har['IslemTipi'].str.contains('Çıkış')].groupby('UrunAdi')['Miktar'].sum().nlargest(10).reset_index()
                    fig = px.bar(top, x='UrunAdi', y='Miktar', color='Miktar', color_continuous_scale='Oranges')
                    fig.update_layout(template="plotly_white", plot_bgcolor="#fff", paper_bgcolor="#fff", font_color="#000000")
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Veri yok.")
            
            with g2:
                st.subheader("📍 Depo Koridor Yoğunluğu")
                if 'RafYeri' in df_stok.columns:
                    df_stok['Koridor'] = df_stok['RafYeri'].str.split('-').str[0]
                    raf = df_stok[df_stok['Koridor'].str.isnumeric()].groupby('Koridor').size().reset_index(name='Adet')
                    fig2 = px.pie(raf, values='Adet', names='Koridor', hole=0.4)
                    fig2.update_layout(template="plotly_white", paper_bgcolor="#fff", font_color="#000000")
                    st.plotly_chart(fig2, use_container_width=True)
                else: st.info("Raf verisi yok.")

            st.markdown("---")
            st.subheader("📊 Marka/Model Dağılımı")
            if 'ModelUyumluluk' in df_stok.columns:
                mod = df_stok['ModelUyumluluk'].value_counts().head(15).reset_index()
                mod.columns = ['Model','Adet']
                fig3 = px.bar(mod, x='Model', y='Adet', color='Adet', color_continuous_scale='Greens')
                fig3.update_layout(template="plotly_white", plot_bgcolor="#fff", paper_bgcolor="#fff", font_color="#000000")
                st.plotly_chart(fig3, use_container_width=True)
        else: st.warning("Veritabanı boş! Lütfen 'Ayarlar' menüsünden Excel dosyanızı yükleyiniz.")

    # --- 2. STOK HAREKET GİRİŞİ ---
    elif menu == "📝 Stok Hareket Girişi":
        st.markdown("## ⚡ Stok Giriş Çıkış (Fatura Modu)")
        
        if 'sepet' not in st.session_state: st.session_state['sepet'] = []

        with st.container():
            c1, c2, c3, c4 = st.columns(4)
            islem = c1.selectbox("İşlem Tipi", ["Stok Çıkış (Satış)", "Stok Giriş (İade/Alım)"])
            evrak = c2.text_input("Evrak / Fatura No")
            p_list = df_tanim['Personel'].dropna().unique().tolist()
            personel = c3.selectbox("Personel", p_list if p_list else ["Tanımsız"])
            cari = c4.selectbox("Cari Hesap", df_tanim['Cari'].dropna().unique().tolist() or ["Genel"])

        st.markdown("---")
        col_sol, col_sag = st.columns([2, 1])
        
        with col_sol:
            urun = st.selectbox("Ürün Seçiniz", df_stok['UrunAdi'].unique())
            if urun:
                rec = df_stok[df_stok['UrunAdi']==urun].iloc[0]
                alis_goster = rec['SonAlisFiyati'] if rec['SonAlisFiyati'] > 0 else rec['PacalMaliyet']
                st.info(f"📍 Raf: **{rec['RafYeri']}** | 📦 Stok: **{rec['MevcutStok']}** | 📉 Son Alış: **{alis_goster:.2f} TL** | 📈 Satış: **{rec['SatisFiyati']:.2f} TL**")
                
                c_qty, c_price, c_kdv, c_btn = st.columns([1, 1, 1, 1])
                miktar = c_qty.number_input("Adet", 1, 1000, 1)
                fiyat = c_price.number_input("Birim Fiyat", value=float(rec['SatisFiyati']))
                
                kdv_tip = c_kdv.radio("KDV", ["Dahil", "Hariç"], horizontal=True)
                kdv_oran = st.selectbox("KDV Oranı", [0,1,8,10,18,20], index=5)
                
                if c_btn.button("➕ Listeye Ekle", use_container_width=True):
                    ham = miktar * fiyat
                    if kdv_tip == "Hariç":
                        toplam = ham
                        matrah = toplam / (1 + kdv_oran/100)
                        kdv_tutari = toplam - matrah
                    else: 
                        matrah = ham
                        kdv_tutari = matrah * (kdv_oran/100)
                        toplam = matrah + kdv_tutari
                    
                    item = {"UrunAdi": urun, "Miktar": miktar, "BirimFiyat": fiyat, "KDVOrani": kdv_oran, "KDVTutari": kdv_tutari, "Toplam": toplam, "StokKodu": rec['StokKodu'], "MevcutStok": rec['MevcutStok']}
                    st.session_state['sepet'].append(item)
                    st.success(f"{urun} eklendi.")

        with col_sag:
            st.markdown("### 🛒 İşlem Listesi")
            if st.session_state['sepet']:
                df_sepet = pd.DataFrame(st.session_state['sepet'])
                st.dataframe(df_sepet[['UrunAdi', 'Miktar', 'Toplam']], hide_index=True)
                genel_toplam = df_sepet['Toplam'].sum()
                st.markdown(f"<h2 style='text-align:right; color:#E67E22;'>TOPLAM: {genel_toplam:,.2f} TL</h2>", unsafe_allow_html=True)
                
                col_save, col_cancel = st.columns(2)
                
                if col_save.button("✅ FİŞİ TAMAMLA", type="primary", use_container_width=True):
                    if not evrak: st.error("Lütfen Evrak No giriniz!")
                    else:
                        with get_connection() as conn:
                            for item in st.session_state['sepet']:
                                conn.execute("INSERT INTO hareketler (Tarih, EvrakNo, IslemTipi, UrunAdi, Cari, Personel, Miktar, BirimFiyat, KDVOrani, KDVTutari, GenelToplam, IslemZamani) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                             (datetime.now(), evrak, islem, item['UrunAdi'], cari, personel, item['Miktar'], item['BirimFiyat'], item['KDVOrani'], item['KDVTutari'], item['Toplam'], datetime.now()))
                                cur_stok = int(item['MevcutStok'])
                                yeni_stok = cur_stok - item['Miktar'] if "Çıkış" in islem else cur_stok + item['Miktar']
                                conn.execute("UPDATE stoklar SET MevcutStok=? WHERE StokKodu=?", (yeni_stok, item['StokKodu']))
                            conn.commit()
                        st.session_state['sepet'] = [] 
                        st.balloons()
                        st.success("Kaydedildi!")
                        time.sleep(1.5)
                        st.rerun() 
                
                if col_cancel.button("❌ VAZGEÇ / TEMİZLE", type="secondary", use_container_width=True):
                    st.session_state['sepet'] = []
                    st.warning("Liste temizlendi.")
                    time.sleep(0.5)
                    st.rerun()
                    
            else: st.info("Liste boş.")

    # --- 3. STOK KARTLARI ---
    elif menu == "📦 Stok Kartları":
        st.markdown("## 📦 Stok Kartları")
        tab_list, tab_ekle = st.tabs(["📋 Stok Listesi ve Raporlama", "➕ Tekil Ürün Ekle / Düzenle"])
        
        with tab_list:
            with st.expander("🔍 Detaylı Filtreleme Seçenekleri", expanded=True):
                col_search, col_seg = st.columns([2, 1])
                search = col_search.text_input("Genel Arama", placeholder="Barkod, İsim, Raf Yeri...")
                
                col_kat, col_mod = st.columns(2)
                kat_list = df_stok['Kategori'].unique().tolist() if 'Kategori' in df_stok.columns else []
                sel_kat = col_kat.multiselect("Kategori Filtrele", kat_list)
                
                mod_list = df_stok['ModelUyumluluk'].unique().tolist() if 'ModelUyumluluk' in df_stok.columns else []
                sel_mod = col_mod.multiselect("Araç Modeli Filtrele", mod_list)
                
                seg_list = df_stok['Segment'].unique().tolist() if 'Segment' in df_stok.columns else []
                sel_seg = col_seg.multiselect("Segment", seg_list)
            
            view = df_stok.copy()
            if search: view = view[view.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            if sel_kat: view = view[view['Kategori'].isin(sel_kat)]
            if sel_mod: view = view[view['ModelUyumluluk'].isin(sel_mod)]
            if sel_seg: view = view[view['Segment'].isin(sel_seg)]
            
            view['Durum'] = view.apply(lambda x: "⚠️ KRİTİK" if x['MevcutStok'] <= x['KritikLimit'] else "✅ OK", axis=1)
            
            st.dataframe(view, height=500)
            st.markdown("### 📥 Listeyi Dışarı Aktar")
            indirme_butonlari(view, "filtrelenmis_stok_listesi")

        with tab_ekle:
            st.info("Ürün bilgilerini buradan detaylıca yönetebilirsiniz.")
            mod = st.radio("İşlem Modu Seçiniz:", ["🆕 Yeni Ürün Ekle", "✏️ Mevcut Ürünü Düzenle"], horizontal=True)
            st.divider()
            
            def_kod, def_ad, def_raf = "", "", ""
            def_stok, def_alis, def_satis = 0, 0.0, 0.0
            def_kat, def_mod, def_seg = "Genel", "Genel", "C"
            def_limit = 5
            
            if "Düzenle" in mod:
                secilen_urun_adi = st.selectbox("Düzenlenecek Ürünü Listeden Seçiniz:", df_stok['UrunAdi'].unique())
                if secilen_urun_adi:
                    rec = df_stok[df_stok['UrunAdi'] == secilen_urun_adi].iloc[0]
                    def_kod = rec['StokKodu']
                    def_ad = rec['UrunAdi']
                    def_raf = rec['RafYeri']
                    def_stok = int(rec['MevcutStok'])
                    def_alis = float(rec['SonAlisFiyati']) if rec['SonAlisFiyati'] > 0 else float(rec.get('PacalMaliyet', 0))
                    def_satis = float(rec['SatisFiyati'])
                    def_kat = rec['Kategori'] if rec['Kategori'] else "Genel"
                    def_mod = rec['ModelUyumluluk'] if rec['ModelUyumluluk'] else "Genel"
                    def_seg = rec['Segment'] if rec['Segment'] else "C"
                    def_limit = int(rec['KritikLimit']) if rec['KritikLimit'] else 5
            
            with st.form("urun_form"):
                c1, c2 = st.columns(2)
                kod = c1.text_input("Stok Kodu / Barkod", value=def_kod)
                ad = c2.text_input("Ürün Adı", value=def_ad)
                c3, c4, c5 = st.columns(3)
                kat = c3.text_input("Kategori", value=def_kat, help="Örn: Filtre, Fren, Motor")
                model = c4.text_input("Uyumlu Model", value=def_mod, help="Örn: Clio 4, Megane 2")
                raf = c5.text_input("Raf Yeri", value=def_raf)
                c6, c7, c8 = st.columns(3)
                alis = c6.number_input("Alış Fiyatı (Son Alış / Güncel)", min_value=0.0, value=def_alis, format="%.2f")
                satis = c7.number_input("Satış Fiyatı (KDV Dahil)", min_value=0.0, value=def_satis, format="%.2f")
                stok = c8.number_input("Mevcut Stok Adedi", min_value=0, value=def_stok)
                c9, c10 = st.columns(2)
                seg = c9.selectbox("Segment", ["A", "B", "C", "D", "E", "M"], index=["A", "B", "C", "D", "E", "M"].index(def_seg) if def_seg in ["A", "B", "C", "D", "E", "M"] else 2)
                limit = c10.number_input("Kritik Stok Limiti", min_value=1, value=def_limit)
                
                if st.form_submit_button("💾 KAYDET / GÜNCELLE"):
                    if kod and ad:
                        with get_connection() as conn:
                            net_satis = satis / 1.20 
                            try:
                                conn.execute("""
                                    INSERT INTO stoklar (StokKodu, UrunAdi, RafYeri, SatisFiyati, SatisFiyatiNet, MevcutStok, PacalMaliyet, SonAlisFiyati, KritikLimit, Kategori, ModelUyumluluk, Segment, SonGuncelleme)
                                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                    ON CONFLICT(StokKodu) DO UPDATE SET
                                    UrunAdi=excluded.UrunAdi, RafYeri=excluded.RafYeri, SatisFiyati=excluded.SatisFiyati, 
                                    SatisFiyatiNet=excluded.SatisFiyatiNet, MevcutStok=excluded.MevcutStok, PacalMaliyet=excluded.PacalMaliyet,
                                    SonAlisFiyati=excluded.SonAlisFiyati, KritikLimit=excluded.KritikLimit, Kategori=excluded.Kategori,
                                    ModelUyumluluk=excluded.ModelUyumluluk, Segment=excluded.Segment, SonGuncelleme=excluded.SonGuncelleme
                                """, (kod, ad, raf, satis, net_satis, stok, alis, alis, limit, kat, model, seg, datetime.now()))
                                conn.commit()
                                st.success(f"✅ {ad} başarıyla kaydedildi!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e: st.error(f"Hata oluştu: {e}")
                    else: st.warning("Lütfen Stok Kodu ve Ürün Adı alanlarını doldurunuz.")

    # --- 4. RAPORLAR ---
    elif menu == "📈 Raporlar & Analiz":
        st.markdown("## 📈 Rapor Merkezi")
        t1, t2, t3, t4, t5 = st.tabs(["📦 Stok Envanter Raporu", "📊 ABC Analizi", "💰 Kârlılık", "🕸️ Hareketsiz Stoklar", "📋 Hareket Dökümü"])
        with t1:
            st.subheader("📋 Detaylı Stok Envanter Dökümü")
            st.dataframe(df_stok)
            indirme_butonlari(df_stok, "stok_envanteri")
        with t2:
            st.subheader("🅰️🅱️©️ Pareto (ABC) Analizi")
            if not df_har.empty:
                abc = df_har[df_har['IslemTipi'].str.contains('Çıkış')].groupby('UrunAdi')['GenelToplam'].sum().reset_index().sort_values(by='GenelToplam', ascending=False)
                abc['Kumulatif'] = abc['GenelToplam'].cumsum()
                abc['Yuzde'] = (abc['Kumulatif'] / abc['GenelToplam'].sum()) * 100
                abc['Sinif'] = abc['Yuzde'].apply(lambda x: 'A' if x<=80 else ('B' if x<=95 else 'C'))
                st.dataframe(abc)
                indirme_butonlari(abc, "abc_analizi")
            else: st.info("Satış verisi yok.")
        with t3:
            st.subheader("💸 Ürün Bazlı Kârlılık (Son Alış Fiyatına Göre)")
            if not df_har.empty:
                kar = df_har[df_har['IslemTipi'].str.contains('Çıkış')].groupby('UrunAdi').agg({'Miktar':'sum', 'GenelToplam':'sum'}).reset_index()
                kar = kar.merge(df_stok[['UrunAdi','SonAlisFiyati']], on='UrunAdi', how='left')
                kar['NetKar'] = kar['GenelToplam'] - (kar['Miktar']*kar['SonAlisFiyati'])
                st.dataframe(kar)
                indirme_butonlari(kar, "karlilik_raporu")
        with t4:
            st.subheader("🕸️ Hareketsiz Stoklar")
            olu = df_stok[~df_stok['UrunAdi'].isin(df_har[df_har['IslemTipi'].str.contains('Çıkış')]['UrunAdi'])]
            st.dataframe(olu)
            indirme_butonlari(olu, "olu_stok")
        with t5:
            st.subheader("📋 Hareket Dökümü (Detaylı)")
            df_log = df_har.sort_values('id', ascending=False)
            st.dataframe(df_log)
            indirme_butonlari(df_log, "hareket_dokumu")
            st.markdown("---")
            st.error("🔴 **KAYIT SİLME ALANI**")
            c_d1, c_d2 = st.columns([3,1])
            sil_id = c_d1.selectbox("Silinecek İşlem ID Seçiniz", df_log['id'].tolist() if not df_log.empty else [])
            if c_d2.button("❌ SİL"):
                with get_connection() as conn:
                    r = df_har[df_har['id']==sil_id].iloc[0]
                    cur = df_stok[df_stok['UrunAdi']==r['UrunAdi']]['MevcutStok'].iloc[0]
                    rev = cur + r['Miktar'] if "Çıkış" in r['IslemTipi'] else cur - r['Miktar']
                    conn.execute("UPDATE stoklar SET MevcutStok=? WHERE UrunAdi=?", (rev, r['UrunAdi']))
                    conn.execute("DELETE FROM hareketler WHERE id=?", (sil_id,))
                    conn.commit()
                st.success("Silindi!"); time.sleep(1); st.rerun()

    # --- 5. AYARLAR ---
    elif menu == "⚙️ Ayarlar":
        st.markdown("## ⚙️ Sistem Ayarları")
        
        # UYARI
        st.warning("⚠️ **ÖNEMLİ BİLGİ:** Streamlit Cloud kullandığınız için bu sayfadan çıktığınızda veriler silinebilir. Verilerinizi korumak için sık sık **'Yedeği İndir'** butonunu kullanın ve tekrar girişte Excel yükleyin.")
        
        t1, t2, t3, t4 = st.tabs(["📥 Excel Stok Yükle", "📝 Sistem Tanımları", "🔐 Şifre Değiştir", "💾 Veritabanı Yedekle"])
        with t1:
            st.info("Tedarikçiden gelen 'stok1.xlsx' dosyasını buradan yükleyin.")
            up = st.file_uploader("Dosya Seç", type=['xlsx','csv'])
            if up and st.button("🚀 Dosyayı Sisteme İşle", type="primary"):
                ok, msg = process_excel_import(up)
                if ok: st.success(msg); time.sleep(2); st.rerun()
                else: st.error(msg)
        with t2:
            c1, c2, c3 = st.columns(3)
            e_pers = c1.data_editor(df_tanim[['Personel']].dropna(), num_rows="dynamic", key='e1', use_container_width=True)
            e_cari = c2.data_editor(df_tanim[['Cari']].dropna(), num_rows="dynamic", key='e2', use_container_width=True)
            e_kat = c3.data_editor(df_tanim[['Kategori']].dropna(), num_rows="dynamic", key='e3', use_container_width=True)
            if st.button("💾 TÜM TANIMLARI KAYDET", type="primary"):
                l1, l2, l3 = e_pers['Personel'].tolist(), e_cari['Cari'].tolist(), e_kat['Kategori'].tolist()
                mx = max(len(l1), len(l2), len(l3))
                data = {'Personel': l1+[None]*(mx-len(l1)), 'Cari': l2+[None]*(mx-len(l2)), 'Kategori': l3+[None]*(mx-len(l3)), 'Birim': [None]*mx, 'KDV': [None]*mx}
                with get_connection() as conn: pd.DataFrame(data).to_sql('tanimlar', conn, if_exists='replace', index=False)
                st.success("Güncellendi!"); time.sleep(1); st.rerun()
        with t3:
            st.subheader("🔐 Admin Şifresi Değiştir")
            with st.form("pass_change"):
                old_pass = st.text_input("Eski Şifre", type="password")
                new_pass = st.text_input("Yeni Şifre", type="password")
                confirm_pass = st.text_input("Yeni Şifre (Tekrar)", type="password")
                if st.form_submit_button("Şifreyi Güncelle"):
                    with get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT * FROM admin WHERE kullanici='admin' AND sifre=?", (old_pass,))
                        if cur.fetchone():
                            if new_pass == confirm_pass and new_pass != "":
                                cur.execute("UPDATE admin SET sifre=? WHERE kullanici='admin'", (new_pass,))
                                conn.commit(); st.success("Şifre değişti!"); time.sleep(2); st.session_state["logged_in"] = False; st.rerun()
                            else: st.error("Yeni şifreler uyuşmuyor!")
                        else: st.error("Eski şifre yanlış!")
        with t4:
            st.subheader("Veri Güvenliği")
            st.write("Veritabanının bir kopyasını bilgisayarınıza indirin.")
            data = backup_db()
            if data: st.download_button(label="💾 Yedeği İndir", data=data, file_name=f"uzman_oto_yedek_{datetime.now().strftime('%Y%m%d')}.db", mime="application/octet-stream")
