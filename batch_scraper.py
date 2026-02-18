# -*- coding: utf-8 -*-
"""
Toplu İşletme Tarama ve Yorum Toplama Scripti

Bu script iki modda çalışır:
1. Keşif Modu: Belirli bir bölgedeki tüm işletmeleri listeler ve veritabanına kaydeder
2. Toplama Modu: Kaydedilen işletmelerin yorumlarını sırayla toplar

Kullanım:
    # Keşif modu - işletmeleri bul
    python batch_scraper.py --discover "eczane bartın merkez"
    
    # Toplama modu - bekleyen işletmelerin yorumlarını topla
    python batch_scraper.py --collect
    
    # Headless modda
    python batch_scraper.py --collect --headless
"""
import sys
import os
import io
import time
import argparse

# Konsol encoding sorununu çöz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from utils import connect_to_mysql, get_or_create_business, chrome_driver_baslat
from scraper import isletme_ara, yorumlari_yukle, devamini_oku_tikla, yorumlari_cek_ve_kaydet


def ensure_batch_tables(db_connection):
    """Toplu tarama için gerekli tabloları oluşturur."""
    cursor = db_connection.cursor()
    
    # Bekleyen işletmeler tablosu
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pending_businesses (
            id INT AUTO_INCREMENT PRIMARY KEY,
            business_type VARCHAR(255) NOT NULL,
            city VARCHAR(100) NOT NULL,
            district VARCHAR(100) NOT NULL,
            business_name VARCHAR(500) NOT NULL,
            status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            processed_at TIMESTAMP NULL,
            error_message TEXT NULL,
            UNIQUE KEY unique_business (business_type, city, district, business_name)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
    """)
    
    db_connection.commit()
    cursor.close()
    print("Tablo kontrolü tamamlandı.")


def discover_businesses(driver, search_query, db_connection):
    """
    Belirli bir sorgu ile işletmeleri keşfeder ve veritabanına kaydeder.
    
    Args:
        driver: Selenium WebDriver
        search_query: "işletme_türü şehir ilçe" formatında sorgu
        db_connection: MySQL bağlantısı
    
    Returns:
        int: Bulunan işletme sayısı
    """
    parts = search_query.strip().split()
    if len(parts) < 3:
        print("HATA: Sorgu formatı 'İşletme_Türü Şehir İlçe' şeklinde olmalı.")
        return 0
    
    business_type = " ".join(parts[:-2])
    city = parts[-2]
    district = parts[-1]
    
    print(f"Keşif başlatılıyor...")
    print(f"  İşletme Türü: '{business_type}'")
    print(f"  Şehir: '{city}'")
    print(f"  İlçe: '{district}'")
    print("=" * 60)
    
    # Google Maps'i aç
    driver.get("https://www.google.com/maps")
    time.sleep(3)
    
    try:
        # Arama yap
        search_box = WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.ID, "searchboxinput"))
        )
        search_box.clear()
        time.sleep(0.5)
        search_box.send_keys(search_query)
        time.sleep(0.5)
        search_box.send_keys(Keys.RETURN)
        
        print("Arama yapıldı, sonuçlar bekleniyor...")
        time.sleep(5)
        
        # Sonuç listesini bul
        businesses_found = []
        scroll_container = None
        
        # Sonuç listesi container'ını bul
        try:
            # Farklı seçiciler dene
            selectors = [
                "div[role='feed']",
                "div.m6QErb.DxyBCb.kA9KIf.dS8AEf",
                "div.m6QErb"
            ]
            
            for selector in selectors:
                try:
                    scroll_container = driver.find_element(By.CSS_SELECTOR, selector)
                    if scroll_container:
                        break
                except:
                    continue
            
            if not scroll_container:
                print("HATA: Sonuç listesi bulunamadı.")
                return 0
            
        except Exception as e:
            print(f"Container bulma hatası: {e}")
            return 0
        
        # Scroll yaparak tüm işletmeleri yükle
        print("İşletmeler yükleniyor (scroll)...")
        
        previous_count = 0
        no_new_count = 0
        max_no_new = 5
        
        while no_new_count < max_no_new:
            # İşletme kartlarını bul
            try:
                cards = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
                current_count = len(cards)
                
                if current_count > previous_count:
                    no_new_count = 0
                    previous_count = current_count
                    print(f"  Bulunan işletme: {current_count}")
                else:
                    no_new_count += 1
                
                # Scroll yap
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight;", 
                    scroll_container
                )
                time.sleep(2)
                
            except StaleElementReferenceException:
                time.sleep(1)
                continue
            except Exception as e:
                print(f"Scroll hatası: {e}")
                break
        
        # İşletme isimlerini çıkar
        print("\nİşletme isimleri çıkarılıyor...")
        cards = driver.find_elements(By.CSS_SELECTOR, "div.Nv2PK")
        
        for card in cards:
            try:
                # İşletme adını bul
                name_elem = card.find_element(By.CSS_SELECTOR, "div.qBF1Pd")
                business_name = name_elem.text.strip()
                
                if business_name and business_name not in businesses_found:
                    businesses_found.append(business_name)
                    
            except Exception as e:
                continue
        
        print(f"\nToplam {len(businesses_found)} benzersiz işletme bulundu.")
        
        # Veritabanına kaydet
        if businesses_found:
            cursor = db_connection.cursor()
            saved_count = 0
            
            for biz_name in businesses_found:
                try:
                    cursor.execute("""
                        INSERT IGNORE INTO pending_businesses 
                        (business_type, city, district, business_name, status)
                        VALUES (%s, %s, %s, %s, 'pending')
                    """, (business_type, city, district, biz_name))
                    
                    if cursor.rowcount > 0:
                        saved_count += 1
                        print(f"  ✓ Kaydedildi: {biz_name}")
                    else:
                        print(f"  ○ Zaten mevcut: {biz_name}")
                        
                except Exception as e:
                    print(f"  ✗ Kayıt hatası ({biz_name}): {e}")
            
            db_connection.commit()
            cursor.close()
            
            print(f"\n{saved_count} yeni işletme veritabanına kaydedildi.")
        
        return len(businesses_found)
        
    except Exception as e:
        print(f"Keşif hatası: {e}")
        import traceback
        traceback.print_exc()
        return 0


def collect_pending_reviews(driver, db_connection, limit=None):
    """
    Bekleyen işletmelerin yorumlarını toplar.
    
    Args:
        driver: Selenium WebDriver
        db_connection: MySQL bağlantısı
        limit: Maksimum işlenecek işletme sayısı (None = hepsi)
    
    Returns:
        dict: İstatistikler
    """
    cursor = db_connection.cursor(dictionary=True)
    
    # Bekleyen işletmeleri al
    query = """
        SELECT id, business_type, city, district, business_name 
        FROM pending_businesses 
        WHERE status = 'pending'
        ORDER BY created_at ASC
    """
    if limit:
        query += f" LIMIT {limit}"
    
    cursor.execute(query)
    pending = cursor.fetchall()
    
    if not pending:
        print("Bekleyen işletme bulunamadı.")
        return {'processed': 0, 'success': 0, 'failed': 0}
    
    print(f"{len(pending)} bekleyen işletme bulundu.")
    print("=" * 60)
    
    stats = {'processed': 0, 'success': 0, 'failed': 0, 'total_comments': 0}
    
    for idx, biz in enumerate(pending, 1):
        pending_id = biz['id']
        business_name = biz['business_name']
        city = biz['city']
        district = biz['district']
        
        full_query = f"{business_name} {city} {district}"
        
        print(f"\n[{idx}/{len(pending)}] İşleniyor: {business_name}")
        print(f"  Sorgu: {full_query}")
        
        # Durumu 'processing' yap
        cursor.execute(
            "UPDATE pending_businesses SET status = 'processing' WHERE id = %s",
            (pending_id,)
        )
        db_connection.commit()
        
        try:
            # İşletmeyi veritabanına ekle/bul
            business_id = get_or_create_business(db_connection, business_name, city, district)
            
            if not business_id:
                raise Exception("İşletme ID alınamadı")
            
            # İşletmeyi ara ve yorumları topla
            if isletme_ara(driver, full_query, business_name):
                yorumlari_yukle(driver)
                devamini_oku_tikla(driver)
                time.sleep(2)
                
                comments_added = yorumlari_cek_ve_kaydet(driver, db_connection, business_id)
                stats['total_comments'] += comments_added
                
                # Başarılı
                cursor.execute("""
                    UPDATE pending_businesses 
                    SET status = 'completed', processed_at = NOW()
                    WHERE id = %s
                """, (pending_id,))
                db_connection.commit()
                
                stats['success'] += 1
                print(f"  ✓ Tamamlandı! {comments_added} yorum eklendi.")
                
            else:
                raise Exception("İşletme araması başarısız")
                
        except Exception as e:
            error_msg = str(e)
            cursor.execute("""
                UPDATE pending_businesses 
                SET status = 'failed', processed_at = NOW(), error_message = %s
                WHERE id = %s
            """, (error_msg, pending_id))
            db_connection.commit()
            
            stats['failed'] += 1
            print(f"  ✗ Hata: {error_msg}")
        
        stats['processed'] += 1
        
        # Rate limiting - işletmeler arası bekleme
        if idx < len(pending):
            print("  Bir sonraki işletme için bekleniyor...")
            time.sleep(3)
    
    cursor.close()
    return stats


def show_pending_status(db_connection):
    """Bekleyen işletmelerin durumunu gösterir."""
    cursor = db_connection.cursor()
    
    cursor.execute("""
        SELECT status, COUNT(*) as cnt
        FROM pending_businesses
        GROUP BY status
    """)
    status_counts = cursor.fetchall()
    
    print("\nBekleyen İşletme Durumu:")
    print("=" * 40)
    for status, count in status_counts:
        print(f"  {status}: {count}")
    
    # Bekleyenleri listele
    cursor.execute("""
        SELECT business_type, city, district, COUNT(*) as cnt
        FROM pending_businesses
        WHERE status = 'pending'
        GROUP BY business_type, city, district
    """)
    pending_groups = cursor.fetchall()
    
    if pending_groups:
        print("\nBekleyen İşletme Grupları:")
        print("-" * 40)
        for btype, city, district, count in pending_groups:
            print(f"  {btype} - {city}/{district}: {count} işletme")
    
    # Başarısız olanları listele
    cursor.execute("""
        SELECT business_name, error_message
        FROM pending_businesses
        WHERE status = 'failed'
        LIMIT 10
    """)
    failed = cursor.fetchall()
    
    if failed:
        print("\nBaşarısız İşletmeler (ilk 10):")
        print("-" * 40)
        for biz_name, error in failed:
            print(f"  ✗ {biz_name}: {error[:50] if error else 'Bilinmeyen hata'}...")
    
    cursor.close()


def retry_failed_businesses(db_connection):
    """
    Başarısız işletmeleri tekrar deneme için pending durumuna çevirir.
    
    Args:
        db_connection: MySQL bağlantısı
    
    Returns:
        int: Tekrar denemeye alınan işletme sayısı
    """
    cursor = db_connection.cursor()
    
    # Kaç tane failed var?
    cursor.execute("SELECT COUNT(*) FROM pending_businesses WHERE status = 'failed'")
    failed_count = cursor.fetchone()[0]
    
    if failed_count == 0:
        print("Başarısız işletme bulunamadı.")
        cursor.close()
        return 0
    
    print(f"{failed_count} başarısız işletme bulundu.")
    
    # Failed olanları pending yap
    cursor.execute("""
        UPDATE pending_businesses 
        SET status = 'pending', error_message = NULL, processed_at = NULL
        WHERE status = 'failed'
    """)
    
    db_connection.commit()
    updated = cursor.rowcount
    
    print(f"✓ {updated} işletme tekrar deneme için hazırlandı.")
    cursor.close()
    
    return updated


def main():
    """Ana fonksiyon."""
    parser = argparse.ArgumentParser(description='Toplu işletme tarama ve yorum toplama')
    parser.add_argument('--discover', type=str, help='Keşif modu: "işletme_türü şehir ilçe"')
    parser.add_argument('--collect', action='store_true', help='Toplama modu: bekleyen yorumları topla')
    parser.add_argument('--status', action='store_true', help='Bekleyen işletmelerin durumunu göster')
    parser.add_argument('--retry-failed', action='store_true', help='Başarısız işletmeleri tekrar dene')
    parser.add_argument('--limit', type=int, help='Maksimum işlenecek işletme sayısı')
    parser.add_argument('--headless', action='store_true', help='Headless modda çalıştır')
    
    args = parser.parse_args()
    
    if not any([args.discover, args.collect, args.status, args.retry_failed]):
        parser.print_help()
        print("\nÖrnek kullanımlar:")
        print("  python batch_scraper.py --discover 'eczane bartın merkez'")
        print("  python batch_scraper.py --collect --limit 5")
        print("  python batch_scraper.py --retry-failed --collect")
        print("  python batch_scraper.py --status")
        return
    
    driver = None
    db_connection = None
    
    try:
        db_connection = connect_to_mysql()
        if not db_connection:
            print("Veritabanı bağlantısı kurulamadı!")
            return
        
        # Tabloları oluştur
        ensure_batch_tables(db_connection)
        
        # Sadece durum gösterme
        if args.status:
            show_pending_status(db_connection)
            return
        
        # Başarısızları tekrar dene
        if args.retry_failed:
            retry_failed_businesses(db_connection)
        
        # Headless mod
        if args.headless:
            os.environ['HEADLESS_MODE'] = 'true'
        
        # Keşif modu
        if args.discover:
            driver = chrome_driver_baslat(headless=args.headless)
            found = discover_businesses(driver, args.discover, db_connection)
            print(f"\n{'='*60}")
            print(f"KEŞİF TAMAMLANDI!")
            print(f"Bulunan işletme: {found}")
            print(f"{'='*60}")
        
        # Toplama modu
        if args.collect:
            driver = chrome_driver_baslat(headless=args.headless)
            stats = collect_pending_reviews(driver, db_connection, args.limit)
            print(f"\n{'='*60}")
            print(f"TOPLAMA TAMAMLANDI!")
            print(f"İşlenen: {stats['processed']}")
            print(f"Başarılı: {stats['success']}")
            print(f"Başarısız: {stats['failed']}")
            print(f"Toplam yorum: {stats['total_comments']}")
            print(f"{'='*60}")
        
    except Exception as e:
        print(f"Hata: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            print("\nTarayıcı kapanıyor...")
            time.sleep(2)
            driver.quit()
        if db_connection and db_connection.is_connected():
            db_connection.close()
            print("MySQL bağlantısı kapatıldı.")


if __name__ == "__main__":
    main()
