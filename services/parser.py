import re
import json
import logging
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager # For easier WebDriver management


def validate_and_normalize_url(url: str) -> tuple[str | None, str | None]:
    """
    Валидирует и нормализует URL, чтобы он соответствовал одному из поддерживаемых форматов.
    Возвращает нормализованный URL или сообщение об ошибке.
    """
    if 'che168.com' in url:
        return url.split('?')[0], None

    return None, "Пожалуйста, отправьте ссылку на сайт che168.com"

def _parse_encar_preloaded_state(html_content: str) -> tuple[dict, str | None]:
    """
    Парсит данные об автомобиле с encar.com из предоставленного HTML-контента, используя __PRELOADED_STATE__.
    """
    data = {
        'year': None,
        'cost': None,
        'currency': 'KRW',
        'volume': None,
        'engine_type': None,
        'power': None,
        'country': 'korea'
    }
    error = None

    try:
        preloaded_state_match = re.search(r'__PRELOADED_STATE__\s*=\s*({.*?})</script>', html_content)
        if preloaded_state_match:
            preloaded_state = json.loads(preloaded_state_match.group(1))
            car_info = preloaded_state.get('cars', {}).get('base', {})
            if car_info:
                data['year'] = car_info.get('category', {}).get('formYear')
                price = car_info.get('advertisement', {}).get('price')
                if price:
                    try:
                        data['cost'] = int(price) * 10000
                    except ValueError:
                        logging.warning(f"Could not convert price '{price}' to int in preloaded state.")
                data['volume'] = car_info.get('spec', {}).get('displacement')
                # Attempt to get engine_type and power from preloaded state if available
                # This part might need further refinement based on actual preloaded state structure
                data['engine_type'] = car_info.get('spec', {}).get('fuelType') # Assuming fuelType maps to engine_type
                # Power is not directly available in the provided example of preloaded state, will try to parse later if needed
        else:
            error = "Не удалось найти данные о машине на encar.com в __PRELOADED_STATE__."
    except (json.JSONDecodeError, AttributeError) as e:
        error = f"Ошибка обработки данных с encar.com из __PRELOADED_STATE__: {e}"
    
    return data, error

def parse_encar_selenium(url: str) -> tuple[dict, str | None]:
    logging.info(f"Starting to parse encar.com data using Selenium for URL: {url}")
    data = {
        'car_name': None, 'year': None, 'month': None, 'mileage': None, 'cost': None,
        'currency': 'KRW', 'volume': None, 'power': None, 'power_unit': None,
        'country': 'korea', 'engine_type': None
    }
    error = None
    driver = None

    try:
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--window-size=1920,1080')

        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.get(url)

        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )

        preloaded_state = driver.execute_script("return window.__PRELOADED_STATE__;")

        if preloaded_state:
            logging.info("Found __PRELOADED_STATE__. Parsing data from it.")
            car_info = preloaded_state.get('cars', {}).get('base', {})
            if car_info:
                data['car_name'] = car_info.get('gallery', {}).get('title')

                category_info = car_info.get('category', {})
                if category_info:
                    data['year'] = category_info.get('formYear')
                    data['month'] = category_info.get('formMonth')

                advertisement_info = car_info.get('advertisement', {})
                if advertisement_info and advertisement_info.get('price'):
                    try:
                        data['cost'] = int(advertisement_info['price']) * 10000
                    except (ValueError, TypeError):
                        logging.warning(f"Could not parse price from preloaded state: {advertisement_info['price']}")
                
                mileage_info = car_info.get('mileage', {})
                if mileage_info:
                    data['mileage'] = mileage_info.get('mileage')

                spec_info = car_info.get('spec', {})
                performance_info = car_info.get('performance', {})

                if spec_info:
                    fuel_type = spec_info.get('fuelName', '').lower()
                    if '전기' in fuel_type:
                        data['engine_type'] = 'electro'
                        data['volume'] = 0
                        power_kw = spec_info.get('standardCapacity') 
                        if power_kw:
                            data['power'] = power_kw
                            data['power_unit'] = 'кВт'
                    else:
                        data['engine_type'] = 'ice'
                        data['volume'] = spec_info.get('displacement')

                if not data.get('power') and performance_info:
                    power_hp = performance_info.get('power')
                    if power_hp:
                        data['power_display'] = power_hp
                        data['power'] = power_hp * 0.7355 # Convert HP to kW
                        data['power_unit'] = 'л.с.'

                if not data['engine_type']:
                    if data.get('volume', 0) > 0:
                        data['engine_type'] = 'ice'
                    elif data.get('power', 0) > 0:
                        data['engine_type'] = 'electro'
            else:
                error = "Could not find 'base' info in __PRELOADED_STATE__"
        else:
            error = "Could not find __PRELOADED_STATE__ in page."
            logging.warning(error)

        if not all(data.get(k) for k in ['year', 'cost', 'volume', 'car_name', 'mileage', 'power']):
            if not error:
                error = "Не удалось извлечь все данные из __PRELOADED_STATE__."
            logging.error(f"Failed to parse all required data from encar.com. Data: {data}")

    except Exception as e:
        error = f"Произошла непредвиденная ошибка при парсинге encar.com с помощью Selenium: {e}"
        logging.error(error)
    finally:
        if driver:
            driver.quit()

    logging.info(f"Final parsed data for encar.com (Selenium): {data}")
    logging.info(f"Final error state for encar.com (Selenium): {error}")
    return data, error

