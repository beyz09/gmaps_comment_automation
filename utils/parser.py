# -*- coding: utf-8 -*-
"""
Yorum ayrıştırma (parsing) modülü.
Yorum elementlerinden veri çıkarma fonksiyonları.
"""
import re
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from .config import USERNAME_SELECTORS, COMMENT_TEXT_SELECTORS


def get_username(yorum_elem):
    """Yorum elementinden kullanıcı adını çeker."""
    for selector in USERNAME_SELECTORS:
        try:
            elem = yorum_elem.find_element(By.XPATH, selector)
            text = elem.text.strip()
            if text and len(text) > 0:
                return text
        except NoSuchElementException:
            continue
    return None


def get_rating(yorum_elem):
    """Yorum elementinden puanı çeker."""
    try:
        star_elements = yorum_elem.find_elements(
            By.XPATH, 
            ".//*[contains(@aria-label, 'yıldız') or contains(@aria-label, 'star') or contains(@aria-label, '★')]"
        )
        for elem in star_elements:
            aria_label = elem.get_attribute("aria-label") or ""
            puan_match = re.search(r'(\d+)', aria_label)
            if puan_match:
                return int(puan_match.group(1))
        
        star_icons = yorum_elem.find_elements(By.XPATH, ".//span[contains(@class, 'hCCjke')]//span")
        if star_icons:
            return len(star_icons)
    except Exception:
        pass
    return None


def get_date(yorum_elem):
    """Yorum elementinden tarihi çeker."""
    try:
        time_elements = yorum_elem.find_elements(
            By.XPATH, 
            ".//*[contains(text(), 'önce') or contains(text(), 'gün') or contains(text(), 'hafta') or contains(text(), 'ay') or contains(text(), 'yıl')]"
        )
        for elem in time_elements:
            text = elem.text.strip()
            if text and any(word in text.lower() for word in ['gün', 'hafta', 'ay', 'yıl', 'önce']):
                return text
        
        time_elements = yorum_elem.find_elements(
            By.XPATH, 
            ".//*[contains(@aria-label, 'önce') or contains(@aria-label, 'gün')]"
        )
        for elem in time_elements:
            aria = elem.get_attribute("aria-label") or ""
            if aria:
                return aria
    except Exception:
        pass
    return None


def get_comment_text(yorum_elem):
    """Yorum elementinden yorum metnini çeker."""
    for selector in COMMENT_TEXT_SELECTORS:
        try:
            elem = yorum_elem.find_element(By.XPATH, selector)
            text = elem.text.strip()
            if text and len(text) > 10:
                return text
        except NoSuchElementException:
            continue
    
    try:
        full_text = yorum_elem.text.strip()
        lines = full_text.split('\n')
        if len(lines) > 2:
            yorum_metni = '\n'.join(lines[2:])
            if len(yorum_metni) > 10:
                return yorum_metni
    except Exception:
        pass
    return ""


def get_likes(yorum_elem):
    """Yorum elementinden beğeni sayısını çeker."""
    try:
        like_elements = yorum_elem.find_elements(
            By.XPATH, 
            ".//*[contains(@aria-label, 'Beğenildi') or contains(@aria-label, 'liked')]"
        )
        for elem in like_elements:
            aria = elem.get_attribute("aria-label") or ""
            match = re.search(r'(\d+)', aria)
            if match:
                return int(match.group(1))
    except Exception:
        pass
    return 0


def parse_review(yorum_elem):
    """Yorum elementini ayrıştırır ve tüm verileri döndürür."""
    username = get_username(yorum_elem)
    if not username:
        return None
    
    return {
        'username': username,
        'rating': get_rating(yorum_elem),
        'date': get_date(yorum_elem),
        'text': get_comment_text(yorum_elem),
        'likes': get_likes(yorum_elem)
    }
