# -*- coding: utf-8 -*-
"""
Konu Bazlı Duygu Analizi (Aspect-Based Sentiment Analysis)

Bu script, yorumlardan konu tespiti yaparak her konu için 1-10 arası puan verir.

Kategoriler:
- Yemek Kalitesi
- Personel Tutumu
- Fiyat
- Temizlik
- Hizmet Hızı
- Atmosfer
- Konum/Ulaşım

Kullanım:
    python aspect_analyzer.py "Yemekler lezzetli, personel ilgiliydi"
    python aspect_analyzer.py --analyze-all  # Tüm yorumları analiz et
"""
import re
import sys
import json
from collections import defaultdict

# Kategori tanımları ve anahtar kelimeler
ASPECTS = {
    'yemek_kalitesi': {
        'name': 'Yemek Kalitesi',
        'icon': '🍽️',
        'positive': [
            'lezzetli', 'lezzet', 'nefis', 'muhteşem', 'harika', 'güzel yemek',
            'taze', 'enfes', 'mükemmel tat', 'başarılı', 'tat', 'damak', 
            'leziz', 'yemekler güzel', 'yemekleri güzel', 'doyurucu', 
            'porsiyon büyük', 'porsiyon dolu', 'kaliteli', 'özenli',
            'ev yapımı', 'geleneksel', 'otantik'
        ],
        'negative': [
            'lezzetsiz', 'tatsız', 'bayat', 'soğuk yemek', 'kötü yemek',
            'berbat', 'yavan', 'tuzlu', 'tuzsuz', 'yanık', 'çiğ',
            'porsiyon küçük', 'yetersiz', 'kalitesiz', 'bozuk',
            'kokmuş', 'eski', 'donmuş'
        ]
    },
    'personel_tutumu': {
        'name': 'Personel Tutumu',
        'icon': '👥',
        'positive': [
            'ilgili', 'güler yüzlü', 'nazik', 'kibar', 'yardımcı',
            'personel harika', 'çalışan', 'garson', 'saygılı', 'profesyonel',
            'sıcakkanlı', 'samimi', 'anlayışlı', 'ilgi', 'alakalı',
            'hizmet güzel', 'personel güzel', 'çalışanlar güzel'
        ],
        'negative': [
            'ilgisiz', 'kaba', 'saygısız', 'umursamaz', 'soğuk',
            'personel kötü', 'garson kötü', 'hizmet kötü', 'alakasız',
            'küstah', 'sinirli', 'sert', 'kayıtsız', 'yüzsüz'
        ]
    },
    'fiyat': {
        'name': 'Fiyat',
        'icon': '💰',
        'positive': [
            'uygun fiyat', 'ucuz', 'hesaplı', 'ekonomik', 'makul',
            'fiyat uygun', 'fiyatı uygun', 'fiyatına göre', 'değer',
            'bütçe dostu', 'cüzdan dostu', 'fiyat performans'
        ],
        'negative': [
            'pahalı', 'fahiş', 'kazık', 'aşırı fiyat', 'fiyat yüksek',
            'değmez', 'para tuzağı', 'fiyatına değmez', 'çok pahalı',
            'hesap yüksek', 'fiyat/performans kötü'
        ]
    },
    'temizlik': {
        'name': 'Temizlik',
        'icon': '🧹',
        'positive': [
            'temiz', 'hijyenik', 'tertemiz', 'pırıl pırıl', 'bakımlı',
            'düzenli', 'steril', 'hijyen', 'temizlik güzel'
        ],
        'negative': [
            'pis', 'kirli', 'hijyensiz', 'bakımsız', 'dağınık',
            'kir', 'leş', 'iğrenç', 'temiz değil', 'berbat ortam'
        ]
    },
    'hizmet_hizi': {
        'name': 'Hizmet Hızı',
        'icon': '⏱️',
        'positive': [
            'hızlı', 'çabuk', 'anında', 'bekletmedi', 'hemen geldi',
            'süratli', 'dakik', 'zamanında', 'gecikmesiz'
        ],
        'negative': [
            'yavaş', 'geç', 'beklettiler', 'uzun sürdü', 'gecikmeli',
            'bekledik', 'yarım saat', 'bir saat', 'çok bekledik',
            'sipariş geç', 'servis yavaş'
        ]
    },
    'atmosfer': {
        'name': 'Atmosfer',
        'icon': '🏠',
        'positive': [
            'ortam güzel', 'ambiyans', 'dekor', 'şık', 'ferah',
            'rahat', 'huzurlu', 'keyifli', 'romantik', 'samimi ortam',
            'müzik güzel', 'manzara', 'dekorasyon', 'tasarım'
        ],
        'negative': [
            'gürültülü', 'kalabalık', 'bunaltıcı', 'sıkışık', 'karanlık',
            'kasvetli', 'soğuk ortam', 'rahatsız', 'dar', 'havasız',
            'müzik kötü', 'gürültü', 'ses'
        ]
    },
    'konum': {
        'name': 'Konum/Ulaşım',
        'icon': '📍',
        'positive': [
            'merkezi', 'kolay ulaşım', 'park var', 'otopark', 'konumu güzel',
            'ulaşım kolay', 'merkez', 'bulunabilir', 'erişilebilir'
        ],
        'negative': [
            'park yok', 'otopark yok', 'ulaşım zor', 'uzak', 'köşe bucak',
            'zor bulunur', 'park sorunu', 'konum kötü'
        ]
    }
}

