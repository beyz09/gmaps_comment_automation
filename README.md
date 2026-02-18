# Google Maps İşletme Yorum Analiz Sistemi

Google Maps'ten işletme yorumlarını otomatik olarak toplayan, ön işleyen, etiketleyen ve analiz eden bir yapay zeka destekli sistem.

## � Özellikler

- **Otomatik Yorum Toplama**: Selenium ile Google Maps'ten yorum scraping
- **Toplu Tarama**: Bir bölgedeki tüm işletmeleri otomatik keşfetme ve tarama
- **Duygu Analizi**: Hugging Face modeli ile Türkçe sentiment analizi
- **Aspect-Based Analiz (ABSA)**: Yemek, servis, fiyat, temizlik gibi kategorilerde detaylı analiz
- **Model Eğitimi**: XGBoost ve CatBoost ile özel model eğitimi
- **Streamlit Dashboard**: İnteraktif analiz ve görselleştirme arayüzü

---

## ⚙️ Kurulum

### 1. Gereksinimler

```bash
pip install -r requirements.txt
```

### 2. Chrome ve ChromeDriver Kurulumu

Bu proje Selenium kullanır. ChromeDriver'ın sisteminizde kurulu olması gerekir.

#### Chrome Sürümünüzü Öğrenin
Chrome tarayıcıda adres çubuğuna yazın: `chrome://version`

#### ChromeDriver İndirme
- Chrome 115 ve üzeri için: https://googlechromelabs.github.io/chrome-for-testing/
- Eski sürümler için: https://chromedriver.chromium.org/downloads

> **Not:** Bu proje `webdriver-manager` yerine Selenium 4'ün otomatik driver yönetimini kullanır. Chrome güncel ise ek bir kurulum gerekmez.

#### ChromeDriver'ı Manuel Tanımlamak İsterseniz

`utils/browser_utils.py` dosyasında şu satırı değiştirin:

```python
# Mevcut (otomatik):
driver = webdriver.Chrome(options=options)

# Manuel yol tanımlamak için:
from selenium.webdriver.chrome.service import Service
service = Service("C:/path/to/chromedriver.exe")  # Windows
# service = Service("/usr/local/bin/chromedriver")  # Linux/Mac
driver = webdriver.Chrome(service=service, options=options)
```

---

### 3. MySQL Veritabanı Kurulumu

#### Veritabanı Oluşturma

MySQL'e bağlanın ve şu komutları çalıştırın:

```sql
CREATE DATABASE google_maps_data_v2 CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE google_maps_data_v2;

CREATE TABLE businesses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    city VARCHAR(100),
    district VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE comments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    business_id INT NOT NULL,
    username VARCHAR(255),
    rating FLOAT,
    date VARCHAR(100),
    comment_text TEXT,
    likes INT DEFAULT 0,
    sentiment VARCHAR(50),
    processed TINYINT(1) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (business_id) REFERENCES businesses(id)
);

CREATE TABLE pending_businesses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    search_query VARCHAR(500),
    status ENUM('pending','processing','completed','failed') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);
```

#### Bağlantı Ayarları

`utils/config.py` dosyasında MySQL bilgilerinizi girin:

```python
DB_CONFIG = {
    "host": "localhost",       # MySQL sunucu adresi
    "user": "root",            # MySQL kullanıcı adı
    "password": "",            # MySQL şifresi
    "database": "google_maps_data_v2"  # Veritabanı adı
}
```

---

## 🖥️ Uygulamayı Çalıştırma

```bash
cd comment_automation
streamlit run app.py
```

Tarayıcıda otomatik olarak `http://localhost:8501` açılır.

---

## 📁 Proje Yapısı

```
comment_automation/
├── app.py                  # Ana Streamlit uygulaması
├── gmapsv1.py              # Tekli işletme scraper
├── batch_scraper.py        # Toplu işletme scraper
├── scraper.py              # Yorum scraping motoru
├── preprocess_comments.py  # Yorum ön işleme
├── auto_label.py           # Otomatik duygu etiketleme
├── train_model.py          # Model eğitimi (XGBoost/CatBoost)
├── aspect_analyzer.py      # Aspect-Based Sentiment Analysis
├── predict.py              # Tahmin modülü
├── requirements.txt        # Python bağımlılıkları
└── utils/
    ├── config.py           # ⚠️ Ayarlar buraya (DB, ChromeDriver)
    ├── db_utils.py         # Veritabanı fonksiyonları
    ├── browser_utils.py    # Chrome/Selenium ayarları
    ├── scraper.py          # Scraping yardımcıları
    └── parser.py           # HTML parse fonksiyonları
```

---

## � Sık Karşılaşılan Sorunlar

### ChromeDriver Sürüm Uyumsuzluğu
```
SessionNotCreatedException: Message: session not created
```
**Çözüm:** Chrome ve ChromeDriver sürümlerinin eşleştiğinden emin olun.

### MySQL Bağlantı Hatası
```
mysql.connector.errors.InterfaceError: 2003
```
**Çözüm:** `utils/config.py` dosyasındaki `DB_CONFIG` bilgilerini kontrol edin. MySQL servisinin çalıştığından emin olun.

### Headless Mod Sorunu
Scraping headless modda çalışmıyorsa `app.py`'de "Headless Mod" kutucuğunun işaretini kaldırın.

---

## 📦 Bağımlılıklar

| Paket | Kullanım |
|-------|----------|
| `streamlit` | Web arayüzü |
| `selenium` | Google Maps scraping |
| `mysql-connector-python` | Veritabanı bağlantısı |
| `pandas` | Veri işleme |
| `scikit-learn` | ML altyapısı |
| `xgboost` | Sentiment modeli |
| `catboost` | Sentiment modeli |
| `transformers` | Hugging Face NLP modelleri |
| `torch` | Deep learning altyapısı |
