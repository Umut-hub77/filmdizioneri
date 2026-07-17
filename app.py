import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import requests
import difflib
import re
import random
import urllib.parse
import sqlite3
import hashlib
import base64
from contextlib import contextmanager
from PIL import Image

# ==========================================
# SAYFA AYARLARI
# ==========================================
try:
    _page_icon = Image.open("icon.png")
except Exception:
    _page_icon = "🍿"

st.set_page_config(page_title="NextWatch", page_icon=_page_icon, layout="wide")

# GÜVENLİK NOTU: API anahtarını kaynak kodun içine gömmek yerine
# .streamlit/secrets.toml dosyasına koyup st.secrets ile okuyun.
# Örnek secrets.toml içeriği: TMDB_API_KEY = "xxxx"
# Böylece repo public olsa bile anahtar sızmaz.
TMDB_API_KEY = st.secrets.get("TMDB_API_KEY", "10e5fa6138c11560285b0c8af67e1376")
DB_PATH = "nextwatch.db"
MIN_PASSWORD_LEN = 6

# ==========================================
# VERİTABANI KATMANI (SQLite)
# ==========================================
@contextmanager
def get_db():
    """Tüm DB işlemleri için tek noktadan bağlantı yönetimi.
    Bağlantı otomatik kapanır, hata olursa da sızıntı olmaz."""
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with get_db() as conn:
        c = conn.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password TEXT, profile_pic TEXT)')
        c.execute('''CREATE TABLE IF NOT EXISTS favorites
                     (username TEXT, tmdb_id TEXT, title TEXT, media_type TEXT, poster_path TEXT,
                      UNIQUE(username, tmdb_id))''')
        # Eski veritabanlarında profile_pic sütunu yoksa ekle (migration)
        try:
            c.execute('ALTER TABLE users ADD COLUMN profile_pic TEXT')
        except sqlite3.OperationalError:
            pass  # sütun zaten var


init_db()


def make_hashes(password: str) -> str:
    return hashlib.sha256(str.encode(password)).hexdigest()


def check_hashes(password: str, hashed_text: str) -> bool:
    return make_hashes(password) == hashed_text


def add_user(username: str, password: str) -> bool:
    """Yeni kullanıcı ekler. Kullanıcı adı zaten varsa False döner."""
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO users (username, password) VALUES (?, ?)',
                         (username, make_hashes(password)))
        return True
    except sqlite3.IntegrityError:
        return False


def login_user(username: str, password: str) -> bool:
    with get_db() as conn:
        row = conn.execute('SELECT password FROM users WHERE username=?', (username,)).fetchone()
    return bool(row) and check_hashes(password, row[0])


def get_profile_pic(username):
    with get_db() as conn:
        row = conn.execute('SELECT profile_pic FROM users WHERE username=?', (username,)).fetchone()
    return row[0] if row and row[0] else None


def set_profile_pic(username, b64_data):
    with get_db() as conn:
        conn.execute('UPDATE users SET profile_pic=? WHERE username=?', (b64_data, username))


def add_favorite(username, tmdb_id, title, media_type, poster_path):
    try:
        with get_db() as conn:
            conn.execute('INSERT INTO favorites VALUES (?, ?, ?, ?, ?)',
                         (username, str(tmdb_id), title, media_type, poster_path))
    except sqlite3.IntegrityError:
        pass  # Zaten favorilerde


def remove_favorite(username, tmdb_id):
    with get_db() as conn:
        conn.execute('DELETE FROM favorites WHERE username=? AND tmdb_id=?', (username, str(tmdb_id)))


def get_favorites(username):
    with get_db() as conn:
        return conn.execute(
            'SELECT tmdb_id, title, media_type, poster_path FROM favorites WHERE username=?',
            (username,)
        ).fetchall()


# ==========================================
# OTURUM YÖNETİMİ
# ==========================================
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

# --- URL PARAMETRELERİ İLE HTML'DEN TETİKLENEN FAVORİ İŞLEMLERİ ---
if "action" in st.query_params:
    action = st.query_params["action"]
    if st.session_state.logged_in:
        fav_id = st.query_params.get("id")
        if action == "add_fav":
            add_favorite(
                st.session_state.username,
                fav_id,
                st.query_params.get("title"),
                st.query_params.get("type"),
                st.query_params.get("poster"),
            )
            st.toast("Favorilere eklendi!")
        elif action == "remove_fav":
            remove_favorite(st.session_state.username, fav_id)
            st.toast("Favorilerden çıkarıldı!")
    else:
        st.warning("Favori işlemi için giriş yapmalısınız!")

    st.query_params.clear()
    st.rerun()

