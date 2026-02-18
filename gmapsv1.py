# -*- coding: utf-8 -*-
"""
Google Maps Yorum Toplama Scripti

Kullanım:
    python gmapsv1.py
    python gmapsv1.py --headless
"""
import sys
import os
import io
import time
import argparse

# Konsol encoding sorununu çöz
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from utils import ISLETME_ADI_TAM_SORGUSU, connect_to_mysql, get_or_create_business, chrome_driver_baslat
from scraper import isletme_ara, yorumlari_yukle, devamini_oku_tikla, yorumlari_cek_ve_kaydet


def parse_business_query(query):
    """Sorguyu işletme adı, şehir ve ilçeye ayrıştırır."""
    parts = query.strip().split()
    if len(parts) < 3:
        return None, None, None
    
    business_name = " ".join(parts[:-2])
    city = parts[-2]
    district = parts[-1]
    return business_name, city, district


def main():
    """Ana fonksiyon."""
    driver = None
    db_connection = None
    start_time = time.time()
    
    try:
        business_name, city, district = parse_business_query(ISLETME_ADI_TAM_SORGUSU)
        if not business_name:
            print("HATA: Sorgu formatı 'İşletme Adı Şehir İlçe' şeklinde olmalı.")
            sys.exit(1)
        
        print(f"İşletme: '{business_name}', Şehir: '{city}', İlçe: '{district}'")
        
        driver = chrome_driver_baslat(headless=os.environ.get('HEADLESS_MODE') == 'true')
        db_connection = connect_to_mysql()
        
        if not db_connection:
            print("Veritabanı bağlantısı kurulamadı!")
            sys.exit(1)
        
        business_id = get_or_create_business(db_connection, business_name, city, district)
        if not business_id:
            print("İşletme ID'si alınamadı!")
            sys.exit(1)
        
        if not isletme_ara(driver, ISLETME_ADI_TAM_SORGUSU, business_name):
            print("İşletme araması başarısız!")
            return
        
        yorumlari_yukle(driver)
        devamini_oku_tikla(driver)
        time.sleep(2)
        
        total_added = yorumlari_cek_ve_kaydet(driver, db_connection, business_id)
        
        elapsed = time.time() - start_time
        print(f"\n{'='*50}")
        print(f"İŞLEM TAMAMLANDI!")
        print(f"İşletme ID: {business_id}")
        print(f"Eklenen yorum: {total_added}")
        print(f"Süre: {elapsed:.2f} saniye")
        print(f"{'='*50}")
        
    except Exception as e:
        print(f"Hata: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if driver:
            print("\nTarayıcı kapanıyor...")
            time.sleep(3)
            driver.quit()
        if db_connection and db_connection.is_connected():
            db_connection.close()
            print("MySQL bağlantısı kapatıldı.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Google Maps yorum toplama')
    parser.add_argument('--headless', action='store_true', help='Headless modda çalıştır')
    args = parser.parse_args()
    
    if args.headless:
        os.environ['HEADLESS_MODE'] = 'true'
    
    main()