# -*- coding: utf-8 -*-
"""
XGBoost/CatBoost Sentiment Sınıflandırma Model Eğitimi

Bu script, etiketlenmiş yorumları kullanarak bir sentiment sınıflandırma modeli eğitir.

Kullanım:
    python train_model.py

Gerekli kütüphaneler:
    pip install xgboost catboost scikit-learn pandas numpy
"""
import sys
import os
import pickle
import warnings
warnings.filterwarnings('ignore')

import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score, StratifiedKFold
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score
from sklearn.utils.class_weight import compute_class_weight

# XGBoost
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    print("XGBoost yüklü değil. Yüklemek için: pip install xgboost")

# CatBoost
try:
    from catboost import CatBoostClassifier
    CATBOOST_AVAILABLE = True
except ImportError:
    CATBOOST_AVAILABLE = False
    print("CatBoost yüklü değil. Yüklemek için: pip install catboost")

from utils import get_db_connection


def load_labeled_data():
    """Veritabanından etiketlenmiş verileri yükler."""
    conn = get_db_connection()
    if not conn:
        print("Veritabanı bağlantısı kurulamadı!")
        return None
    
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT comment_text, rating, sentiment
        FROM comments
        WHERE sentiment IS NOT NULL AND sentiment != ''
        AND comment_text IS NOT NULL AND comment_text != ''
    """)
    
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    
    df = pd.DataFrame(rows)
    print(f"Yüklenen veri sayısı: {len(df)}")
    
    return df


def preprocess_data(df):
    """Veriyi model eğitimi için hazırlar."""
    # Boş değerleri temizle
    df = df.dropna(subset=['comment_text', 'sentiment'])
    df = df[df['comment_text'].str.strip() != '']
    
    # Sınıf dağılımını göster
    print("\nSınıf Dağılımı:")
    print(df['sentiment'].value_counts())
    
    return df


def create_features(df):
    """
    TF-IDF ve ek özellikler oluşturur.
    
    Returns:
        X: Özellik matrisi
        y: Hedef değişken
        vectorizer: TF-IDF vectorizer (kaydetmek için)
        label_encoder: Label encoder (kaydetmek için)
    """
    # TF-IDF vektörizasyonu
    vectorizer = TfidfVectorizer(
        max_features=5000,
        ngram_range=(1, 2),  # Unigram ve bigram
        min_df=2,
        max_df=0.95,
        sublinear_tf=True
    )
    
    X_tfidf = vectorizer.fit_transform(df['comment_text'])
    
    # Ek özellikler: rating, metin uzunluğu
    additional_features = pd.DataFrame({
        'rating': df['rating'].fillna(3).astype(float),
        'text_length': df['comment_text'].str.len(),
        'word_count': df['comment_text'].str.split().str.len()
    })
    
    # TF-IDF ve ek özellikleri birleştir
    from scipy.sparse import hstack
    X = hstack([X_tfidf, additional_features.values])
    
    # Label encoding
    label_encoder = LabelEncoder()
    y = label_encoder.fit_transform(df['sentiment'])
    
    print(f"\nÖzellik matrisi boyutu: {X.shape}")
    print(f"Sınıflar: {label_encoder.classes_}")
    
    return X, y, vectorizer, label_encoder


def train_xgboost(X_train, X_test, y_train, y_test, label_encoder):
    """XGBoost modeli eğitir."""
    if not XGBOOST_AVAILABLE:
        print("XGBoost yüklü değil!")
        return None, 0
    
    print("\n" + "=" * 60)
    print("XGBoost Eğitimi Başlıyor...")
    print("=" * 60)
    
    # Sınıf ağırlıklarını hesapla (dengesiz veri için)
    classes = np.unique(y_train)
    class_weights = compute_class_weight('balanced', classes=classes, y=y_train)
    sample_weights = np.array([class_weights[c] for c in y_train])
    
    # Model parametreleri
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        objective='multi:softmax',
        num_class=len(label_encoder.classes_),
        use_label_encoder=False,
        eval_metric='mlogloss',
        random_state=42,
        n_jobs=-1
    )
    
    # Eğitim
    model.fit(
        X_train, y_train,
        sample_weight=sample_weights,
        eval_set=[(X_test, y_test)],
        verbose=False
    )
    
    # Tahmin
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\nXGBoost Doğruluk: {accuracy:.4f}")
    print("\nSınıflandırma Raporu:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))
    
    print("\nKarışıklık Matrisi:")
    print(confusion_matrix(y_test, y_pred))
    
    return model, accuracy


def train_catboost(X_train, X_test, y_train, y_test, label_encoder):
    """CatBoost modeli eğitir."""
    if not CATBOOST_AVAILABLE:
        print("CatBoost yüklü değil!")
        return None, 0
    
    print("\n" + "=" * 60)
    print("CatBoost Eğitimi Başlıyor...")
    print("=" * 60)
    
    # Sparse matrix'i dense'e çevir (CatBoost için)
    X_train_dense = X_train.toarray() if hasattr(X_train, 'toarray') else X_train
    X_test_dense = X_test.toarray() if hasattr(X_test, 'toarray') else X_test
    
    # Model
    model = CatBoostClassifier(
        iterations=200,
        depth=6,
        learning_rate=0.1,
        loss_function='MultiClass',
        auto_class_weights='Balanced',
        random_state=42,
        verbose=False
    )
    
    # Eğitim
    model.fit(X_train_dense, y_train, eval_set=(X_test_dense, y_test))
    
    # Tahmin
    y_pred = model.predict(X_test_dense)
    accuracy = accuracy_score(y_test, y_pred)
    
    print(f"\nCatBoost Doğruluk: {accuracy:.4f}")
    print("\nSınıflandırma Raporu:")
    print(classification_report(y_test, y_pred, target_names=label_encoder.classes_))
    
    return model, accuracy


def save_model(model, vectorizer, label_encoder, model_name):
    """Modeli ve gerekli bileşenleri kaydeder."""
    model_dir = "models"
    os.makedirs(model_dir, exist_ok=True)
    
    # Model
    model_path = os.path.join(model_dir, f"{model_name}_model.pkl")
    with open(model_path, 'wb') as f:
        pickle.dump(model, f)
    
    # Vectorizer
    vectorizer_path = os.path.join(model_dir, "tfidf_vectorizer.pkl")
    with open(vectorizer_path, 'wb') as f:
        pickle.dump(vectorizer, f)
    
    # Label Encoder
    encoder_path = os.path.join(model_dir, "label_encoder.pkl")
    with open(encoder_path, 'wb') as f:
        pickle.dump(label_encoder, f)
    
    print(f"\nModel kaydedildi: {model_path}")
    print(f"Vectorizer kaydedildi: {vectorizer_path}")
    print(f"Encoder kaydedildi: {encoder_path}")


def main():
    """Ana fonksiyon."""
    print("=" * 60)
    print("SENTIMENT SINIFLANDIRMA MODEL EĞİTİMİ")
    print("=" * 60)
    
    # Veri yükleme
    df = load_labeled_data()
    if df is None or len(df) == 0:
        print("Veri yüklenemedi!")
        return
    
    # Ön işleme
    df = preprocess_data(df)
    
    # Minimum veri kontrolü
    min_samples = 100
    if len(df) < min_samples:
        print(f"\nUYARI: Veri sayısı ({len(df)}) çok az. En az {min_samples} olmalı.")
        print("Daha fazla yorum toplayıp etiketlemeniz önerilir.")
        proceed = input("Yine de devam etmek istiyor musunuz? (e/h): ")
        if proceed.lower() != 'e':
            return
    
    # Özellik çıkarımı
    X, y, vectorizer, label_encoder = create_features(df)
    
    # Train/Test bölümü
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    
    print(f"\nEğitim seti: {X_train.shape[0]} örnek")
    print(f"Test seti: {X_test.shape[0]} örnek")
    
    # Model eğitimi
    best_model = None
    best_accuracy = 0
    best_name = ""
    
    # XGBoost
    if XGBOOST_AVAILABLE:
        xgb_model, xgb_acc = train_xgboost(X_train, X_test, y_train, y_test, label_encoder)
        if xgb_acc > best_accuracy:
            best_model = xgb_model
            best_accuracy = xgb_acc
            best_name = "xgboost"
    
    # CatBoost
    if CATBOOST_AVAILABLE:
        cat_model, cat_acc = train_catboost(X_train, X_test, y_train, y_test, label_encoder)
        if cat_acc > best_accuracy:
            best_model = cat_model
            best_accuracy = cat_acc
            best_name = "catboost"
    
    # En iyi modeli kaydet
    if best_model is not None:
        print("\n" + "=" * 60)
        print(f"EN İYİ MODEL: {best_name.upper()}")
        print(f"DOĞRULUK: {best_accuracy:.4f}")
        print("=" * 60)
        
        save_model(best_model, vectorizer, label_encoder, best_name)
    else:
        print("Hiçbir model eğitilemedi!")


if __name__ == "__main__":
    main()
