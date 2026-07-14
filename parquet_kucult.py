import pandas as pd

# 1. Mevcut büyük parquet dosyanızı okuyun
# (Dosya adını kendi dosyanıza göre değiştirin)
df = pd.read_parquet('imdb_cache.parquet')

# 2. Gereksiz yapımları temizleyin (Sadece Film ve Diziler kalsın)
valid_types = ['movie', 'tvSeries', 'tvMiniSeries']
if 'titleType' in df.columns:
    df = df[df['titleType'].isin(valid_types)]

# 3. Sadece en az 1000 oy almış popüler yapımları tut (KRİTİK FİLTRE)
if 'numVotes' in df.columns:
    df['numVotes'] = df['numVotes'].fillna(0).astype(int)
    df = df[df['numVotes'] >= 1000]

# 4. Yeni ve küçücük Parquet dosyasını kaydet
df.to_parquet('imdb_verisi_kucuk.parquet', index=False)

print("İşlem tamam! Yeni 'imdb_verisi_kucuk.parquet' dosyanız hazır.")