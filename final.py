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
# 1. AYARLAR VE TASARIM
# =========================================================
st.set_page_config(
    page_title="Uzman Otomotiv",
    page_icon="🚘",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS SİHİRLERİ (DÜZELTİLMİŞ VERSİYON) ---
st.markdown("""
<style>
    /* 1. MENÜ AÇMA/KAPAMA DÜĞMESİNİ KURTARMA */
    /* Header'ı gizlemiyoruz, sadece şeffaf yapıyoruz ki düğme görünsün */
    [data-testid="stHeader"] {
        background-color: rgba(0,0,0,0);
    }
    
    /* Menü kapandığında çıkan OK (>) işaretinin rengi */
    [data-testid="stSidebarCollapsedControl"] {
        color: #004D40 !important;
        background-color: white;
        border-radius: 0 10px 10px 0;
        border: 1px solid #004D40;
    }

    /* 2. SOL MENÜ TASARIMI */
    [data-testid="stSidebar"] {
        background-color: #004D40;
        background-image: linear-gradient(180deg, #004D40 0%, #00251a 100%);
    }
    [data-testid="stSidebar"] * {
        color: white !important;
    }

    /* 3. TABLO BAŞLIKLARI */
    [data-testid="stDataFrame"] th {
        background-color: #004D40 !important;
        color: white !important;
    }

    /* 4. KARTLAR VE METRİKLER */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF !important;
        border: 1px solid #E0E0E0 !important;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        border-left: 5px solid #E67E22 !important;
    }
    div[data-testid="stMetricLabel"] p { color: #555 !important; font-weight: bold; }
    div[data-testid="stMetricValue"] div { color: #000 !important; }

    /* 5. BUTONLAR */
    .stButton > button {
        background-color: #E67E22 !important;
        color: white !important;
        border: none;
        border-radius: 8px;
        font-weight: bold;
    }
    .stButton > button:hover {
        background-color: #D35400 !important;
    }

    /* 6. FİŞ KUTUSU */
    .fiş-kutusu {
        background-color: #E3F2FD; 
        padding: 20px; 
        border-radius: 12px; 
        border: 2px solid #1565C0; 
        text-align: center; 
        margin: 20px 0;
    }
    .fiş-baslik { color: #1565C0; font-weight: bold; font-size: 1.2em; }
    .fiş-tutar { color: #0D47A1; font-weight: 800; font-size: 2.5em; margin: 10px 0; }
    .fiş-detay { color: #455A64; font-size: 1em; font-weight: bold;}

    /* Genel Yazı Rengi */
    h1, h2, h3, p, span, div { color: #333333; }
    
    /* Sadece Footer ve Hamburger Menüyü Gizle (Oku değil) */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
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
    if os.path.exists("Uzman.png"):
        st.sidebar.image("Uzman.png", use_container_width=True)
    elif os.path.exists("uzman.png"):
        st.sidebar.image("uzman.png", use_container_width=True)
    else:
        st.sidebar.markdown("<h2 style='color:white; text-align:center;'>🚘 UZMAN OTO</h2>", unsafe_allow_html=True)

def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False

    if not st.session_state["logged_in"]:
        col1, col2, col3 = st.columns([1,2,1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            if os.path.exists("Uzman.png"):
                st.image("Uzman.png", width=200)
            else:
                st.markdown("<h1 style='text-align: center; color:#004D40;'>🚘</h1>", unsafe_allow_html=True)
                
            st.markdown("<h2 style='text-align: center; color: #333;'>YÖNETİM PANELİ</h2>", unsafe_allow_html=True)
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

# =========================================================
# 4. GİRİŞ KONTROLÜ VE MENÜ
# =========================================================
if check_password():
    show_logo()
    st.sidebar.title(" YEDEK PARÇA ") 
    st.sidebar.caption("Yönetim Paneli v2.2")
    
    if st.sidebar.button("🚪 ÇIKIŞ YAP"):
        st.session_state["logged_in"] = False
        st.rerun()

    menu = st.sidebar.radio("MENÜ", ["📊 Dashboard", "📦 Stok Yönetimi", "📝 Hareket Girişi", "📈 Raporlar & Analiz", "⚙️ Ayarlar"])

    conn = get_connection()
    df_stok = pd.read_sql("SELECT * FROM stoklar", conn)
    df_har = pd.read_sql("SELECT * FROM hareketler", conn)
    df_tanim = pd.read_sql("SELECT * FROM tanimlar", conn)
    conn.close()

    # --- 1. DASHBOARD ---
    if menu == "📊 Dashboard":
        st.markdown("## 🚀 Ana Kontrol Paneli")
        st.markdown("---")
        
        if not df_stok.empty:
            stok_maliyet_net = (df_stok['MevcutStok'] * df_stok['PacalMaliyet']).sum()
            if 'SatisFiyatiNet' in df_stok.columns:
                satis_degeri_net = (df_stok['MevcutStok'] * df_stok['SatisFiyatiNet']).sum()
            else:
                satis_degeri_net = (df_stok['MevcutStok'] * df_stok['SatisFiyati']).sum() / 1.20 
            
            tahmini_kar = satis_degeri_net - stok_maliyet_net
            kritik = len(df_stok[df_stok['MevcutStok'] <= df_stok['KritikLimit']])
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("💰 Stok Maliyeti (NET)", f"{stok_maliyet_net:,.0f} TL", "Paçal Maliyet")
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
                    fig.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="black")
                    st.plotly_chart(fig, use_container_width=True)
                else: st.info("Veri yok.")
            
            with g2:
                st.subheader("📍 Depo Koridor Yoğunluğu")
                if 'RafYeri' in df_stok.columns:
                    df_stok['Koridor'] = df_stok['RafYeri'].str.split('-').str[0]
                    raf = df_stok[df_stok['Koridor'].str.isnumeric()].groupby('Koridor').size().reset_index(name='Adet')
                    fig2 = px.pie(raf, values='Adet', names='Koridor', hole=0.4)
                    fig2.update_layout(paper_bgcolor="rgba(0,0,0,0)", font_color="black")
                    st.plotly_chart(fig2, use_container_width=True)
                else: st.info("Raf verisi yok.")

            st.markdown("---")
            st.subheader("📊 Marka/Model Dağılımı")
            if 'ModelUyumluluk' in df_stok.columns:
                mod = df_stok['ModelUyumluluk'].value_counts().head(15).reset_index()
                mod.columns = ['Model','Adet']
                fig3 = px.bar(mod, x='Model', y='Adet', color='Adet', color_continuous_scale='Greens')
                fig3.update_layout(plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)", font_color="black")
                st.plotly_chart(fig3, use_container_width=True)
                
        else: st.warning("Veritabanı boş! Lütfen 'Ayarlar' menüsünden Excel dosyanızı yükleyiniz.")

    # --- 2. STOK YÖNETİMİ ---
    elif menu == "📦 Stok Yönetimi":
        st.markdown("## 📦 Stok Kartları")
        
        tab_list, tab_ekle = st.tabs(["📋 Stok Listesi", "➕ Tekil Ürün Ekle/Düzenle"])
        
        with tab_list:
            with st.expander("🔍 Arama ve Filtreleme", expanded=True):
                c1, c2 = st.columns([3,1])
                search = c1.text_input("Hızlı Ara", placeholder="Barkod, İsim, Raf...")
                seg = c2.multiselect("Segment", df_stok['Segment'].unique())
            
            view = df_stok.copy()
            if search: view = view[view.astype(str).apply(lambda x: x.str.contains(search, case=False)).any(axis=1)]
            if seg: view = view[view['Segment'].isin(seg)]
            
            view['Durum'] = view.apply(lambda x: "⚠️ KRİTİK" if x['MevcutStok'] <= x['KritikLimit'] else "✅ OK", axis=1)
            
            st.dataframe(view[['StokKodu','UrunAdi','RafYeri','MevcutStok','Durum','SatisFiyatiNet','SatisFiyati']], 
                        use_container_width=True, height=600,
                        column_config={
                            "SatisFiyatiNet": st.column_config.NumberColumn("Satış (Net)", format="%.2f TL"),
                            "SatisFiyati": st.column_config.NumberColumn("Satış (Brüt)", format="%.2f TL"),
                            "MevcutStok": st.column_config.ProgressColumn("Mevcut", min_value=0, max_value=100, format="%.f"),
                            "Durum": st.column_config.TextColumn("Durum", width="small")
                        })

        with tab_ekle:
            st.info("Buradan tek bir ürünü sisteme ekleyebilir veya var olanı güncelleyebilirsiniz.")
            with st.form("manual_stok"):
                c1, c2 = st.columns(2)
                kod = c1.text_input("Stok Kodu (Barkod)", placeholder="Örn: 123456")
                ad = c2.text_input("Ürün Adı")
                
                c3, c4, c5 = st.columns(3)
                raf = c3.text_input("Raf Yeri", placeholder="1-1-1-1")
                fiyat = c4.number_input("Satış Fiyatı (KDV Dahil)", min_value=0.0)
                stok = c5.number_input("Stok Adedi", min_value=0)
                
                submit = st.form_submit_button("💾 KAYDET / GÜNCELLE")
                if submit and kod and ad:
                    with get_connection() as conn:
                        try:
                            net_fiyat = fiyat / 1.20
                            conn.execute("""
                                INSERT INTO stoklar (StokKodu, UrunAdi, RafYeri, SatisFiyati, SatisFiyatiNet, MevcutStok, PacalMaliyet, KritikLimit, SonGuncelleme)
                                VALUES (?, ?, ?, ?, ?, ?, 0, 5, ?)
                                ON CONFLICT(StokKodu) DO UPDATE SET
                                UrunAdi=excluded.UrunAdi, RafYeri=excluded.RafYeri, SatisFiyati=excluded.SatisFiyati, 
                                SatisFiyatiNet=excluded.SatisFiyatiNet, MevcutStok=excluded.MevcutStok, SonGuncelleme=excluded.SonGuncelleme
                            """, (kod, ad, raf, fiyat, net_fiyat, stok, datetime.now()))
                            conn.commit()
                            st.success(f"{ad} başarıyla kaydedildi!")
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"Hata: {e}")

    # --- 3. HAREKET GİRİŞİ ---
    elif menu == "📝 Hareket Girişi":
        st.markdown("## ⚡ Satış Ekranı")
        c_l, c_r = st.columns([1, 2])
        with c_l:
            st.info("İşlem Bilgileri")
            islem = st.selectbox("Tip", ["Stok Çıkış (Satış)", "Stok Giriş (İade)"])
            p_list = df_tanim['Personel'].dropna().unique().tolist()
            personel = st.selectbox("Personel", p_list if p_list else ["Tanımsız"])
            cari = st.selectbox("Cari", df_tanim['Cari'].dropna().unique().tolist() or ["Genel"])
            evrak = st.text_input("Evrak No")
        
        with c_r:
            st.warning("Ürün & Hesap")
            urun = st.selectbox("Ürün Seç", df_stok['UrunAdi'].unique())
            if urun:
                rec = df_stok[df_stok['UrunAdi']==urun].iloc[0]
                st.caption(f"Raf: {rec['RafYeri']} | Stok: {rec['MevcutStok']} | Liste Fiyatı: {rec['SatisFiyati']} TL")
                st.divider()
                
                k1, k2, k3 = st.columns(3)
                miktar = k1.number_input("Adet", 1, 1000, 1)
                fiyat = k2.number_input("Birim Fiyat", value=float(rec['SatisFiyati']))
                kdv_tip = k3.radio("KDV", ["Dahil", "Hariç"], horizontal=True)
                kdv_oran = st.selectbox("Oran", [0,1,8,10,18,20], index=5)
                
                ham = miktar * fiyat
                if kdv_tip == "Dahil":
                    toplam = ham
                    matrah = toplam / (1 + kdv_oran/100)
                    kdv = toplam - matrah
                else:
                    matrah = ham
                    kdv = matrah * (kdv_oran/100)
                    toplam = matrah + kdv
                
                st.markdown(f"""<div class="fiş-kutusu"><div class="fiş-baslik">TOPLAM TUTAR</div><div class="fiş-tutar">{toplam:,.2f} TL</div><div class="fiş-detay">Net: {matrah:,.2f} TL | KDV: {kdv:,.2f} TL</div></div>""", unsafe_allow_html=True)
                
                if st.button("✅ KAYDET"):
                    with get_connection() as conn:
                        conn.execute("INSERT INTO hareketler (Tarih, EvrakNo, IslemTipi, UrunAdi, Cari, Personel, Miktar, BirimFiyat, KDVOrani, KDVTutari, GenelToplam, IslemZamani) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                                     (datetime.now(), evrak, islem, urun, cari, personel, miktar, fiyat, kdv_oran, kdv, toplam, datetime.now()))
                        mevcut = int(rec['MevcutStok'])
                        yeni = mevcut - miktar if "Çıkış" in islem else mevcut + miktar
                        conn.execute("UPDATE stoklar SET MevcutStok=? WHERE StokKodu=?", (yeni, rec['StokKodu']))
                        conn.commit()
                    st.success("İşlem Tamam!"); time.sleep(1); st.rerun()

    # --- 4. RAPORLAR ---
    elif menu == "📈 Raporlar & Analiz":
        st.markdown("## 📈 Rapor Merkezi")
        t1, t2, t3, t4, t5 = st.tabs(["📦 Stok Envanter Raporu", "📊 ABC Analizi", "💰 Kârlılık", "🕸️ Ölü Stoklar", "Hareket Listeleme"])
        
        with t1:
            st.subheader("📋 Detaylı Stok Envanter Dökümü")
            st.write("Depodaki tüm ürünlerin detaylı listesini buradan alabilirsiniz.")
            st.dataframe(df_stok, use_container_width=True)
            indirme_butonlari(df_stok, "stok_envanteri")

        with t2:
            st.subheader("🅰️🅱️©️ Pareto (ABC) Analizi")
            if not df_har.empty:
                abc = df_har[df_har['IslemTipi'].str.contains('Çıkış')].groupby('UrunAdi')['GenelToplam'].sum().reset_index().sort_values(by='GenelToplam', ascending=False)
                abc['Kumulatif'] = abc['GenelToplam'].cumsum()
                abc['Yuzde'] = (abc['Kumulatif'] / abc['GenelToplam'].sum()) * 100
                abc['Sinif'] = abc['Yuzde'].apply(lambda x: 'A' if x<=80 else ('B' if x<=95 else 'C'))
                st.dataframe(abc, use_container_width=True)
                indirme_butonlari(abc, "abc_analizi")
            else: st.info("Satış verisi yok.")
            
        with t3:
            st.subheader("💸 Ürün Bazlı Kârlılık")
            if not df_har.empty:
                kar = df_har[df_har['IslemTipi'].str.contains('Çıkış')].groupby('UrunAdi').agg({'Miktar':'sum', 'GenelToplam':'sum'}).reset_index()
                kar = kar.merge(df_stok[['UrunAdi','PacalMaliyet']], on='UrunAdi', how='left')
                kar['NetKar'] = kar['GenelToplam'] - (kar['Miktar']*kar['PacalMaliyet'])
                st.dataframe(kar, use_container_width=True)
                indirme_butonlari(kar, "karlilik_raporu")
        
        with t4:
            st.subheader("🕸️ Hareket Görmeyen Ürünler")
            olu = df_stok[~df_stok['UrunAdi'].isin(df_har[df_har['IslemTipi'].str.contains('Çıkış')]['UrunAdi'])]
            st.dataframe(olu, use_container_width=True)
            indirme_butonlari(olu, "olu_stok")
            
        with t5:
            st.subheader("📋 Hareketler Listesi")
            df_log = df_har.sort_values('id', ascending=False)
            st.dataframe(df_log, use_container_width=True)
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
        t1, t2, t3, t4 = st.tabs(["📥 Excel Stok Yükle", "📝 Sistem Tanımları", "🔐 Şifre Değiştir", "💾 Veritabanı Yedekle"])
        
        with t1:
            st.info("Tedarikçiden gelen 'stok1.xlsx' dosyasını buradan yükleyin.")
            up = st.file_uploader("Dosya Seç", type=['xlsx','csv'])
            if up and st.button("🚀 Dosyayı Sisteme İşle", type="primary"):
                ok, msg = process_excel_import(up)
                if ok: st.success(msg); time.sleep(2); st.rerun()
                else: st.error(msg)
                
        with t2:
            st.warning("Listeleri düzenledikten sonra en alttaki 'KAYDET' butonuna basmayı unutmayın.")
            c1, c2, c3 = st.columns(3)
            e_pers = c1.data_editor(df_tanim[['Personel']].dropna(), num_rows="dynamic", key='e1', use_container_width=True)
            e_cari = c2.data_editor(df_tanim[['Cari']].dropna(), num_rows="dynamic", key='e2', use_container_width=True)
            e_kat = c3.data_editor(df_tanim[['Kategori']].dropna(), num_rows="dynamic", key='e3', use_container_width=True)
            
            if st.button("💾 TÜM TANIMLARI KAYDET", type="primary"):
                l1, l2, l3 = e_pers['Personel'].tolist(), e_cari['Cari'].tolist(), e_kat['Kategori'].tolist()
                mx = max(len(l1), len(l2), len(l3))
                data = {
                    'Personel': l1 + [None]*(mx-len(l1)),
                    'Cari': l2 + [None]*(mx-len(l2)),
                    'Kategori': l3 + [None]*(mx-len(l3)),
                    'Birim': [None]*mx, 'KDV': [None]*mx
                }
                with get_connection() as conn:
                    pd.DataFrame(data).to_sql('tanimlar', conn, if_exists='replace', index=False)
                st.success("✅ Tanımlar başarıyla güncellendi!"); time.sleep(1); st.rerun()

        with t3:
            st.subheader("🔐 Admin Şifresi Değiştir")
            with st.form("pass_change"):
                old_pass = st.text_input("Eski Şifre", type="password")
                new_pass = st.text_input("Yeni Şifre", type="password")
                confirm_pass = st.text_input("Yeni Şifre (Tekrar)", type="password")
                btn_pass = st.form_submit_button("Şifreyi Güncelle")
                
                if btn_pass:
                    with get_connection() as conn:
                        cur = conn.cursor()
                        cur.execute("SELECT * FROM admin WHERE kullanici='admin' AND sifre=?", (old_pass,))
                        if cur.fetchone():
                            if new_pass == confirm_pass and new_pass != "":
                                cur.execute("UPDATE admin SET sifre=? WHERE kullanici='admin'", (new_pass,))
                                conn.commit()
                                st.success("Şifre başarıyla değiştirildi! Lütfen tekrar giriş yapın.")
                                time.sleep(2)
                                st.session_state["logged_in"] = False
                                st.rerun()
                            else: st.error("Yeni şifreler uyuşmuyor veya boş!")
                        else: st.error("Eski şifre yanlış!")

        with t4:
            st.subheader("Veri Güvenliği")
            st.write("Veritabanının bir kopyasını bilgisayarınıza indirin.")
            data = backup_db()
            if data:
                st.download_button(
                    label="💾 Yedeği İndir (Backup)",
                    data=data,
                    file_name=f"uzman_oto_yedek_{datetime.now().strftime('%Y%m%d')}.db",
                    mime="application/octet-stream"
                )
