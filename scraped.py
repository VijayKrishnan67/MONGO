import time
import re
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient

# MongoDB Atlas Connection URI (Replace with your credentials or use environment variable)
MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "stock_data"
COLLECTION_NAME = "market_movers"
print("exist")
def clean_number(value):
    """Convert numbers with suffixes like T, B, M, K to float"""
    value = value.replace("\u202f", "").replace(",", "")  # Remove non-breaking spaces and commas

    if "T" in value:
        return float(value.replace("T", "")) * 1e12
    elif "B" in value:
        return float(value.replace("B", "")) * 1e9
    elif "M" in value:
        return float(value.replace("M", "")) * 1e6
    elif "K" in value:
        return float(value.replace("K", "")) * 1e3
    return float(value)

def connect_mongo():
    """Connect to MongoDB Atlas"""
    client = MongoClient(MONGO_URI)
    return client[DATABASE_NAME][COLLECTION_NAME]

def scrape_tradingview():
    """Scrape stock data from TradingView Market Movers"""

    chrome_options = Options()
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920x1080")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    url = "https://www.tradingview.com/markets/stocks-usa/market-movers-large-cap/"
    driver.get(url)

    # Wait for the stock table to load
    try:
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "table tbody tr"))
        )
    except Exception as e:
        print("Timeout: Data table not found")
        driver.quit()
        return []

    rows = driver.find_elements(By.CSS_SELECTOR, "table tbody tr")
    print(f"Found {len(rows)} rows")

    data = []
    for row in rows:
        try:
            columns = row.find_elements(By.TAG_NAME, "td")
            if len(columns) < 5:
                continue

            name = columns[0].text.split("\n")[0]
            raw_price = columns[1].text.strip()
            raw_change = columns[2].text.strip()
            raw_percent_change = columns[3].text.strip()
            raw_volume = columns[4].text.strip()

            price = clean_number(raw_price.split(" ")[0])
            change = clean_number(raw_change.replace("USD", "").strip())
            percent_change = float(raw_percent_change.replace("%", "").replace("−", "-"))
            volume = clean_number(raw_volume)

            stock_data = {
                "name": name,
                "price": price,
                "change": change,
                "percent_change": percent_change,
                "volume": volume,
                "timestamp": time.time()
            }
            data.append(stock_data)
        except Exception as e:
            print(f"Error parsing row: {e}")

    driver.quit()
    return data

def update_mongodb(data):
    """Insert stock data into MongoDB without checking for existing entries"""
    collection = connect_mongo()
    if data:
        collection.insert_many(data)
        print("Data successfully inserted into MongoDB.")


stock_data = scrape_tradingview()
if stock_data:
    update_mongodb(stock_data)
