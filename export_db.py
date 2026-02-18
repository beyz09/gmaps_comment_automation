# -*- coding: utf-8 -*-
"""
Yerel MySQL veritabanını SQL dump olarak export eder.
"""
import mysql.connector
import os

# Yerel DB bağlantısı
LOCAL_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "google_maps_data_v2"
}

def export_to_sql():
    conn = mysql.connector.connect(**LOCAL_CONFIG)
    cursor = conn.cursor()
    
    output = []
    output.append("-- Google Maps DB Export\n")
    output.append("SET NAMES utf8mb4;\n\n")
    
    # businesses tablosu
    cursor.execute("SELECT * FROM businesses")
    rows = cursor.fetchall()
    cursor.execute("DESCRIBE businesses")
    cols = [c[0] for c in cursor.fetchall()]
    
    output.append(f"-- businesses tablosu: {len(rows)} kayıt\n")
    output.append("INSERT IGNORE INTO businesses (" + ", ".join(f"`{c}`" for c in cols) + ") VALUES\n")
    vals = []
    for row in rows:
        escaped = []
        for v in row:
            if v is None:
                escaped.append("NULL")
            elif isinstance(v, str):
                escaped.append("'" + v.replace("'", "\\'") + "'")
            else:
                escaped.append(str(v))
        vals.append("(" + ", ".join(escaped) + ")")
    output.append(",\n".join(vals) + ";\n\n")
    
    # comments tablosu
    cursor.execute("SELECT COUNT(*) FROM comments")
    total = cursor.fetchone()[0]
    print(f"Toplam yorum: {total}")
    
    cursor.execute("DESCRIBE comments")
    cols = [c[0] for c in cursor.fetchall()]
    
    output.append(f"-- comments tablosu: {total} kayıt\n")
    
    # Batch olarak çek
    batch_size = 500
    offset = 0
    first = True
    while offset < total:
        cursor.execute(f"SELECT * FROM comments LIMIT {batch_size} OFFSET {offset}")
        rows = cursor.fetchall()
        if not rows:
            break
        
        if first:
            output.append("INSERT IGNORE INTO comments (" + ", ".join(f"`{c}`" for c in cols) + ") VALUES\n")
            first = False
        else:
            output.append(",\n")
        
        vals = []
        for row in rows:
            escaped = []
            for v in row:
                if v is None:
                    escaped.append("NULL")
                elif isinstance(v, str):
                    escaped.append("'" + v.replace("\\", "\\\\").replace("'", "\\'") + "'")
                else:
                    escaped.append(str(v))
            vals.append("(" + ", ".join(escaped) + ")")
        output.append(",\n".join(vals))
        offset += batch_size
        print(f"{offset}/{total} yorum export edildi...")
    
    output.append(";\n")
    
    with open("db_export.sql", "w", encoding="utf-8") as f:
        f.writelines(output)
    
    print(f"\n✅ Export tamamlandı: db_export.sql")
    cursor.close()
    conn.close()

if __name__ == "__main__":
    export_to_sql()
