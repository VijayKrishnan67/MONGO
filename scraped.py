import os
import pytz
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from pymongo import MongoClient

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = "stock_data"
COLLECTION_NAME = "market_movers"

def get_current_ist():
    ist = pytz.timezone('Asia/Kolkata')
    return datetime.now(ist).strftime('%Y-%m-%d %H:%M:%S')

def connect_mongo():
    client = MongoClient(MONGO_URI)
    return client[DATABASE_NAME][COLLECTION_NAME]

def scrape_tradingview():
    chrome_options = Options()
    chrome_options.add_argument("--headless=new")  # Use new headless mode
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920x1080")


    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
    url = "https://www.tradingview.com/markets/stocks-usa/market-movers-large-cap/"
    driver.get(url)

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
            if len(columns) < 12:
                continue

            col_values = [col.text.strip() for col in columns]

            stock_data = {
                "name_info": col_values[0],
                "market_cap": col_values[1],
                "price": col_values[2],
                "percent_change": col_values[3],
                "volume": col_values[4],
                "change": col_values[5],
                "pe_ratio": col_values[6],
                "eps": col_values[7],
                "weekly_change": col_values[8],
                "monthly_change": col_values[9],
                "sector": col_values[10],
                "analyst_rating": col_values[11],
                "timestamp_ist": get_current_ist()
            }

            data.append(stock_data)

        except Exception as e:
            print(f"Error parsing row: {e}")

    driver.quit()
    return data

def update_mongodb(data):
    collection = connect_mongo()
    if data:
        collection.insert_many(data)
        print("Data successfully inserted into MongoDB.")

if __name__ == "__main__":
    stock_data = scrape_tradingview()
    if stock_data:
        update_mongodb(stock_data)
