# -*- coding: utf-8 -*-
"""
Tarayıcı yardımcı fonksiyonları.
Chrome WebDriver başlatma ve yapılandırma.
"""
import os

def chrome_driver_baslat(headless=True):
    """Chrome WebDriver'ı başlatır."""
    if os.environ.get('HEADLESS_MODE') == 'true':
        headless = True
    
    try:
        # Önce undetected-chromedriver dene (bot tespitini atlatır)
        import undetected_chromedriver as uc
        options = uc.ChromeOptions()
        options.add_argument('--lang=tr')
        options.add_argument('--window-size=1920,1080')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        if headless:
            options.add_argument('--headless=new')
        driver = uc.Chrome(options=options, use_subprocess=True)
        print("undetected-chromedriver kullanılıyor.")
        return driver
    except Exception as e:
        print(f"undetected-chromedriver başlatılamadı: {e}, normal Chrome deneniyor...")
    
    # Fallback: normal selenium
    from selenium import webdriver
    options = webdriver.ChromeOptions()
    options.add_argument('--lang=tr')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-blink-features=AutomationControlled')
    options.add_experimental_option('excludeSwitches', ['enable-automation'])
    options.add_experimental_option('useAutomationExtension', False)
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    if headless:
        options.add_argument('--headless=new')
        options.add_argument('--disable-gpu')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
    else:
        options.add_argument('--start-maximized')
    
    driver = webdriver.Chrome(options=options)
    driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
        'source': '''
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            })
        '''
    })
    return driver
