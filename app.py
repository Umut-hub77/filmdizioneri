import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import difflib
import re
import random
import urllib.parse
from pathlib import Path

# --- SAYFA AYARLARI ---
st.set_page_config(page_title="Yayın Rehberi", page_icon="🍿", layout="wide")
TMDB_API_KEY = "10e5fa6138c11560285b0c8af67e1376"

# --- CSS ---
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;500;700&display=swap');
html, body, [class*="css"] { font-family: 'Montserrat', sans-serif !important; }
.block-container { padding-top: 2rem; max-width: 1300px; }
.main-title { font-size: 3.5rem; font-weight: 900; background: linear-gradient(to right, #ffffff, #a0aec0); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
</style>
""", unsafe_allow_html=True)

# --- VERİ YÜKLEME ---
@st.cache_data
def load_imdb_data():
    try:
        df = pd.read_parquet('imdb_verisi_kucuk.parquet')
        if 'type' not in df.columns and 'titleType' in df.columns:
            df['type'] = df['titleType'].apply(lambda x: 'movie' if x == 'movie' else 'tv')
        df['genres'] = df['genres'].fillna('')
        df['numVotes'] = df['numVotes'].fillna(0).astype(int)
        df['averageRating'] = df['averageRating'].fillna(0.0)
        df['startYear'] = df['startYear'].fillna('?')
        return df.reset_index(drop=True)
    except Exception as e:
        st.error(f"Veri yükleme hatası: {e}")
        st.stop()

# --- API FONKSİYONLARI (Doğru Hizalamada) ---
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
    params = {'api_key': api_key, 'language': 'tr-TR', 'with_genres': genre_id, 'sort_by': 'vote_average.desc', 'vote_count.gte': 500, 'page': 1}
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200: return resp.json().get('results', [])[:limit]
    except: pass
    return []

@st.cache_data(ttl=3600)
def get_tmdb_recommendations(imdb_id: str, api_key: str, media_type: str = 'movie', limit: int = 15):
    find_url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    try:
        resp = requests.get(find_url, params={'api_key': api_key, 'external_source': 'imdb_id', 'language': 'tr-TR'}, timeout=5)
        if resp.status_code != 200: return None
        data = resp.json()
        results = data.get('movie_results', []) if media_type == 'movie' else data.get('tv_results', [])
        if not results: return None
        tmdb_id = results[0]['id']
        rec_resp = requests.get(f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/recommendations", params={'api_key': api_key, 'language': 'tr-TR'}, timeout=5)
        if rec_resp.status_code == 200: return rec_resp.json().get('results', [])[:limit]
    except: pass
    return None

@st.cache_data(ttl=300)
def get_random_recommendation(genre_id: str, media_type: str, api_key: str):
    url = f"https://api.themoviedb.org/3/discover/{media_type}"
    params = {'api_key': api_key, 'with_genres': genre_id, 'language': 'tr-TR', 'page': random.randint(1, 5), 'vote_average.gte': 6.5}
    try:
        resp = requests.get(url, params=params).json()
        results = [i for i in resp.get('results', []) if i.get('poster_path')]
        if results: return random.choice(results)
    except: pass
    return None

def render_scrollable_strip(title: str, items: list):
    if not items: return
    container_id = "scroll_" + re.sub(r'[^a-zA-Z0-9]', '', title)
    html_content = f"""
    <style>
    .header {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 15px; padding: 10px 15px; background: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    .header h3 {{ margin: 0; color: #141414; }}
    .scroll-container {{ display: flex; overflow-x: auto; gap: 15px; padding-bottom: 10px; scrollbar-width: none; }}
    .scroll-container::-webkit-scrollbar {{ display: none; }}
    .movie-card {{ flex: 0 0 140px; width: 140px; display: flex; flex-direction: column; }}
    .poster-box {{ position: relative; width: 100%; height: 210px; border-radius: 6px; overflow: hidden; cursor: pointer; }}
    .poster-img {{ width: 100%; height: 100%; object-fit: cover; }}
    .hover-overlay {{ position: absolute; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.85); display: flex; flex-direction: column; justify-content: center; align-items: center; gap: 10px; opacity: 0; pointer-events: none; transition: 0.3s; }}
    .show-overlay {{ opacity: 1 !important; pointer-events: auto !important; }}
    .action-btn {{ padding: 8px 15px; border-radius: 4px; color: white !important; text-decoration: none !important; font-size: 0.75rem; width: 80%; text-align: center; background: #E50914; }}
    </style>
    <div class="header"><h3>{title}</h3></div>
    <div id="{container_id}" class="scroll-container">
    """
    for row in items:
        baslik = row.get('title') or row.get('name')
        poster_path = row.get('poster_path')
        if not poster_path: continue
        watch_link = f"https://www.justwatch.com/tr/ara?q={urllib.parse.quote(baslik)}"
        imdb_link = f"https://www.imdb.com/find?q={urllib.parse.quote(baslik)}"
        image_url = f"https://image.tmdb.org/t/p/w300{poster_path}"
        html_content += f"""
        <div class="movie-card">
            <div class="poster-box" onclick="this.querySelector('.hover-overlay').classList.toggle('show-overlay')">
                <img src="{image_url}" class="poster-img">
                <div class="hover-overlay">
                    <a href="{watch_link}" target="_blank" class="action-btn">▶ İZLE</a>
                    <a href="{imdb_link}" target="_blank" class="action-btn" style="border:1px solid white; background:transparent;">IMDB</a>
                </div>
            </div>
        </div>"""
    html_content += "</div>"
    components.html(html_content, height=330, scrolling=False)

# --- ANA PROGRAM ---
st.markdown('<h1 class="main-title">Yayın Rehberi</h1>', unsafe_allow_html=True)
df_all = load_imdb_data()
secim = st.radio("Menü", ["Film", "Dizi", "Belgesel", "Ne İzlesem?"], horizontal=True, label_visibility="collapsed")
media_type = 'tv' if secim == "Dizi" else 'movie'

if secim == "Ne İzlesem?":
    # ... (Kendi mevcut Ne İzlesem kodlarını buraya ekleyebilirsin)
    pass
else:
    search_query = st.text_input("Arama", placeholder="🔍 Ne izlemek istiyorsunuz?")
    if search_query:
        # Arama mantığın...
        pass
    else:
        if secim == "Belgesel":
            # Belgesel mantığın...
            render_scrollable_strip("En Popüler Belgeseller", get_tmdb_discover_by_genre("99", TMDB_API_KEY, 'movie'))
        else:
            genres = get_tmdb_genres(TMDB_API_KEY, media_type)
            for genre in [g for g in genres if g['id'] != 99]:
                render_scrollable_strip(f"En İyi {genre['name']} Yapımları", get_tmdb_discover_by_genre(str(genre['id']), TMDB_API_KEY, media_type))
