# -*- coding: utf-8 -*-
"""
Web scraping modülü.
Google Maps'te arama, scroll ve yorum toplama fonksiyonları.
"""
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, StaleElementReferenceException

from utils import (
    SCROLL_PAUSE_TIME, 
    MAX_NO_NEW_REVIEWS_SCROLLS, 
    CLICK_MORE_BUTTONS_LIMIT,
    REVIEW_SELECTORS,
    SEARCH_RESULT_SELECTORS,
    parse_review,
    get_existing_comment_signatures,
    save_comments_batch
)


def isletme_ara(driver, isletme_adi_tam_sorgusu, business_name):
    """Google Maps'te işletmeyi arar ve yorumlar sekmesini açar."""
    import urllib.parse
    
    # Direkt arama URL'si ile git (daha güvenilir)
    encoded_query = urllib.parse.quote(isletme_adi_tam_sorgusu)
    search_url = f"https://www.google.com/maps/search/{encoded_query}"
    print(f"Google Maps arama URL'sine gidiliyor: {search_url}")
    driver.get(search_url)
    time.sleep(8)  # VPS'te daha uzun bekleme
    
    # Consent/cookie popup varsa kabul et
    try:
        consent_btns = driver.find_elements(By.XPATH, 
            "//button[contains(., 'Kabul') or contains(., 'Accept') or contains(., 'Tümünü kabul') or contains(., 'Agree')]")
        if consent_btns:
            consent_btns[0].click()
            print("Çerez popup'ı kabul edildi.")
            time.sleep(3)
            driver.get(search_url)
            time.sleep(8)
    except:
        pass
    
    try:
        print(f"Arama sonuçları bekleniyor...")
        
        # Önce yorumlar butonunu dene (tek sonuç varsa direkt açılır)
        if _try_click_reviews_button(driver):
            return True
        
        # Birden fazla sonuç varsa listeden seç
        target_business = _find_business_in_results(driver, business_name)
        if not target_business:
            print("İlk denemede bulunamadı, bekleniyor...")
            time.sleep(6)
            target_business = _find_business_in_results(driver, business_name)
            
        if not target_business:
            print(f"HATA: '{business_name}' işletmesi bulunamadı!")
            print(f"Mevcut URL: {driver.current_url}")
            print(f"Sayfa başlığı: {driver.title}")
            return False
        
        print(f"Seçilen işletme: '{target_business['name']}'")
        driver.execute_script("arguments[0].click();", target_business['element'])
        time.sleep(5)

        
        return _try_click_reviews_button(driver, timeout=15)
        
    except Exception as e:
        print(f"Arama sırasında hata: {e}")
        import traceback
        traceback.print_exc()
        return False


def _try_click_reviews_button(driver, timeout=5):
    """Yorumlar butonuna tıklamayı dener."""
    try:
        yorumlar_xpath = "//button[contains(@aria-label, 'Yorumlar') or .//span[contains(., 'Yorumlar')]]"
        yorumlar_button = WebDriverWait(driver, timeout).until(
            EC.element_to_be_clickable((By.XPATH, yorumlar_xpath))
        )
        yorumlar_button.click()
        time.sleep(3)
        return True
    except TimeoutException:
        return False


def _find_business_in_results(driver, business_name):
    """Arama sonuçlarından doğru işletmeyi bulur."""
    search_results = []
    
    for selector in SEARCH_RESULT_SELECTORS:
        try:
            elements = driver.find_elements(By.XPATH, selector)
            for elem in elements:
                try:
                    name_elem = elem.find_element(
                        By.XPATH, 
                        ".//h3 | .//span[contains(@class, 'OSrXXb')] | .//div[contains(@class, 'qBF1Pd')] | .//a//span"
                    )
                    name = name_elem.text.strip()
                    if name:
                        link_elem = elem.find_element(By.XPATH, ".//a") if elem.tag_name != 'a' else elem
                        search_results.append({
                            'name': name,
                            'element': link_elem,
                            'href': link_elem.get_attribute('href') or ''
                        })
                except:
                    continue
            if search_results:
                break
        except:
            continue
    
    target_name = business_name.lower().strip()
    for result in search_results:
        result_name = result['name'].lower().strip()
        if result_name == target_name or target_name in result_name or result_name in target_name:
            return result
    
    return None


