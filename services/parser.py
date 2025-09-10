import re
import json

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

    elif 'che168.com' in url:
        try:
            year_match = re.search(r'<span class="item-name">.*?</span>(\d{4})\d{2}', html_content)
            if year_match:
                data['year'] = year_match.group(1)

            cost_match = re.search(r'<span class="price" id="overlayPrice">.*?(\d+\.?\d*).*?</span>', html_content)
            if cost_match:
                data['cost'] = int(float(cost_match.group(1)) * 10000)
                data['currency'] = 'CNY'

            volume_match = re.search(r'<span class="item-name">.*?</span>([\d\.]+)L', html_content)
            if volume_match:
                data['volume'] = int(float(volume_match.group(1)) * 1000)
            
            if not all(data.values()):
                error = "Could not extract all necessary data from che168.com"

        except Exception as e:
            error = f"Error parsing che168.com data: {e}"

    return data, error
