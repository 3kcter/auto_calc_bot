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
    if 'encar.com' in url:
        match = re.search(r'encar.com/cars/detail/(\d+)', url)
        if match:
            car_id = match.group(1)
            return f"https://fem.encar.com/cars/detail/{car_id}", None
        return None, "Неверный формат ссылки a. Пожалуйста, отправьте корректную ссылку."
    
    if 'che168.com' in url:
        return url.split('?')[0], None

    return None, "Пожалуйста, отправьте ссылку на сайт encar.com или che168.com"

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
        'year': None,
        'cost': None,
        'currency': 'KRW',
        'volume': None,
        'engine_type': None,
        'power': None,
        'country': 'korea'
    }
    error = None
    driver = None

    try:
        # Setup Chrome options for headless browsing
        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu') # Applicable to Windows as well
        options.add_argument('--window-size=1920,1080') # Set a common window size

        # Initialize WebDriver
        # Using ChromeDriverManager to automatically download and manage ChromeDriver
        driver = webdriver.Chrome(service=ChromeService(ChromeDriverManager().install()), options=options)
        driver.get(url)

        # --- CAPTCHA Handling Placeholder ---
        # If a CAPTCHA is detected, this is where you would implement logic to handle it.
        # This might involve waiting for user input, using a CAPTCHA solving service,
        # or more advanced techniques. Direct CAPTCHA solving is beyond the scope
        # of this automated refactoring.
        # Example: if "captcha" in driver.page_source.lower():
        #     error = "CAPTCHA detected. Manual intervention or CAPTCHA solving service required."
        #     return data, error
        # --- End CAPTCHA Handling Placeholder ---

        # Wait for the body element to be present, which is more generic.
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )

        # Attempt to extract from __PRELOADED_STATE__ first, as it's often more reliable
        # This requires executing JavaScript in the browser context
        preloaded_state_script = "return window.__PRELOADED_STATE__;"
        preloaded_state = driver.execute_script(preloaded_state_script)

        if preloaded_state:
            logging.debug(f"Preloaded state: {preloaded_state}")
            car_info = preloaded_state.get('cars', {}).get('base', {})
            if car_info:
                logging.debug(f"Car info from preloaded state: {car_info}")
                year_str = car_info.get('category', {}).get('formYear')
                if year_str:
                    try:
                        data['year'] = int(year_str)
                    except ValueError:
                        logging.warning(f"Could not convert year '{year_str}' to int in preloaded state (Selenium).")
                price = car_info.get('advertisement', {}).get('price')
                if price:
                    try:
                        data['cost'] = int(price) * 10000
                    except ValueError:
                        logging.warning(f"Could not convert price '{price}' to int in preloaded state (Selenium).")
                data['volume'] = car_info.get('spec', {}).get('displacement')
                fuel_type_from_preloaded = car_info.get('spec', {}).get('fuelName') # Changed from 'fuelType' to 'fuelName'
                if fuel_type_from_preloaded:
                    normalized_fuel_type = fuel_type_from_preloaded.lower()
                    if "diesel" in normalized_fuel_type or "gasoline" in normalized_fuel_type or "디젤" in normalized_fuel_type or "가솔린" in normalized_fuel_type: # Added Korean terms
                        data['engine_type'] = 'ice'
                    elif "electro" in normalized_fuel_type or "전기" in normalized_fuel_type: # Added Korean term
                        data['engine_type'] = 'electro'
                    else:
                        data['engine_type'] = fuel_type_from_preloaded # Keep original if not matched
                        logging.debug(f"Unmatched fuel type from preloaded state: {fuel_type_from_preloaded}")
                # Power might still need to be scraped from HTML if not in preloaded state
        else:
            logging.warning("Could not find __PRELOADED_STATE__ using Selenium. Falling back to BeautifulSoup-like scraping.")

        # If data is still missing, or if __PRELOADED_STATE__ wasn't found,
        # fall back to scraping from the rendered HTML using Selenium's element finders.
        # This part will be similar to the BeautifulSoup logic but using Selenium methods.
        if not all(data.get(k) for k in ['year', 'cost', 'volume']):
            logging.info("Attempting to parse encar.com data with Selenium element finders.")

            # Year
            try:
                year_element = driver.find_element(By.CLASS_NAME, 'year')
                year_match = re.search(r'(\d{4})', year_element.text)
                if year_match:
                    try:
                        data['year'] = int(year_match.group(1))
                    except ValueError:
                        logging.warning(f"Could not convert year '{year_match.group(1)}' to int.")
            except Exception as e:
                logging.debug(f"Could not find year with Selenium: {e}")

            # Cost
            try:
                price_element = driver.find_element(By.CLASS_NAME, 'info_price')
                price_text = price_element.text.replace(',', '').strip()
                price_match = re.search(r'(\d+)', price_text)
                if price_match:
                    try:
                        data['cost'] = int(price_match.group(1)) * 10000
                    except ValueError:
                        logging.warning(f"Could not convert cost '{price_match.group(1)}' to int.")
            except Exception as e:
                logging.debug(f"Could not find cost with Selenium: {e}")

            # Volume, Engine Type, Power
            spec_items = driver.find_elements(By.CLASS_NAME, 'spec_item')
            for item in spec_items:
                try:
                    title = item.find_element(By.CLASS_NAME, 'tit').text.strip()
                    value = item.find_element(By.CLASS_NAME, 'txt').text.strip()

                    if '배기량' in title and not data['volume']:
                        volume_match = re.search(r'(\d+)', value)
                        if volume_match:
                            try:
                                data['volume'] = int(volume_match.group(1))
                            except ValueError:
                                logging.warning(f"Could not convert volume '{volume_match.group(1)}' to int.")

                    if '연료' in title and not data['engine_type']:
                        normalized_fuel_type = value.lower()
                        if "diesel" in normalized_fuel_type or "gasoline" in normalized_fuel_type or "디젤" in normalized_fuel_type or "가솔린" in normalized_fuel_type: # Added Korean terms
                            data['engine_type'] = 'ice'
                        elif "electro" in normalized_fuel_type or "전기" in normalized_fuel_type: # Added Korean term
                            data['engine_type'] = 'electro'
                        else:
                            data['engine_type'] = value # Keep original if not matched
                            logging.debug(f"Unmatched fuel type from Selenium scraping: {value}")

                    if '최고출력' in title and not data['power']:
                        power_match = re.search(r'(\d+)', value)
                        if power_match:
                            try:
                                data['power'] = int(power_match.group(1))
                            except ValueError:
                                logging.warning(f"Could not convert power '{power_match.group(1)}' to int.")
                except Exception as e:
                    logging.debug(f"Error parsing spec item with Selenium: {e}")

        if not all(data.get(k) for k in ['year', 'cost', 'volume']):
            error = error if error else "Не удалось полностью спарсить данные с encar.com с помощью Selenium."
            if driver:
                logging.error(f"Page source on error: {driver.page_source}")

    except Exception as e:
        error = f"Произошла непредвиденная ошибка при парсинге encar.com с помощью Selenium: {e}"
        logging.error(error)
    finally:
        if driver:
            driver.quit()

    logging.info(f"Final parsed data for encar.com (Selenium): {data}")
    logging.info(f"Final error state for encar.com (Selenium): {error}")
    return data, error

