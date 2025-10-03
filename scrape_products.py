import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import os
import shutil # Import shutil for rmtree
import time

# --- Configuration Variables ---
product = "mobile_phones"  # Manually set by developer, must match key in product_links.json
headless = True           # Toggle for headless/headful browser mode

# --- Constants ---
PRODUCT_LINKS_FILE = "product_links.json"
OUTPUT_FOLDER = "temp" # Folder to save downloaded HTML and scraped data

# Ensure output folder exists
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

def clear_output_folder(folder_path):
    """Clears all contents of the specified folder."""
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'Failed to delete {file_path}. Reason: {e}')

def load_product_links(file_path, product_key):
    """Loads product links from a JSON file and returns the URL for the specified product key."""
    with open(file_path, 'r') as f:
        data = json.load(f)
        for item in data:
            if product_key in item:
                return item[product_key]
    return None

def setup_driver(headless_mode):
    """Sets up and returns a Selenium WebDriver instance."""
    chrome_options = Options()
    if headless_mode:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_argument("--start-maximized") # Open browser in maximized mode

    # Assuming chromedriver is in PATH or specify path
    # service = Service(executable_path="/path/to/chromedriver")
    driver = webdriver.Chrome(options=chrome_options)
    return driver

def scrape_page(driver, url):
    """Navigates to a URL, waits for content, and returns page source."""
    driver.get(url)
    # Wait for the page to load dynamically. Adjust the condition as needed.
    # For example, wait for a specific element to be present.
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, 'body')) # Wait for the body tag to be present
    )
    return driver.page_source

def parse_products(html_content):
    """Parses HTML content to extract product details."""
    soup = BeautifulSoup(html_content, 'html.parser')
    products_data = []

    # Amazon-specific selectors (these are common but might need adjustment based on live page)
    # Product listings are typically within divs with role="listitem" or similar
    product_listings = soup.find_all('div', {'data-component-type': 's-search-result'})

    for product_listing in product_listings:
        # Product Name / Title and Sponsored Product Check
        product_name = "N/A"
        h2_tag = product_listing.select_one('h2.a-size-base-plus.a-spacing-none.a-color-base.a-text-normal')
        if h2_tag:
            aria_label = h2_tag.get('aria-label', '')
            if "Sponsored Ad" in aria_label:
                continue # Skip sponsored products
            
            # Extract product name from aria-label or inner span
            if aria_label and not aria_label.startswith("{"): # Check if aria_label is valid
                product_name = aria_label
            else:
                span_tag = h2_tag.select_one('span')
                if span_tag:
                    product_name = span_tag.get_text(strip=True)

        # Further validation for product name (optional, as aria-label should be clean)
        if product_name and (len(product_name) < 5 or "on select bank cards" in product_name.lower() or "offer" in product_name.lower()):
            product_name = "N/A" # Filter out short or promotional names

        # Product Price (using a-price-whole and a-price-fraction)
        price_whole_tag = product_listing.select_one('span.a-price-whole')
        price_fraction_tag = product_listing.select_one('span.a-price-fraction')
        if price_whole_tag and price_fraction_tag:
            product_price = f"{price_whole_tag.get_text(strip=True)}{price_fraction_tag.get_text(strip=True)}"
        elif price_whole_tag:
            product_price = price_whole_tag.get_text(strip=True)
        else:
            product_price = "N/A"

        # Product URL
        product_url_tag = product_listing.find('a', class_='a-link-normal', href=True)
        product_url = product_url_tag['href'] if product_url_tag else "N/A"

        # Prepend base URL if product_url is relative
        if product_url and not product_url.startswith('http') and product_url != "N/A":
            # Assuming the base URL is for amazon.in, we can construct the full URL
            # This needs to be more robust if the domain changes.
            product_url = f"https://www.amazon.in{product_url}"

        if product_name != "N/A" and product_price != "N/A" and product_url != "N/A":
            products_data.append({
                "product_name": product_name,
                "product_price": product_price,
                "product_url": product_url
            })
    return products_data

def save_to_json(data, filename):
    """Saves data to a JSON file, appending if file exists."""
    # Save directly to the root directory
    file_path = filename
    if os.path.exists(file_path):
        with open(file_path, 'r+', encoding='utf-8') as f:
            existing_data = json.load(f)
            existing_data.extend(data)
            f.seek(0)
            json.dump(existing_data, f, indent=4, ensure_ascii=False)
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)

def main():
    # Clear the output folder at the beginning
    print(f"Clearing contents of '{OUTPUT_FOLDER}' folder...")
    clear_output_folder(OUTPUT_FOLDER)
    print(f"Contents of '{OUTPUT_FOLDER}' cleared.")

    base_url = load_product_links(PRODUCT_LINKS_FILE, product)

    if not base_url:
        print(f"Error: Product '{product}' not found in {PRODUCT_LINKS_FILE}")
        return

    # Clear the content of the product JSON file at the beginning
    output_filename = f"{product}.json"
    if os.path.exists(output_filename):
        print(f"Clearing content of '{output_filename}'...")
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump([], f) # Write an empty JSON array
        print(f"Content of '{output_filename}' cleared.")

    page_num = 1
    no_product_pages_count = 0 # Counter for consecutive pages with no non-sponsored products
    driver = None

    try:
        driver = setup_driver(headless)
        while True:
            current_url = f"{base_url}&page={page_num}" if page_num > 1 else base_url
            print(f"Scraping page {page_num}: {current_url}")

            html_content = scrape_page(driver, current_url)

            page_products = parse_products(html_content)
            
            if not page_products:
                no_product_pages_count += 1
                print(f"No non-sponsored products found on page {page_num}. Consecutive empty pages: {no_product_pages_count}")
                if no_product_pages_count >= 3:
                    print("No non-sponsored products found on 3 consecutive pages. Exiting program.")
                    break
            else:
                no_product_pages_count = 0 # Reset counter if products are found
                # Save products for the current page directly to JSON
                output_filename = f"{product}.json"
                save_to_json(page_products, output_filename)
                print(f"Found {len(page_products)} products on page {page_num}. Appended to {output_filename}.")

            # Implement a more robust check for next page availability if possible
            # For now, a simple page increment. You might need to check for a "next page" button/link.
            page_num += 1
            time.sleep(2) # Be polite and avoid hammering the server

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if driver:
            driver.quit()
        
    print("Scraping process finished.")

if __name__ == "__main__":
    main()