# Sentiment ağırlıklandırma kelimeleri
INTENSIFIERS = {
    'çok': 1.3,
    'aşırı': 1.4,
    'son derece': 1.5,
    'oldukça': 1.2,
    'gayet': 1.1,
    'bayağı': 1.2,
    'gerçekten': 1.3,
    'kesinlikle': 1.4,
    'muhteşem': 1.5,
    'harika': 1.4
}

NEGATIONS = ['değil', 'yok', 'olmadı', 'yoktu', 'olmuyor', 'olmaz', 'hiç']


def normalize_turkish(text):
    """Türkçe karakterleri ASCII'ye çevirir (eşleştirme için)."""
    replacements = {
        'ğ': 'g', 'Ğ': 'G',
        'ü': 'u', 'Ü': 'U',
        'ş': 's', 'Ş': 'S',
        'ı': 'i', 'İ': 'I',
        'ö': 'o', 'Ö': 'O',
        'ç': 'c', 'Ç': 'C'
    }
    for tr, en in replacements.items():
        text = text.replace(tr, en)
    return text


def preprocess_text(text):
    """Metni küçük harfe çevirir ve temizler."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'[^\w\sğüşıöçĞÜŞİÖÇ]', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def detect_aspects(text):
    """
    Metinde hangi konulardan bahsedildiğini tespit eder.
    
    Returns:
        dict: {aspect_key: {'mentioned': bool, 'sentiment': 'positive'/'negative'/'neutral', 'score': 1-10}}
    """
    text_lower = preprocess_text(text)
    text_normalized = normalize_turkish(text_lower)  # ASCII versiyonu da kontrol et
    results = {}
    
    for aspect_key, aspect_data in ASPECTS.items():
        positive_matches = []
        negative_matches = []
        
        # Pozitif eşleşmeler
        for keyword in aspect_data['positive']:
            keyword_lower = keyword.lower()
            keyword_normalized = normalize_turkish(keyword_lower)
            # Hem orijinal hem normalized kontrol
            if keyword_lower in text_lower or keyword_normalized in text_normalized:
                positive_matches.append(keyword)
        
        # Negatif eşleşmeler
        for keyword in aspect_data['negative']:
            keyword_lower = keyword.lower()
            keyword_normalized = normalize_turkish(keyword_lower)
            if keyword_lower in text_lower or keyword_normalized in text_normalized:
                negative_matches.append(keyword)
        
        # Konu bahsedilmiş mi?
        if positive_matches or negative_matches:
            # Negation kontrolü
            has_negation = any(neg in text_lower for neg in NEGATIONS)
            
            # Intensifier kontrolü
            intensity = 1.0
            for intensifier, weight in INTENSIFIERS.items():
                if intensifier in text_lower:
                    intensity = max(intensity, weight)
            
            # Sentiment ve skor hesaplama
            pos_count = len(positive_matches)
            neg_count = len(negative_matches)
            
            if has_negation:
                # Negation varsa sentiment'ı tersine çevir
                pos_count, neg_count = neg_count, pos_count
            
            if pos_count > neg_count:
                sentiment = 'positive'
                base_score = 7 + min(pos_count, 3)  # 7-10 arası
            elif neg_count > pos_count:
                sentiment = 'negative'
                base_score = 4 - min(neg_count, 3)  # 1-4 arası
            else:
                sentiment = 'neutral'
                base_score = 5
            
            # Intensifier uygula
            if sentiment == 'positive':
                score = min(10, base_score * intensity)
            elif sentiment == 'negative':
                score = max(1, base_score / intensity)
            else:
                score = base_score
            
            results[aspect_key] = {
                'name': aspect_data['name'],
                'icon': aspect_data['icon'],
                'mentioned': True,
                'sentiment': sentiment,
                'score': round(score, 1),
                'keywords_found': positive_matches + negative_matches
            }
    
    return results


def analyze_comment(text, rating=None):
    """
    Bir yorumu analiz eder ve konu bazlı puanlar döndürür.
    
    Args:
        text: Yorum metni
        rating: Opsiyonel yıldız puanı (1-5)
    
    Returns:
        dict: Analiz sonuçları
    """
    aspects = detect_aspects(text)
    
    # Rating bilgisi varsa skorları ayarla
    if rating:
        rating_factor = rating / 5.0  # 0.2 - 1.0 arası
        for aspect_key, data in aspects.items():
            # Rating ile uyumlu hale getir
            if data['sentiment'] == 'positive':
                data['score'] = min(10, data['score'] * (0.7 + 0.3 * rating_factor))
            elif data['sentiment'] == 'negative':
                data['score'] = max(1, data['score'] * (1.3 - 0.3 * rating_factor))
            data['score'] = round(data['score'], 1)
    
    return {
        'text': text,
        'rating': rating,
        'aspects': aspects,
        'aspect_count': len(aspects)
    }


def format_results(analysis):
    """Analiz sonuçlarını formatlar."""
    output = []
    output.append("=" * 50)
    output.append("KONU BAZLI ANALİZ SONUÇLARI")
    output.append("=" * 50)
    
    if analysis.get('rating'):
        output.append(f"Yıldız: {'⭐' * analysis['rating']}")
    
    output.append(f"\nTespit Edilen Konu Sayısı: {analysis['aspect_count']}")
    output.append("-" * 50)
    
    if analysis['aspects']:
        for aspect_key, data in analysis['aspects'].items():
            sentiment_emoji = '✅' if data['sentiment'] == 'positive' else ('❌' if data['sentiment'] == 'negative' else '➖')
            score_bar = '█' * int(data['score']) + '░' * (10 - int(data['score']))
            output.append(f"{data['icon']} {data['name']}: {data['score']}/10 [{score_bar}] {sentiment_emoji}")
            output.append(f"   Bulunan: {', '.join(data['keywords_found'][:3])}")
    else:
        output.append("❓ Hiçbir konu tespit edilemedi.")
    
    output.append("=" * 50)
    return "\n".join(output)


def main():
    """Ana fonksiyon."""
    if len(sys.argv) > 1:
        if sys.argv[1] == '--analyze-all':
            # Tüm yorumları analiz et
            from utils import get_db_connection
            
            conn = get_db_connection()
            if not conn:
                print("Veritabanı bağlantısı kurulamadı!")
                return
            
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT id, comment_text, rating
                FROM comments
                WHERE comment_text IS NOT NULL AND comment_text != ''
                LIMIT 10
            """)
            
            comments = cursor.fetchall()
            
            for comment in comments:
                print(f"\n{'#' * 60}")
                print(f"ID: {comment['id']}")
                print(f"Yorum: {comment['comment_text'][:100]}...")
                
                analysis = analyze_comment(comment['comment_text'], comment['rating'])
                print(format_results(analysis))
            
            cursor.close()
            conn.close()
        else:
            # Tek yorum analizi
            text = " ".join(sys.argv[1:])
            analysis = analyze_comment(text)
            print(f"\nYorum: {text}")
            print(format_results(analysis))
    else:
        # Örnek kullanım
        examples = [
            "Yemekler çok lezzetliydi, personel ilgiliydi, kesinlikle tavsiye ederim",
            "Fiyatlar çok pahalı ama ortam güzeldi",
            "Servis çok yavaştı, bir saat bekledik. Yemekler soğuk geldi.",
            "Temiz ve hijyenik bir yer. Konum merkezi, park yeri var.",
            "Berbat bir deneyimdi. Personel kaba, yemekler tatsız."
        ]
        
        for text in examples:
            print(f"\n{'#' * 60}")
            print(f"Yorum: {text}")
            analysis = analyze_comment(text)
            print(format_results(analysis))


if __name__ == "__main__":
    main()
