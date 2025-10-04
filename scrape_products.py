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
import random # Import random for random delays
from selenium_stealth import stealth
from webdriver_manager.chrome import ChromeDriverManager

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
    # Common arguments for stealth and stability
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_argument("--start-maximized")
    chrome_options.add_argument("--disable-extensions")
    chrome_options.add_argument("--disable-features=site-per-process")
    chrome_options.add_argument("--disable-popup-blocking")
    chrome_options.add_argument("--profile-directory=Default")
    chrome_options.add_argument("--incognito")
    chrome_options.add_argument("--disable-background-networking")
    chrome_options.add_argument("--enable-automation")
    chrome_options.add_argument("--disable-background-timer-throttling")
    chrome_options.add_argument("--disable-backgrounding-occluded-windows")
    chrome_options.add_argument("--disable-breakpad")
    chrome_options.add_argument("--disable-client-side-phishing-detection")
    chrome_options.add_argument("--disable-component-update")
    chrome_options.add_argument("--disable-default-apps")
    chrome_options.add_argument("--disable-hang-monitor")
    chrome_options.add_argument("--disable-ipc-flooding-protection")
    chrome_options.add_argument("--disable-notifications")
    chrome_options.add_argument("--disable-offer-store-unmasked-wallet-cards")
    chrome_options.add_argument("--disable-print-preview")
    chrome_options.add_argument("--disable-prompt-on-repost")
    chrome_options.add_argument("--disable-renderer-backgrounding")
    chrome_options.add_argument("--disable-sync")
    chrome_options.add_argument("--hide-scrollbars")
    chrome_options.add_argument("--metrics-recording-only")
    chrome_options.add_argument("--mute-audio")
    chrome_options.add_argument("--no-first-run")
    chrome_options.add_argument("--safebrowsing-disable-auto-update")
    chrome_options.add_argument("--enable-blink-features=IdleDetection")

    if headless_mode:
        chrome_options.add_argument("--headless=new") # Use new headless mode

    # Setup Chrome driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    # Apply stealth settings
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            app_version="5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            os_cpu="Intel Mac OS X", # Spoofing OS for better stealth
            device_memory=8, # Spoofing device memory
            navigator_platform="Win32",
            navigator_vendor="Google Inc.",
            navigator_plugins=["Chrome PDF Plugin", "Chrome PDF Viewer"], # Spoofing plugins
            navigator_mimetypes=["application/pdf", "application/x-google-chrome-pdf"], # Spoofing mimetypes
            )

    # Execute CDP command to disable automation flags
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": """
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5] // Mimic a few plugins
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            Object.defineProperty(navigator, 'deviceMemory', {
                get: () => 8 // Mimic device memory
            });
            Object.defineProperty(navigator, 'maxTouchPoints', {
                get: () => 0 // Mimic no touch screen
            });
            Object.defineProperty(navigator, 'hardwareConcurrency', {
                get: () => 8 // Mimic CPU cores
            });
            window.chrome = {
                runtime: {},
                // Add other properties if needed
            };
            // Further spoofing for window.outerWidth/innerWidth if necessary
            // This might require more dynamic adjustments based on actual browser window
            window.outerWidth = window.innerWidth;
            window.outerHeight = window.innerHeight;
        """
    })
    return driver

def handle_amazon_home_link(driver, current_page_num, base_url):
    """
    Checks for the 'Go to the Amazon.in home page to continue shopping' link.
    If found, clicks it, waits for the home page to load, and then
    either restarts scraping from page 1 or navigates back to the current page.
    Returns the page number to continue scraping from.
    """
    try:
        # Look for the link by its text
        home_link = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Go to the Amazon.in home page to continue shopping"))
        )
        
        print("Found 'Go to the Amazon.in home page to continue shopping' link. Clicking it.")
        home_link.click()
        
        # Wait for the home page to load
        WebDriverWait(driver, 10).until(
            EC.url_contains("amazon.in") # Assuming it navigates to amazon.in home
        )
        print("Navigated to Amazon.in home page.")

        # Now, navigate back to the correct product search page
        target_url = f"{base_url}&page={current_page_num}" if current_page_num > 1 else base_url
        print(f"Navigating to product search page {current_page_num}: {target_url}")
        driver.get(target_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        print(f"Successfully navigated to product search page {current_page_num}.")
        return True # Indicate that the link was found and handled
            
    except Exception as e:
        # Link not found or other error, continue as normal
        # print(f"Amazon home link not found or error during handling: {e}")
        return False # Indicate that the link was not found or an error occurred

def scrape_page(driver, url):
    """Navigates to a URL, waits for content, and returns page source."""
    # Add a random delay before navigating to the URL to simulate human behavior
    time.sleep(random.uniform(1, 3)) # Random delay between 1 and 3 seconds
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

            # Check for the "Go to the Amazon.in home page" link
            # This needs to happen before parsing products, as the link might replace product listings
            # If the link is found and handled, the page_num might change or the driver navigates.
            # Check for the "Go to the Amazon.in home page" link
            link_was_handled = handle_amazon_home_link(driver, page_num, base_url)
            
            if link_was_handled:
                # If the link was handled, the driver is now on the correct product search page.
                # We need to re-fetch the HTML content from the current driver state.
                print(f"Amazon home link handled. Re-fetching HTML content from current driver state for page {page_num}.")
                html_content = driver.page_source
                no_product_pages_count = 0 # Reset counter as we've navigated and are on a fresh product page
            
            page_products = parse_products(html_content)
            
            if not page_products:
                no_product_pages_count += 1
                print(f"No non-sponsored products found on page {page_num}. Consecutive empty pages: {no_product_pages_count}")
                time.sleep(180) # Wait for 3 minutes before trying again
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
            time.sleep(random.uniform(2, 5)) # Be polite and avoid hammering the server, random delay

    except KeyboardInterrupt:
        print("\nScraping interrupted by user (KeyboardInterrupt). Saving current progress and exiting.")
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if driver:
            driver.quit()
        
    print("Scraping process finished.")

if __name__ == "__main__":
    main()