user_favs_set = set()
if st.session_state.logged_in:
    user_favs_set = {row[0] for row in get_favorites(st.session_state.username)}


# ==========================================
# STİL
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;500;600;700;900&display=swap');

html, body, [class*="css"] { font-family: 'Montserrat', sans-serif !important; }

.block-container { padding-top: 2rem; max-width: 1300px; }
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

/* Sidebar tamamen kaldırıldı, giriş/profil artık sağ üstte */
section[data-testid="stSidebar"] { display: none !important; }
div[data-testid="collapsedControl"] { display: none !important; }

div[data-testid="stStatusWidget"], div[data-testid="stSpinner"], .stSpinner {
    display: none !important; visibility: hidden !important;
}

.sub-title {
    text-align: left; color: #a0aec0; font-size: 1.1rem;
    margin-top: 5px; margin-bottom: 30px; font-weight: 400;
}

div[data-testid="stButton"] button,
button[data-testid^="stBaseButton"] {
    border-radius: 8px !important;
    font-weight: 600 !important;
    letter-spacing: 0.3px !important;
    transition: all 0.2s ease !important;
    width: 100% !important;
}

div[data-testid="stButton"] button[kind="secondary"],
button[data-testid="stBaseButton-secondary"] {
    background: transparent !important;
    border: 1px solid transparent !important;
    color: #8c8c8c !important;
    box-shadow: none !important;
    text-transform: none !important;
}
div[data-testid="stButton"] button[kind="secondary"]:hover,
button[data-testid="stBaseButton-secondary"]:hover {
    color: #ffffff !important;
    background: rgba(255,255,255,0.06) !important;
}

