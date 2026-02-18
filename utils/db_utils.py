# -*- coding: utf-8 -*-
"""
Veritabanı işlemleri modülü.
MySQL bağlantısı ve CRUD operasyonları.
"""
import mysql.connector
from mysql.connector import Error
from .config import DB_CONFIG


def get_db_connection(silent=False):
    """
    Veritabanı bağlantısı kurar.
    
    Args:
        silent: True ise hata mesajı yazdırmaz (Streamlit için)
    
    Returns:
        MySQL connection veya None
    """
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        if conn.is_connected():
            return conn
        return None
    except Error as e:
        if not silent:
            print(f"Veritabanı bağlantı hatası: {e}")
        return None


def connect_to_mysql():
    """MySQL veritabanına bağlanır (geriye uyumluluk için)."""
    conn = get_db_connection()
    if conn:
        print("MySQL veritabanına başarıyla bağlanıldı.")
    return conn


def get_or_create_business(db_connection, business_name, city, district):
    """İşletmeyi veritabanına ekler veya mevcutsa ID'sini döndürür."""
    cursor = db_connection.cursor()
    
    sql = "SELECT id FROM businesses WHERE name = %s AND city = %s AND district = %s"
    cursor.execute(sql, (business_name, city, district))
    result = cursor.fetchone()
    
    if result:
        print(f"İşletme '{business_name}' veritabanında bulundu. ID: {result[0]}")
        return result[0]
    else:
        sql = "INSERT INTO businesses (name, city, district) VALUES (%s, %s, %s)"
        try:
            cursor.execute(sql, (business_name, city, district))
            db_connection.commit()
            business_id = cursor.lastrowid
            print(f"İşletme '{business_name}' veritabanına eklendi. Yeni ID: {business_id}")
            return business_id
        except mysql.connector.Error as err:
            print(f"İşletme veritabanına eklenirken hata: {err}")
            db_connection.rollback()
            return None


def save_comments_batch(db_connection, comments_to_insert):
    """Yorumları toplu olarak veritabanına kaydeder."""
    if not comments_to_insert:
        return 0
    
    cursor = db_connection.cursor()
    try:
        sql = "INSERT INTO comments (business_id, username, rating, date, comment_text, likes) VALUES (%s, %s, %s, %s, %s, %s)"
        cursor.executemany(sql, comments_to_insert)
        db_connection.commit()
        print(f"Batch insert tamamlandı: {len(comments_to_insert)} yorum veritabanına eklendi.")
        return len(comments_to_insert)
    except mysql.connector.Error as err:
        print(f"Batch insert hatası: {err}")
        db_connection.rollback()
        return 0


def get_existing_comment_signatures(db_connection, business_id):
    """Mevcut yorumların imzalarını (username, rating, text) döndürür."""
    cursor = db_connection.cursor()
    sql = "SELECT username, rating, comment_text FROM comments WHERE business_id = %s"
    cursor.execute(sql, (business_id,))
    
    signatures = set()
    for row in cursor.fetchall():
        signatures.add((row[0], row[1], row[2]))
    
    return signatures


def get_business_list(db_connection):
    """Veritabanındaki tüm işletme isimlerini döndürür."""
    cursor = db_connection.cursor()
    cursor.execute("SELECT DISTINCT name FROM businesses")
    businesses = [row[0] for row in cursor.fetchall()]
    cursor.close()
    return businesses
