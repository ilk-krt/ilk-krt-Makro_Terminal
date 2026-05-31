import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import yfinance as yf
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import time

# ==========================================
# 0. RADİKAL DARK MODE CSS & KESKİN KONTRAST YAMASI
# ==========================================
st.set_page_config(layout="wide", page_title="V127.0 OTONOM MAKRO & EFOR TERMİNALİ", page_icon="🏛️")

st.markdown("""
    <style>
    /* Ana Ekran Arka Planı ve Yazı Rengi */
    .stApp { background-color: #050505 !important; color: #e0e0e0 !important; }
    p, h1, h2, h3, h4, h5, h6, span, label, div { color: #e0e0e0 !important; }
    
    /* DROPDOWN (AÇILIR MENÜ) ANA KUTUSU */
    div[data-baseweb="select"] > div { 
        background-color: #111111 !important; 
        color: #ffffff !important; 
        border: 1px solid #00ff88 !important; /* Menü çerçevesini ŞAHANE yeşili yapar */
    }
    
    /* DROPDOWN SEÇİM ESNASINDA SEÇİLEN METİN */
    div[data-baseweb="select"] span {
        color: #ffffff !important;
        font-weight: bold !important;
    }
    
    /* MENÜ TIKLANDIĞINDA AŞAĞI AÇILAN PANEL (POPOVER) */
    div[data-baseweb="popover"] {
        background-color: #111111 !important;
    }
    div[data-baseweb="popover"] > div { 
        background-color: #111111 !important; 
        border: 1px solid #444444 !important;
    }
    
    /* AÇILAN LİSTEDEKİ HER BİR SEÇENEK (LİSTE ELEMANLARI) */
    ul[role="listbox"] { 
        background-color: #111111 !important; 
        padding: 0px !important;
    }
    ul[role="listbox"] li { 
        color: #ffffff !important; 
        background-color: #111111 !important;
        padding: 10px !important;
        border-bottom: 1px solid #222222 !important;
    }
    
    /* FARE İLE ÜZERİNE GELİNEN SEÇENEK (HOVER) */
    ul[role="listbox"] li:hover { 
        background-color: #222222 !important; 
        color: #00ff88 !important; /* Yazıyı ŞAHANE yeşiline boyar */
        font-weight: bold !important;
    }
    
    /* Veri Tabloları Kontrast Ayarı */
    [data-testid="stTable"], [data-testid="stDataFrame"] { background-color: #111111 !important; }
    th { background-color: #222222 !important; color: #00ff88 !important; border-bottom: 1px solid #444 !important; }
    td { border-bottom: 1px solid #333 !important; color: #ffffff !important; }
    
    /* Form Buton Tasarımı */
    div.stButton > button { background-color: #1a1a1a !important; color: #ffffff !important; border: 1px solid #444 !important; border-radius: 8px !important; }
    div.stButton > button:hover { border-color: #00ff88 !important; color: #00ff88 !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 1. ETKEN ETF & HİSSE EVRENİ SÖZLÜĞÜ
# ==========================================
PORTFOLIO_UNIVERSE = {
    "XLU (Utilities & Nükleer)": ["NEE", "SO", "CEG", "VST", "AEP", "SRE"],
    "XLK & SOXX (Tech & Yarı İletken)": ["NVDA", "AAPL", "MSFT", "MU", "AVGO", "AMD", "TSM"],
    "ARKX & UFO (Uzay & Savunma)": ["RKLB", "LMT", "BA", "CPSH", "LHX", "NOC"],
    "WGMI & Kripto Altyapı": ["MARA", "IREN", "CORZ", "HUT", "CLSK"],
    "PAVE & XLI (Altyapı & Endüstri)": ["ETN", "CAT", "GE", "URI", "PWR"],
    "COPX & XME (Metal & Maden)": ["FCX", "SCCO", "NUE", "CLF", "X"],
    "XLE & XOP (Fosil Yakıtlar)": ["XOM", "CVX", "COP", "OXY", "SLB"],
    "ICLN & LIT (Temiz Enerji & Lityum)": ["ENPH", "FSLR", "ALB", "TSLA", "PLUG"],
    "XLC & Dijital İletişim": ["META", "GOOGL", "NFLX", "TTD", "DIS"]
}

POLICY_IMPACTS = {
    "America First Enerji (Fosil Teşviki)": {
        "XLE & XOP (Fosil Yakıtlar)": 9, "XLU (Utilities & Nükleer)": 4, 
        "ICLN & LIT (Temiz Enerji & Lityum)": -7, "PAVE & XLI (Altyapı & Endüstri)": 5
    },
    "Çin'e Ek Gümrük Vergisi (Tariff)": {
        "XLK & SOXX (Tech & Yarı İletken)": -6, "COPX & XME (Metal & Maden)": 7, 
        "XLC & Dijital İletişim": -2, "PAVE & XLI (Altyapı & Endüstri)": 6
    },
    "Savunma ve Uzay Bütçesi Artışı": {
        "ARKX & UFO (Uzay & Savunma)": 9, "XLK & SOXX (Tech & Yarı İletken)": 3, 
        "PAVE & XLI (Altyapı & Endüstri)": 5, "XLU (Utilities & Nükleer)": 2
    },
    "Yapay Zeka ve Kripto Deregülasyonu": {
        "WGMI & Kripto Altyapı": 9, "XLK & SOXX (Tech & Yarı İletken)": 8, 
        "XLU (Utilities & Nükleer)": 6, "XLC & Dijital İletişim": 5
    },
    "Yeşil Enerji Sübvansiyon İptalleri": {
        "ICLN & LIT (Temiz Enerji & Lityum)": -9, "XLE & XOP (Fosil Yakıtlar)": 6, 
        "XLU (Utilities & Nükleer)": 2, "ARKX & UFO (Uzay & Savunma)": 0
    }
}

# Tüm tekil hisselerin listesi
ALL_STOCKS_LIST = list(set([t for tkrs in PORTFOLIO_UNIVERSE.values() for t in tkrs]))

# ==========================================
# 2. OTONOM CANLI TRUMP & SPEKÜLASYON MOTORU (RSS)
# ==========================================
def fetch_live_trump_news():
    # Google News RSS: Küresel olarak Trump + borsa/hisse akışını tarar
    rss_url = "https://news.google.com/rss/search?q=Trump+stock+market+OR+company&hl=en-US&gl=US&ceid=US:en"
    news_alerts = []
    try:
        response = requests.get(rss_url, timeout=10)
        root = ET.fromstring(response.content)
        
        for item in root.findall('.//item')[:30]:  # Son 30 güncel haberi analiz et
            title = item.find('title').text
            link = item.find('link').text
            pub_date = item.find('pubDate').text
            
            # Başlıkta veya haber özetinde portföyümüzdeki bir hisse geçiyor mu kontrol et
            detected_tickers = []
            for ticker in ALL_STOCKS_LIST:
                if f" {ticker} " in f" {title} " or f"({ticker})" in title or ticker.lower() in title.lower():
                    detected_tickers.append(ticker)
            
            # Eğer Trump haberi bizim hisselerden birine dokunuyorsa radara al
            if detected_tickers:
                news_alerts.append({
                    "Tarih": pub_date[:16],
                    "Gelişme / Haber Başlığı": title,
                    "Hedef Ticker": ", ".join(detected_tickers),
                    "Kaynak Link": link
                })
        
        if not news_alerts:
            # Eğer spesifik ticker eşleşmediyse genel Trump makro başlıklarını düşür
            for item in root.findall('.//item')[:4]:
                news_alerts.append({
                    "Tarih": item.find('pubDate').text[:16],
                    "Gelişme / Haber Başlığı": item.find('title').text,
                    "Hedef Ticker": "📊 MAKRO / SEKTÖREL",
                    "Kaynak Link": item.find('link').text
                })
    except Exception as e:
        return [{"Tarih": "-", "Gelişme / Haber Başlığı": f"Haber motoru başlatılamadı: {e}", "Hedef Ticker": "HATA", "Kaynak Link": ""}]
    
    return news_alerts

# ==========================================
# 3. ŞAHANE V650 MATEMATİK MOTORU (YFINANCE)
# ==========================================
def get_rma(s, period): return s.ewm(alpha=1/period, min_periods=period, adjust=False).mean()
def get_wma(s, period):
    weights = np.arange(1, period + 1)
    return s.rolling(period).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)

def get_rsi(s, period):
    delta = s.diff()
    ma_up = get_rma(delta.clip(lower=0), period)
    ma_down = get_rma(-1 * delta.clip(upper=0), period)
    return 100 - (100 / (1 + (ma_up / ma_down.replace(0, 0.001))))

# TTL'i kaldırıp yerine dinamik cache_by_time ekliyoruz (Hafıza kilitlenmesini çözer)
@st.cache_data
def calculate_v127_signals(ticker_list, cache_bypass_time):
    if not ticker_list: return pd.DataFrame()
    end_date = datetime.now()
    try:
        raw_data = yf.download(ticker_list, start=end_date - timedelta(days=90), end=end_date, interval="1d", group_by='ticker', progress=False)
    except: return pd.DataFrame()

    results = []
    for t in ticker_list:
        try:
            df = raw_data[t].copy().dropna() if len(ticker_list) > 1 else raw_data.copy().dropna()
            if len(df) < 25: continue

            close, high, low, open_p, vol = df['Close'], df['High'], df['Low'], df['Open'], df['Volume']
            pct_1d = (close.iloc[-1] / close.iloc[-2] - 1) * 100

            # 📊 EFOR ÇİZGİSİ (EFFORT LINE) HESAPLAMA
            i_vwm_len = 14
            wma_cv = get_wma(close * vol, i_vwm_len)
            wma_v = get_wma(vol, i_vwm_len).clip(lower=0.001)
            raw_effort = wma_cv / wma_v
            eff_price = get_wma(raw_effort, 3)

            price_cross_eff_up = (close > eff_price) & (close.shift(1) <= eff_price.shift(1))
            price_cross_eff_dn = (close < eff_price) & (close.shift(1) >= eff_price.shift(1))

            eff_status = "➖ NÖTR"
            if close.iloc[-1] > eff_price.iloc[-1]: eff_status = "🟢 POZ"
            if close.iloc[-1] < eff_price.iloc[-1]: eff_status = "🔴 NEG"
            if price_cross_eff_up.iloc[-1]: eff_status = "🚀 UP KIRILIM"
            if price_cross_eff_dn.iloc[-1]: eff_status = "🩸 DOWN KIRILIM"

            # 🧭 MOMENTUM & BALİNA GÜCÜ (WHALE POWER)
            r14 = get_rsi(close, 14)
            c_range_q = (high - low).clip(lower=0.001)
            delta_q = ((close - low) - (high - close)) / c_range_q
            delta_vol_q = (delta_q * vol).rolling(20).mean() / vol.rolling(20).mean().clip(lower=0.001)
            rvol_q = (vol / vol.rolling(20).mean().clip(lower=1)).clip(upper=2.5)

            base_pwr_q = ((r14 - 50) + (delta_vol_q * 50)) * rvol_q * 1.5
            logic_pwr_q = np.log(1 + np.exp(base_pwr_q / 5)) * 5
            log_w_q = np.log10(1 + np.clip(logic_pwr_q, 0, None))
            pct_w_q = np.clip((log_w_q * 65)**0.8 * 1.8, 0, 100)
            w_pwr_q = get_wma(pd.Series(pct_w_q, index=close.index), 2)

            # 🛠️ FUSION SCORE
            v150_v_avg = vol.rolling(20).mean()
            _kin_b = ((vol > v150_v_avg * 1.2) & (close > open_p)).astype(int)
            _tre_b = (close > close.ewm(span=34).mean()).astype(int)
            _kur_b = ((r14 > 50) & (r14.shift(1) <= 50)).astype(int)
            total_score_b = _kin_b + _tre_b + _kur_b

            results.append({
                "Ticker": t,
                "Fiyat": f"${close.iloc[-1]:.2f}",
                "1 Gün (%)": round(pct_1d, 2),
                "Efor Çizgisi": eff_status,
                "Whale Power": round(w_pwr_q.iloc[-1], 1),
                "Fusion": int(total_score_b.iloc[-1])
            })
        except: continue
    return pd.DataFrame(results)

# ==========================================
# 4. RENKLENDİRME STYLER FONKSİYONLARI
# ==========================================
def style_efor(val):
    if '🚀' in str(val): return 'background-color: #00FF88; color: black; font-weight: bold;'
    if '🩸' in str(val): return 'background-color: #FF1744; color: white; font-weight: bold;'
    if '🟢' in str(val): return 'color: #00FF88; font-weight: bold;'
    if '🔴' in str(val): return 'color: #FF1744; font-weight: bold;'
    return 'color: #888;'

def style_puan(val):
    if val > 5: return 'background-color: #006400; color: white; font-weight: bold;'
    if val > 0: return 'background-color: #1b5e20; color: #e0e0e0;'
    if val < -5: return 'background-color: #8b0000; color: white; font-weight: bold;'
    if val < 0: return 'background-color: #4a148c; color: #e0e0e0;'
    return 'color: gray;'

# ==========================================
# 5. ARAYÜZ OLUŞTURMA
# ==========================================
st.title("🏛️ V127.0 OTONOM MAKRO & EFOR TERMİNALİ")
st.markdown("Kararnamelerin ve canlı spekülasyonların rasyonel etki puanlarını **ŞAHANE V650 Efor Kırılımı** ve **Whale Power Momentum** verileriyle çakıştırır.")
st.markdown("---")

# 📡 SEKMELİ KOKPİT YAPISI
tab_radar, tab_matrix = st.tabs(["📡 CANLI TRUMP SPEKÜLASYON RADARI", "📊 POLİTİKA-HİSSE MATRİSİ & HEATMAP"])

# --- TAB 1: CANLI TRUMP SPEKÜLASYON RADARI ---
with tab_radar:
    st.subheader("🔊 Canlı Medya & Sosyal Medya Akış Filtresi")
    st.markdown("*Dünya basınında Trump'ın telaffuz ettiği veya doğrudan etkilediği şirket kodları anlık ayıklanır.*")
    
    col_btn, col_time = st.columns([1, 4])
    # Güncelleme için manuel bypass tetiği
    current_timestamp = str(time.time()) if col_btn.button("🔄 Radarı Anlık Güncelle", use_container_width=True) else str(time.strftime("%Y-%m-%d_%H"))
    
    with st.spinner("Beyaz Saray konuşmaları ve global borsa akışı taranıyor..."):
        live_news = fetch_live_trump_news()
        df_news = pd.DataFrame(live_news)
        
        if not df_news.empty:
            st.dataframe(
                df_news,
                use_container_width=True,
                column_config={"Kaynak Link": st.column_config.LinkColumn("Haber Detayı (Link)")},
                hide_index=True
            )
        else:
            st.info("Şu anda radar eşleşmesi olan acil bir hisse spekülasyonu bulunmuyor.")

# --- TAB 2: POLİTİKA-HİSSE MATRİSİ & HEATMAP ---
with tab_matrix:
    col_control, col_space = st.columns([1, 2])
    with col_control:
        selected_policy = st.selectbox("Açıklanan Kararname / Haber Tipi:", list(POLICY_IMPACTS.keys()))
        multiplier = st.slider("Etki Şiddeti Çarpanı", min_value=0.5, max_value=2.0, value=1.0, step=0.1)

    # Dinamik zaman damgası her dakika veya butonla yenilenerek yfinance verisini taze tutar
    with st.spinner("🚀 Canlı yfinance verileri, Efor Çizgileri ve Kinetik Güçler hesaplanıyor..."):
        df_live = calculate_v127_signals(ALL_STOCKS_LIST, current_timestamp)

    if not df_live.empty:
        heatmap_rows = []
        base_impacts = POLICY_IMPACTS[selected_policy]

        for sector, tickers in PORTFOLIO_UNIVERSE.items():
            base_score = base_impacts.get(sector, 0)
            final_score = round(base_score * multiplier, 1)

            for t in tickers:
                live_row = df_live[df_live['Ticker'] == t]
                if not live_row.empty:
                    heatmap_rows.append({
                        "Sektör / ETF": sector,
                        "Ticker": t,
                        "Makro Etki Puanı": final_score,
                        "Fiyat": live_row['Fiyat'].values[0],
                        "1 Gün (%)": live_row['1 Gün (%)'].values[0],
                        "Efor Çizgisi (14M)": live_row['Efor Çizgisi'].values[0],
                        "Whale Power (Kinetik)": live_row['Whale Power'].values[0],
                        "Fusion Skor": live_row['Fusion'].values[0]
                    })

        df_final_matrix = pd.DataFrame(heatmap_rows)

        st.dataframe(
            df_final_matrix.style.map(style_puan, subset=['Makro Etki Puanı'])
            .map(style_efor, subset=['Efor Çizgisi (14M)']),
            use_container_width=True,
            height=500,
            hide_index=True
        )

        # 🎯 AKSİYON PANELİ FILTERİ
        st.markdown("---")
        st.subheader("🎯 V127.0 Çarpan Etkisi Aksiyon Paneli")

        top_buys = df_final_matrix[(df_final_matrix['Makro Etki Puanı'] >= 5) & (df_final_matrix['Efor Çizgisi (14M)'].str.contains('POZ|UP'))]['Ticker'].tolist()
        top_sells = df_final_matrix[(df_final_matrix['Makro Etki Puanı'] <= -5) & (df_final_matrix['Efor Çizgisi (14M)'].str.contains('NEG|DOWN'))]['Ticker'].tolist()

        col3, col4 = st.columns(2)
        with col3:
            st.success(f"🟢 Makro + Efor Onaylı BUY Adayları: {', '.join(top_buys) if top_buys else 'Koşul sağlayan yok'}")
            all_candidates = list(set(top_buys + top_sells))
            if not all_candidates: all_candidates = df_final_matrix['Ticker'].tolist()
            trade_ticker = st.selectbox("Aksiyon İçin Hisse Seçin:", sorted(all_candidates))
            trade_dir = "BUY" if trade_ticker in top_buys else "SELL" if trade_ticker in top_sells else "NÖTR"

        with col4:
            st.error(f"🔴 Makro + Efor Onaylı Dynamic SELL Adayları: {', '.join(top_sells) if top_sells else 'Koşul sağlayan yok'}")
            
            with st.form("v134_action_form"):
                selected_row = df_final_matrix[df_final_matrix['Ticker'] == trade_ticker]
                if not selected_row.empty:
                    st.markdown(f"**Seçilen Hisse:** `{trade_ticker}` | **Önerilen Yön:** `{trade_dir}`")
                    st.markdown(f"**Anlık Efor Durumu:** {selected_row['Efor Çizgisi (14M)'].values[0]} | **Whale Power:** %{selected_row['Whale Power (Kinetik)'].values[0]}")
                
                trade_channel = st.selectbox("Kırılım Yaşanan Kanal Çizgisi (V127.0)", [f"Kanal {i}" for i in range(1, 13)])
                trade_close_focus = st.text_input("Close-Only Focus Kapanış Seviyesi Notları")
                
                submitted = st.form_submit_button("Doğrulamayı Hafızaya Al ve Logla")
                if submitted:
                    st.success(f"🔓 {trade_ticker} işlemi {trade_channel} üzerinden {trade_dir} yönlü başarıyla kaydedildi! Kapanış Odak Noktası: {trade_close_focus}")
    else:
        st.error("Canlı piyasa verileri çekilemedi, internet bağlantınızı veya yfinance kütüphanesini kontrol edin.")
