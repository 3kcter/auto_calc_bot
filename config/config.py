from dataclasses import dataclass, asdict
from environs import Env
import json
import aiofiles

@dataclass
class TgBot:
    token: str
    admin_ids: list[int]
    channel_id: int
    channel_url: str

@dataclass
class LogSettings:
    level: str
    format: str

@dataclass
class ChinaConfig:
    dealer_commission: int
    documents_delivery_cny: int
    logistics_kazan_usd: int
    logistics_kazan_rub: int
    lab_svh_kazan_rub: int
    lab_svh_not_kazan_rub: int
    other_expenses_rub: int

@dataclass
class KoreaConfig:
    dealer_commission_krw: int
    inland_transport_krw: int
    port_transport_loading_krw: int
    vladivostok_expenses_rub: int
    logistics_vladivostok_kazan_rub: int
    car_preparation_rub: int
    other_expenses_rub: int

@dataclass
class GeneralConfig:
    delivery_to_region_rub: int

@dataclass
class CalcConfig:
    china: ChinaConfig
    korea: KoreaConfig
    general: GeneralConfig

@dataclass
class Config:
    bot: TgBot
    log: LogSettings
    calc: CalcConfig

def load_calc_config(path: str = 'calc_config.json') -> CalcConfig:
    with open(path, 'r') as f:
        data = json.load(f)
        return CalcConfig(
            china=ChinaConfig(**data['china']),
            korea=KoreaConfig(**data['korea']),
            general=GeneralConfig(**data['general'])
        )

async def load_calc_config_async(path: str = 'calc_config.json') -> CalcConfig:
    async with aiofiles.open(path, 'r', encoding='utf-8') as f:
        data = json.loads(await f.read())
        return CalcConfig(
            china=ChinaConfig(**data['china']),
            korea=KoreaConfig(**data['korea']),
            general=GeneralConfig(**data['general'])
        )

def save_calc_config(config: CalcConfig, path: str = 'calc_config.json'):
    with open(path, 'w') as f:
        json.dump(asdict(config), f, indent=4)

async def save_calc_config_async(config: CalcConfig, path: str = 'calc_config.json'):
    async with aiofiles.open(path, 'w', encoding='utf-8') as f:
        await f.write(json.dumps(asdict(config), indent=4))

def load_config(path: str | None = None) -> Config:
    env: Env = Env()
    env.read_env(path)

    return Config(
        bot=TgBot(
            token=env('BOT_TOKEN'),
            admin_ids=list(map(int, env.list('ADMIN_IDS'))),
            channel_id=env('CHANNEL_ID'),
            channel_url=env('CHANNEL_URL')
        ),
        log=LogSettings(level=env('LOG_LEVEL'), format=env('LOG_FORMAT')),
        calc=load_calc_config()
    )