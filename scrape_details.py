import json
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import traceback
import re
import html
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

product_file = "mobile_phones.json"
headless = True

def get_main_image_element_safely(driver):
    """Helper function to safely get the main image element."""
    try:
        return driver.find_element(By.CSS_SELECTOR, ".imgTagWrapper img, #landingImage, #imgTagWrapperId img")
    except Exception:
        return None

def get_main_image_src_safely(driver):
    """Helper function to safely get the src of the main image element."""
    main_img = get_main_image_element_safely(driver)
    return main_img.get_attribute("src") if main_img else None

def extract_image_urls_from_page(driver, image_urls_set, allowed_endings):
    """Extracts image URLs from the current page using various selectors and XPaths."""
    # Get the initial main image URL
    try:
        initial_src = get_main_image_src_safely(driver)
        if initial_src and initial_src.startswith("https://m.media-amazon.com/images/I/") and initial_src.endswith(allowed_endings):
            image_urls_set.add(initial_src)
    except Exception as e:
        print(f"{Fore.YELLOW}Could not get initial main image: {e}{Style.RESET_ALL}")

    # Also look for image URLs in 'ivThumbImage' divs
    iv_thumb_elements = driver.find_elements(By.CSS_SELECTOR, "div.ivThumbImage")
    for thumb_div in iv_thumb_elements:
        style_attr = thumb_div.get_attribute("style")
        if style_attr and "background: url" in style_attr:
            match = re.search(r'url\("([^"]+)"\)', style_attr)
            if match:
                bg_url = match.group(1)
                if bg_url and bg_url.startswith("https://m.media-amazon.com/images/I/") and bg_url.endswith(allowed_endings):
                    image_urls_set.add(bg_url)
                    if len(image_urls_set) >= 5:
                        break # Stop if we have enough URLs from this source

    # Also look for image URLs from the provided XPaths
    # Main/first image
    try:
        main_image_element = driver.find_element(By.XPATH, "//*[@id='imgTagWrapperId']/img")
        main_image_src = main_image_element.get_attribute("src")
        if main_image_src and main_image_src.startswith("https://m.media-amazon.com/images/I/") and main_image_src.endswith(allowed_endings):
            image_urls_set.add(main_image_src)
            print(f"{Fore.CYAN}  Found main image URL from XPath: {main_image_src}{Style.RESET_ALL}")
    except Exception:
        pass # Silently pass if an XPath element is not found

    # Other images with the new pattern
    for i in range(1, 15): # Iterate from 1 to 14
        if len(image_urls_set) >= 5:
            break
        try:
            xpath = f"/html/body/div[2]/div/div/div[5]/div[3]/div[1]/div[1]/div/div/div[2]/div[1]/div[1]/ul/li[{i}]/span/span/div"
            div_element = driver.find_element(By.XPATH, xpath)
            img_element = div_element.find_element(By.XPATH, ".//img")
            img_src = img_element.get_attribute("src")
            if img_src and img_src.startswith("https://m.media-amazon.com/images/I/") and img_src.endswith(allowed_endings):
                image_urls_set.add(img_src)
                print(f"{Fore.CYAN}  Found image URL from XPath li[{i}]: {img_src}{Style.RESET_ALL}")
        except Exception:
            pass # Silently pass if an XPath element is not found

