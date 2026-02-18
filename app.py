# -*- coding: utf-8 -*-
"""
Google Maps Yorum Yönetimi - Streamlit Uygulaması

Çalıştırma:
streamlit run app.py
"""
import streamlit as st
import subprocess
import sys
import os
import pandas as pd
from mysql.connector import Error
from utils import get_db_connection, get_business_list

# Tablo adı
TABLE_NAME = 'comments'

# Ana uygulama
st.set_page_config(page_title="Google Maps Yorum Yönetimi", layout="wide")
st.title("Google Maps Yorum Toplama ve Etiketleme")

# Sekmeler
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📥 Yorum Topla", "🔍 Toplu Tarama", "🧹 Ön İşleme", "🏷️ Etiketle", "📊 Analiz"])

# Sekme 1: Yorum Topla (Tekli)
with tab1:
    st.header("Google Maps'ten Yorum Toplama")
    st.write("Belirtilen **tek işletme** için yorumları otomatik olarak toplar.")
    st.error("""
    🚫 **Bu özellik demo ortamında çalıştırılamamaktadır.**
    
    Scraping özelliği, sunucu ortamında Google Maps'in bot kısıtlamaları nedeniyle çalışmamaktadır.
    
    Bu özelliği test etmek için projeyi yerel bilgisayarınıza kurabilirsiniz:
    👉 [GitHub Reposu](https://github.com/beyz09/gmaps_comment_automation)
    """)
    st.info("💡 **Analiz** sekmesinden mevcut verilerle analizleri inceleyebilirsiniz.")

# Sekme 2: Toplu Tarama
with tab2:
    st.header("Toplu İşletme Tarama")
    st.write("Belirli bir bölgedeki tüm işletmeleri tarar ve yorumlarını toplar.")
    st.error("""
    🚫 **Bu özellik demo ortamında çalıştırılamamaktadır.**
    
    Scraping özelliği, sunucu ortamında Google Maps'in bot kısıtlamaları nedeniyle çalışmamaktadır.
    
    Bu özelliği test etmek için projeyi yerel bilgisayarınıza kurabilirsiniz:
    👉 [GitHub Reposu](https://github.com/beyz09/gmaps_comment_automation)
    """)
    st.info("💡 **Analiz** sekmesinden mevcut verilerle analizleri inceleyebilirsiniz.")

    
    st.subheader("1️⃣ İşletme Keşfi")
    st.write("Önce işletmeleri bulup veritabanına kaydedin.")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        isletme_turu = st.text_input("İşletme Türü", "eczane", key="batch_type")
    with col2:
        sehir = st.text_input("Şehir", "bartın", key="batch_city")
    with col3:
        ilce = st.text_input("İlçe", "merkez", key="batch_district")
    
    batch_headless = st.checkbox("Headless Mod", value=False, key="batch_headless")
    
    if st.button("🔍 İşletmeleri Keşfet", type="primary", key="batch_discover"):
        search_query = f"{isletme_turu} {sehir} {ilce}"
        with st.spinner(f"'{search_query}' için işletmeler aranıyor..."):
            try:
                cmd = [sys.executable, "batch_scraper.py", "--discover", search_query]
                if batch_headless:
                    cmd.append("--headless")
                
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        cwd=os.path.dirname(os.path.abspath(__file__)),
                                        encoding='utf-8', errors='replace')
                
                st.subheader("Keşif Sonucu:")
                if result.stdout:
                    st.text_area("Çıktı", result.stdout, height=300)
                if result.stderr:
                    st.error("Hata:")
                    st.text_area("Hata Detayı", result.stderr, height=200)
                
                if result.returncode == 0:
                    st.success("Keşif tamamlandı! İşletmeler veritabanına kaydedildi.")
                else:
                    st.error(f"Keşif başarısız. Çıkış kodu: {result.returncode}")
                    
            except Exception as e:
                st.error(f"Hata: {e}")
    
    st.divider()
    
    st.subheader("2️⃣ Yorum Toplama")
    st.write("Kaydedilen işletmelerin yorumlarını sırayla toplar.")
    
    limit = st.number_input("Maksimum İşletme Sayısı (0 = hepsi)", min_value=0, value=5, key="batch_limit")
    
    if st.button("📥 Yorumları Topla", type="primary", key="batch_collect"):
        with st.spinner("Bekleyen işletmelerin yorumları toplanıyor..."):
            try:
                cmd = [sys.executable, "batch_scraper.py", "--collect"]
                if limit > 0:
                    cmd.extend(["--limit", str(limit)])
                if batch_headless:
                    cmd.append("--headless")
                
                result = subprocess.run(cmd, capture_output=True, text=True,
                                        cwd=os.path.dirname(os.path.abspath(__file__)),
                                        encoding='utf-8', errors='replace',
                                        timeout=1800)  # 30 dakika timeout
                
                st.subheader("Toplama Sonucu:")
                if result.stdout:
                    st.text_area("Çıktı", result.stdout, height=400)
                if result.stderr:
                    st.error("Hata:")
                    st.text_area("Hata Detayı", result.stderr, height=200)
                
                if result.returncode == 0:
                    st.success("Yorum toplama tamamlandı!")
                else:
                    st.error(f"Toplama başarısız. Çıkış kodu: {result.returncode}")
                    
            except subprocess.TimeoutExpired:
                st.warning("İşlem zaman aşımına uğradı (30 dakika). Kalan işletmeler için tekrar çalıştırın.")
            except Exception as e:
                st.error(f"Hata: {e}")
    
    st.divider()
    
    st.subheader("📊 Durum")
    col_status1, col_status2 = st.columns([2, 1])
    
    with col_status1:
        if st.button("🔄 Durumu Güncelle", key="batch_status"):
            try:
                conn = get_db_connection(silent=True)
                if conn:
                    cursor = conn.cursor(dictionary=True)
                    
                    # Tablo var mı kontrol et
                    cursor.execute("SHOW TABLES LIKE 'pending_businesses'")
                    if cursor.fetchone():
                        cursor.execute("""
                            SELECT status, COUNT(*) as cnt
                            FROM pending_businesses
                            GROUP BY status
                        """)
                        status_data = cursor.fetchall()
                        
                        if status_data:
                            col1, col2, col3, col4 = st.columns(4)
                            for item in status_data:
                                status = item['status']
                                cnt = item['cnt']
                                if status == 'pending':
                                    col1.metric("⏳ Bekleyen", cnt)
                                elif status == 'processing':
                                    col2.metric("🔄 İşleniyor", cnt)
                                elif status == 'completed':
                                    col3.metric("✅ Tamamlanan", cnt)
                                elif status == 'failed':
                                    col4.metric("❌ Başarısız", cnt)
                        else:
                            st.info("Henüz bekleyen işletme yok. Önce keşif yapın.")
                    else:
                        st.info("Henüz toplu tarama yapılmamış.")
                    
                    cursor.close()
                    conn.close()
                else:
                    st.error("Veritabanı bağlantısı kurulamadı.")
            except Exception as e:
                st.error(f"Durum kontrol hatası: {e}")
    
    with col_status2:
        if st.button("🔁 Başarısızları Tekrar Dene", key="batch_retry"):
            with st.spinner("Başarısız işletmeler tekrar deneme için hazırlanıyor..."):
                try:
                    cmd = [sys.executable, "batch_scraper.py", "--retry-failed"]
                    result = subprocess.run(cmd, capture_output=True, text=True,
                                            cwd=os.path.dirname(os.path.abspath(__file__)),
                                            encoding='utf-8', errors='replace')
                    
                    if result.stdout:
                        st.text_area("Sonuç", result.stdout, height=100)
                    
                    if result.returncode == 0:
                        st.success("Başarısız işletmeler tekrar deneme için hazır!")
                        st.info("Şimdi 'Yorumları Topla' butonuna tıklayarak tekrar deneyin.")
                    else:
                        st.error("İşlem başarısız!")
                except Exception as e:
                    st.error(f"Hata: {e}")

