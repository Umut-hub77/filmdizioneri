import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import difflib
import re
import random
from pathlib import Path
import urllib.parse
# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Seyir Rehberi", page_icon="🍿", layout="wide")
TMDB_API_KEY = "10e5fa6138c11560285b0c8af67e1376"


st.markdown("""
<style>
/* 1. Resmi ve Kurumsal Font Yüklemesi */
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;500;700&display=swap');

html, body, [class*="css"] {
font-family: 'Montserrat', sans-serif !important;
}

.block-container { padding-top: 2rem; max-width: 1300px; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Streamlit animasyonlarını gizle */
div[data-testid="stStatusWidget"], div[data-testid="stSpinner"], .stSpinner {
display: none !important; visibility: hidden !important;
}

/* Başlık Tasarımları */
.main-title {
font-size: 3.5rem; font-weight: 900; text-align: left;
background: linear-gradient(to right, #ffffff, #a0aec0);
-webkit-background-clip: text; -webkit-text-fill-color: transparent;
margin-bottom: 0; padding-bottom: 0; letter-spacing: -1px;
}
.sub-title {
text-align: left; color: #a0aec0; font-size: 1.1rem;
margin-top: 5px; margin-bottom: 30px; font-weight: 400;
}

/* 2. Üst Menü Konumlandırması (Tam Ortalanmış ve Eşit Dağıtılmış) */
div[data-testid="stRadio"] {
display: flex;
justify-content: center; /* Menüyü sayfanın tam ortasına hizalar */
margin-top: 20px;
margin-bottom: 30px;
padding-bottom: 15px;
border-bottom: 1px solid rgba(255, 255, 255, 0.1);
width: 100%;
}
/* 1. Yuvarlakları (Radio) tamamen gizle */
/* 1. Üst Menü Taşıyıcısı (Mobil Uyumlu) */
div[role="radiogroup"] {
    display: flex !important;
    flex-direction: row !important;
    flex-wrap: nowrap !important; /* Yazıların alt satıra inmesini kesinlikle engeller */
    justify-content: space-around !important;
    gap: 10px !important;
    width: 100% !important;
    overflow-x: auto !important; /* Ekrana sığmazsa mobilde yana kaydırılabilir yapar */
    padding-bottom: 5px !important; 
    scrollbar-width: none; /* Firefox için scrollbar gizleme */
}
div[role="radiogroup"]::-webkit-scrollbar { 
    display: none; /* Chrome/Safari için scrollbar gizleme */
}

/* 2. Radyo Yuvarlaklarını Gizle */
div[role="radiogroup"] label input[type="radio"],
div[data-baseweb="radio"] {
    display: none !important;
}

/* 3. Menü Başlıkları (Çerçevesiz Temel Yapı) */
div[role="radiogroup"] > label {
    background: transparent !important;
    border: none !important;
    padding: 10px 5px !important;
    cursor: pointer !important;
    transition: all 0.3s ease !important;
    border-bottom: 2px solid transparent !important; /* Başlangıçta görünmez alt çizgi */
    border-radius: 0 !important; /* Kutu görünümünü sıfırla */
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
}

/* 4. Yazı Stili (Sönük Hal) */
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p {
    color: #8c8c8c !important; /* Başlangıçta sönük gri */
    font-weight: 600 !important;
    font-size: 1.1rem !important;
    margin: 0 !important;
    white-space: nowrap !important; /* Yazıların asla bölünmemesini sağlar */
    transition: color 0.3s ease !important;
}

/* 5. Hover (Üstüne Gelince Biraz Aydınlanma) */
div[role="radiogroup"] > label:hover div[data-testid="stMarkdownContainer"] p {
    color: #d1d1d1 !important;
}

/* 6. Aktif / Seçili Durum (Tam Beyaz Yazı ve Alt Çizgi) */
div[role="radiogroup"] label[data-checked="true"] {
    border-bottom: 2px solid #ffffff !important; /* Altına beyaz çizgi */
}
div[role="radiogroup"] label[data-checked="true"] div[data-testid="stMarkdownContainer"] p {
    color: #ffffff !important; /* Seçiliyken tam aydınlık beyaz */
}

/* "Format:" yazısının kırılmasını engellemek için */
div[data-testid="stRadio"] label[data-testid="stWidgetLabel"] {
    white-space: nowrap !important;
    margin-right: 15px !important;
}

/* Arama Çubuğu */
.stTextInput > div > div > input { font-size: 1.1rem !important; padding: 12px 20px !important; }
div[data-baseweb="input"] {
border-radius: 8px !important; border: 1px solid #333 !important;
background-color: #141414 !important; transition: all 0.3s ease;
}
div[data-baseweb="input"]:focus-within {
border-color: #E50914 !important; box-shadow: 0 0 10px rgba(229, 9, 20, 0.3) !important;
}
</style>
""", unsafe_allow_html=True)

