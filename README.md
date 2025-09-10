# AutoBot - Telegram Bot for Car Cost Calculation

This Telegram bot helps users calculate the total cost of importing a car, including customs duties and other associated fees. It provides two main functionalities: a step-by-step calculator and a feature to calculate costs by parsing car data from specific URLs.

## Features

### 1. Car Cost Calculator
This feature guides the user through a series of questions to determine the car's total cost.
-   **Input:**
    -   Car Age (e.g., "Less than 3 years", "3 to 5 years", "5 to 7 years", "More than 7 years")
    -   Car Cost (in selected currency)
    -   Currency (RUB, EUR, USD, CNY, KRW)
    -   Engine Volume (in cubic centimeters, e.g., 2000)
-   **Output:**
    -   Detailed breakdown of costs including:
        -   Car cost in RUB
        -   Korean dealer commission
        -   Customs payments
        -   Recycling fee
        -   Customs clearance
        -   SBKTS and EPTS
        -   Loading, unloading, and temporary storage
        -   Ferry
        -   Other expenses
        -   Total cost in RUB

### 2. Calculate by URL
This feature allows users to get a cost calculation by providing a URL to a car listing on supported websites.
-   **Supported Websites:**
    -   encar.com
    -   che168.com
-   **Input:** A direct URL to a car listing on one of the supported websites.
-   **Output:** The bot attempts to parse car data (year, cost, currency, engine volume) from the provided URL and then performs the same cost calculation as the manual calculator, displaying a detailed breakdown.

### 3. Exchange Rates
Users can view the current exchange rates for EUR, USD, KRW, and CNY against the Russian Ruble.

## Customs Duty and Recycling Fee Calculation Logic

The bot implements a complex logic for calculating customs duties and recycling fees based on the car's age, customs value (for cars up to 3 years old), and engine volume.

**Customs Payments:**
-   **Cars up to 3 years old:** Calculated based on the car's customs value in EUR, with different percentage rates and minimum fees per cubic centimeter depending on value tiers.
-   **Cars 3 to 7 years old:** Calculated based on engine volume in EUR per cubic centimeter, with varying rates for different volume ranges.
-   **Cars older than 7 years:** Calculated based on engine volume in EUR per cubic centimeter, with varying rates for different volume ranges.

**Recycling Fee (`Утилизационный сбор`):**
-   **Cars less than 3 years old:**
    -   Engine volume < 3000 cm³: 3,400 RUB
    -   Engine volume 3000-3500 cm³: 2,153,400 RUB
    -   Engine volume > 3500 cm³: 2,742,200 RUB
-   **Cars older than 3 years:**
    -   Engine volume < 3000 cm³: 5,200 RUB
    -   Engine volume 3000-3500 cm³: 3,296,800 RUB
    -   Engine volume > 3500 cm³: 3,604,800 RUB

## How to Use

1.  **Start the bot:** Send the `/start` command in the Telegram chat.
2.  **Main Menu:** You will be presented with options: "Calculator", "Calculate by URL", and "Exchange Rates".
3.  **Calculator:**
    -   Select "Calculator".
    -   Follow the prompts to enter the car's age, cost, currency, and engine volume.
    -   The bot will display the detailed cost breakdown.
4.  **Calculate by URL:**
    -   Select "Calculate by URL".
    -   Send the URL of the car listing from encar.com or che168.com.
    -   The bot will attempt to parse the data and display the cost breakdown.
5.  **Exchange Rates:**
    -   Select "Exchange Rates" to view current currency rates.
6.  **Navigation:** Use "Back" and "Exit" buttons to navigate through the calculator flow or return to the main menu.

## Development Setup (for developers)

To run this bot locally:

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd auto_bot
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Configure environment variables:**
    Create a `.env` file in the root directory with your bot token and admin IDs:
    ```
    BOT_TOKEN=YOUR_BOT_TOKEN
    ADMIN_IDS=YOUR_ADMIN_ID_1,YOUR_ADMIN_ID_2
    ```
4.  **Run the bot:**
    ```bash
    python main.py
    ```