# Sekme 3: Ön İşleme
with tab3:
    st.header("Yorum Ön İşleme")
    st.write("Boş yorumları veritabanından siler.")

    if st.button("🧹 Ön İşlemeyi Başlat", type="primary"):
        with st.spinner("Ön işleme yapılıyor..."):
            try:
                result = subprocess.run([sys.executable, "preprocess_comments.py"],
                                      capture_output=True, text=True, 
                                      cwd=os.path.dirname(os.path.abspath(__file__)))

                st.subheader("Ön İşleme Çıktısı:")
                if result.stdout:
                    st.text_area("Standart Çıktı", result.stdout, height=200)
                if result.stderr:
                    st.error("Hata Çıktısı:")
                    st.text_area("Hata", result.stderr, height=200)

                if result.returncode == 0:
                    st.success("Ön işleme tamamlandı!")
                else:
                    st.error(f"Ön işleme başarısız. Çıkış kodu: {result.returncode}")

            except Exception as e:
                st.error(f"Hata: {e}")

# Sekme 4: Etiketle
with tab4:
    st.header("Otomatik Duygu Etiketleme")
    st.write("Hazır Türkçe sentiment modeli ile yorumları etiketler.")

    if st.button("🏷️ Etiketlemeyi Başlat", type="primary"):
        with st.spinner("Etiketleme yapılıyor... Bu işlem biraz sürebilir."):
            try:
                result = subprocess.run([sys.executable, "auto_label.py"],
                                      capture_output=True, text=True, 
                                      cwd=os.path.dirname(os.path.abspath(__file__)))

                st.subheader("Etiketleme Çıktısı:")
                if result.stdout:
                    st.text_area("Standart Çıktı", result.stdout, height=300)
                if result.stderr:
                    st.error("Hata Çıktısı:")
                    st.text_area("Hata", result.stderr, height=200)

                if result.returncode == 0:
                    st.success("Etiketleme tamamlandı!")
                else:
                    st.error(f"Etiketleme başarısız. Çıkış kodu: {result.returncode}")

            except Exception as e:
                st.error(f"Hata: {e}")