def yorumlari_yukle(driver):
    """Yorumları scroll yaparak yükler."""
    print("Yorumlar yükleniyor...")
    
    try:
        if not _wait_for_reviews(driver):
            print("HATA: Yorumlar bulunamadı.")
            return
        
        scrollable_container = _find_scrollable_container(driver)
        
        previous_count = 0
        no_new_reviews_count = 0
        scroll_count = 0
        
        print(f"Scroll başlıyor... Max {MAX_NO_NEW_REVIEWS_SCROLLS} boş scroll sonrası duracak.")
        
        while no_new_reviews_count < MAX_NO_NEW_REVIEWS_SCROLLS:
            _click_more_buttons(driver)
            current_count = len(driver.find_elements(By.XPATH, REVIEW_SELECTORS[0]))
            _scroll_down(driver, scrollable_container)
            
            scroll_count += 1
            if scroll_count % 5 == 0:
                print(f"Scroll: {scroll_count} | Yorum: {current_count}")
            
            if current_count > previous_count:
                no_new_reviews_count = 0
                previous_count = current_count
            else:
                no_new_reviews_count += 1
        
        print(f"Toplam {scroll_count} scroll, {previous_count} yorum yüklendi.")
        
    except Exception as e:
        print(f"Scroll hatası: {e}")


def _wait_for_reviews(driver):
    """İlk yorumların yüklenmesini bekler."""
    for selector in REVIEW_SELECTORS:
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, selector))
            )
            return True
        except TimeoutException:
            continue
    return False


def _find_scrollable_container(driver):
    """Scrollable container'ı bulur."""
    try:
        return driver.execute_script("""
            function findScrollableParent(el){
                while(el && el !== document.body){
                    const st = window.getComputedStyle(el);
                    if ((st.overflowY === 'auto' || st.overflowY === 'scroll') && el.scrollHeight > el.clientHeight){
                        return el;
                    }
                    el = el.parentElement;
                }
                return document.scrollingElement || document.body;
            }
            const selectors = ["div[class*='jftiEf']", "div[class*='fontBodyMedium']"];
            let firstReview = null;
            for (const selector of selectors) {
                firstReview = document.querySelector(selector);
                if (firstReview) break;
            }
            return firstReview ? findScrollableParent(firstReview) : document.scrollingElement;
        """)
    except:
        return driver.find_element(By.TAG_NAME, 'body')


def _scroll_down(driver, container):
    """Sayfayı aşağı kaydırır."""
    try:
        driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", container)
    except:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
    time.sleep(SCROLL_PAUSE_TIME)


def _click_more_buttons(driver):
    """'Diğer' butonlarına tıklar."""
    try:
        buttons = driver.find_elements(By.XPATH, "//button[@class='w8nwRe kyuRq']")
        for btn in buttons[:CLICK_MORE_BUTTONS_LIMIT]:
            try:
                driver.execute_script("arguments[0].click();", btn)
                time.sleep(0.1)
            except StaleElementReferenceException:
                pass
    except:
        pass


def devamini_oku_tikla(driver):
    """'Devamını oku' butonlarına tıklar."""
    print("'Devamını oku' butonlarına tıklanıyor...")
    
    click_count = 0
    for _ in range(5):
        try:
            buttons = driver.find_elements(
                By.XPATH, 
                "//button[contains(@class, 'w8nwRe') and (contains(., 'Daha Fazla') or contains(., 'Devamını oku'))]"
            )
            if not buttons:
                break
            
            for btn in buttons:
                try:
                    driver.execute_script("arguments[0].click();", btn)
                    click_count += 1
                except StaleElementReferenceException:
                    pass
            time.sleep(1)
        except:
            break
    
    print(f"{click_count} 'Devamını oku' butonuna tıklandı.")


def yorumlari_cek_ve_kaydet(driver, db_connection, business_id):
    """Yorumları çeker ve veritabanına kaydeder."""
    print("Yorumlar çekiliyor...")
    
    existing_signatures = get_existing_comment_signatures(db_connection, business_id)
    print(f"Mevcut yorum sayısı: {len(existing_signatures)}")
    
    yorum_elementleri = None
    for selector in REVIEW_SELECTORS:
        try:
            yorum_elementleri = WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.XPATH, selector))
            )
            if yorum_elementleri:
                print(f"{len(yorum_elementleri)} yorum bulundu.")
                break
        except TimeoutException:
            continue
    
    if not yorum_elementleri:
        print("HATA: Yorum elementi bulunamadı!")
        return 0
    
    comments_to_insert = []
    for yorum_elem in yorum_elementleri:
        review_data = parse_review(yorum_elem)
        if not review_data:
            continue
        
        signature = (review_data['username'], review_data['rating'], review_data['text'])
        if signature not in existing_signatures:
            comments_to_insert.append((
                business_id,
                review_data['username'],
                review_data['rating'],
                review_data['date'],
                review_data['text'],
                review_data['likes']
            ))
            existing_signatures.add(signature)
    
    saved_count = save_comments_batch(db_connection, comments_to_insert)
    print(f"Toplam {saved_count} yeni yorum eklendi.")
    return saved_count
