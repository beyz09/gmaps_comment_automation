# -*- coding: utf-8 -*-
"""
Eğitilmiş Model ile Tahmin Yapma

Bu script, eğitilmiş modeli kullanarak yeni yorumları sınıflandırır.

Kullanım:
    python predict.py "Bu restoran harika!"
    python predict.py  # Veritabanındaki etiketsiz yorumları tahmin eder
"""
import sys
import os
import pickle
import warnings
warnings.filterwarnings('ignore')

import numpy as np
from scipy.sparse import hstack
from utils import get_db_connection


def load_model():
    """Kaydedilmiş modeli ve bileşenlerini yükler."""
    model_dir = "models"
    
    # Model
    model_files = [f for f in os.listdir(model_dir) if f.endswith('_model.pkl')]
    if not model_files:
        print("Model bulunamadı!")
        return None, None, None
    
    model_path = os.path.join(model_dir, model_files[0])
    with open(model_path, 'rb') as f:
        model = pickle.load(f)
    
    # Vectorizer
    with open(os.path.join(model_dir, 'tfidf_vectorizer.pkl'), 'rb') as f:
        vectorizer = pickle.load(f)
    
    # Label Encoder
    with open(os.path.join(model_dir, 'label_encoder.pkl'), 'rb') as f:
        label_encoder = pickle.load(f)
    
    print(f"Model yüklendi: {model_files[0]}")
    return model, vectorizer, label_encoder


def predict_single(text, rating, model, vectorizer, label_encoder):
    """Tek bir yorum için tahmin yapar."""
    # TF-IDF
    X_tfidf = vectorizer.transform([text])
    
    # Ek özellikler
    additional = np.array([[
        float(rating) if rating else 3.0,
        len(text),
        len(text.split())
    ]])
    
    # Birleştir
    X = hstack([X_tfidf, additional])
    
    # CatBoost için dense matrix gerekebilir
    if hasattr(model, 'predict') and 'catboost' in str(type(model)).lower():
        X = X.toarray()
    
    # Tahmin
    pred = model.predict(X)
    pred_label = label_encoder.inverse_transform(pred.flatten().astype(int))[0]
    
    # Olasılıklar (varsa)
    if hasattr(model, 'predict_proba'):
        proba = model.predict_proba(X)[0]
        return pred_label, dict(zip(label_encoder.classes_, proba))
    
    return pred_label, None


def predict_unlabeled_comments(model, vectorizer, label_encoder):
    """Veritabanındaki etiketsiz yorumları tahmin eder."""
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor(dictionary=True)
    
    # Etiketsiz yorumları al
    cursor.execute("""
        SELECT id, comment_text, rating
        FROM comments
        WHERE (sentiment IS NULL OR sentiment = '')
        AND comment_text IS NOT NULL AND comment_text != ''
    """)
    
    unlabeled = cursor.fetchall()
    print(f"\nEtiketsiz yorum sayısı: {len(unlabeled)}")
    
    if not unlabeled:
        print("Etiketsiz yorum bulunamadı.")
        return
    
    # Tahmin yap
    updated = 0
    for comment in unlabeled:
        try:
            pred_label, _ = predict_single(
                comment['comment_text'],
                comment['rating'],
                model, vectorizer, label_encoder
            )
            
            # Veritabanını güncelle
            cursor.execute("""
                UPDATE comments
                SET sentiment = %s
                WHERE id = %s
            """, (pred_label, comment['id']))
            
            updated += 1
            
        except Exception as e:
            print(f"Hata (ID: {comment['id']}): {e}")
    
    conn.commit()
    cursor.close()
    conn.close()
    
    print(f"✓ {updated} yorum etiketlendi.")


def main():
    # Model yükle
    model, vectorizer, label_encoder = load_model()
    if model is None:
        return
    
    # Komut satırı argümanı varsa tek tahmin yap
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
        rating = 3  # Varsayılan
        
        pred_label, proba = predict_single(text, rating, model, vectorizer, label_encoder)
        
        print(f"\nMetin: {text}")
        print(f"Tahmin: {pred_label}")
        
        if proba:
            print("\nOlasılıklar:")
            for label, prob in sorted(proba.items(), key=lambda x: -x[1]):
                print(f"  {label}: {prob:.2%}")
    
    else:
        # Etiketsiz yorumları tahmin et
        predict_unlabeled_comments(model, vectorizer, label_encoder)


if __name__ == "__main__":
    main()