# Sekme 5: Analiz
with tab5:
    st.header("İşletme Analizi")
    st.write("İşletmeleri seçerek detaylı analizlere bakın.")

    conn = get_db_connection(silent=True)
    if conn:
        try:
            businesses = get_business_list(conn)
            if businesses:
                # İşletme seçimi
                selected_business = st.selectbox("İşletme Seçin", businesses)
                
                # Kullanıcı arama alanı
                st.subheader("🔍 Kullanıcı Yorum Arama")
                search_user = st.text_input("Kullanıcı Adı Ara (boş bırakırsanız tüm yorumlar gösterilir)")
                
                # Analiz butonu
                if st.button("📊 Analiz Et"):
                    cursor = conn.cursor(dictionary=True)
                    
                    # Kullanıcı adı filtreli sorgu
                    if search_user and search_user.strip():
                        cursor.execute("""
                            SELECT c.username, c.rating, c.date, c.comment_text, 
                                   COALESCE(c.sentiment, 'Etiketsiz') as sentiment, 
                                   c.likes
                            FROM comments c
                            JOIN businesses b ON c.business_id = b.id
                            WHERE b.name = %s
                            AND c.username LIKE %s
                            ORDER BY c.rating DESC, c.id DESC
                        """, (selected_business, f"%{search_user.strip()}%"))
                    else:
                        cursor.execute("""
                            SELECT c.username, c.rating, c.date, c.comment_text, 
                                   COALESCE(c.sentiment, 'Etiketsiz') as sentiment, 
                                   c.likes
                            FROM comments c
                            JOIN businesses b ON c.business_id = b.id
                            WHERE b.name = %s
                            ORDER BY c.rating DESC, c.id DESC
                        """, (selected_business,))
                    
                    comments = cursor.fetchall()
                    cursor.close()

                    if comments:
                        df = pd.DataFrame(comments)
                        
                        # Arama sonucu bilgisi
                        if search_user and search_user.strip():
                            st.success(f"'{search_user}' için {len(df)} yorum bulundu.")
                        
                        # Duygu dağılımı
                        st.subheader(f"📈 {selected_business} Duygu Dağılımı")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            sentiment_counts = df['sentiment'].value_counts()
                            st.bar_chart(sentiment_counts)
                        
                        with col2:
                            # İstatistikler
                            avg_rating = df['rating'].mean()
                            st.metric("⭐ Ortalama Puan", f"{avg_rating:.2f}")
                            st.metric(" Toplam Yorum", len(df))
                        
                        # Yorumları göster
                        st.subheader("📋 Yorumlar")
                        display_df = df.copy()
                        display_df['rating'] = display_df['rating'].apply(lambda x: f"{'⭐' * int(x)} ({x})" if x else "N/A")
                        display_df['date'] = display_df['date'].astype(str)
                        st.dataframe(
                            display_df[['username', 'rating', 'date', 'comment_text', 'sentiment', 'likes']], 
                            use_container_width=True,
                            height=400
                        )
                        
                        # En yüksek ve düşük puanlı yorumlar
                        col3, col4 = st.columns(2)
                        with col3:
                            st.subheader("🌟 En Yüksek Puanlı Yorumlar")
                            top_positive = df.nlargest(3, 'rating')[['username', 'comment_text', 'rating']]
                            for _, row in top_positive.iterrows():
                                st.info(f"**{row['username']}** (⭐ {row['rating']})\n\n{row['comment_text'][:200]}...")
                        
                        with col4:
                            st.subheader("⚠️ En Düşük Puanlı Yorumlar")
                            top_negative = df.nsmallest(3, 'rating')[['username', 'comment_text', 'rating']]
                            for _, row in top_negative.iterrows():
                                st.warning(f"**{row['username']}** (⭐ {row['rating']})\n\n{row['comment_text'][:200]}...")
                    else:
                        if search_user and search_user.strip():
                            st.info(f"'{search_user}' kullanıcısına ait yorum bulunamadı.")
                        else:
                            st.info("Bu işletme için yorum bulunamadı.")
            else:
                st.info("Henüz işletme bulunamadı.")
        except Error as e:
            st.error(f"Veri çekme hatası: {e}")
        finally:
            conn.close()
    else:
        st.error("Veritabanı bağlantısı kurulamadı.")