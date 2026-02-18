# Konu Bazlı Duygu Analizi (Aspect-Based Sentiment Analysis)

## 🎯 Hedef
Yorumlardan konu bazlı puanlama çıkarmak - Trendyol benzeri konu filtreleme sistemi

## 📊 Örnek Çıktı

**Giriş:**
```
"Yemekler çok lezzetliydi, personel ilgiliydi, kesinlikle tavsiye ederim"
```

**Çıktı:**
```
🍽️ Yemek Kalitesi: 9/10 (positive)
👥 Personel Tutumu: 9/10 (positive)
```

---

## 📁 Oluşturulan Dosyalar

| Dosya | Açıklama |
|-------|----------|
| `aspect_analyzer.py` | Konu bazlı analiz scripti |
| `train_model.py` | XGBoost model eğitimi (opsiyonel) |
| `predict.py` | Model ile tahmin (opsiyonel) |

---

## 🏷️ Kategoriler (Aspects)

| Kategori | İkon | Örnek Anahtar Kelimeler |
|----------|------|-------------------------|
| Yemek Kalitesi | 🍽️ | lezzetli, taze, bayat, tatsız |
| Personel Tutumu | 👥 | ilgili, nazik, kaba, ilgisiz |
| Fiyat | 💰 | uygun, pahalı, hesaplı |
| Temizlik | 🧹 | temiz, kirli, hijyenik |
| Hizmet Hızı | ⏱️ | hızlı, yavaş, bekledik |
| Atmosfer | 🏠 | ortam güzel, gürültülü, ferah |
| Konum/Ulaşım | 📍 | merkezi, park var, ulaşım zor |

---

## 🚀 Kullanım

### Tek Yorum Analizi:
```bash
python aspect_analyzer.py "Yemekler lezzetli personel ilgili"
```

### Veritabanından Analiz (ilk 10):
```bash
python aspect_analyzer.py --analyze-all
```

---

## 📈 Gelecek Geliştirmeler

### Faz 1: Mevcut (Rule-Based) ✅
- Anahtar kelime tabanlı konu tespiti
- Sentiment skorlama (1-10)
- Intensifier desteği (çok, aşırı, vb.)

### Faz 2: XGBoost/ML Modeli
1. 1000+ yorum topla
2. Her yorum için manuel konu etiketlemesi
3. Multi-label classification modeli eğit
4. Regresyon ile skor tahmini

### Faz 3: LLM Tabanlı
- GPT/Gemini API ile doğal dil anlama
- Zero-shot aspect extraction
- Daha doğru puanlama

---

## 💡 Streamlit Entegrasyonu (Gelecek)
- Analiz sekmesine konu bazlı filtre
- Her işletme için kategori ortalamaları
- Görsel grafikler ve karşılaştırma
