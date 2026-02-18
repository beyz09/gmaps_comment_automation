# -*- coding: utf-8 -*-
"""
Gelismis Yorum On Isleme Scripti v2

Bu script, yorumlari on isler:
1. URL ve HTML temizligi
2. Google olcut-bazli yorumlari (yorum metni olmayan) isleme
3. Yildiz bilgisini yorum metnine ekleme (model karari icin)
4. Coklu bosluk ve satir temizligi

Olcut Bazli Yorumlar:
- Bazi kullanicilar yorum yazmak yerine sadece Google'in sundugu
  olcutleri (Hizmet, Fiyat, Park yeri vb.) dolduruyor
- Bu yorumlar anlamli icerik olarak islenmeli, silinmemeli

Calistirma:
python preprocess_comments.py
"""
import re
import sys
import io

# Windows console encoding fix
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

from utils import get_db_connection

# Google Maps ölçüt kalıpları - Türkçe
# Format: (başlık, değer) çiftleri veya tek satır değerler
METRIC_PATTERNS = {
    # Hizmet türleri
    'hizmet': [
        'İçeride servis', 'Dışarıda servis', 'Paket servis', 'Self servis',
        'Masa servisi', 'Drive-through', 'Al-götür', 'Teslimat', 'Açık büfe',
        'Hizmet', 'Servis'
    ],
    # Fiyat aralığı
    'fiyat': [
        r'₺\d+-\d+', r'₺\d+', 'Kişi başı fiyat', 'Fiyat aralığı',
        'Ucuz', 'Pahalı', 'Uygun fiyat', 'Orta fiyat'
    ],
    # Bekleme süresi
    'bekleme': [
        'Beklemek gerekmiyor', 'Kısa bekleme', 'Uzun bekleme',
        'Bekleme süresi', r'\d+ dakika', 'Anında', 'Hemen'
    ],
    # Oturma alanı
    'oturma': [
        'Kapalı yemek alanı', 'Açık hava oturma alanı', 'Teras',
        'Bahçe', 'Balkon', 'İç mekan', 'Dış mekan', 'Oturma alanı türü'
    ],
    # Park yeri
    'park': [
        'Park yeri bulmak zor', 'Park yeri bulmak kolay', 'Otopark yok',
        'Otopark var', 'Ücretsiz park', 'Ücretli park', 'Vale',
        'Yol kenarı park', 'Park yeri seçenekleri', 'Park yeri'
    ],
    # Atmosfer
    'atmosfer': [
        'Rahat', 'Samimi', 'Lüks', 'Casual', 'Romantik', 'Aile dostu',
        'Kalabalık', 'Sessiz', 'Canlı', 'Atmosfer'
    ],
    # Erişilebilirlik
    'erisim': [
        'Tekerlekli sandalye', 'Engelli erişimi', 'Erişilebilirlik',
        'Çocuk dostu', 'Evcil hayvan'
    ]
}

# Yıldız puanına göre Türkçe açıklamalar
RATING_SUFFIX = {
    1: "[1 yıldız - çok kötü deneyim]",
    2: "[2 yıldız - kötü deneyim]",
    3: "[3 yıldız - orta deneyim]",
    4: "[4 yıldız - iyi deneyim]",
    5: "[5 yıldız - mükemmel deneyim]"
}

# Ölçüt tespiti için minimum kelime sayısı
# Eğer yorum metni bu kadar veya daha az kelime içeriyorsa ve 
# birden fazla ölçüt kalıbı içeriyorsa, ölçüt-bazlı olarak kabul edilir
METRIC_WORD_THRESHOLD = 15


def detect_metrics_in_text(text):
    """
    Metin içindeki Google ölçütlerini tespit eder.
    
    Returns:
        dict: Kategori -> değerler listesi
    """
    if not text:
        return {}
    
    found_metrics = {}
    
    for category, patterns in METRIC_PATTERNS.items():
        for pattern in patterns:
            # Regex pattern mı kontrol et
            if pattern.startswith('r'):
                pattern = pattern[1:]  # r prefix'ini kaldır
            
            try:
                if re.search(pattern, text, re.IGNORECASE):
                    if category not in found_metrics:
                        found_metrics[category] = []
                    # Pattern eşleşmesini bul
                    matches = re.findall(pattern, text, re.IGNORECASE)
                    for match in matches:
                        if match not in found_metrics[category]:
                            found_metrics[category].append(match)
            except re.error:
                # Regex hatası durumunda düz metin araması yap
                if pattern.lower() in text.lower():
                    if category not in found_metrics:
                        found_metrics[category] = []
                    if pattern not in found_metrics[category]:
                        found_metrics[category].append(pattern)
    
    return found_metrics


