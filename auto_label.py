# -*- coding: utf-8 -*-
"""
Otomatik Duygu Etiketleme Scripti

Çok dilli sentiment modeli ile yorumları etiketler.
Model: tabularisai/multilingual-sentiment-analysis

Skor Hesaplama:
sentiment_score = Σ (P(sınıf) × ağırlık)
- Çok Negatif: -1.0
- Negatif: -0.5
- Nötr: 0.0
- Pozitif: +0.5
- Çok Pozitif: +1.0

Çalıştırma:
python auto_label.py
"""
from transformers import AutoTokenizer, AutoModelForSequenceClassification
import torch
import time
from utils import get_db_connection

# Model bilgileri
MODEL_NAME = "tabularisai/multilingual-sentiment-analysis"

# Sentiment haritası (5 kategori)
SENTIMENT_MAP = {
    0: "Çok Negatif",
    1: "Negatif",
    2: "Nötr",
    3: "Pozitif",
    4: "Çok Pozitif"
}

# Ağırlıklı skor hesaplama için değerler
SCORE_WEIGHTS = torch.tensor([-1.0, -0.5, 0.0, 0.5, 1.0])


def predict_sentiment(texts, tokenizer, model):
    """
    Metinler için sentiment tahminleri ve skorları hesaplar.
    
    Returns:
        List of tuples: [(kategori, skor), ...]
        - kategori: Türkçe sentiment etiketi
        - skor: -1.0 ile +1.0 arasında ağırlıklı skor
    """
    inputs = tokenizer(texts, return_tensors="pt", truncation=True, padding=True, max_length=512)
    
    with torch.no_grad():
        outputs = model(**inputs)
    
    # Softmax ile olasılıkları hesapla
    probabilities = torch.nn.functional.softmax(outputs.logits, dim=-1)
    
    # Kategori tahminleri
    predictions = torch.argmax(probabilities, dim=-1).tolist()
    
    # Ağırlıklı skor hesaplama: Σ (P(sınıf) × ağırlık)
    # Her satır için: probs[i] @ weights = weighted_score
    weighted_scores = (probabilities * SCORE_WEIGHTS).sum(dim=-1).tolist()
    
    # Skorları 4 ondalık basamağa yuvarla
    results = []
    for pred, score in zip(predictions, weighted_scores):
        results.append((SENTIMENT_MAP[pred], round(score, 4)))
    
    return results


def auto_label_comments():
    """Çok dilli sentiment modeli ile yorumları etiketler."""
    print("Otomatik etiketleme başlıyor...")
    print(f"Model: {MODEL_NAME}")
    print("Skor araligi: -1.0 (Cok Negatif) <-> +1.0 (Cok Pozitif)")
    start_time = time.time()

    # Model ve tokenizer yükle
    try:
        print("Model yükleniyor...")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
        model = AutoModelForSequenceClassification.from_pretrained(MODEL_NAME)
        print("Model başarıyla yüklendi.")
    except Exception as e:
        print(f"Model yükleme hatası: {e}")
        return False

    conn = get_db_connection()
    if not conn:
        return False

    try:
        cursor = conn.cursor()

        # Etiketlenmemiş yorumları çek
        cursor.execute("SELECT id, comment_text FROM comments WHERE sentiment IS NULL OR sentiment = ''")
        comments = cursor.fetchall()

        if not comments:
            print("Etiketlenmemiş yorum bulunamadı.")
            return True

        comment_ids = [row[0] for row in comments]
        texts = [row[1][:512] if row[1] else "" for row in comments]

        print(f"{len(texts)} yorum etiketleniyor...")

        # Batch processing (bellek yönetimi için küçük gruplar halinde)
        batch_size = 32
        labeled_count = 0

        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_ids = comment_ids[i:i + batch_size]
            
            try:
                results = predict_sentiment(batch_texts, tokenizer, model)
            except Exception as e:
                print(f"Batch etiketleme hatası (batch {i // batch_size + 1}): {e}")
                continue

            for comment_id, (sentiment, score) in zip(batch_ids, results):
                cursor.execute(
                    "UPDATE comments SET sentiment = %s, sentiment_score = %s WHERE id = %s", 
                    (sentiment, score, comment_id)
                )
                labeled_count += 1

            # İlerleme bildirimi
            if (i + batch_size) % 100 == 0 or (i + batch_size) >= len(texts):
                print(f"İlerleme: {min(i + batch_size, len(texts))}/{len(texts)} yorum işlendi")

        conn.commit()
        elapsed_time = time.time() - start_time
        print(f"Etiketleme tamamlandı: {labeled_count} yorum etiketlendi.")
        print(f"Toplam süre: {elapsed_time:.2f} saniye")
        return True

    except Exception as e:
        print(f"Etiketleme hatası: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    auto_label_comments()