div[data-testid="stButton"] button[kind="primary"],
button[data-testid="stBaseButton-primary"] {
    background: linear-gradient(135deg, #E50914, #a8050d) !important;
    border: none !important;
    color: #ffffff !important;
    box-shadow: 0 0 16px rgba(229,9,20,0.55) !important;
}
div[data-testid="stButton"] button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {
    box-shadow: 0 0 26px rgba(229,9,20,0.85) !important;
    transform: translateY(-1px) !important;
}

.top-menu-row div[data-testid="stButton"] button {
    padding: 12px 10px !important; font-size: 1rem !important;
}

.stTextInput > div > div > input { font-size: 1.1rem !important; padding: 12px 20px !important; }
div[data-baseweb="input"] {
    border-radius: 8px !important; border: 1px solid #333 !important;
    background-color: #141414 !important; transition: all 0.3s ease;
}
div[data-baseweb="input"]:focus-within {
    border-color: #E50914 !important; box-shadow: 0 0 10px rgba(229, 9, 20, 0.3) !important;
}

/* --- Sağ üst profil rozeti --- */
div[data-testid="stPopover"] {
    position: fixed !important;
    top: 18px;
    right: 28px;
    z-index: 9999;
}
div[data-testid="stPopover"] > div > button {
    width: 46px !important;
    height: 46px !important;
    min-width: 46px !important;
    border-radius: 50% !important;
    padding: 0 !important;
    background: linear-gradient(135deg, #E50914, #a8050d) !important;
    border: 2px solid rgba(255,255,255,0.18) !important;
    box-shadow: 0 0 14px rgba(229,9,20,0.55) !important;
    color: #ffffff !important;
    font-weight: 700 !important;
    font-size: 1.05rem !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    overflow: hidden !important;
}
div[data-testid="stPopover"] > div > button:hover {
    box-shadow: 0 0 22px rgba(229,9,20,0.85) !important;
    transform: translateY(-1px);
}

/* --- Detay sayfası (Ne İzlesem?) aksiyon butonları --- */
.hero-actions { display:flex; gap:14px; margin: 18px 0 6px 0; flex-wrap: wrap; }
.hero-btn {
    background: linear-gradient(135deg, #E50914, #a8050d);
    color: #ffffff !important; text-decoration: none !important;
    padding: 12px 26px; border-radius: 8px; font-weight: 700; font-size: 0.9rem;
    letter-spacing: 0.4px; text-transform: uppercase;
    box-shadow: 0 0 16px rgba(229,9,20,0.55);
    transition: all 0.2s ease; display: inline-block;
}
.hero-btn:hover { box-shadow: 0 0 26px rgba(229,9,20,0.85); transform: translateY(-2px); }
.hero-btn-active {
    background: linear-gradient(135deg, #2b2b2b, #141414);
    border: 1px solid #E50914; box-shadow: none;
}
</style>
""", unsafe_allow_html=True)


# ==========================================
# SAĞ ÜST PROFİL / GİRİŞ ROZETİ
# ==========================================
def render_profile_corner():
    # Profil fotoğrafı varsa, popover tetikleyici butonunun arka planına basıyoruz
    if st.session_state.logged_in:
        pic = get_profile_pic(st.session_state.username)
        if pic:
            st.markdown(f"""
            <style>
            div[data-testid="stPopover"] > div > button {{
                background-image: url("data:image/png;base64,{pic}") !important;
                background-size: cover !important;
                background-position: center !important;
                color: transparent !important;
            }}
            </style>
            """, unsafe_allow_html=True)

    trigger_label = "👤" if not st.session_state.logged_in else st.session_state.username[0].upper()

    with st.popover(trigger_label, use_container_width=False):
        if not st.session_state.logged_in:
            st.markdown("#### Giriş Yap / Kayıt Ol")
            auth_mode = st.radio("İşlem Seçin:", ["Giriş Yap", "Kayıt Ol"], horizontal=True, key="auth_mode_corner")
            user_input = st.text_input("Kullanıcı Adı", key="user_corner").strip()
            pass_input = st.text_input("Şifre", type="password", key="pass_corner")

            if st.button("Onayla", type="primary", key="confirm_corner", use_container_width=True):
                if not user_input or not pass_input:
                    st.warning("Lütfen alanları doldurun.")
                elif auth_mode == "Kayıt Ol" and len(pass_input) < MIN_PASSWORD_LEN:
                    st.error(f"Şifre en az {MIN_PASSWORD_LEN} karakter olmalı.")
                elif auth_mode == "Kayıt Ol":
                    if add_user(user_input, pass_input):
                        st.success("Hesap oluşturuldu! Şimdi giriş yapabilirsiniz.")
                    else:
                        st.error("Bu kullanıcı adı zaten alınmış!")
                else:
                    if login_user(user_input, pass_input):
                        st.session_state.logged_in = True
                        st.session_state.username = user_input
                        st.rerun()
                    else:
                        st.error("Kullanıcı adı veya şifre hatalı!")
        else:
            st.markdown(f"**{st.session_state.username}**")
            uploaded = st.file_uploader("Profil fotoğrafı seç", type=["png", "jpg", "jpeg"], key="pfp_upload")
            if uploaded is not None:
                b64 = base64.b64encode(uploaded.read()).decode()
                set_profile_pic(st.session_state.username, b64)
                st.rerun()
            st.caption("Favorilerini üst menüdeki **Favorilerim** sekmesinden görebilirsin.")
            if st.button("Çıkış Yap", key="logout_corner", use_container_width=True):
                st.session_state.logged_in = False
                st.session_state.username = ""
                st.rerun()


render_profile_corner()


# ==========================================
# TMDB VERİ ÇEKME FONKSİYONLARI
# ==========================================
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
    except Exception:
        return pd.DataFrame()


@st.cache_data(ttl=3600)
def get_imdb_id(tmdb_id, media_type):
    try:
        url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/external_ids"
        res = requests.get(url, params={'api_key': TMDB_API_KEY}, timeout=3)
        if res.status_code == 200:
            return res.json().get('imdb_id')
    except requests.RequestException:
        pass
    return None


@st.cache_data(ttl=3600)
def get_tmdb_trailer_key(tmdb_id, media_type):
    """Resmi YouTube fragman anahtarını döner (varsa)."""
    url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/videos"
    try:
        res = requests.get(url, params={'api_key': TMDB_API_KEY, 'language': 'tr-TR'}, timeout=3)
        if res.status_code == 200:
            results = res.json().get('results', [])
            # tr-TR'de bulunamazsa İngilizce videoları dene
            if not results:
                res = requests.get(url, params={'api_key': TMDB_API_KEY}, timeout=3)
                results = res.json().get('results', []) if res.status_code == 200 else []
            for v in results:
                if v.get('site') == 'YouTube' and v.get('type') == 'Trailer':
                    return v.get('key')
            for v in results:
                if v.get('site') == 'YouTube':
                    return v.get('key')
    except requests.RequestException:
        pass
    return None


@st.cache_data(ttl=3600)
def get_tmdb_genres(api_key: str, media_type: str):
    url = f"https://api.themoviedb.org/3/genre/{media_type}/list"
    try:
        resp = requests.get(url, params={'api_key': api_key, 'language': 'tr-TR'}, timeout=5)
        if resp.status_code == 200:
            return resp.json().get('genres', [])
    except requests.RequestException:
        pass
    return []


@st.cache_data(ttl=3600)
def get_tmdb_search(query: str, api_key: str, media_type: str = "multi"):
    url = f"https://api.themoviedb.org/3/search/{media_type}"
    params = {'api_key': api_key, 'query': query, 'language': 'tr-TR', 'page': 1, 'include_adult': 'false'}
    try:
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            return response.json().get('results', [])
    except requests.RequestException:
        pass
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
        if resp.status_code == 200:
            return resp.json().get('results', [])[:limit]
    except requests.RequestException:
        pass
    return []


@st.cache_data(ttl=3600)
def get_tmdb_recommendations(imdb_id: str, api_key: str, media_type: str = 'movie', limit: int = 15):
    find_url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    find_params = {'api_key': api_key, 'external_source': 'imdb_id', 'language': 'tr-TR'}
    try:
        resp = requests.get(find_url, params=find_params, timeout=5)
        data = resp.json()
        results = data.get('movie_results', []) if media_type == 'movie' else data.get('tv_results', [])
        if not results:
            return None
        tmdb_id = results[0]['id']
        rec_url = f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/recommendations"
        rec_resp = requests.get(rec_url, params={'api_key': api_key, 'language': 'tr-TR'}, timeout=5)
        if rec_resp.status_code == 200:
            return rec_resp.json().get('results', [])[:limit]
    except requests.RequestException:
        pass
    return None


@st.cache_data(ttl=0)  # kasıtlı: her seferinde farklı bir öneri gelsin diye önbelleklenmiyor
def get_random_recommendation(genre_id: str, media_type: str, api_key: str):
    url = f"https://api.themoviedb.org/3/discover/{media_type}"
    base_params = {
        'api_key': api_key, 'with_genres': genre_id, 'language': 'tr-TR',
        'sort_by': 'vote_average.desc', 'include_adult': 'false', 'without_genres': '99',
    }
    quality_tiers = [(6.8, 600), (6.5, 250), (6.2, 80), (6.0, 30)]
    for min_rating, min_votes in quality_tiers:
        params = {**base_params, 'vote_average.gte': min_rating, 'vote_count.gte': min_votes}
        try:
            first = requests.get(url, params={**params, 'page': 1}, timeout=5).json()
            total_pages = first.get('total_pages', 0)
            if not total_pages:
                continue
            random_page = random.randint(1, min(total_pages, 12))
            resp = requests.get(url, params={**params, 'page': random_page}, timeout=5).json()
            results = [i for i in resp.get('results', []) if i.get('poster_path') and i.get('overview')]
            if results:
                return random.choice(results)
        except requests.RequestException:
            continue
    return None


# ==========================================
# NETFLIX TARZI HOVER'DA FRAGMAN OYNATAN POSTER
# ==========================================
# ==========================================
# NETFLIX TARZI HOVER/TIKLAMA İLE FRAGMAN OYNATAN POSTER
# ==========================================
def render_hero_poster(poster_url, trailer_key):
    tpl = """
    <!DOCTYPE html><html><head><style>
    body { margin:0; padding:40px; background:transparent; overflow:visible; font-family:'Montserrat',sans-serif; }
    .hero-wrap { display:flex; align-items:center; justify-content:center; }
    .hero-poster {
        position:relative; width:280px; height:400px; border-radius:10px; overflow:visible;
        transition: all .4s ease; cursor:pointer; background:#111;
    }
    
    /* Masaüstünde hover olunca veya mobilde tıklanınca ekranı büyüt */
    .hero-poster.hero-active {
        position: fixed;
        top: 50%;
        left: 50%;
        transform: translate(-50%, -50%) !important;
        width: 70vw;  /* Ekranın %70'ini kaplar */
        height: 70vh;
        max-width: 1000px;
        box-shadow: 0 12px 65px rgba(229,9,20,0.85);
        z-index: 99999;
        border-radius: 16px;
        overflow: hidden;
    }
    
    .hero-img { width:100%; height:100%; object-fit:cover; display:block; transition: opacity .25s ease; border-radius:10px;}
    .hero-video-box { position:absolute; top:0; left:0; width:100%; height:100%; background:black; border-radius:10px; overflow:hidden;}
    .hero-video-box iframe { width:100%; height:100%; border:0; }
    
    .hero-badge {
        position:absolute; bottom:10px; left:10px; background:rgba(0,0,0,0.8); color:#fff;
        font-size:0.75rem; padding:6px 12px; border-radius:4px; opacity:1; transition:opacity .3s;
        pointer-events:none;
    }
    .hero-active .hero-badge { opacity:0; }
    
    /* Mobil cihazlarda kapatmak için çarpı butonu */
    .close-btn {
        display: none; position: absolute; top: -15px; right: -15px;
        background: #E50914; color: white; width: 35px; height: 35px;
        border-radius: 50%; text-align: center; line-height: 35px;
        font-weight: bold; font-size: 16px; cursor: pointer;
        box-shadow: 0 4px 10px rgba(0,0,0,0.5); z-index: 100000;
    }
    .hero-active .close-btn { display: block; }

    /* Telefon ve Tabletler için Özel Boyutlandırma */
    @media (max-width: 768px) {
        .hero-poster.hero-active { 
            width: 95vw; 
            height: 40vh; /* Mobilde yatay videonun sığması için */
        }
        .close-btn { 
            top: 5px; right: 5px; /* Mobilde buton ekranın dışına taşmasın diye içeri aldık */
        }
    }
    </style></head><body>
    <div class="hero-wrap">
      <div class="hero-poster" id="heroPoster">
        <div class="close-btn" id="closeBtn">✖</div>
        <img src="__POSTER_URL__" class="hero-img" id="heroImg">
        <div class="hero-video-box" id="heroVideoBox"></div>
        __BADGE__
      </div>
    </div>
    <script>
    var poster = document.getElementById('heroPoster');
    var img = document.getElementById('heroImg');
    var box = document.getElementById('heroVideoBox');
    var closeBtn = document.getElementById('closeBtn');
    var trailerKey = "__TRAILER_KEY__";

    function playTrailer() {
        if (!poster.classList.contains('hero-active')) {
            poster.classList.add('hero-active');
            if (trailerKey) {
                // controls=1 eklendi, böylece ileri geri sarabilirsin.
                box.innerHTML = '<iframe src="https://www.youtube.com/embed/' + trailerKey +
                    '?autoplay=1&controls=1&modestbranding=1&rel=0&playsinline=1" allow="autoplay; encrypted-media; fullscreen" allowfullscreen frameborder="0"></iframe>';
                img.style.opacity = '0';
            }
        }
    }

    function stopTrailer(e) {
        if (e) e.stopPropagation();
        if (poster.classList.contains('hero-active')) {
            poster.classList.remove('hero-active');
            box.innerHTML = '';
            img.style.opacity = '1';
        }
    }

    // Masaüstü için (Fare ile üzerine gelme ve çıkma)
    poster.addEventListener('mouseenter', playTrailer);
    poster.addEventListener('mouseleave', stopTrailer);

    // Telefon ve Tabletler için (Dokunma / Tıklama)
    poster.addEventListener('click', function(e) {
        // Eğer tıklanan yer kapatma butonu değilse videoyu oynat
        if (e.target !== closeBtn) {
            playTrailer();
        }
    });

    // Kapat butonuna tıklanınca videoyu durdur ve küçült
    closeBtn.addEventListener('click', stopTrailer);
    </script>
    </body></html>
    """
    badge = '<div class="hero-badge">Fragman için tıkla / üzerine gel</div>' if trailer_key else ''
    html_out = (tpl.replace("__POSTER_URL__", poster_url)
                    .replace("__TRAILER_KEY__", trailer_key or "")
                    .replace("__BADGE__", badge))
    
    # Streamlit iframe yüksekliğini 700'e çıkardık ki video büyüdüğünde alttan kesilmesin
    components.html(html_out, height=700, scrolling=False)


def render_hero_actions(watch_link, imdb_link, tmdb_id, safe_title, m_type, poster_path, is_logged_in, is_fav):
    fav_html = ""
    if is_logged_in:
        if is_fav:
            fav_html = f'<a href="?action=remove_fav&id={tmdb_id}" class="hero-btn hero-btn-active">Favoriden Çıkar</a>'
        else:
            fav_html = (f'<a href="?action=add_fav&id={tmdb_id}&title={safe_title}&type={m_type}'
                        f'&poster={poster_path}" class="hero-btn">Favoriye Ekle</a>')
    html_out = f"""
    <div class="hero-actions">
      <a href="{watch_link}" target="_blank" rel="noopener noreferrer" class="hero-btn">İZLE</a>
      <a href="{imdb_link}" target="_blank" rel="noopener noreferrer" class="hero-btn">IMDb</a>
      {fav_html}
    </div>
    """
    st.markdown(html_out, unsafe_allow_html=True)


# ==========================================
# KAYDIRILABİLİR LİSTE RENDER FONKSİYONU
# ==========================================
def render_scrollable_strip(title: str, items: list):
    if not items:
        return
    container_id = "scroll_" + re.sub(r'[^a-zA-Z0-9]', '', title)

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@500;600;700&display=swap');
    body {{ margin: 0; padding: 0; font-family: 'Montserrat', sans-serif; background: transparent; overflow: hidden; }}
    .header {{
        display: flex; justify-content: space-between; align-items: center; gap: 10px;
        margin-bottom: 15px; padding: 10px 15px; background-color: white; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }}
    .header h3 {{ margin: 0; font-size: 1.2rem; font-weight: 700; color: #141414; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }}
    .nav-buttons {{ display: flex; gap: 6px; }}
    .nav-btn {{
        background: rgba(255,255,255,0.06); border: 1px solid rgba(0,0,0,0.08); color: #141414; width: 32px; height: 26px;
        border-radius: 6px; cursor: pointer; transition: 0.25s; font-size: 0.85rem; display: flex; align-items: center; justify-content: center;
    }}
    .nav-btn:hover {{ background: #E50914; color: #ffffff; border-color: #E50914; }}
    .scroll-container {{ display: flex; overflow-x: auto; gap: 15px; padding-bottom: 10px; scrollbar-width: none; }}
    .scroll-container::-webkit-scrollbar {{ display: none; }}
    .movie-card {{ flex: 0 0 140px; width: 140px; display: flex; flex-direction: column; }}
    .poster-box {{ position: relative; width: 100%; height: 210px; border-radius: 6px; overflow: hidden; cursor: pointer; }}
    .poster-img {{ width: 100%; height: 100%; object-fit: cover; transition: 0.3s; }}
    .hover-overlay {{
        position: absolute; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.85); display: flex; flex-direction: column;
        justify-content: center; align-items: center; gap: 8px; opacity: 0; pointer-events: none; transition: 0.3s;
    }}
    .show-overlay {{ opacity: 1 !important; pointer-events: auto !important; }}
    .action-btn {{ padding: 6px 10px; border-radius: 4px; text-decoration: none !important; font-size: 0.7rem; font-weight: bold; width: 85%; text-align: center; box-sizing: border-box; }}
    .btn-red {{ background: #E50914; color: white !important; }}
    .btn-dark {{ background: transparent; border: 1px solid white; color: white !important; }}
    .btn-fav-add {{ background: transparent; border: 1px solid #ff3366; color: #ff3366 !important; }}
    .btn-fav-remove {{ background: #ff3366; color: white !important; border: none; }}
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
        if not poster_path or not tmdb_id:
            continue

        safe_baslik = urllib.parse.quote(baslik)
        watch_link = f"https://www.justwatch.com/tr/ara?q={safe_baslik}"
        m_type_guess = 'movie' if 'title' in row else 'tv'

        imdb_id = get_imdb_id(tmdb_id, m_type_guess)
        imdb_link = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else f"https://www.imdb.com/find?q={safe_baslik}"
        image_url = f"https://image.tmdb.org/t/p/w300{poster_path}"

        # NOT: target="_top" -> iframe içindeki link, Streamlit sayfasının tamamını
        # (üst pencereyi) yönlendirir. JS ile window.top.location değiştirmek yerine
        # native <a> linki kullanmak, tarayıcının sandbox/iframe kısıtlamalarına takılmaz.
        if str(tmdb_id) in user_favs_set:
            fav_btn = (
                f'<a href="?action=remove_fav&id={tmdb_id}" target="_top" '
                f'class="action-btn btn-fav-remove">❌ Favoriden Çıkar</a>'
            )
        else:
            fav_btn = (
                f'<a href="?action=add_fav&id={tmdb_id}&title={safe_baslik}'
                f'&type={m_type_guess}&poster={poster_path}" target="_top" '
                f'class="action-btn btn-fav-add">❤️ Favoriye Ekle</a>'
            )

        html_content += f"""
        <div class="movie-card">
        <div class="poster-box" onclick="this.querySelector('.hover-overlay').classList.toggle('show-overlay')">
        <img src="{image_url}" class="poster-img">
        <div class="hover-overlay">
        <a href="{watch_link}" target="_blank" rel="noopener noreferrer" class="action-btn btn-red">İZLE</a>
        <a href="{imdb_link}" target="_blank" rel="noopener noreferrer" class="action-btn btn-dark">IMDB</a>
        {fav_btn}
        </div>
        </div>
        </div>
        """
    html_content += "</div></body></html>"
    components.html(html_content, height=330, scrolling=False)


# ==========================================
# ANA ARAYÜZ
# ==========================================
logo_svg = """
<svg width="340" height="60" viewBox="0 0 340 60" xmlns="http://www.w3.org/2000/svg">
  <defs>
    <linearGradient id="glowRed" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#ff3366" />
      <stop offset="50%" stop-color="#E50914" />
      <stop offset="100%" stop-color="#8a0000" />
    </linearGradient>
    <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#E50914" flood-opacity="0.55"/>
    </filter>
  </defs>
  <path d="M 12 44 L 12 18 L 30 44 L 30 18" fill="none" stroke="#ffffff" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" />
  <path d="M 30 26 L 38 44 L 46 26 L 54 44 L 62 18" fill="none" stroke="url(#glowRed)" stroke-width="6" stroke-linecap="round" stroke-linejoin="round" filter="url(#neonGlow)"/>
  <polygon points="42,15 42,23 49,19" fill="#ffffff" />
  <text x="76" y="38" font-family="'Montserrat', sans-serif" font-size="28" font-weight="900" fill="#ffffff" letter-spacing="-0.5">
    Next<tspan fill="#E50914">Watch</tspan>
  </text>
</svg>
"""

st.markdown(f'<div style="margin-bottom: -5px;">{logo_svg}</div>', unsafe_allow_html=True)
st.markdown('<p class="sub-title">Find something to watch, discover the best recommendations based on story and atmosphere.</p>', unsafe_allow_html=True)

if "secim" not in st.session_state:
    st.session_state.secim = "Film"

st.markdown('<div class="top-menu-row">', unsafe_allow_html=True)
menu_items = ["Film", "Dizi", "Belgesel", "Ne İzlesem?", "Favorilerim"]
menu_cols = st.columns(len(menu_items))
for col, item in zip(menu_cols, menu_items):
    with col:
        if st.button(item, key=f"menu_{item}", use_container_width=True,
                     type="primary" if st.session_state.secim == item else "secondary"):
            st.session_state.secim = item
            st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

secim = st.session_state.secim
media_type = 'tv' if secim == "Dizi" else 'movie'

# --- FAVORİLERİM SEKMESİ ---
if secim == "Favorilerim":
    st.markdown("<h2 style='font-weight: 700;'>FAVORİLERİM</h2>", unsafe_allow_html=True)
    if not st.session_state.logged_in:
        st.info("Kendi favori listenizi oluşturmak ve görüntülemek için sağ üstten giriş yapmalısınız.")
    else:
        fav_data = get_favorites(st.session_state.username)
        if not fav_data:
            st.warning("Henüz favorilere eklenmiş bir yapım bulunmuyor. Keşfetmeye başlayın!")
        else:
            fav_items = [{"id": row[0], "title": row[1], "poster_path": row[3]} for row in fav_data]
            render_scrollable_strip(f"{st.session_state.username} adlı kullanıcının Favorileri", fav_items)

# --- NE İZLESEM SEKMESİ ---
elif secim == "Ne İzlesem?":
    st.markdown("<h2 style='font-weight: 700;'>KARARSIZ MI KALDINIZ?</h2>", unsafe_allow_html=True)
    st.write("Türü seçin, arşivimizi tarayıp size yüksek puanlı bir yapım önerelim.")

    if "tur_tipi" not in st.session_state:
        st.session_state.tur_tipi = "Film"
    st.markdown("<p style='color:#8c8c8c; font-weight:600; font-size:0.85rem; text-transform:uppercase;'>Format</p>", unsafe_allow_html=True)

    fcol1, fcol2, _spacer = st.columns([1, 1, 4])
    with fcol1:
        if st.button("Film", key="format_film", use_container_width=True,
                     type="primary" if st.session_state.tur_tipi == "Film" else "secondary"):
            st.session_state.tur_tipi = "Film"
            st.rerun()
    with fcol2:
        if st.button("Dizi", key="format_dizi", use_container_width=True,
                     type="primary" if st.session_state.tur_tipi == "Dizi" else "secondary"):
            st.session_state.tur_tipi = "Dizi"
            st.rerun()

    tur_tipi = st.session_state.tur_tipi
    m_type = "movie" if tur_tipi == "Film" else "tv"

    genres = get_tmdb_genres(TMDB_API_KEY, m_type)
    genre_dict = {g['name']: str(g['id']) for g in genres}
    selected_genre_name = st.selectbox("Tür Tercihiniz:", list(genre_dict.keys()))

    if st.button("ÖNERİ GETİR", use_container_width=True, type="primary"):
        with st.spinner("Arşiv taranıyor..."):
            chosen = get_random_recommendation(genre_dict[selected_genre_name], m_type, TMDB_API_KEY)

        if chosen:
            st.markdown("<hr style='border-color: rgba(255,255,255,0.1);'>", unsafe_allow_html=True)
            baslik = chosen.get('title') or chosen.get('name')
            ozet = chosen.get('overview') or 'Bu yapım için özet bulunmamaktadır.'
            puan = round(chosen.get('vote_average', 0), 1)
            yil = (chosen.get('release_date') or chosen.get('first_air_date') or '?')[:4]
            poster_url = f"https://image.tmdb.org/t/p/w500{chosen.get('poster_path')}"
            tmdb_id = chosen.get('id')
            imdb_id = get_imdb_id(tmdb_id, m_type)

            safe_b = urllib.parse.quote(baslik)
            watch_link = f"https://www.justwatch.com/tr/ara?q={safe_b}"
            imdb_link = f"https://www.imdb.com/title/{imdb_id}/" if imdb_id else f"https://www.imdb.com/find?q={safe_b}"
            trailer_key = get_tmdb_trailer_key(tmdb_id, m_type)

            col1, col2 = st.columns([1, 2.5])
            with col1:
                render_hero_poster(poster_url, trailer_key)
            with col2:
                st.markdown(f"<h1 style='font-weight:700;'>{baslik} ({yil})</h1>", unsafe_allow_html=True)
                st.markdown(f"**TMDb Puanı:** `{puan} / 10`")
                st.markdown(f"<p style='line-height:1.6; color:#a0aec0;'>{ozet}</p>", unsafe_allow_html=True)

                render_hero_actions(
                    watch_link, imdb_link, tmdb_id, safe_b, m_type, chosen.get('poster_path'),
                    st.session_state.logged_in, str(tmdb_id) in user_favs_set
                )
        else:
            st.error("Kriterlerinize uygun bir yapım bulunamadı.")

# --- FİLM / DİZİ / BELGESEL KEŞİF ve ARAMA ---
else:
    search_query = st.text_input("Arama", placeholder="🔍 Ne izlemek istiyorsunuz? (Örn. Matrix)").strip()

    if search_query:
        st.markdown(f"### '{search_query}' İçin Arama Sonuçları")
        search_type = 'movie' if secim in ["Film", "Belgesel"] else 'tv'
        search_results = get_tmdb_search(search_query, TMDB_API_KEY, search_type)
        filtered_search = [i for i in search_results if i.get('poster_path')]

        if filtered_search:
            render_scrollable_strip("Sonuçlar", filtered_search)
        else:
            st.warning("Maalesef aradığınız kriterlere uygun bir sonuç bulunamadı.")

        df_all = load_imdb_data()
        matched_imdb_id = None
        if not df_all.empty:
            if secim == "Film":
                df = df_all[(df_all['type'] == 'movie') & (~df_all['genres'].str.contains('Documentary', case=False, na=False))]
            elif secim == "Dizi":
                df = df_all[(df_all['type'] == 'tv') & (~df_all['genres'].str.contains('Documentary', case=False, na=False))]
            else:
                df = df_all[df_all['genres'].str.contains('Documentary', case=False, na=False)]

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
            else:
                with st.spinner("Kategoriler Yükleniyor..."):
                    genres = get_tmdb_genres(TMDB_API_KEY, media_type)
                    genres = [g for g in genres if g['id'] != 99]
                    for genre in genres:
                        genre_id = str(genre['id'])
                        genre_name = genre['name']
                        category_items = get_tmdb_discover_by_genre(genre_id, TMDB_API_KEY, media_type, limit=15)
                        render_scrollable_strip(f"En İyi {genre_name} Yapımları", category_items)
