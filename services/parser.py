import re
import json
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from services.driver_manager import safe_driver_execute

def validate_and_normalize_url(url: str) -> tuple[str | None, str | None]:
    """
    Валидирует и нормализует URL, чтобы он соответствовал одному из поддерживаемых форматов.
    Возвращает нормализованный URL или сообщение об ошибке.
    """
    if 'encar.com' in url:
        match = re.search(r'encar.com/cars/detail/(\d+)', url)
        if match:
            car_id = match.group(1)
            return f"https://fem.encar.com/cars/detail/{car_id}", None
        return None, "Неверный формат ссылки a. Пожалуйста, отправьте корректную ссылку."
    
    if 'che168.com' in url:
        return url.split('?')[0], None

    return None, "Пожалуйста, отправьте ссылку на сайт encar.com или che168.com"

def parse_car_data(url: str, html_content: str) -> tuple[dict, str | None]:
    """
    Парсит данные об автомобиле с encar.com из предоставленного HTML-контента.
    """
    data = {
        'year': None,
        'cost': None,
        'currency': None,
        'volume': None,
        'engine_type': None
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
                error = "Не удалось найти данные о машине на encar.com."
        except (json.JSONDecodeError, AttributeError) as e:
            error = f"Ошибка обработки данных с encar.com: {e}"
    
    return data, error

@safe_driver_execute
def parse_che168_selenium(driver, url: str) -> tuple[dict, str | None]:
    """
    Парсит данные об автомобиле с che168.com с использованием Selenium, извлекая данные из скрытых полей ввода.
    """
    data = {
        'year': None,
        'cost': None,
        'currency': 'CNY',  # Валюта для che168.com всегда CNY
        'volume': None,
        'country': 'china',
        'engine_type': None 
    }
    error = None
    
    try:
        print(f"DEBUG: Navigating to URL: {url}")
        driver.get(url)
        print(f"DEBUG: Page loaded for URL: {url}")
        
        wait = WebDriverWait(driver, 30) # Increased timeout to 30 seconds
        
        # Ожидаем появления элемента, который содержит данные
        wait.until(EC.presence_of_element_located((By.ID, "car_price")))

        # Извлечение данных из скрытых полей ввода
        price_str = driver.find_element(By.ID, "car_price").get_attribute("value")
        year_str = driver.find_element(By.ID, "car_firstregtime").get_attribute("value")
        car_name = driver.find_element(By.ID, "car_carname").get_attribute("value")
        print(f"DEBUG: price_str: {price_str}, year_str: {year_str}, car_name: {repr(car_name)}")

        # Преобразование данных
        try:
            data['cost'] = int(float(price_str) * 10000) # Цена в юанях, переводим в копейки
        except ValueError:
            error = "Неверный формат цены."

        try:
            # Год может быть в формате "YYYY/MM", берем только год
            data['year'] = int(year_str.split('/')[0])
        except ValueError:
            error = "Неверный формат года."
        
        # Try to find fuel type first
        fuel_type_element = _find_element_by_xpath(driver, "//li[span[contains(text(), '能源类型') or contains(text(), '燃料类型')]]")
        fuel_type_text = fuel_type_element.text if fuel_type_element else ""
        print(f"DEBUG: fuel_type_text: {fuel_type_text}")

        if fuel_type_text and "纯电动" in fuel_type_text:
            data['engine_type'] = "electro"
            # Для электромобилей объем двигателя не указывается, но может быть емкость батареи
            # Попробуем найти емкость батареи (например, 75kWh)
            try:
                battery_capacity_element = _find_element_by_xpath(driver, "//li[span[contains(text(), '电池容量')]]")
                battery_capacity_str = battery_capacity_element.text.strip() if battery_capacity_element else ""
                print(f"DEBUG: battery_capacity_str: {battery_capacity_str}")
                # Извлекаем числовое значение, например, из "75kWh"
                capacity_match = re.search(r'(\d+\.?\d*)', battery_capacity_str)
                if capacity_match:
                    data['volume'] = int(float(capacity_match.group(1)) * 1000) # Переводим kWh в Wh для объема
                    print(f"DEBUG: Electric volume (Wh): {data['volume']}")
                else:
                    data['volume'] = 0 # Если не удалось извлечь, ставим 0
            except ValueError:
                error = "Неверный формат емкости батареи."
        else:
            # If not electric by fuel type, try to find displacement
            displacement_element = _find_element_by_xpath(driver, "//li[span[contains(text(), '排量')]]")
            displacement_text = displacement_element.text if displacement_element else ""
            print(f"DEBUG: displacement_text: {displacement_text}")

            if displacement_text:
                volume_match = re.search(r'(\d+\.?\d*)(L|T)', displacement_text)
                if volume_match:
                    try:
                        volume_liters = float(volume_match.group(1))
                        data['volume'] = int(volume_liters * 1000) # Переводим литры в куб. см.
                        data['engine_type'] = "ДВС"
                        print(f"DEBUG: ICE volume (cc): {data['volume']}")
                    except ValueError:
                        error = "Неверный формат объема двигателя."
                else:
                    error = "Не удалось извлечь объем двигателя из элемента '排量'."
            elif "纯电动" in car_name or "纯电动" in driver.page_source: # Fallback to original check if specific elements not found
                data['engine_type'] = "electro"
                # For electric vehicles, engine volume is not specified, but battery capacity might be
                # Try to find battery capacity (e.g., 75kWh)
                try:
                    battery_capacity_element = _find_element_by_xpath(driver, "//li[span[contains(text(), '电池容量')]]")
                    battery_capacity_str = battery_capacity_element.text.strip() if battery_capacity_element else ""
                    print(f"DEBUG: Fallback battery_capacity_str: {battery_capacity_str}")
                    # Извлекаем числовое значение, например, из "75kWh"
                    capacity_match = re.search(r'(\d+\.?\d*)', battery_capacity_str)
                    if capacity_match:
                        data['volume'] = int(float(capacity_match.group(1)) * 1000) # Переводим kWh в Wh для объема
                        print(f"DEBUG: Fallback Electric volume (Wh): {data['volume']}")
                    else:
                        data['volume'] = 0 # Если не удалось извлечь, ставим 0
                except ValueError:
                    error = "Неверный формат емкости батареи."
            else:
                # Fallback to searching the entire page_source for volume
                page_source_volume_match = re.search(r'(\d+\.?\d*)(L|T)', driver.page_source)
                if page_source_volume_match:
                    try:
                        volume_liters = float(page_source_volume_match.group(1))
                        data['volume'] = int(volume_liters * 1000) # Переводим литры в куб. см.
                        data['engine_type'] = "ДВС"
                        print(f"DEBUG: Fallback ICE volume (cc) (page_source): {data['volume']}")
                    except ValueError:
                        error = "Неверный формат объема двигателя из page_source."
                else:
                    error = "Не удалось извлечь объем двигателя или определить тип двигателя."

    except TimeoutException:
        error = "Время ожидания загрузки страницы истекло. Попробуйте еще раз."
    except NoSuchElementException as e:
        error = f"Не найден элемент на странице: {e}. Возможно, изменилась структура сайта."
    except Exception as e:
        error = f"Произошла непредвиденная ошибка при парсинге che168.com: {e}"
            
    print(f"DEBUG: Final data (parse_car_data): {data}")
    print(f"DEBUG: Final error (parse_car_data): {error}")
    return data, error

def _find_element_by_xpath(driver, xpath):
    try:
        return driver.find_element(By.XPATH, xpath)
    except NoSuchElementException:
        return None