def parse_encar_requests(url: str) -> tuple[dict, str | None]:
    """
    Парсит данные об автомобиле с encar.com с использованием Selenium.
    """
    return parse_encar_selenium(url)

def parse_che168_requests(html_content: str) -> tuple[dict, str | None]:
    """
    Парсит данные об автомобиле с che168.com с использованием BeautifulSoup.
    """
    logging.info("Starting to parse che168.com data.")
    data = {
        'year': None,
        'cost': None,
        'currency': 'CNY',
        'volume': None,
        'power': None,  # New field for power
        'country': 'china',
        'engine_type': None
    }
    error = None

    try:
        soup = BeautifulSoup(html_content, 'lxml')

        # ... (rest of the price and year parsing code remains the same)
        price_input = soup.find('input', {'id': 'car_price'})
        year_input = soup.find('input', {'id': 'car_firstregtime'})
        
        if price_input and price_input.get('value'):
            try:
                data['cost'] = int(float(price_input['value']) * 10000)
            except (ValueError, TypeError):
                error = "Неверный формат цены."
        else:
            error = "Не удалось найти цену."
        logging.info(f"Price parsing result: cost={data['cost']}, error={error}")

        if year_input and year_input.get('value'):
            try:
                year_parts = year_input['value'].split('/')
                data['year'] = int(year_parts[0])
                data['month'] = int(year_parts[1]) if len(year_parts) > 1 else 1
            except (ValueError, IndexError):
                error = "Неверный формат года."
        else:
            # Fallback for year if hidden input not found
            year_info_div = soup.find('div', class_='car-base-info')
            if year_info_div:
                year_text = year_info_div.find('li').get_text() # Assuming first li is year
                year_match = re.search(r'(\d{4})', year_text)
                if year_match:
                    data['year'] = int(year_match.group(1))
                    # Month is not available in this format, default to 1
                    data['month'] = 1

        if data.get('year') == 1900 and data.get('month') == 1:
            data['special_message'] = "В объявлении не указан год выпуска автомобиля, невозможно корректно провести расчёт"
            return data, None

        if not data['year']:
             error = "Не удалось найти год."
        logging.info(f"Year parsing result: year={data['year']}, month={data.get('month')}, error={error}")

        # Определение типа двигателя и объема
        text_content = soup.get_text()
        logging.info(f"Full text content for engine parsing:\n{text_content}")

        is_hybrid = any(keyword in text_content for keyword in ["混合动力", "油电混合", "插电式混合动力", "插混", "增程式"])
        is_electric = "0L" in text_content or "纯电动" in text_content
        
        logging.info(f"Is hybrid check: {is_hybrid}")
        logging.info(f"Is electric check: {is_electric}")

        if is_hybrid:
            data['engine_type'] = 'ice'
            volume_match = re.search(r'(\d+\.?\d*)\s*L', text_content)
            if volume_match:
                data['volume'] = int(float(volume_match.group(1)) * 1000)
            data['power'] = None
        elif is_electric:
            data['engine_type'] = 'electro'
            data['volume'] = 0
            # Search for power in kW, e.g., "150kW"
            power_match = re.search(r'(\d+)\s*kW', text_content, re.IGNORECASE)
            if power_match:
                data['power'] = int(power_match.group(1))
            else:
                # Fallback or error handling if power is not found
                data['power'] = 0
        else:
            data['engine_type'] = 'ice'
            data['power'] = None
            volume_match = re.search(r'(\d+\.?\d*)\s*L', text_content)
            logging.info(f"Volume match: {volume_match}")
            if volume_match:
                data['volume'] = int(float(volume_match.group(1)) * 1000) # L to cc

        if data['volume'] is None and data['power'] is None:
            error = "Не удалось определить объем или мощность двигателя."
        
        logging.info(f"Final parsed data: {data}")
        logging.info(f"Final error state: {error}")

    except Exception as e:
        error = f"Произошла непредвиденная ошибка при парсинге che168.com: {e}"
        logging.error(error)

    return data, error
