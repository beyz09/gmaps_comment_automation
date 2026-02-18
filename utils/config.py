# -*- coding: utf-8 -*-
"""
Yapılandırma ve sabit değerler.
Tüm ayarlar ve selector'lar burada tanımlı.
"""
import os

# ================== AYARLAR ==================
ISLETME_ADI_TAM_SORGUSU = os.environ.get("ISLETME_ADI_TAM_SORGUSU", "bartın üniversitesi, bartın, kutlubey")
SCROLL_PAUSE_TIME = 3.0
MAX_NO_NEW_REVIEWS_SCROLLS = 5
CLICK_MORE_BUTTONS_LIMIT = 20

# ================== VERITABANI ==================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "",
    "database": "google_maps_data_v2"
}

# ================== SELECTOR'LAR ==================
REVIEW_SELECTORS = [
    "//div[contains(@class, 'jftiEf')]",
    "//div[contains(@class, 'fontBodyMedium')]",
    "//div[contains(@aria-label, 'yorum')]",
    "//div[contains(@aria-label, 'review')]",
    "//div[contains(@class, 'MyEned')]",
    "//div[contains(@class, 'ODSEW')]"
]

USERNAME_SELECTORS = [
    ".//div[contains(@class, 'd4r55')]",
    ".//span[contains(@class, 'd4r55')]",
    ".//a[contains(@class, 'd4r55')]",
    ".//div[contains(@class, 'fontBodySmall')]",
    ".//span[contains(@class, 'fontBodySmall')]",
    ".//a[contains(@href, '/maps/contrib/')]"
]

COMMENT_TEXT_SELECTORS = [
    ".//span[contains(@class, 'wiI7pd')]",
    ".//div[contains(@class, 'wiI7pd')]",
    ".//span[contains(@class, 'fontBodyMedium')]",
    ".//div[contains(@class, 'fontBodyMedium')]",
    ".//span[contains(@jsaction, 'pane.review.text')]",
    ".//div[contains(@jsaction, 'pane.review.text')]"
]

SEARCH_RESULT_SELECTORS = [
    "//div[contains(@class, 'Nv2PK')]",
    "//div[@role='article']",
    "//a[contains(@href, '/maps/place/')]"
]
