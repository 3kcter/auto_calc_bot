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
    },
    'more_than_7': {
        'by_volume': [
            (1000, 3.0), (1500, 3.2), (1800, 3.5), (2500, 4.8),
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
    (4200000, 16524), (5500000, 21344), (7000000, 27540), (float('inf'), 30000)
]

def _get_rate_from_table(value, table):
    for limit, rate in table:
        if value <= limit:
            return rate
    return table[-1][1]

def _calculate_customs_payments(age, cost_eur, volume, engine_type):
    if engine_type == 'electro':
        return cost_eur * 0.15

    age_category = 'older'
    if age == 'up_to_3':
        age_category = 'up_to_3'
    elif age == '3_to_5':
        age_category = '3_to_5'
    elif age == '5_to_7':
        age_category = '5_to_7'
    else:
        age_category = 'more_than_7'

    rates = CUSTOMS_PAYMENTS_RATES.get(age_category, {})
    
    if 'by_cost' in rates:
        for limit, rate_percent, rate_eur in rates['by_cost']:
            if cost_eur < limit:
                return max(cost_eur * rate_percent, rate_eur * volume)
    elif 'by_volume' in rates:
        for limit, rate_eur in rates['by_volume']:
            if volume <= limit:
                return rate_eur * volume
    return 0

def _calculate_recycling_fee(age, volume, engine_type):
    fee_category = 'electric_hybrid' if engine_type == 'electro' else 'ice'
    age_category = 'up_to_3' if age == 'up_to_3' else 'older'
    
    rates = RECYCLING_FEE_RATES[fee_category]
    
    if fee_category == 'electric_hybrid':
        return rates[age_category]
    
    return _get_rate_from_table(volume, rates[age_category])

def _calculate_customs_clearance(cost_rub):
    return _get_rate_from_table(cost_rub, CUSTOMS_CLEARANCE_FEES)

async def calculate_cost(age: str, cost: int, currency: str, volume: int, calc_config: CalcConfig, engine_type: str = 'ice') -> dict:
    rates = await get_rates()
    cost_rub = cost * rates.get(currency, 1.0)
    eur_rate = rates.get('EUR', 90.0)
    cost_eur = cost_rub / eur_rate

    customs_payments_eur = _calculate_customs_payments(age, cost_eur, volume, engine_type)
    customs_payments = customs_payments_eur * eur_rate

    recycling_fee = _calculate_recycling_fee(age, volume, engine_type)
    customs_clearance = _calculate_customs_clearance(cost_rub)

    total_cost = (
        cost_rub + calc_config.korea_dealer_commission + customs_payments + recycling_fee +
        customs_clearance + calc_config.sbkts_and_epts +
        calc_config.loading_and_unloading_and_temporary_storage + calc_config.ferry + calc_config.other_expenses
    )

    vat = 0
    if engine_type == 'electro':
        vat = (cost_rub + customs_payments) * 0.20
        total_cost += vat

    return {
        "car_cost": cost_rub,
        "korea_dealer_commission": calc_config.korea_dealer_commission,
        "customs_payments": customs_payments,
        "recycling_fee": recycling_fee,
        "customs_clearance": customs_clearance,
        "sbkts_and_epts": calc_config.sbkts_and_epts,
        "loading_and_unloading_and_temporary_storage": calc_config.loading_and_unloading_and_temporary_storage,
        "ferry": calc_config.ferry,
        "other_expenses": calc_config.other_expenses,
        "vat": vat,
        "total_cost": total_cost,
    }