def is_metric_only_comment(text):
    """
    Yorumun ağırlıklı olarak ölçütlerden mi oluştuğunu kontrol eder.
    
    Kriterler:
    1. Metin çok kısa ve ölçüt içeriyor
    2. Satırların çoğu ölçüt formatında (başlık: değer)
    3. Az kelime ama çok ölçüt
    """
    if not text or not text.strip():
        return True
    
    # Zaten yıldız eki varsa, onu çıkararak kontrol et
    text_without_rating = re.sub(r'\[\d yıldız - .*?\]', '', text).strip()
    
    if not text_without_rating:
        return True
    
    # Kelime sayısı
    words = text_without_rating.split()
    word_count = len(words)
    
    # Ölçüleri tespit et
    found_metrics = detect_metrics_in_text(text_without_rating)
    metric_count = sum(len(v) for v in found_metrics.values())
    
    # Eğer kelime sayısı az ve ölçüt oranı yüksekse
    if word_count <= METRIC_WORD_THRESHOLD and metric_count >= 2:
        return True
    
    # Satır bazlı kontrol - her satır kısa mı?
    lines = [l.strip() for l in text_without_rating.split('\n') if l.strip()]
    short_lines = sum(1 for l in lines if len(l.split()) <= 3)
    
    if lines and len(lines) > 3 and (short_lines / len(lines)) >= 0.7:
        return True
    
    return False


def create_metric_summary(text, metrics):
    """
    Ölçütlerden anlamlı bir özet oluşturur.
    
    Örnek çıktılar:
    - "Hizmet: İçeride servis. Fiyat: ₺200-400. Park: Park yeri bulmak zor."
    - "Ortam: Kapalı yemek alanı. Bekleme: Beklemek gerekmiyor."
    """
    parts = []
    
    category_labels = {
        'hizmet': 'Hizmet',
        'fiyat': 'Fiyat',
        'bekleme': 'Bekleme',
        'oturma': 'Ortam',
        'park': 'Park',
        'atmosfer': 'Atmosfer',
        'erisim': 'Erişim'
    }
    
    for category, values in metrics.items():
        if values:
            label = category_labels.get(category, category.title())
            # Tek değer varsa sadece değeri yaz
            if len(values) == 1:
                parts.append(f"{label}: {values[0]}")
            else:
                parts.append(f"{label}: {', '.join(values)}")
    
    if parts:
        return ". ".join(parts) + "."
    return ""


def add_rating_suffix(text, rating):
    """
    Yorum metninin sonuna yıldız bilgisini ekler.
    Zaten eklenmişse tekrar eklemez.
    """
    if not rating or rating not in RATING_SUFFIX:
        return text
    
    suffix = RATING_SUFFIX[rating]
    
    # Zaten yıldız bilgisi var mı kontrol et
    if 'yıldız' in (text or '').lower() or 'yildiz' in (text or '').lower():
        return text
    
    if text and text.strip():
        return f"{text.strip()} {suffix}"
    else:
        return suffix


def is_meaningful_comment(text):
    """
    Yorumun anlamlı içerik içerip içermediğini kontrol eder.
    
    Anlamsız kabul edilen durumlar:
    - Sadece noktalama ve boşluk
    - Sadece tarih bilgisi (X gün/ay/yıl önce)
    - 5 karakterden kısa
    """
    if not text:
        return False
    
    # Yıldız bilgisini çıkar
    text_without_rating = re.sub(r'\[\d yıldız - .*?\]', '', text).strip()
    
    # Sadece noktalama ve boşluk mu?
    if re.match(r'^[\s\.,\-]*$', text_without_rating):
        return False
    
    # Sadece tarih mi? (X gün/ay/yıl önce)
    if re.match(r'^(\d+\s*)?(bir\s+)?(gün|hafta|ay|yıl)\s+önce\s*$', text_without_rating, re.IGNORECASE):
        return False
    
    # Çok kısa mı? (5 karakterden az)
    if len(text_without_rating) < 5:
        return False
    
    return True