def _find_spec_value(soup: BeautifulSoup, label_text: str) -> str | None:
    """Finds a spec value based on its label text."""
    try:
        label_tag = soup.find(lambda tag: tag.name and label_text in tag.text)
        if not label_tag:
            return None
        
        # Common pattern: <li><span>Label</span><p>Value</p></li>
        parent_li = label_tag.find_parent('li')
        if parent_li:
            value_tag = parent_li.find('p')
            if value_tag:
                return value_tag.text.strip()

        # Common pattern: <td>Label</td><td>Value</td>
        parent_td = label_tag.find_parent('td')
        if parent_td:
            next_td = parent_td.find_next_sibling('td')
            if next_td:
                return next_td.text.strip()
        
        # Fallback for less structured data
        parent = label_tag.parent
        value_tag = parent.find(['p', 'span', 'div'], class_=lambda x: x != 'label')
        if value_tag:
            return value_tag.text.strip()

    except Exception:
        return None
    return None

def parse_encar_requests(url: str) -> tuple[dict, str | None]:
    """
    Парсит данные об автомобиле с encar.com с использованием Selenium.
    """
    return parse_encar_selenium(url)

def parse_che168_requests(html_content: str) -> tuple[dict, str | None]:
    """
    Парсит данные об автомобиле с che168.com, используя скрытые поля ввода и эвристики для видимого текста.
    """
    logging.info("Starting to parse che168.com data using hidden inputs and heuristics.")
    data = {
        'car_name': None, 'year': None, 'month': None, 'mileage': None, 'cost': None,
        'currency': 'CNY', 'volume': None, 'power': None, 'power_unit': 'кВт',
        'country': 'china', 'engine_type': None
    }
    error = None

    try:
        soup = BeautifulSoup(html_content, 'lxml')

        def get_input_val(input_id):
            input_tag = soup.find('input', {'id': input_id})
            return input_tag.get('value') if input_tag else None

        # --- Get data from hidden inputs ---
        data['car_name'] = get_input_val('car_carname')
        reg_time = get_input_val('car_firstregtime')
        if reg_time:
            try:
                year, month = reg_time.split('/')
                data['year'] = int(year)
                data['month'] = int(month)
            except (ValueError, IndexError):
                logging.warning(f"Could not parse car_firstregtime: {reg_time}")
        mileage_val = get_input_val('car_mileage')
        if mileage_val:
            try:
                data['mileage'] = int(float(mileage_val) * 10000)
            except (ValueError, TypeError):
                logging.warning(f"Could not parse car_mileage: {mileage_val}")
        price_val = get_input_val('car_price')
        if price_val:
            try:
                data['cost'] = int(float(price_val) * 10000)
            except (ValueError, TypeError):
                logging.warning(f"Could not parse car_price: {price_val}")

        # --- Determine Engine Type and get specs ---
        text_content = soup.get_text()
        is_electric = "纯电动" in text_content

        if is_electric:
            data['engine_type'] = 'electro'
            data['volume'] = 0
            data['power_unit'] = 'кВт'
            # Try to find power in the spec table first
            power_text = _find_spec_value(soup, '最大功率(kW)')
            if power_text:
                power_match = re.search(r'(\d+)', power_text)
                if power_match:
                    data['power'] = int(power_match.group(1))
            # Fallback to regex search in the whole text
            if not data['power']:
                power_match = re.search(r'(\d+)\s*kW', text_content, re.IGNORECASE)
                if power_match:
                    data['power'] = int(power_match.group(1))
        else:
            data['engine_type'] = 'ice'
            # --- Power and Volume for ICE from visible text ---
            all_lis = soup.find_all('li')
            for li in all_lis:
                text = li.text
                if ('T' in text or 'L' in text) and (re.search(r'V\d', text) or re.search(r'\d{3}', text)):
                    power_match = re.search(r'(\d{3,})', text)
                    if power_match:
                        data['power'] = int(power_match.group(1))
                        data['power_unit'] = 'л.с.'
                    
                    volume_match = re.search(r'(\d\.\d)[TL]?', text)
                    if volume_match:
                        data['volume'] = int(float(volume_match.group(1)) * 1000)
                    
                    if data['power'] and data['volume']:
                        break
            # Fallback for volume if not found in engine string
            if not data['volume']:
                volume_text = _find_spec_value(soup, '排量(L)')
                if volume_text:
                    try:
                        data['volume'] = 0 if volume_text == '-' else int(float(volume_text) * 1000)
                    except (ValueError, TypeError):
                        logging.warning(f"Could not parse volume from {volume_text}")


    except Exception as e:
        error = f"Произошла непредвиденная ошибка при парсинге che168.com: {e}"
        logging.error(error)

    return data, error