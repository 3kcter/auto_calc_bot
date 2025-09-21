import re
import json
import logging
from bs4 import BeautifulSoup
import aiohttp
from playwright.async_api import async_playwright

def validate_and_normalize_url(url: str) -> tuple[str | None, str | None]:
    if 'che168.com' in url:
        return url.split('?')[0], None
    if 'encar.com' in url:
        return url.split('?')[0], None
    return None, "Пожалуйста, отправьте ссылку на сайт che168.com или encar.com"

async def parse_encar_playwright(url: str) -> tuple[dict, str | None]:
    logging.info(f"Starting to parse encar.com data using Playwright for URL: {url}")
    data = {
        'car_name': None, 'year': None, 'month': None, 'mileage': None, 'cost': None,
        'currency': 'KRW', 'volume': None, 'power': None, 'power_unit': None,
        'country': 'korea', 'engine_type': None
    }
    error = None
    
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(headless=False)
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36'
            )
            page = await context.new_page()
            await page.goto(url, wait_until='domcontentloaded', timeout=60000)

            preloaded_state = await page.evaluate("window.__PRELOADED_STATE__")

            if preloaded_state:
                logging.info("Found __PRELOADED_STATE__. Parsing data from it.")
                car_info = preloaded_state.get('cars', {}).get('base', {})
                if car_info:
                    category_info = car_info.get('category', {})
                    if category_info:
                        manufacturer = category_info.get('manufacturerName', '')
                        model = category_info.get('modelGroupName', '')
                        grade = category_info.get('gradeDetailName', '')
                        data['car_name'] = f"{manufacturer} {model} {grade}".strip()
                        
                        year_month = str(category_info.get('yearMonth'))
                        if len(year_month) == 6:
                            data['year'] = int(year_month[:4])
                            data['month'] = int(year_month[4:])

                    advertisement_info = car_info.get('advertisement', {})
                    if advertisement_info and advertisement_info.get('price'):
                        try:
                            data['cost'] = int(advertisement_info['price']) * 10000
                        except (ValueError, TypeError):
                            logging.warning(f"Could not parse price from preloaded state: {advertisement_info['price']}")
                    
                    spec_info = car_info.get('spec', {})
                    if spec_info:
                        data['mileage'] = spec_info.get('mileage')
                        data['volume'] = spec_info.get('displacement')
                        fuel_name = spec_info.get('fuelName', '').lower()
                        if '가솔린' in fuel_name or '디젤' in fuel_name:
                            data['engine_type'] = 'ice'
                        elif '전기' in fuel_name:
                            data['engine_type'] = 'electro'
                            data['volume'] = 0

                else:
                    error = "Could not find 'base' info in __PRELOADED_STATE__"
            else:
                error = "Could not find __PRELOADED_STATE__ in page."
                logging.warning(error)


            required_fields = ['year', 'cost', 'car_name', 'mileage']
            if data.get('engine_type') != 'electro':
                required_fields.append('volume')

            if not all(data.get(k) for k in required_fields):
                if not error:
                    error = "Не удалось извлечь все данные из __PRELOADED_STATE__."
                logging.error(f"Failed to parse all required data from encar.com. Data: {data}")

        except Exception as e:
            error = f"Произошла непредвиденная ошибка при парсинге encar.com с помощью Playwright: {e}"
            logging.error(error)
        finally:
            if 'browser' in locals() and browser:
                await browser.close()

    logging.info(f"Final parsed data for encar.com (Playwright): {data}")
    logging.info(f"Final error state for encar.com (Playwright): {error}")
    return data, error

async def parse_encar_requests(url: str) -> tuple[dict, str | None]:
    return await parse_encar_playwright(url)

def parse_che168_requests(html_content: str) -> tuple[dict, str | None]:
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
        text_content = soup.get_text()
        is_electric = "纯电动" in text_content
        if is_electric:
            data['engine_type'] = 'electro'
            data['volume'] = 0
            data['power_unit'] = 'кВт'
            power_text = _find_spec_value(soup, '最大功率(kW)')
            if power_text:
                power_match = re.search(r'(\d+)', power_text)
                if power_match:
                    data['power'] = int(power_match.group(1))
            if not data['power']:
                power_match = re.search(r'(\d+)\s*kW', text_content, re.IGNORECASE)
                if power_match:
                    data['power'] = int(power_match.group(1))
        else:
            data['engine_type'] = 'ice'
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

def _find_spec_value(soup: BeautifulSoup, label_text: str) -> str | None:
    try:
        label_tag = soup.find(lambda tag: tag.name and label_text in tag.text)
        if not label_tag:
            return None
        
        parent_li = label_tag.find_parent('li')
        if parent_li:
            value_tag = parent_li.find('p')
            if value_tag:
                return value_tag.text.strip()

        parent_td = label_tag.find_parent('td')
        if parent_td:
            next_td = parent_td.find_next_sibling('td')
            if next_td:
                return next_td.text.strip()
        
        parent = label_tag.parent
        value_tag = parent.find(['p', 'span', 'div'], class_=lambda x: x != 'label')
        if value_tag:
            return value_tag.text.strip()

    except Exception:
        return None
    return None
