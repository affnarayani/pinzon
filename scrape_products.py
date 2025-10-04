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

# --- ANSI Color Codes ---
COLOR_RESET = "\033[0m"
COLOR_INFO = "\033[94m"    # Blue
COLOR_SUCCESS = "\033[92m" # Green
COLOR_WARNING = "\033[93m" # Yellow
COLOR_ERROR = "\033[91m"   # Red
COLOR_CRITICAL = "\033[41m\033[97m" # Red background, White text
COLOR_STEP = "\033[96m"    # Cyan

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
            print(f"{COLOR_ERROR}ERR: Failed to delete {file_path}. Reason: {e}{COLOR_RESET}", flush=True)

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
        
        print(f"{COLOR_INFO}INFO: Detected 'Go to Amazon.in home page' link. Clicking to proceed...{COLOR_RESET}", flush=True)
        home_link.click()
        
        # Wait for the home page to load
        WebDriverWait(driver, 10).until(
            EC.url_contains("amazon.in") # Assuming it navigates to amazon.in home
        )
        print(f"{COLOR_INFO}INFO: Successfully navigated to Amazon.in home page.{COLOR_RESET}", flush=True)

        # Now, navigate back to the correct product search page
        target_url = f"{base_url}&page={current_page_num}" if current_page_num > 1 else base_url
        print(f"{COLOR_INFO}INFO: Navigating back to product search page {current_page_num}. URL: {target_url}{COLOR_RESET}", flush=True)
        driver.get(target_url)
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
        print(f"{COLOR_INFO}INFO: Successfully returned to product search page {current_page_num}.{COLOR_RESET}", flush=True)
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
    print(f"\n{COLOR_STEP}--- STEP 1: Initializing Scraping Process ---{COLOR_RESET}", flush=True)
    print(f"{COLOR_STEP}Clearing contents of '{OUTPUT_FOLDER}' folder...{COLOR_RESET}", flush=True)
    clear_output_folder(OUTPUT_FOLDER)
    print(f"{COLOR_STEP}Contents of '{OUTPUT_FOLDER}' cleared.{COLOR_RESET}\n", flush=True)

    base_url = load_product_links(PRODUCT_LINKS_FILE, product)

    if not base_url:
        print(f"{COLOR_ERROR}ERR: Product '{product}' not found in {PRODUCT_LINKS_FILE}. Please check configuration.{COLOR_RESET}", flush=True)
        return

    # Clear the content of the product JSON file at the beginning
    output_filename = f"{product}.json"
    print(f"{COLOR_STEP}--- STEP 2: Preparing Output File ---{COLOR_RESET}", flush=True)
    if os.path.exists(output_filename):
        print(f"{COLOR_STEP}Clearing existing data in '{output_filename}'...{COLOR_RESET}", flush=True)
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump([], f) # Write an empty JSON array
        print(f"{COLOR_STEP}Output preparation complete. '{output_filename}' is now empty.{COLOR_RESET}\n", flush=True)
    else:
        print(f"{COLOR_STEP}Output file '{output_filename}' does not exist. It will be created.{COLOR_RESET}\n", flush=True)

    page_num = 1
    no_product_pages_count = 0 # Counter for consecutive pages with no non-sponsored products
    driver = None

    try:
        driver = setup_driver(headless)
        while True:
            current_page_retry_count = 0
            while current_page_retry_count < 3: # Retry up to 3 times for the current page
                current_url = f"{base_url}&page={page_num}" if page_num > 1 else base_url
                print(f"{COLOR_STEP}--- STEP 3: Scraping Page {page_num} (Attempt {current_page_retry_count + 1}) ---{COLOR_RESET}", flush=True)
                print(f"{COLOR_INFO}INFO: Navigating to URL: {current_url}{COLOR_RESET}", flush=True)

                html_content = scrape_page(driver, current_url)

                link_was_handled = handle_amazon_home_link(driver, page_num, base_url)
                
                if link_was_handled:
                    print(f"{COLOR_INFO}INFO: Amazon home link successfully handled. Re-fetching HTML content from current driver state for page {page_num}...{COLOR_RESET}", flush=True)
                    html_content = driver.page_source
                    # Reset retry count if link was handled, as it's a fresh attempt on the page
                    current_page_retry_count = 0
                
                page_products = parse_products(html_content)
                
                if not page_products:
                    current_page_retry_count += 1
                    print(f"{COLOR_WARNING}WARNING: No non-sponsored products found on page {page_num} (Attempt {current_page_retry_count}).{COLOR_RESET}", flush=True)
                    if current_page_retry_count < 3:
                        print(f"{COLOR_INFO}INFO: Retrying page {page_num}...{COLOR_RESET}", flush=True)
                        time.sleep(random.uniform(3, 7)) # Add a longer delay before retrying the same page
                        continue # Retry the current page
                    else:
                        print(f"{COLOR_CRITICAL}CRITICAL: No non-sponsored products found on page {page_num} after 3 attempts. Moving to next page.{COLOR_RESET}", flush=True)
                        no_product_pages_count += 1 # Increment global empty page counter
                        break # Exit retry loop, proceed to next page
                else:
                    no_product_pages_count = 0 # Reset global empty page counter if products are found
                    current_page_retry_count = 0 # Reset current page retry counter
                    output_filename = f"{product}.json"
                    save_to_json(page_products, output_filename)
                    print(f"{COLOR_SUCCESS}SUCCESS: Found {len(page_products)} products on page {page_num}. Data appended to {output_filename}.{COLOR_RESET}", flush=True)
                    break # Exit retry loop, products found, proceed to next page

            if no_product_pages_count >= 3: # Check global empty page counter after all retries for a page
                print(f"{COLOR_CRITICAL}CRITICAL: No non-sponsored products found on 3 consecutive pages (including retries). Terminating scraping process.{COLOR_RESET}", flush=True)
                break

            page_num += 1
            time.sleep(random.uniform(2, 5)) # Be polite and avoid hammering the server, random delay

    except KeyboardInterrupt:
        print(f"\n{COLOR_INFO}INFO: Scraping interrupted by user (KeyboardInterrupt). Saving progress and exiting.{COLOR_RESET}", flush=True)
    except Exception as e:
        print(f"{COLOR_ERROR}ERR: An unexpected error occurred: {e}{COLOR_RESET}", flush=True)
    finally:
        if driver:
            driver.quit()
        
    print(f"\n{COLOR_INFO}INFO: Scraping process finished.{COLOR_RESET}", flush=True)

if __name__ == "__main__":
    main()
