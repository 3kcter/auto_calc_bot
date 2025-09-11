from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import threading

_driver = None
_lock = threading.Lock()

def initialize_driver():
    global _driver
    if _driver is None:
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        _driver = webdriver.Chrome(options=options)

def get_driver():
    return _driver

def get_lock():
    return _lock

def quit_driver():
    global _driver
    if _driver:
        _driver.quit()
        _driver = None
