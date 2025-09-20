import asyncio
from services.parser import parse_encar_requests, validate_and_normalize_url

async def main():
    url = "https://fem.encar.com/cars/detail/40229222"
    normalized_url, error = validate_and_normalize_url(url)
    if error:
        print(error)
        return

    data, error = await parse_encar_requests(normalized_url)
    if error:
        print(f"Error: {error}")
    else:
        for key, value in data.items():
            print(f"{key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())