def clean_text(text):
    """Temel metin temizliği yapar."""
    if not text:
        return ""
    
    # 1. Private Use Area (PUA) karakterlerini temizle (U+E000 - U+F8FF)
    # Bunlar Google'ın özel fontundaki ikonlar (yıldız, beğen butonu vb.)
    cleaned_chars = []
    for char in text:
        code = ord(char)
        if not (0xE000 <= code <= 0xF8FF):
            cleaned_chars.append(char)
    text = ''.join(cleaned_chars)
    
    # 2. Bozuk Unicode karakterleri temizle (Replacement Character U+FFFD)
    text = text.replace('\ufffd', '')
    text = text.replace('�', '')
    
    # 3. Diğer yaygın bozuk karakterleri temizle
    # Kontrol karakterleri (tab ve newline hariç)
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    
    # 3. Google Maps UI metinlerini temizle
    # Bunlar scraping sırasında yanlışlıkla alınmış olabilir
    ui_patterns = [
        r'\bBeğen\b',
        r'\bPaylaş\b', 
        r'\bYanıtla\b',
        r'\bDaha fazla\b',
        r'\bDevamını oku\b',
        r'\bYardımcı oldu\b',
        r'^\d+$',  # Sadece rakamlardan oluşan satırlar
        r'^[,\.\s]+$',  # Sadece noktalama ve boşluktan oluşan satırlar
    ]
    
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        clean_line = line.strip()
        # UI pattern'larından birini içeriyorsa ve kısa ise atla
        skip_line = False
        for pattern in ui_patterns:
            if re.match(pattern, clean_line, re.IGNORECASE):
                skip_line = True
                break
        if not skip_line and clean_line:
            # Satır içindeki UI metinlerini temizle
            clean_line = re.sub(r',?\s*Beğen\s*,?', '', clean_line)
            clean_line = re.sub(r',?\s*Paylaş\s*,?', '', clean_line)
            clean_line = re.sub(r',?\s*Yanıtla\s*,?', '', clean_line)
            clean_line = re.sub(r',?\s*\d+\s*,', ',', clean_line)  # Tek rakamları temizle
            cleaned_lines.append(clean_line.strip())
    
    text = '\n'.join(cleaned_lines)
    
    # 4. URL temizliği
    text = re.sub(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', '', text)
    
    # 5. HTML etiket temizliği
    text = re.sub(r'<[^>]+>', '', text)
    
    # 6. Boş değerli ölçüt pattern'larını temizle
    # "Hizmet: Atmosfer:  ." gibi anlamsız metinleri temizle
    text = re.sub(r'Hizmet:\s*Atmosfer:\s*\.?', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Atmosfer:\s*\.', '', text, flags=re.IGNORECASE)
    text = re.sub(r'Hizmet:\s*\.', '', text, flags=re.IGNORECASE)
    # Genel boş ölçüt pattern'ları: "Kategori:  ," veya "Kategori:  ."
    text = re.sub(r'\b\w+:\s*[,\.]\s*', '', text)
    # Art arda gelen ölçüt başlıkları değer olmadan: "Hizmet: Atmosfer:"
    text = re.sub(r'(\b\w+:)\s*(\b\w+:)', r'\2', text)
    
    # 7. Çoklu virgül ve noktalama temizliği
    text = re.sub(r',\s*,', ',', text)
    text = re.sub(r':\s*,', ':', text)
    text = re.sub(r',\s*\.', '.', text)
    text = re.sub(r'\.\s*\.', '.', text)
    # ",  ." veya ". ," gibi kalıntıları temizle
    text = re.sub(r',\s+\.', '.', text)
    text = re.sub(r'\.\s+,', '.', text)
    # Yıldız etiketinden önce gereksiz noktalama
    text = re.sub(r',\s*\[', ' [', text)
    text = re.sub(r'\.\s*\[', '. [', text)
    
    # 8. Çoklu boşluk temizliği
    text = re.sub(r'[ \t]+', ' ', text)
    
    # 9. Çoklu satır sonu temizliği
    text = re.sub(r'\n\s*\n', '\n', text)
    
    # 10. Baştaki ve sondaki virgül/nokta temizliği
    text = re.sub(r'^[\s,\.]+', '', text)
    text = re.sub(r'[\s,]+$', '', text)
    
    return text.strip()


def preprocess_comments():
    """Yorumları gelişmiş yöntemlerle ön işler."""
    print("=" * 60)
    print("GELİŞMİŞ YORUM ÖN İŞLEME v2")
    print("=" * 60)
    print()
    print("İşlemler:")
    print("  1. URL ve HTML temizliği")
    print("  2. Ölçüt-bazlı yorumları tespit ve işleme")
    print("  3. Yıldız bilgisi ekleme")
    print()

    conn = get_db_connection()
    if not conn:
        print("HATA: Veritabanı bağlantısı kurulamadı!")
        return False

    try:
        cursor = conn.cursor()

        # 0. Duplicate yorumları sil (aynı business_id, username, comment_text)
        print("Duplicate yorumlar kontrol ediliyor...")
        cursor.execute("""
            SELECT business_id, username, comment_text, GROUP_CONCAT(id) as ids
            FROM comments
            GROUP BY business_id, username, comment_text
            HAVING COUNT(*) > 1
        """)
        duplicates = cursor.fetchall()
        
        duplicate_deleted = 0
        for business_id, username, comment_text, ids in duplicates:
            id_list = [int(x) for x in ids.split(',')]
            keep_id = min(id_list)  # En eski ID'yi tut
            delete_ids = [x for x in id_list if x != keep_id]
            for del_id in delete_ids:
                cursor.execute("DELETE FROM comments WHERE id = %s", (del_id,))
                duplicate_deleted += 1
        
        if duplicate_deleted > 0:
            conn.commit()
            print(f"  ✓ {duplicate_deleted} duplicate yorum silindi.")
        else:
            print("  ○ Duplicate yorum bulunamadı.")

        # Tüm yorumları çek (rating dahil)
        cursor.execute("SELECT id, comment_text, rating FROM comments")
        comments = cursor.fetchall()

        stats = {
            'total': len(comments),
            'updated': 0,
            'deleted': 0,
            'metric_processed': 0,
            'rating_added': 0,
            'already_has_rating': 0,
            'meaningless_fixed': 0
        }
        
        examples = {
            'metric': [],
            'updated': []
        }

        for comment_id, original_text, rating in comments:
            text = original_text or ""
            
            # 1. Temel temizlik
            text = clean_text(text)
            
            # 2. Zaten yıldız eki var mı?
            has_rating_suffix = 'yıldız' in text.lower()
            
            # 3. Ölçüt-bazlı yorum kontrolü
            # Sadece yıldız eki olmayan kısmı kontrol et
            text_for_check = re.sub(r'\[\d yıldız - .*?\]', '', text).strip()
            
            is_metric = is_metric_only_comment(text_for_check)
            
            if is_metric and not has_rating_suffix:
                # Ölçütleri tespit et
                metrics = detect_metrics_in_text(text_for_check)
                
                if metrics:
                    # Ölçütlerden özet oluştur
                    summary = create_metric_summary(text_for_check, metrics)
                    if summary:
                        text = summary
                        stats['metric_processed'] += 1
                        if len(examples['metric']) < 3:
                            examples['metric'].append({
                                'id': comment_id,
                                'original': (original_text[:80] + '...') if original_text and len(original_text) > 80 else original_text,
                                'processed': summary[:80] + '...' if len(summary) > 80 else summary
                            })
            
            # 4. Yıldız bilgisi ekleme
            if rating and not has_rating_suffix:
                old_text = text
                text = add_rating_suffix(text, rating)
                if text != old_text:
                    stats['rating_added'] += 1
            elif has_rating_suffix:
                stats['already_has_rating'] += 1
            
            # 5. Anlamsız yorum kontrolü
            # Sadece tarih veya noktalama içeren yorumları sadece rating bilgisine dönüştür
            if not is_meaningful_comment(text) and rating:
                text = RATING_SUFFIX.get(rating, text)
                stats['meaningless_fixed'] += 1
            
            # 6. Tamamen boş mu? (rating da yoksa sil)
            final_check = re.sub(r'\[\d yıldız - .*?\]', '', text).strip()
            if not final_check and not rating:
                cursor.execute("DELETE FROM comments WHERE id = %s", (comment_id,))
                stats['deleted'] += 1
                continue
            
            # 7. Değişiklik olduysa güncelle
            if text != original_text:
                cursor.execute("UPDATE comments SET comment_text = %s WHERE id = %s", (text, comment_id))
                stats['updated'] += 1

        conn.commit()
        
        # Sonuç raporu
        print("=" * 60)
        print("İŞLEM TAMAMLANDI")
        print("=" * 60)
        print()
        print(f"Toplam yorum sayısı: {stats['total']}")
        print()
        print("Güncelleme İstatistikleri:")
        print(f"  ✓ Güncellenen yorum: {stats['updated']}")
        print(f"  ✓ Ölçüt-bazlı işlenen: {stats['metric_processed']}")
        print(f"  ✓ Yıldız bilgisi eklenen: {stats['rating_added']}")
        print(f"  ✓ Anlamsız yorum düzeltilen: {stats['meaningless_fixed']}")
        print(f"  ○ Zaten yıldız bilgisi olan: {stats['already_has_rating']}")
        print(f"  ✗ Silinen boş yorum: {stats['deleted']}")
        
        if examples['metric']:
            print()
            print("Ölçüt-Bazlı Yorum Örnekleri:")
            print("-" * 40)
            for ex in examples['metric']:
                print(f"ID: {ex['id']}")
                print(f"  Önce: {ex['original']}")
                print(f"  Sonra: {ex['processed']}")
                print()
        
        print("=" * 60)
        return True

    except Exception as e:
        print(f"HATA: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    preprocess_comments()