import pandas as pd
from pathlib import Path

# Dosyalarınızı okuyun (İsimleri kendi klasörünüze göre güncelleyin)
folder = Path(".")
basics_file = list(folder.glob('title.basics*.tsv*'))[0]
ratings_file = list(folder.glob('title.ratings*.tsv*'))[0]

# Oku
df_basics = pd.read_csv(basics_file, sep='\t', quoting=3, na_values='\\N', dtype=str)
df_ratings = pd.read_csv(ratings_file, sep='\t', quoting=3, na_values='\\N')

# 1. Aşama: Sadece filmleri ve dizileri tut, belgesiz türleri ayırma
valid_types = ['movie', 'tvSeries', 'tvMiniSeries']
df_basics = df_basics[df_basics['titleType'].isin(valid_types)]

# 2. Aşama: İki tabloyu birleştir
df = df_basics.merge(df_ratings, on='tconst', how='inner')

# 3. Aşama: KRİTİK FİLTRE (Sadece en az 1000 oy almış popüler yapımları tut)
# Bu işlem dosya boyutunu %95 oranında küçültecek ve sistemi ışık hızına ulaştıracak!
df['numVotes'] = df['numVotes'].fillna(0).astype(int)
df_filtered = df[df['numVotes'] >= 1000]

# Yeni küçük dosyaları kaydedelim
df_filtered[['tconst', 'titleType', 'primaryTitle', 'startYear', 'genres']].to_csv('title.basics.tsv.gz', sep='\t', index=False, compression='gzip')
df_filtered[['tconst', 'averageRating', 'numVotes']].to_csv('title.ratings.tsv.gz', sep='\t', index=False, compression='gzip')

print("Boyut küçültme başarılı! Artık bu yeni küçük .tsv.gz dosyalarını GitHub'a yükleyebilirsiniz.")