@st.cache_data
# --- VERİ YÜKLEME (PARQUET) ---
@st.cache_data
def load_imdb_data():
    try:
        # Tek bir küçük parquet dosyasını okuyoruz
        df = pd.read_parquet('imdb_verisi_kucuk.parquet')

        # 'type' sütunu yoksa oluşturalım
        if 'type' not in df.columns and 'titleType' in df.columns:
            df['type'] = df['titleType'].apply(lambda x: 'movie' if x == 'movie' else 'tv')

        # DİKKAT: Buradaki satırları if bloğunun dışına çıkardık. 
        # Böylece if koşulu sağlanmasa bile işlemler yapılıp veri döndürülecek.
        df['genres'] = df['genres'].fillna('')
        df['numVotes'] = df['numVotes'].fillna(0).astype(int)
        df['averageRating'] = df['averageRating'].fillna(0.0)
        df['startYear'] = df['startYear'].fillna('?')

        return df.reset_index(drop=True)
        
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        st.stop()
        return pd.DataFrame() # Kodun çökmesini önlemek için yedek
@st.cache_data(ttl=3600)
def get_imdb_id(tmdb_id, media_type):
    """TMDb ID'sini kullanarak filmin/dizinin resmi IMDb tt kimliğini bulur."""
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids"
        res = requests.get(url, params={'api_key': TMDB_API_KEY}, timeout=3)
        if res.status_code == 200:
            return res.json().get('imdb_id')
    except:
        pass
    return None
@st.cache_data(ttl=3600)
def get_tmdb_genres(api_key: str, media_type: str):
    url = f"https://api.themoviedb.org/3/genre/{media_type}/list"
    try:
        resp = requests.get(url, params={'api_key': api_key, 'language': 'tr-TR'}, timeout=5)
        if resp.status_code == 200: return resp.json().get('genres', [])
    except: pass
    return []

@st.cache_data(ttl=3600)
def get_tmdb_search(query: str, api_key: str, media_type: str = "multi"):
    url = f"https://api.themoviedb.org/3/search/{media_type}"
    params = {'api_key': api_key, 'query': query, 'language': 'tr-TR', 'page': 1, 'include_adult': 'false'}
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200: return response.json().get('results', [])
    except: pass
    return []

