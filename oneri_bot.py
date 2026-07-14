import sys
import os
import requests
import difflib
import pandas as pd
from pathlib import Path

def load_imdb_data() -> pd.DataFrame:
    """Basics ve Ratings dosyalarını hızlıca okuyup birleştirir."""
    folder = Path(__file__).parent
    basics_path = list(folder.glob('title.basics*.tsv*'))
    ratings_path = list(folder.glob('title.ratings*.tsv*'))

    if not basics_path:
        print("HATA: 'title.basics.tsv.gz' dosyası bulunamadı!")
        sys.exit(1)

    print("IMDb Yerel Veritabanı yükleniyor (Hızlı arama için)...")
    df_basics = pd.read_csv(
        basics_path[0], sep='\t', quoting=3, na_values='\\N',
        # Türlere (genres) artık ihtiyacımız yok, API'den çekeceğiz
        usecols=['tconst', 'titleType', 'primaryTitle', 'startYear'],
        dtype={'tconst': str, 'titleType': str, 'primaryTitle': str, 'startYear': str}
    )
    df_basics = df_basics[df_basics['titleType'] == 'movie'].copy()

    if ratings_path:
        df_ratings = pd.read_csv(
            ratings_path[0], sep='\t', quoting=3, na_values='\\N',
            usecols=['tconst', 'averageRating', 'numVotes']
        )
        df = df_basics.merge(df_ratings, on='tconst', how='left')
    else:
        df = df_basics
        df['numVotes'] = 0
        df['averageRating'] = 0.0

    df['numVotes'] = df['numVotes'].fillna(0).astype(int)
    df['averageRating'] = df['averageRating'].fillna(0.0)
    df['startYear'] = df['startYear'].fillna('?')

    del df_basics
    if ratings_path: del df_ratings

    return df.reset_index(drop=True)

def get_tmdb_recommendations(imdb_id: str, api_key: str, limit: int = 5):
    """
    Yerel veritabanında bulduğumuz filmin IMDb ID'sini (tconst) alır,
    TMDb üzerinden o filmin gerçek 'İçerik/Hikaye' tabanlı önerilerini çeker.
    """
    # 1. IMDb ID'yi (Örn: tt0118688) TMDb ID'ye dönüştürme
    find_url = f"https://api.themoviedb.org/3/find/{imdb_id}"
    find_params = {'api_key': api_key, 'external_source': 'imdb_id', 'language': 'tr-TR'}
    
    try:
        resp = requests.get(find_url, params=find_params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        
        movie_results = data.get('movie_results', [])
        if not movie_results:
            return None
            
        tmdb_id = movie_results[0]['id']
        
        # 2. Bulunan TMDb ID ile önerileri çekme (Türlere değil, hikayeye bakar)
        rec_url = f"https://api.themoviedb.org/3/movie/{tmdb_id}/recommendations"
        rec_params = {'api_key': api_key, 'language': 'tr-TR'}
        
        rec_resp = requests.get(rec_url, params=rec_params, timeout=5)
        rec_resp.raise_for_status()
        rec_data = rec_resp.json()
        
        return rec_data.get('results', [])[:limit]
        
    except Exception as e:
        print(f"TMDb API Hatası: {e}")
        return None

# --- BAŞLANGIÇ YÜKLEMESİ ---
print("\n--- SİSTEM BAŞLATILIYOR ---")
df = load_imdb_data()
print(f"Toplam {len(df)} film hazır! (RAM dostu sürüm)\n" + "="*50)

if __name__ == '__main__':
    # Eğer ortam değişkenlerinde yoksa, API Key'inizi doğrudan aşağıya yapıştırabilirsiniz.
    TMDB_API_KEY = "10e5fa6138c11560285b0c8af67e1376"


    try:
        watched = input('Hangi filmi izlediniz? (Başlık girin): ').strip()

        matched_idx = None
        matched_title = None

        # 1. Aşama: Yerel IMDb veritabanında arama
        titles_lower = df['primaryTitle'].str.lower()
        exact_matches = df[titles_lower == watched.lower()]
        
        if not exact_matches.empty:
            best_match = exact_matches.sort_values(by='numVotes', ascending=False).iloc[0]
            matched_idx = best_match.name
            matched_title = best_match['primaryTitle']
            matched_imdb_id = best_match['tconst']
            print(f"\nTam eşleşme bulundu: {matched_title} ({best_match['startYear']})")
        else:
            print("\nBirebir eşleşme bulunamadı, bilinen filmler içinde aranıyor...")
            popular_df = df[df['numVotes'] > 1000]
            titles = popular_df['primaryTitle'].tolist()
            
            matches = difflib.get_close_matches(watched, titles, n=5, cutoff=0.6)
            if matches:
                print('\nYakın başlıklar bulundu, lütfen seçim yapın:')
                for i, t in enumerate(matches, 1):
                    match_info = popular_df[popular_df['primaryTitle'] == t].iloc[0]
                    print(f"{i}. {t} ({match_info['startYear']})")
                sel = input('Seçiminiz (numara girin veya iptal için Enter): ').strip()
                if sel.isdigit() and 1 <= int(sel) <= len(matches):
                    chosen_title = matches[int(sel) - 1]
                    best_match = df[df['primaryTitle'] == chosen_title].sort_values(by='numVotes', ascending=False).iloc[0]
                    matched_idx = best_match.name
                    matched_title = best_match['primaryTitle']
                    matched_imdb_id = best_match['tconst']
            else:
                print('Girilen başlığa yakın bilindik bir film bulunamadı.')

        # 2. Aşama: Filmi bulduysak, IMDb ID'si ile TMDb API üzerinden öneri çek
        if matched_idx is not None:
            print("\nTMDb Yapay Zekası üzerinden içerik bazlı öneriler çekiliyor...")
            oneriler = get_tmdb_recommendations(matched_imdb_id, TMDB_API_KEY, limit=5)
            
            if oneriler:
                print(f"\n'{matched_title}' filminin HİKAYESİNİ sevenler için en iyi öneriler:\n")
                for i, row in enumerate(oneriler, 1):
                    o_baslik = row.get('title')
                    o_yil = row.get('release_date', '?')[:4]
                    o_puan = round(row.get('vote_average', 0), 1)
                    o_ozet = row.get('overview', 'Özet bulunmuyor.').replace('\n', ' ')
                    
                    if len(o_ozet) > 130:
                        o_ozet = o_ozet[:130] + "..."
                        
                    print(f"{i}. {o_baslik} ({o_yil}) | Puan: {o_puan}/10")
                    print(f"   Konu: {o_ozet}\n")
            else:
                print("\nBu film için TMDb üzerinde yeterli öneri verisi bulunamadı.")
        else:
            print('\nEşleşen film bulunamadığı için işlem iptal edildi.')

    except KeyboardInterrupt:
        print("\nProgramdan çıkıldı.")