import aiohttp
import xml.etree.ElementTree as ET
from datetime import date

rates_cache = {
    'timestamp': None,
    'rates': {}
}


async def get_cbr_rates_async() -> dict[str, float]:
    url = f"https://www.cbr.ru/scripts/XML_daily.asp?date_req={date.today().strftime('%d/%m/%Y')}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            response.raise_for_status()
            content = await response.read()
            root = ET.fromstring(content)

            rates = {'RUB': 1.0}
            for valute in root.findall('Valute'):
                char_code = valute.find('CharCode').text
                value = valute.find('Value').text.replace(',', '.')
                nominal = valute.find('Nominal').text.replace(',', '.')
                rates[char_code] = float(value) / float(nominal)
            return rates


async def get_rates() -> dict[str, float]:
    today = date.today()
    if rates_cache['timestamp'] == today and rates_cache['rates']:
        return rates_cache['rates']

    rates = await get_cbr_rates_async()
    rates_cache['timestamp'] = today
    rates_cache['rates'] = rates
    return rates