def _scrape_single_product_details(driver, product):
    """Scrapes details for a single product, including images and product details."""
    product_url = product.get("product_url")
    product_name = product.get("product_name", "Unknown Product")
    if not product_url:
        print(f"{Fore.RED}  Skipping product '{product_name}' due to missing product_url.{Style.RESET_ALL}")
        return

    print(f"{Fore.GREEN}Navigating to: {Fore.YELLOW}{product_name}{Style.RESET_ALL}")
    driver.get(product_url)
    time.sleep(3) # Increased initial sleep time

    image_urls = set() # Use a set to store unique URLs

    # Initialize thumbnail_elements to an empty list
    thumbnail_elements = []

    # Attempt to find thumbnail elements with a primary selector
    thumbnail_elements = driver.find_elements(By.CSS_SELECTOR, "#altImages .item, .image-block .a-list-item")

    # Fallback if the specific selector doesn't yield results
    if not thumbnail_elements:
        thumbnail_elements = driver.find_elements(By.CSS_SELECTOR, "#altImages .item")
    if not thumbnail_elements:
        thumbnail_elements = driver.find_elements(By.CSS_SELECTOR, ".image-block .a-list-item")

    # Define the allowed image URL endings
    allowed_endings = ("SX679_.jpg")

    # Initial image extraction
    extract_image_urls_from_page(driver, image_urls, allowed_endings)

    for i, thumbnail in enumerate(thumbnail_elements):
        if len(image_urls) >= 5:
            break

        try:
            # Wait for the thumbnail to be clickable
            clickable_thumbnail = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(thumbnail)
            )
            # Try clicking directly, if it fails, use JavaScript click
            try:
                clickable_thumbnail.click()
            except Exception:
                driver.execute_script("arguments[0].click();", clickable_thumbnail)
            
            time.sleep(2) # Give some time for the main image to load after click

            # Re-extract all image URLs after clicking the thumbnail
            # This will re-scan all XPaths and main image
            extract_image_urls_from_page(driver, image_urls, allowed_endings)

        except Exception as e:
            print(f"{Fore.YELLOW}  General error during thumbnail click or image extraction for thumbnail {i+1}: {e}{Style.RESET_ALL}")
            traceback.print_exc() # Print full traceback for debugging
            continue
    
    # Scrape product details
    details = []
    for i in range(1, 20): # Iterate through potential list items
        try:
            xpath = f"/html/body/div[2]/div/div/div[5]/div[4]/div[49]/div/ul/li[{i}]/span"
            detail_element = driver.find_element(By.XPATH, xpath)
            detail_text = html.unescape(detail_element.text.strip()) # Handle special characters
            if detail_text:
                details.append(f"<p>{detail_text}</p>")
        except Exception:
            # Break if no more list items are found
            break
    
    if details:
        product_details_str = "\n".join(details)
        print(f"{Fore.MAGENTA}  Scraped product details for {product_name}{Style.RESET_ALL}")
    else:
        product_details_str = ""
        print(f"{Fore.YELLOW}  No product details found for {product_name}{Style.RESET_ALL}")

    # Create a new dictionary to reorder keys
    new_product = {}
    for key, value in product.items():
        new_product[key] = value
        if key == "product_url":
            new_product["product_details"] = product_details_str
            # Add image_urls after product_details
            for i, url in enumerate(list(image_urls)[:5]): # Take up to 5 unique URLs
                new_product[f"image_url_{i+1}"] = url
            break # Stop after adding product_details and image_urls

    # Append remaining image_urls if not already added
    for i, url in enumerate(list(image_urls)[:5]):
        if f"image_url_{i+1}" not in new_product:
            new_product[f"image_url_{i+1}"] = url

    # Update the original product dictionary with the reordered keys and new data
    product.clear()
    product.update(new_product)

def scrape_product_details():
    products_data = []
    try:
        with open(product_file, 'r', encoding='utf-8') as f:
            products_data = json.load(f)
    except FileNotFoundError:
        print(f"{Fore.RED}Error: {product_file} not found. Please run scrape_products.py first.{Style.RESET_ALL}")
        return
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error: Could not decode JSON from {product_file}. File might be empty or corrupted.{Style.RESET_ALL}")
        return

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    chrome_options.add_argument("--start-maximized") # Maximize browser window
    
    # Setup Chrome driver
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    try:
        for i, product in enumerate(products_data):
            print(f"\n{Fore.WHITE}--- Processing product {i+1}/{len(products_data)} ---{Style.RESET_ALL}")
            
            # Skip if product_details already exists
            if "product_details" in product and product["product_details"]:
                print(f"{Fore.YELLOW}  Skipping '{product.get('product_name', 'Unknown Product')}' - product details already scraped.{Style.RESET_ALL}")
                continue

            # Only process products that have less than 5 image_url_X keys or if product_details is missing
            image_url_count = sum(1 for key in product if key.startswith("image_url_"))
            if image_url_count < 5 or "product_details" not in product:
                _scrape_single_product_details(driver, product)
                
                # Write the updated data back to the file after each product
                with open(product_file, 'w', encoding='utf-8') as f:
                    json.dump(products_data, f, indent=4, ensure_ascii=False)
                print(f"{Fore.GREEN}  Successfully updated '{product.get('product_name', 'Unknown Product')}' in {product_file}{Style.RESET_ALL}")
            else:
                print(f"{Fore.YELLOW}  Skipping '{product.get('product_name', 'Unknown Product')}' - already has 5 images and product details.{Style.RESET_ALL}")
                
    except KeyboardInterrupt:
        print(f"\n{Fore.RED}KeyboardInterrupt detected. Exiting gracefully...{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}An unexpected error occurred: {e}{Style.RESET_ALL}")
        traceback.print_exc()
    finally:
        driver.quit() # Close the browser after scraping all products
        print(f"{Fore.CYAN}Browser closed.{Style.RESET_ALL}")

if __name__ == "__main__":
    scrape_product_details()
