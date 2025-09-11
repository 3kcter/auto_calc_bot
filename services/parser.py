import re
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service

def validate_and_normalize_url(url: str) -> tuple[str | None, str | None]:
    if 'encar.com' in url:
        match = re.search(r'encar\.com/cars/detail/(\d+)', url)
        if match:
            car_id = match.group(1)
            return f"https://fem.encar.com/cars/detail/{car_id}", None
        return None, "Неверный формат ссылки a. Пожалуйста, отправьте корректную ссылку."
    
    if 'che168.com' in url:
        return url.split('?')[0], None

    return None, "Пожалуйста, отправьте ссылку на сайт encar.com или che168.com"

def parse_car_data(url: str, html_content: str) -> tuple[dict, str | None]:
    data = {
        'year': None,
        'cost': None,
        'currency': None,
        'volume': None
    }
    error = None

    if 'encar.com' in url:
        try:
            preloaded_state_match = re.search(r'__PRELOADED_STATE__\s*=\s*({.*?})</script>', html_content)
            if preloaded_state_match:
                preloaded_state = json.loads(preloaded_state_match.group(1))
                car_info = preloaded_state.get('cars', {}).get('base', {})
                if car_info:
                    data['year'] = car_info.get('category', {}).get('formYear')
                    price = car_info.get('advertisement', {}).get('price')
                    if price:
                        data['cost'] = int(price) * 10000
                        data['currency'] = 'KRW'
                    data['volume'] = car_info.get('spec', {}).get('displacement')
            else:
                error = "Could not find __PRELOADED_STATE__ in encar.com HTML"
        except (json.JSONDecodeError, AttributeError) as e:
            error = f"Error parsing encar.com data: {e}"
    
    return data, error

def parse_che168_selenium(url: str) -> tuple[dict, str | None]:
    data = {}
    error = None
    
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=options)
        driver.get(url)
        
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "car-brand-name")))

        title = driver.find_element(By.CLASS_NAME, "car-brand-name").text
        price = driver.find_element(By.ID, "overlayPrice").text
        
        # Extract year from a more reliable element if possible
        year_element = driver.find_element(By.XPATH, "//li[contains(., '上牌时间')]/span[2]")
        year = year_element.text.split('年')[0]

        # Extract volume
        volume_element = driver.find_element(By.XPATH, "//li[contains(., '排量')]/span[2]")
        volume_liters = volume_element.text.replace('L', '')
        volume_cc = int(float(volume_liters) * 1000)


        data = {
            'year': int(year),
            'cost': int(float(price.replace('万','')) * 10000),
            'currency': 'CNY',
            'volume': volume_cc,
            'country': 'china'
        }

    except Exception as e:
        error = f"Error parsing che168.com with selenium: {e}"
    finally:
        if 'driver' in locals():
            driver.quit()
            
    return data, error