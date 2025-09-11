from services.cache import get_rates
from config.config import CalcConfig

CUSTOMS_PAYMENTS_RATES = {
    'up_to_3': {
        'by_cost': [
            (8500, 0.54, 2.5), (16700, 0.48, 3.5), (42300, 0.48, 5.5),
            (84500, 0.48, 7.5), (169000, 0.48, 15), (float('inf'), 0.48, 20)
        ]
    },
    '3_to_5': {
        'by_volume': [
            (1000, 1.5), (1500, 1.7), (1800, 2.5), (2300, 2.7),
            (3000, 3.0), (float('inf'), 3.6)
        ]
    },
    '5_to_7': {
        'by_volume': [
            (1000, 3.0), (1500, 3.2), (1800, 3.5), (2300, 4.8),
            (3000, 5.0), (float('inf'), 5.7)
        ]
    }
}

RECYCLING_FEE_RATES = {
    'electric_hybrid': {'up_to_3': 3400, 'older': 5200},
    'ice': {
        'up_to_3': [(3000, 3400), (3500, 2153400), (float('inf'), 2742200)],
        'older': [(3000, 5200), (3500, 3296800), (float('inf'), 3604800)]
    }
}

CUSTOMS_CLEARANCE_FEES = [
    (200000, 1067), (450000, 2134), (1200000, 4269), (2700000, 11746),
    (4200000, 16524), (5500000, 21344), (7000000, 27540), (8000000, 30000),
    (9000000, 30000), (10000000, 30000), (float('inf'), 30000)
]

def _get_rate_from_table(value, table):
    for limit, rate in table:
        if value <= limit:
            return rate
    return table[-1][1]

def _get_row_from_table(value, table):
    for row in table:
        if value <= row[0]:
            return row
    return table[-1]

def _calculate_customs_payments(age, cost_eur, volume, engine_type):
    if engine_type == 'electro':
        return cost_eur * 0.15

    age_category = ''
    if age == 'year_less_3':
        age_category = 'up_to_3'
    elif age == 'year_3_5':
        age_category = '3_to_5'
    elif age == 'year_more_5':
        age_category = '5_to_7'

    rates = CUSTOMS_PAYMENTS_RATES.get(age_category, {})
    
    if not rates:
        return 0

    if 'by_cost' in rates:
        # For cars up to 3 years old, the calculation is per euro of cost or per cm3 of volume
        rate_info = _get_row_from_table(cost_eur, rates['by_cost'])
        return min(cost_eur * rate_info[1], rate_info[2] * volume)

    elif 'by_volume' in rates:
        rate_eur = _get_rate_from_table(volume, rates['by_volume'])
        return rate_eur * volume
    return 0

def _calculate_recycling_fee(age, volume, engine_type):
    fee_category = 'electric_hybrid' if engine_type == 'electro' else 'ice'
    
    age_category = 'older'
    if age == 'year_less_3':
        age_category = 'up_to_3'

    rates = RECYCLING_FEE_RATES[fee_category]
    
    if fee_category == 'electric_hybrid':
        return rates[age_category]
    
    return _get_rate_from_table(volume, rates[age_category])

def _calculate_customs_clearance(cost_rub):
    return _get_rate_from_table(cost_rub, CUSTOMS_CLEARANCE_FEES)

COUNTRY_CURRENCY_MAP = {
    'china': 'CNY',
    'korea': 'KRW'
}

async def calculate_cost(age: str, cost: int, country: str, volume: int, calc_config: CalcConfig, engine_type: str = 'ice', is_from_kazan: str | None = None) -> dict:
    rates = await get_rates()
    
    currency = COUNTRY_CURRENCY_MAP.get(country)
    
    cost_rub = cost * rates.get(currency, 1.0)
    eur_rate = rates.get('EUR', 90.0)
    usd_rate = rates.get('USD', 90.0)
    cny_rate = rates.get('CNY', 12.0)
    cost_eur = cost_rub / eur_rate

    customs_payments_eur = _calculate_customs_payments(age, cost_eur, volume, engine_type)
    customs_payments = customs_payments_eur * eur_rate

    recycling_fee = _calculate_recycling_fee(age, volume, engine_type)
    customs_clearance = _calculate_customs_clearance(cost_rub)

    dealer_commission = 0
    if country == 'korea':
        dealer_commission = calc_config.korea_dealer_commission
    elif country == 'china':
        dealer_commission = calc_config.china_dealer_commission

    china_documents_delivery = 0
    logistics_cost = 0
    lab_svh_cost = 0

    if country == 'china':
        china_documents_delivery = calc_config.china_documents_delivery_cny * cny_rate
        
        logistics_cost = calc_config.logistics_kazan_usd * usd_rate + calc_config.logistics_kazan_rub
        if is_from_kazan == 'no':
            logistics_cost += 40000

        lab_svh_cost = calc_config.lab_svh_kazan_rub
        if is_from_kazan == 'no':
            lab_svh_cost = calc_config.lab_svh_not_kazan_rub

    total_cost_rub = (
        cost_rub + dealer_commission + customs_payments + recycling_fee +
        customs_clearance + china_documents_delivery + logistics_cost + lab_svh_cost
    )

    vat = 0
    # if engine_type == 'electro':
    #     vat = (cost_rub + customs_payments) * 0.20
    #     total_cost_rub += vat

    # Convert total_cost_rub back to original currency
    rate_to_original_currency = rates.get(currency, 1.0)
    total_cost_original_currency = total_cost_rub / rate_to_original_currency

    return {
        "car_cost": cost_rub,
        "korea_dealer_commission": calc_config.korea_dealer_commission,
        "china_dealer_commission": calc_config.china_dealer_commission,
        "customs_payments": customs_payments,
        "recycling_fee": recycling_fee,
        "customs_clearance": customs_clearance,
        "china_documents_delivery": china_documents_delivery,
        "logistics_cost": logistics_cost,
        "lab_svh_cost": lab_svh_cost,
        "vat": vat,
        "total_cost": total_cost_original_currency,
        "total_cost_rub": total_cost_rub,
    }
    print("Calculated costs:", {
        "car_cost": cost_rub,
        "korea_dealer_commission": calc_config.korea_dealer_commission,
        "china_dealer_commission": calc_config.china_dealer_commission,
        "customs_payments": customs_payments,
        "recycling_fee": recycling_fee,
        "customs_clearance": customs_clearance,
        "china_documents_delivery": china_documents_delivery,
        "logistics_cost": logistics_cost,
        "lab_svh_cost": lab_svh_cost,
        "vat": vat,
        "total_cost": total_cost_original_currency,
        "total_cost_rub": total_cost_rub,
    })