@st.cache_data(ttl=3600)
def get_tmdb_discover_by_genre(genre_id: str, api_key: str, media_type: str, limit: int = 15):
    url = f"https://api.themoviedb.org/3/discover/{media_type}"
    params = {
    'api_key': api_key, 'language': 'tr-TR', 'with_genres': genre_id,
    'without_genres': '16' if '10759' in genre_id or '28' in genre_id else '',
    'sort_by': 'vote_average.desc', 'vote_count.gte': 500, 'page': 1
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200: return resp.json().get('results', [])[:limit]
    except: pass
    return []

@st.cache_data(ttl=3600)
def get_tmdb_recommendations(imdb_id: str, api_key: str, media_type: str = 'movie', limit: int = 15):
    find_url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    find_params = {'api_key': api_key, 'external_source': 'imdb_id', 'language': 'tr-TR'}
    try:
        resp = requests.get(find_url, params=find_params, timeout=5)
        if resp.status_code != 200: return None
        data = resp.json()
        results = data.get('movie_results', []) if media_type == 'movie' else data.get('tv_results', [])
        if not results: return None
        tmdb_id = results[0]['id']
        rec_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/recommendations"
        rec_resp = requests.get(rec_url, params={'api_key': api_key, 'language': 'tr-TR'}, timeout=5)
        if rec_resp.status_code == 200: return rec_resp.json().get('results', [])[:limit]
    except: pass
    return None

@st.cache_data(ttl=0) 
def get_random_recommendation(genre_id: str, media_type: str, api_key: str):
    random_page = random.randint(1, 50)
    url = f"https://api.themoviedb.org/3/discover/{media_type}"
    params = {
        'api_key': api_key, 
        'with_genres': genre_id, 
        'language': 'tr-TR', 
        'page': random_page, 
        'vote_average.gte': 6.0, 
        'sort_by' : 'desc'
    }
    try:
        resp = requests.get(url, params=params).json()
        results = [i for i in resp.get('results', []) if i.get('poster_path')]
        
        if results: 
            return random.choice(results)
    except: 
        pass
    return None



def render_scrollable_strip(title: str, items: list):
    if not items: return
    import urllib.parse
    import re

    container_id = "scroll_" + re.sub(r'[^a-zA-Z0-9]', '', title)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap');
    body {{ margin: 0; padding: 0; font-family: 'Montserrat', sans-serif; background: transparent; overflow: hidden; }}

    /* BAŞLIK KISMI: BEYAZ ARKA PLAN VE KOYU YAZI */
    .header {{
    display: flex; justify-content: space-between; align-items: center;
    margin-bottom: 15px; padding: 10px 15px;
    background-color: white; border-radius: 8px; /* Beyaz kutu */
    box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .header h3 {{ margin: 0; font-size: 1.2rem; font-weight: 700; color: #141414; }} /* Başlık siyah */

    /* OK BUTONLARI */
    .nav-buttons {{ display: flex; gap: 8px; }}
    .nav-btn {{
    background: #141414; border: none; color: white; width: 30px; height: 30px;
    border-radius: 50%; cursor: pointer; transition: 0.3s;
    }}
    .nav-btn:hover {{ background: #E50914; }}

    /* AFİŞLER VE DİĞERLERİ */
    .scroll-container {{ display: flex; overflow-x: auto; gap: 15px; padding-bottom: 10px; scrollbar-width: none; }}
    .scroll-container::-webkit-scrollbar {{ display: none; }}
    .movie-card {{ flex: 0 0 140px; width: 140px; display: flex; flex-direction: column; }}
    .poster-box {{ position: relative; width: 100%; height: 210px; border-radius: 6px; overflow: hidden; cursor: pointer; }}
    .poster-img {{ width: 100%; height: 100%; object-fit: cover; transition: 0.3s; }}

    .hover-overlay {{
    position: absolute; top: 0; left: 0; width: 100%; height: 100%;
    background: rgba(0,0,0,0.85); display: flex; flex-direction: column;
    justify-content: center; align-items: center; gap: 10px;
    opacity: 0; pointer-events: none; transition: 0.3s;
    }}
    .show-overlay {{ opacity: 1 !important; pointer-events: auto !important; }}

    .action-btn {{ padding: 8px 15px; border-radius: 4px; color: white !important; text-decoration: none !important; font-size: 0.75rem; font-weight: bold; width: 80%; text-align: center; }}
    .btn-red {{ background: #E50914; }}
    .btn-dark {{ background: transparent; border: 1px solid white; }}
    /* Butonu İnceltme */
    </style>
    </head>
    <body>
    <div class="header">
    <h3>{title}</h3>
    <div style="display:flex; gap:8px;">
    <button class="nav-btn" onclick="document.getElementById('{container_id}').scrollBy({{left: -300, behavior: 'smooth'}})">❮</button>
    <button class="nav-btn" onclick="document.getElementById('{container_id}').scrollBy({{left: 300, behavior: 'smooth'}})">❯</button>
    </div>
    </div>
    <div id="{container_id}" class="scroll-container">
    """

    for row in items:
        baslik = row.get('title') or row.get('name')
        poster_path = row.get('poster_path')
        tmdb_id = row.get('id')
        if not poster_path or not tmdb_id: continue

        safe_baslik = urllib.parse.quote(baslik)
        watch_link = f"https://www.justwatch.com/tr/ara?q={safe_baslik}"
        
        # 1. Filmin/Dizinin türünü belirliyoruz
        m_type_guess = 'movie' if 'title' in row else 'tv'
        
        # 2. tt kimliğini arka planda çekiyoruz
        imdb_id = get_imdb_id(tmdb_id, m_type_guess)
        
        # 3. Eğer tt kimliği varsa doğrudan sayfaya, yoksa mecburen aramaya yönlendiriyoruz
        if imdb_id:
            imdb_link = f"https://www.imdb.com/title/{imdb_id}/"
        else:
            imdb_link = f"https://www.imdb.com/find?q={safe_baslik}"

        image_url = f"https://image.tmdb.org/t/p/w300{poster_path}"

        html_content += f"""
        <div class="movie-card">
        <!-- onclick ile dokunulduğunda overlay'i gösteren JS fonksiyonu -->
        <div class="poster-box" onclick="this.querySelector('.hover-overlay').classList.toggle('show-overlay')">
        <img src="{image_url}" class="poster-img">
        <div class="hover-overlay">
        <a href="{watch_link}" target="_blank" rel="noopener noreferrer" class="action-btn btn-red">▶ İZLE</a>
        <a href="{imdb_link}" target="_blank" rel="noopener noreferrer" class="action-btn btn-dark">IMDB</a>
        </div>
        </div>
        </div>
        """

    html_content += "</div></body></html>"
    components.html(html_content, height=330, scrolling=False)



# Modern SVG Logo - Neon Akış (Neon Stream) Konsepti
logo_svg = """
<svg width="340" height="60" viewBox="0 0 340 60" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <!-- Canlı Kırmızı Degrade (Enerji ve Derinlik) -->
    <linearGradient id="glowRed" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ff3366" />
      <stop offset="50%" stop-color="#E50914" />
      <stop offset="100%" stop-color="#8a0000" />
    </linearGradient>
    <!-- Neon Gölge Efekti -->
    <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#E50914" flood-opacity="0.55"/>
    </filter>
  </defs>

  <!-- KESKİN BEYAZ 'N' HARFİ -->
  <path d="M 12 44 L 12 18 L 30 44 L 30 18" fill="none" stroke="#ffffff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
  
  <!-- NEON KIRMIZI 'W' HARFİ (N ile iç içe başlayıp akıp gidiyor) -->
  <path d="M 30 26 L 38 44 L 46 26 L 54 44 L 62 18" fill="none" stroke="url(#glowRed)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" filter="url(#neonGlow)"/>
  
  <!-- GİZLİ OYNAT (PLAY) İKONU (W'nin orta boşluğuna yerleştirilmiş) -->
  <polygon points="42,15 42,23 49,19" fill="#ffffff" />

  <!-- LOGO METNİ -->
  <text x="76" y="38" font-family="'Montserrat', sans-serif" font-size="28" font-weight="900" fill="#ffffff" letter-spacing="-0.5">
    Next<tspan fill="#E50914">Watch</tspan>
  </text>
</svg>
"""

st.markdown(f'<div style="margin-bottom: -5px;">{logo_svg}</div>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Find something to watch, discover the best recommendations based on story and atmosphere.</p>', unsafe_allow_html=True)

# Emojiler kaldırıldı, menü sağ üste hizalandı (CSS ile)
secim = st.radio("Menü", ["Film", "Dizi", "Belgesel", "Ne İzlesem?"], horizontal=True, label_visibility="collapsed")
media_type = 'tv' if secim == "Dizi" else 'movie'


if secim == "Ne İzlesem?":
    st.markdown("<h2 style='font-weight: 700;'>KARARSIZ MI KALDINIZ?</h2>", unsafe_allow_html=True)
    st.write("Türü seçin, arşivimizi tarayıp size yüksek puanlı bir yapım önerelim.")

    tur_tipi = st.radio("Format:", ["Film", "Dizi"], horizontal=True)
    m_type = "movie" if tur_tipi == "Film" else "tv"

    genres = get_tmdb_genres(TMDB_API_KEY, m_type)
    genre_dict = {g['name']: str(g['id']) for g in genres}
    selected_genre_name = st.selectbox("Tür Tercihiniz:", list(genre_dict.keys()))

    if st.button("ÖNERİ GETİR", use_container_width=True):
        with st.spinner("Arşiv taranıyor..."):
            chosen = get_random_recommendation(genre_dict[selected_genre_name], m_type, TMDB_API_KEY)
            if chosen:
                st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
                baslik = chosen.get('title') or chosen.get('name')
                ozet = chosen.get('overview') or 'Bu yapım için özet bulunmamaktadır.'
                puan = round(chosen.get('vote_average', 0), 1)
                yil = (chosen.get('release_date') or chosen.get('first_air_date') or '?')[:4]
                poster_url = f"https://image.tmdb.org/t/p/w500{chosen.get('poster_path')}"
                
                # Yeni tt kimlik entegrasyonu
                tmdb_id = chosen.get('id')
                imdb_id = get_imdb_id(tmdb_id, m_type)
                
                watch_link = f"https://www.justwatch.com/tr/ara?q={baslik.replace(' ', '%20')}"
                
                if imdb_id:
                    imdb_link = f"https://www.imdb.com/title/{imdb_id}/"
                else:
                    imdb_link = f"https://www.imdb.com/find?q={baslik.replace(' ', '%20')}"
                col1, col2 = st.columns([1, 2.5])
                with col1:
                    st.image(poster_url, use_column_width=True, clamp=True)
                with col2:
                    st.markdown(f"<h1 style='font-weight:700;'>{baslik} ({yil})</h1>", unsafe_allow_html=True)
                    st.markdown(f"**TMDb Puanı:** `{puan} / 10`")
                    st.markdown(f"<p style='line-height:1.6; color:#a0aec0;'>{ozet}</p>", unsafe_allow_html=True)
                    st.markdown(f"""
                    <div style="display:flex; gap:15px; margin-top:20px;">
                    <!-- rel="noopener noreferrer" eklendi -->
                    <a href="{watch_link}" target="_blank" rel="noopener noreferrer" style="background-color:#E50914; color:white; padding:12px 30px; text-decoration:none; border-radius:4px; font-weight:700; font-size:1rem; text-transform:uppercase;">Şimdi İzle</a>
                    <a href="{imdb_link}" target="_blank" rel="noopener noreferrer" style="background-color:transparent; border: 1px solid white; color:white; padding:12px 30px; text-decoration:none; border-radius:4px; font-weight:700; font-size:1rem; text-transform:uppercase;">IMDb</a>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.error("Kriterlerinize uygun bir yapım bulunamadı.")


else:
    # İki farklı input yerine TEK BİR ARAMA ÇUBUĞU oluşturduk.
    placeholder_text = "Örn: Matrix, Breaking Bad, Cosmos..."
    search_query = st.text_input("Arama", placeholder=f"🔍 Ne izlemek istiyorsunuz? ({placeholder_text})")

    if search_query:
        # 1. Doğrudan arama sonuçlarını göster
        st.markdown(f"### '{search_query}' İçin Arama Sonuçları")
        search_type = 'movie' if secim in ["Film", "Belgesel"] else 'tv'
        search_results = get_tmdb_search(search_query, TMDB_API_KEY, search_type)
        filtered_search = [i for i in search_results if i.get('poster_path')]

        if filtered_search:
            render_scrollable_strip("Sonuçlar", filtered_search)
        else:
            st.warning("Maalesef aradığınız kriterlere uygun bir sonuç bulunamadı.")

        # 2. TSV veritabanından benzerini bulup önerileri göster (Sizin eski mantığınız)
        matched_imdb_id = None
        if secim == "Film": df = df_all[(df_all['type'] == 'movie') & (~df_all['genres'].str.contains('Documentary', case=False, na=False))]
        elif secim == "Dizi": df = df_all[(df_all['type'] == 'tv') & (~df_all['genres'].str.contains('Documentary', case=False, na=False))]
        else: df = df_all[df_all['genres'].str.contains('Documentary', case=False, na=False)]

        titles_lower = df['primaryTitle'].str.lower()
        exact_matches = df[titles_lower == search_query.lower()]

        if not exact_matches.empty:
            best_match = exact_matches.sort_values(by='numVotes', ascending=False).iloc[0]
            matched_title = best_match['primaryTitle']
            matched_imdb_id = best_match['tconst']
        else:
            popular_df = df[df['numVotes'] > 1000]
            titles = popular_df['primaryTitle'].tolist()
            matches = difflib.get_close_matches(search_query, titles, n=1, cutoff=0.6)
            if matches:
                chosen_title = matches[0]
                best_match = df[df['primaryTitle'] == chosen_title].sort_values(by='numVotes', ascending=False).iloc[0]
                matched_title = best_match['primaryTitle']
                matched_imdb_id = best_match['tconst']
                st.info(f"💡 Şunu mu demek istediniz: **{matched_title}** ({best_match['startYear']})")

        if matched_imdb_id:
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1); margin: 20px 0;'>", unsafe_allow_html=True)
            oneriler = get_tmdb_recommendations(matched_imdb_id, TMDB_API_KEY, media_type, limit=15)
            if oneriler:
                render_scrollable_strip(f"✨ '{matched_title}' Sevenler İçin Öneriler", oneriler)

    else:
        st.markdown("<hr style='border-color: transparent;'>", unsafe_allow_html=True)

        if 'last_selection' not in st.session_state or st.session_state.last_selection != secim:
            st.session_state.seen_ids = set()
            st.session_state.last_selection = secim

            if secim == "Belgesel":
                with st.spinner("Belgeseller yükleniyor..."):
                    populer = get_tmdb_discover_by_genre("99", TMDB_API_KEY, 'movie', limit=15)
                    render_scrollable_strip("En Popüler Belgeseller", populer)

                    tarih = get_tmdb_discover_by_genre("99,36", TMDB_API_KEY, 'movie', limit=15)
                    render_scrollable_strip("Tarih Belgeselleri", tarih)

                    doga = get_tmdb_discover_by_genre("99", TMDB_API_KEY, 'movie', limit=25)
                    doga = [d for d in doga if any(x in (d.get('title') or '').lower() for x in ['nature', 'wild', 'ocean', 'earth'])]
                    render_scrollable_strip("Doğa ve Vahşi Yaşam", doga)

                    suc = get_tmdb_discover_by_genre("99,80", TMDB_API_KEY, 'movie', limit=15)
                    render_scrollable_strip("Suç ve Gizem", suc)

                    muzik = get_tmdb_discover_by_genre("99,10402", TMDB_API_KEY, 'movie', limit=15)
                    render_scrollable_strip("Müzik Belgeselleri", muzik)

            else:
                with st.spinner("Kategoriler Yükleniyor..."):
                    genres = get_tmdb_genres(TMDB_API_KEY, media_type)
                    genres = [g for g in genres if g['id'] != 99]
                    for genre in genres:
                        genre_id = str(genre['id'])
                        genre_name = genre['name']
                        category_items = get_tmdb_discover_by_genre(genre_id, TMDB_API_KEY, media_type, limit=15)
                        render_scrollable_strip(f"En İyi {genre_name} Yapımları", category_items)
