# -*- coding: utf-8 -*-
"""
Tarayıcı yardımcı fonksiyonları.
Chrome WebDriver başlatma ve yapılandırma.
"""
import os
from selenium import webdriver


def chrome_driver_baslat(headless=True):
    """Chrome WebDriver'ı başlatır."""
    if os.environ.get('HEADLESS_MODE') == 'true':
        headless = True
    
    options = webdriver.ChromeOptions()
    
    # Temel ayarlar
    options.add_argument('--lang=tr')
    options.add_argument('--window-size=1920,1080')
    
    # Bot tespitini atlatmak için ayarlar
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    
    # User-Agent ayarı (gerçek Chrome gibi görünmek için)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    # Headless mod için ek ayarlar
    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-software-rasterizer')
        options.add_argument('--disable-extensions')
        options.add_argument('--disable-infobars')
        options.add_argument('--disable-notifications')
        options.add_argument('--disable-popup-blocking')
        # Headless modda da maximize gibi davranması için
        options.add_argument('--start-maximized')
    else:
        options.add_argument('--start-maximized')
    
    driver = webdriver.Chrome(options=options)
    
    # Navigator.webdriver özelliğini gizle (bot tespiti için)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    
    return driver
