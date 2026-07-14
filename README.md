# Öneri Bot

Basit film öneri örneği.

Kullanım:

1. Gerekli paketleri yükleyin:

```bash
pip install -r requirements.txt
```

2. (İsteğe bağlı) OMDb API kullanmak için bir anahtar edinin ve `OMDB_API_KEY` ortam değişkeni olarak ayarlayın.
2b. (Daha geniş ve çok-dilli arama için) TMDb API anahtarı kullanabilirsiniz. `TMDB_API_KEY` ortam değişkeni olarak ayarlayın.

3. Çalıştırın:

```bash
python app.py
```

Program sizden izlediğiniz filmin başlığını isteyecek. Eğer `OMDB_API_KEY` tanımlıysa OMDb üzerinden eşleşme aranır; bulunamazsa yerel veri kümesinde benzer başlık aranır.
Eğer `TMDB_API_KEY` tanımlıysa önce TMDb'de (çok daha büyük bir veritabanı, çeviriler desteklenir) arama yapılır ve benzer filmler TMDb üzerinden getirilir.
