from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
import threading
import os
import logging

_driver = None
_lock = threading.Lock()
_driver_initialized = False

def initialize_driver(chrome_driver_path=None):
    """
    Инициализация драйвера с защитой от race condition
    """
    global _driver, _driver_initialized
    
    with _lock:
        if _driver is None and not _driver_initialized:
            try:
                options = Options()
                options.add_argument("--headless=new")  # новый формат headless
                options.add_argument("--disable-blink-features=AutomationControlled")
                options.add_argument("--no-sandbox")
                options.add_argument("--disable-dev-shm-usage")
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Указываем путь к драйверу если предоставлен
                if chrome_driver_path and os.path.exists(chrome_driver_path):
                    service = Service(executable_path=chrome_driver_path)
                    _driver = webdriver.Chrome(service=service, options=options)
                else:
                    _driver = webdriver.Chrome(options=options)
                
                # Убираем признаки автоматизации
                _driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                
                _driver_initialized = True
                logging.info("Драйвер успешно инициализирован")
                
            except Exception as e:
                logging.error(f"Ошибка инициализации драйвера: {e}")
                _driver_initialized = False
                raise

def get_driver():
    """
    Получение экземпляра драйвера
    """
    global _driver
    if _driver is None:
        initialize_driver()
    return _driver

def get_lock():
    """
    Получение блокировки для многопоточного доступа
    """
    return _lock

def restart_driver():
    """
    Перезапуск драйвера
    """
    global _driver, _driver_initialized
    with _lock:
        quit_driver()
        _driver_initialized = False
        initialize_driver()

def quit_driver():
    """
    Корректное завершение работы драйвера
    """
    global _driver, _driver_initialized
    with _lock:
        if _driver:
            try:
                _driver.quit()
            except Exception as e:
                logging.error(f"Ошибка при закрытии драйвера: {e}")
            finally:
                _driver = None
                _driver_initialized = False

def safe_driver_execute(func):
    """
    Декоратор для безопасного выполнения операций с драйвером
    """
    def wrapper(*args, **kwargs):
        try:
            driver = get_driver()
            return func(driver, *args, **kwargs)
        except Exception as e:
            logging.error(f"Ошибка при работе с драйвером: {e}")
            # Можно добавить логику перезапуска драйвера при ошибках
            restart_driver()
            raise
    return wrapper

# Пример использования
@safe_driver_execute
def example_usage(driver):
    driver.get("https://www.che168.com")
    return driver.title

# Инициализация с указанием пути к драйверу
if __name__ == "__main__":
    # Укажите правильный путь к chromedriver
    driver_path = r"C:\path\to\chromedriver.exe"  # для Windows
    # driver_path = "/usr/local/bin/chromedriver"  # для Linux/Mac
    
    try:
        initialize_driver(driver_path)
        title = example_usage()
        logging.info(f"Заголовок страницы: {title}")
    finally:
        quit_driver()