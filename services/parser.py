import re
import json
import logging
from bs4 import BeautifulSoup

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
        'country': 'china',
        'engine_type': None
    }
    error = None

    try:
        soup = BeautifulSoup(html_content, 'lxml')

        # Извлечение данных из скрытых полей ввода
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

        if not data['year']:
             error = "Не удалось найти год."
        logging.info(f"Year parsing result: year={data['year']}, month={data.get('month')}, error={error}")

        # Определение типа двигателя и объема
        text_content = soup.get_text()
        logging.info(f"Full text content for engine parsing:\n{text_content}")

        is_electric = "0L" in text_content or "纯电动" in text_content
        logging.info(f"Is electric check: {is_electric}")

        if is_electric:
            data['engine_type'] = 'electro'
            capacity_match = re.search(r'(\d+\.?\d*)\s*kwh', text_content, re.IGNORECASE)
            logging.info(f"Capacity match: {capacity_match}")
            if capacity_match:
                data['volume'] = int(float(capacity_match.group(1)) * 1000) # kWh to Wh
            else:
                data['volume'] = 0
        else:
            data['engine_type'] = 'ДВС'
            volume_match = re.search(r'(\d+\.?\d*)\s*L', text_content)
            logging.info(f"Volume match: {volume_match}")
            if volume_match:
                data['volume'] = int(float(volume_match.group(1)) * 1000) # L to cc

        if data['volume'] is None:
            error = "Не удалось определить объем двигателя."
        
        logging.info(f"Final parsed data: {data}")
        logging.info(f"Final error state: {error}")

    except Exception as e:
        error = f"Произошла непредвиденная ошибка при парсинге che168.com: {e}"
        logging.error(error)

    return data, error

