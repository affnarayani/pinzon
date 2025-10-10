import os
import json
import time
import requests
import tempfile
import shutil
import sys # Import sys module for system exit
import logging # Import logging module
from dotenv import load_dotenv
from selenium import webdriver
import google.generativeai as genai
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys # Import Keys for keyboard actions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException # Import TimeoutException
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

# Suppress specific warnings from libraries
os.environ['GRPC_VERBOSITY'] = 'CRITICAL'
os.environ['GLOG_minloglevel'] = '2' # Suppress INFO and WARNING messages from C++ libraries
logging.getLogger('google.generativeai').setLevel(logging.ERROR)
logging.getLogger('urllib3').setLevel(logging.ERROR) # Suppress urllib3 warnings

# Suppress Abseil logging warnings
try:
    import absl.logging
    # Set absl logging to ERROR level
    absl.logging.set_verbosity(absl.logging.ERROR)
    # Optionally, redirect absl logs to a null handler if they still appear
    absl.logging.get_absl_handler().setFormatter(logging.Formatter(''))
    absl.logging.get_absl_handler().setLevel(logging.CRITICAL)
except ImportError:
    pass # absl might not be installed or configured this way

# Load environment variables from .env file
load_dotenv()
PINTEREST_EMAIL = os.getenv("PINTEREST_EMAIL")
PINTEREST_PASSWORD = os.getenv("PINTEREST_PASSWORD")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Configure Gemini API
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
else:
    print("\033[93m[WARNING]\033[0m GEMINI_API_KEY not found in .env file. Product descriptions will not be summarized.", flush=True)

# Configuration Variables
headless = True # Toggle for headless/headful browser mode

def setup_driver(headless_mode):
    """Sets up the Chrome WebDriver with stealth options."""
    options = webdriver.ChromeOptions()
    # Common arguments for stealth and stability
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-features=site-per-process")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--profile-directory=Default")
    options.add_argument("--incognito")
    options.add_argument("--disable-background-networking")
    options.add_argument("--enable-automation")
    options.add_argument("--disable-background-timer-throttling")
    options.add_argument("--disable-backgrounding-occluded-windows")
    options.add_argument("--disable-breakpad")
    options.add_argument("--disable-client-side-phishing-detection")
    options.add_argument("--disable-component-update")
    options.add_argument("--disable-default-apps")
    options.add_argument("--disable-hang-monitor")
    options.add_argument("--disable-ipc-flooding-protection")
    options.add_argument("--disable-notifications")
    options.add_argument("--disable-offer-store-unmasked-wallet-cards")
    options.add_argument("--disable-print-preview")
    options.add_argument("--disable-prompt-on-repost")
    options.add_argument("--disable-renderer-backgrounding")
    options.add_argument("--disable-sync")
    options.add_argument("--hide-scrollbars")
    options.add_argument("--metrics-recording-only")
    options.add_argument("--mute-audio")
    options.add_argument("--no-first-run")
    options.add_argument("--safebrowsing-disable-auto-update")
    options.add_argument("--enable-blink-features=IdleDetection")

    if headless_mode:
        options.add_argument("--headless=new") # Use new headless mode

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    # Apply stealth settings
    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True,
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
            app_version="5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36",
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
        """
    })
    return driver

def login_to_pinterest(driver, email, password):
    """Navigates to Pinterest and logs in."""
    print("\n\033[94m[STEP]\033[0m Navigating to Pinterest and attempting login...", flush=True)
    driver.get("https://www.pinterest.com")

    # Click on the login button to open the dynamic pop-up
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[1]/header/div[2]/nav/div[2]/div[2]/button"))
    ).click()
    print("\033[96m[INFO]\033[0m Login button clicked.", flush=True)

    # Input email
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='email']"))
    ).send_keys(email)
    print("\033[96m[INFO]\033[0m Email entered.", flush=True)

    # Input password
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='password']"))
    ).send_keys(password)
    print("\033[96m[INFO]\033[0m Password entered.", flush=True)

    # Click on the login button
    # First, wait for the loading spinner to disappear if it's present
    try:
        WebDriverWait(driver, 10).until(
            EC.invisibility_of_element_located((By.XPATH, "//svg[@aria-label='Loading']"))
        )
    except:
        pass # Spinner might not always appear, so we continue if it doesn't

    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[1]/div[2]/div/div/div/div/div/div[4]/div[1]/form/div[7]/button"))
    ).click()
    print("\033[96m[INFO]\033[0m Submit login button clicked.", flush=True)

    # Wait for successful login by checking for a known element on the dashboard
    # This is more robust than URL checks as URLs can vary or have redirects.
    # Using a generic data-test-id for the main content area.
    aff_deals_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[1]/div[2]/div/div/div/div[1]/div/div[1]/div/div[2]/div[1]/div[1]/h1/a"
    WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.XPATH, aff_deals_xpath))
    )
    aff_deals_element = driver.find_element(By.XPATH, aff_deals_xpath)
    if "Aff Deals" in aff_deals_element.text:
        print("\033[92m[SUCCESS]\033[0m Successfully logged in to Pinterest and 'Aff Deals' element found.", flush=True)
    else:
        raise Exception("Login successful, but 'Aff Deals' element text not found.")

def sanitize_image_url(url):
    """Sanitizes an image URL by replacing '_SX679_' with '_SL1500_'."""
    return url.replace("_SX679_", "_SL1500_")

def download_images(image_urls, temp_dir):
    """Downloads a list of sanitized image URLs to a temporary directory."""
    downloaded_image_paths = []
    print(f"\n\033[94m[STEP]\033[0m Attempting to download {len(image_urls)} images...", flush=True)
    for i, url in enumerate(image_urls):
        sanitized_url = sanitize_image_url(url)
        try:
            response = requests.get(sanitized_url, stream=True)
            response.raise_for_status() # Raise an exception for HTTP errors
            image_path = os.path.join(temp_dir, f"image_{i+1}.jpg")
            with open(image_path, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            downloaded_image_paths.append(image_path)
            print(f"\033[92m[SUCCESS]\033[0m Downloaded: {sanitized_url} \033[90m->\033[0m {image_path}", flush=True)
        except requests.exceptions.RequestException as e:
            print(f"\033[91m[ERROR]\033[0m Error downloading {sanitized_url}: {e}", flush=True)
    return downloaded_image_paths

def load_existing_asins():
    """Loads existing ASINs from asin.json, handling empty or malformed files."""
    asin_data = []
    try:
        if os.path.exists('asin.json') and os.path.getsize('asin.json') > 0:
            with open('asin.json', 'r', encoding='utf-8') as f:
                asin_data = json.load(f)
        elif not os.path.exists('asin.json'):
            # Create the file if it doesn't exist
            with open('asin.json', 'w', encoding='utf-8') as f:
                json.dump([], f) # Write an empty JSON array
    except json.JSONDecodeError:
        print(f"\033[93m[WARNING]\033[0m asin.json is malformed or empty. Initializing with an empty list.", flush=True)
        asin_data = []
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Error reading asin.json: {e}. Initializing with an empty list.", flush=True)
        asin_data = []
    return asin_data

def main():
    if not PINTEREST_EMAIL or not PINTEREST_PASSWORD:
        print("\n\033[91m[ERROR]\033[0m PINTEREST_EMAIL and PINTEREST_PASSWORD must be set in the .env file. Exiting.", flush=True)
        return

    driver = None
    temp_image_dir = os.path.join(os.getcwd(), "temp") # Use a local 'temp' folder
    try:
        # Ensure the temp directory exists
        os.makedirs(temp_image_dir, exist_ok=True)
        print(f"\n\033[94m[STEP]\033[0m Temporary directory created/ensured: \033[90m{temp_image_dir}\033[0m", flush=True)

        driver = setup_driver(headless)
        login_to_pinterest(driver, PINTEREST_EMAIL, PINTEREST_PASSWORD)

        # Load product data
        print("\n\033[94m[STEP]\033[0m Loading product data from \033[90mmobile_phones.json\033[0m...", flush=True)
        with open('mobile_phones.json', 'r', encoding='utf-8') as f:
            products = json.load(f)
        print(f"\033[92m[SUCCESS]\033[0m Loaded {len(products)} products.", flush=True)

        # Load existing ASINs
        existing_asins = load_existing_asins()
        print(f"\033[96m[INFO]\033[0m Loaded {len(existing_asins)} existing ASINs from \033[90masin.json\033[0m.", flush=True)

        # Filter out already published products and products with existing ASINs
        unpublished_products = []
        for p in products:
            if p.get("published") != True:
                product_asin = extract_asin_from_url(p.get("product_url", ""))
                if product_asin and product_asin in existing_asins:
                    print(f"\033[93m[WARNING]\033[0m Product '\033[1m{p.get('product_name', 'N/A')}\033[0m' (ASIN: {product_asin}) already exists in \033[90masin.json\033[0m. Skipping.", flush=True)
                else:
                    unpublished_products.append(p)

        if not unpublished_products:
            print("\n\033[93m[WARNING]\033[0m No unpublished products or products with new ASINs found. Exiting.", flush=True)
            return

        # Process only one product per run
        product = unpublished_products[0]
        
        product_name = product.get("product_name", "No Name")
        product_details = product.get("product_details", "No Description")
        image_urls = [product[f"image_url_{i}"] for i in range(1, 6) if f"image_url_{i}" in product]

        print(f"\n\033[95m[PRODUCT]\033[0m Processing product: \033[1m{product_name}\033[0m", flush=True)

        # Download images
        downloaded_paths = download_images(image_urls, temp_image_dir)

        if not downloaded_paths:
            print(f"\n\033[93m[WARNING]\033[0m No images downloaded for \033[1m{product_name}\033[0m. Skipping pin creation.", flush=True)
            shutil.rmtree(temp_image_dir)
            return # Exit main function if no images downloaded

        # Navigate to pin builder
        print("\n\033[94m[STEP]\033[0m Navigating to Pinterest pin builder page...", flush=True)
        driver.get("https://in.pinterest.com/pin-builder/")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'media-upload-input')]"))
        )
        print("\033[92m[SUCCESS]\033[0m Navigated to pin builder page.", flush=True)

        # Upload images
        print("\n\033[94m[STEP]\033[0m Uploading images...", flush=True)
        # The input element for file upload is usually hidden, so we find it by its ID pattern
        # and send keys (file paths) to it.
        file_input_xpath = "//*[starts-with(@id, 'media-upload-input')]"
        file_input_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, file_input_xpath))
        )
        # Join all image paths with newline for multiple file upload
        file_input_element.send_keys("\n".join(downloaded_paths)) # Upload in original order
        print(f"\033[92m[SUCCESS]\033[0m Uploaded {len(downloaded_paths)} images in original order.", flush=True)

        # Implement keyboard interaction for carousel/collage pop-up only if more than one image
        if len(downloaded_paths) > 1:
            print("\n\033[94m[STEP]\033[0m Multiple images detected. Interacting with carousel/collage pop-up...", flush=True)
            time.sleep(3) # Give some time for the pop-up to fully load

            # Press TAB to navigate to the first option (carousel)
            driver.switch_to.active_element.send_keys(Keys.TAB)
            time.sleep(2) # 2 seconds delay as requested
            print("\033[96m[INFO]\033[0m Tab pressed (to carousel option).", flush=True)

            # Press ENTER to select the carousel option
            driver.switch_to.active_element.send_keys(Keys.ENTER)
            print("\033[92m[SUCCESS]\033[0m Selected carousel option via keyboard.", flush=True)
            time.sleep(2) # 2 seconds delay as requested

            # Press TAB twice to navigate to the confirmation button
            driver.switch_to.active_element.send_keys(Keys.TAB)
            time.sleep(2) # 2 seconds delay as requested
            driver.switch_to.active_element.send_keys(Keys.TAB)
            time.sleep(2) # 2 seconds delay as requested
            print("\033[96m[INFO]\033[0m Tab pressed twice (to confirmation button).", flush=True)

            # Press ENTER to confirm
            driver.switch_to.active_element.send_keys(Keys.ENTER)
            print("\033[92m[SUCCESS]\033[0m Confirmed carousel selection via keyboard.", flush=True)
            time.sleep(3) # Wait for the pop-up to close and page to update
        else:
            print("\n\033[96m[INFO]\033[0m Only one image uploaded, skipping carousel/collage pop-up interaction.", flush=True)
            time.sleep(3) # Still wait a bit for the page to settle after upload

        # Rewrite product name using Gemini API if key is available
        rewritten_product_name = product_name
        if GEMINI_API_KEY:
            print("\n\033[94m[STEP]\033[0m Rewriting product name with Gemini API...", flush=True)
            rewritten_product_name = rewrite_product_name_with_gemini(product_name)
            print(f"\033[92m[SUCCESS]\033[0m Rewritten product name (Gemini): \033[1m{rewritten_product_name}\033[0m", flush=True)
        else:
            print("\n\033[93m[WARNING]\033[0m GEMINI_API_KEY not found. Using original product name for title and alt text.", flush=True)

        # Enter product name
        print("\n\033[94m[STEP]\033[0m Entering product title...", flush=True)
        title_input_xpath = "//*[starts-with(@id, 'pin-draft-title')]"
        title_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, title_input_xpath))
        )
        title_element.send_keys(rewritten_product_name)
        print(f"\033[92m[SUCCESS]\033[0m Entered product title: \033[1m{rewritten_product_name}\033[0m", flush=True)

        # Enter product description
        print("\n\033[94m[STEP]\033[0m Entering product description...", flush=True)
        if len(downloaded_paths) == 1:
            description_input_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div[2]/div/div[2]/div/div[1]/div[1]/div[3]/div/div[1]/div/div/div[1]/div/div/div/div/div/div/div[2]/div/div/div/div"
        else:
            description_input_xpath = "//*[starts-with(@id, 'pin-draft-description')]"
        
        description_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, description_input_xpath))
        )
        # Remove <p> tags and replace with double newline
        cleaned_description = product_details.replace("<p>", "").replace("</p>", "\n\n").strip()

        # Summarize product details using Gemini API if key is available
        if GEMINI_API_KEY:
            print("\033[96m[INFO]\033[0m Summarizing product description with Gemini API...", flush=True)
            summarized_description = summarize_product_details(cleaned_description)
            description_element.send_keys(summarized_description)
            print(f"\033[92m[SUCCESS]\033[0m Entered summarized product description: \033[1m{summarized_description}\033[0m", flush=True)
        else:
            description_element.send_keys(cleaned_description)
            print("\033[93m[WARNING]\033[0m Entered original product description (Gemini API not configured).", flush=True)
        
        time.sleep(15) # Wait 15 seconds after entering description as requested
        print("\033[96m[INFO]\033[0m Waited 15 seconds after entering description.", flush=True)

        # Click button after product details
        print("\n\033[94m[STEP]\033[0m Clicking button after product description...", flush=True)
        button_after_description_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div[2]/div/div[2]/div/div/div[1]/div[4]/div/button"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, button_after_description_xpath))
        ).click()
        print("\033[92m[SUCCESS]\033[0m Clicked button after product description.", flush=True)

        # Enter product name in alt-text field
        print("\n\033[94m[STEP]\033[0m Entering product name in alt-text field...", flush=True)
        alt_text_input_xpath = "//*[starts-with(@id, 'pin-draft-alttext')]"
        alt_text_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, alt_text_input_xpath))
        )
        alt_text_element.send_keys(rewritten_product_name)
        print(f"\033[92m[SUCCESS]\033[0m Entered rewritten product name in alt-text field: \033[1m{rewritten_product_name}\033[0m", flush=True)
        time.sleep(2) # Wait 2 seconds as requested
        print("\033[96m[INFO]\033[0m Waited 2 seconds after entering alt-text.", flush=True)

        # Trim and affiliate product URL
        print("\n\033[94m[STEP]\033[0m Processing and entering product URL with affiliate ID...", flush=True)
        product_url = product.get("product_url", "")
        trimmed_url = ""
        if product_url:
            # Find the index of "/ref=" or "?" to trim the URL
            ref_index = product_url.find("/ref=")
            query_index = product_url.find("?")
            
            if ref_index != -1:
                trimmed_url = product_url[:ref_index]
            elif query_index != -1:
                trimmed_url = product_url[:query_index]
            else:
                trimmed_url = product_url # No trimming needed if no /ref= or ?
            
            # Append affiliate ID
            final_url = f"{trimmed_url}?tag=affdealsplus-21"
        else:
            final_url = "" # Or handle as appropriate if URL is missing

        link_input_xpath = "//*[starts-with(@id, 'pin-draft-link')]"
        link_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, link_input_xpath))
        )
        link_element.send_keys(final_url)
        print(f"\033[92m[SUCCESS]\033[0m Entered product URL with affiliate ID: \033[90m{final_url}\033[0m", flush=True)
        time.sleep(2) # Wait 2 seconds as requested
        print("\033[96m[INFO]\033[0m Waited 2 seconds after entering URL.", flush=True)

        # Ensure carousel control checkbox is checked only if more than one image
        if len(downloaded_paths) > 1:
            print("\n\033[94m[STEP]\033[0m Checking carousel control checkbox...", flush=True)
            carousel_checkbox_xpath = "//*[@id='pin-draft-carousel-control']"
            carousel_checkbox = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, carousel_checkbox_xpath))
            )
            if not carousel_checkbox.is_selected():
                carousel_checkbox.click()
                print("\033[92m[SUCCESS]\033[0m Carousel control checkbox checked.", flush=True)
            else:
                print("\033[96m[INFO]\033[0m Carousel control checkbox already checked.", flush=True)
            time.sleep(2) # Wait 2 seconds as requested
            print("\033[96m[INFO]\033[0m Waited 2 seconds after carousel checkbox interaction.", flush=True)
        else:
            print("\n\033[96m[INFO]\033[0m Only one image uploaded, skipping carousel control checkbox interaction.", flush=True)
            time.sleep(2) # Still wait a bit for consistency
            print("\033[96m[INFO]\033[0m Waited 2 seconds for consistency.", flush=True)

        # Select "Mobiles" from dropdown
        print("\n\033[94m[STEP]\033[0m Selecting 'Mobiles' board from dropdown...", flush=True)
        dropdown_button_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div[1]/div/div[2]/div/div/div/div[1]/div"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, dropdown_button_xpath))
        ).click()
        print("\033[96m[INFO]\033[0m Clicked dropdown to select board.", flush=True)
        time.sleep(2) # Wait for dropdown to open
        print("\033[96m[INFO]\033[0m Waited 2 seconds for dropdown to open.", flush=True)

        time.sleep(2) # Wait for 2 seconds before accessing dropdown elements
        mobiles_option_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div[1]/div/div[2]/div/div/div[2]/div/div/div/div/div/div/div/div/div[2]/div[2]/div/div/div/div[2]/div"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, mobiles_option_xpath))
        ).click()
        print("\033[92m[SUCCESS]\033[0m Selected 'Mobiles' from dropdown.", flush=True)
        time.sleep(2) # Wait for selection to register
        print("\033[96m[INFO]\033[0m Waited 2 seconds for selection to register.", flush=True)

        # Click publish button
        print("\n\033[94m[STEP]\033[0m Clicking publish button...", flush=True)
        publish_button_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div[1]/div/div[2]/div/div/div/div[2]"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, publish_button_xpath))
        ).click()
        print("\033[92m[SUCCESS]\033[0m Clicked publish button.", flush=True)
        time.sleep(5) # Give time for publishing to complete
        print("\033[96m[INFO]\033[0m Waited 5 seconds for publishing to complete.", flush=True)

        # Update mobile_phones.json with "published": True
        print(f"\n\033[94m[STEP]\033[0m Marking product '\033[1m{product_name}\033[0m' as published in \033[90mmobile_phones.json\033[0m...", flush=True)
        with open('mobile_phones.json', 'r+', encoding='utf-8') as f:
            all_products_data = json.load(f)
            # Find the product that was just processed and mark it as published
            for i, p in enumerate(all_products_data):
                if p.get("product_url") == product.get("product_url") and "published" not in p:
                    all_products_data[i]["published"] = True
                    break
            f.seek(0) # Rewind to the beginning of the file
            json.dump(all_products_data, f, indent=4, ensure_ascii=False)
            f.truncate() # Truncate any remaining old content
        print(f"\033[92m[SUCCESS]\033[0m Product '\033[1m{product_name}\033[0m' marked as published in \033[90mmobile_phones.json\033[0m.", flush=True)

        # Extract ASIN and append to asin.json
        asin = extract_asin_from_url(product_url)
        if asin:
            print(f"\n\033[94m[STEP]\033[0m Extracted ASIN: \033[1m{asin}\033[0m. Appending to \033[90masin.json\033[0m...", flush=True)
            asin_data = []
            try:
                if os.path.exists('asin.json') and os.path.getsize('asin.json') > 0:
                    with open('asin.json', 'r', encoding='utf-8') as f:
                        asin_data = json.load(f)
                elif not os.path.exists('asin.json'):
                    # Create the file if it doesn't exist
                    with open('asin.json', 'w', encoding='utf-8') as f:
                        json.dump([], f) # Write an empty JSON array
            except json.JSONDecodeError:
                print(f"\033[93m[WARNING]\033[0m asin.json is malformed or empty. Initializing with an empty list.", flush=True)
                asin_data = []
            except Exception as e:
                print(f"\033[91m[ERROR]\033[0m Error reading asin.json: {e}. Initializing with an empty list.", flush=True)
                asin_data = []

            if asin not in asin_data:
                asin_data.append(asin)
                with open('asin.json', 'w', encoding='utf-8') as f:
                    json.dump(asin_data, f, indent=4, ensure_ascii=False)
                print(f"\033[92m[SUCCESS]\033[0m ASIN '\033[1m{asin}\033[0m' appended to \033[90masin.json\033[0m.", flush=True)
            else:
                print(f"\033[96m[INFO]\033[0m ASIN '\033[1m{asin}\033[0m' already exists in \033[90masin.json\033[0m. Skipping.", flush=True)
        else:
            print(f"\033[93m[WARNING]\033[0m No ASIN extracted from product URL: \033[90m{product_url}\033[0m. Skipping asin.json update.", flush=True)

        # The loop is already effectively broken by processing only the first unpublished product.
        pass

    except TimeoutException as e:
        print(f"\n\033[91m[ERROR]\033[0m A timeout occurred: {e}", flush=True)
        print("\033[91m[ERROR]\033[0m The program will exit due to a critical timeout.", flush=True)
        sys.exit(1) # Exit with error code 1
    except Exception as e:
        print(f"\n\033[91m[ERROR]\033[0m An unexpected error occurred: {type(e).__name__}: {e.args}", flush=True)
    finally:
        if driver:
            print("\n\033[96m[INFO]\033[0m Waiting for 30 seconds before closing the browser...", flush=True)
            time.sleep(30) # Wait 30 seconds as requested
            driver.quit()
            print("\033[96m[INFO]\033[0m Browser closed.", flush=True)
        if temp_image_dir and os.path.exists(temp_image_dir):
            for filename in os.listdir(temp_image_dir):
                file_path = os.path.join(temp_image_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"\033[91m[ERROR]\033[0m Failed to delete {file_path}. Reason: {e}", flush=True)
            print(f"\033[96m[INFO]\033[0m Final cleanup: Cleared contents of temporary directory: {temp_image_dir}", flush=True)

def summarize_product_details(text):
    """Summarizes product details using the Gemini API."""
    if not GEMINI_API_KEY: # Check for API key directly as configure is called globally
        return text # Return original text if API key is not set

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            f"Concise the following product details into a professional, SEO-friendly summary of maximum 150 characters. "
            f"Ensure it covers all important aspects and is production-ready, without using special characters like asterisks, pipes, or brackets, and without mentioning character counts:\n\n{text}"
        )
        summary = response.text.strip()
        # Sanitize the summary to remove special characters
        summary = "".join(char for char in summary if char.isalnum() or char.isspace() or char in (',', '.', '-', '!', '?'))
        # Ensure the summary is within 150 characters
        if len(summary) > 150:
            summary = summary[:147] + "..." # Truncate and add ellipsis if still too long
        return summary
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Error summarizing with Gemini API: {e}. Returning original text.", flush=True)
        return text

def rewrite_product_name_with_gemini(product_name):
    """Rewrites the product name using the Gemini API for SEO-friendly title/alt text."""
    if not GEMINI_API_KEY:
        return product_name # Return original name if API key is not set

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            f"Rewrite the following product name into a professional, SEO-friendly title/alt text of maximum 60 characters. "
            f"Focus on keywords and clarity, without using special characters like asterisks, pipes, or brackets, and without mentioning character counts:\n\n{product_name}"
        )
        rewritten_name = response.text.strip()
        # Sanitize the rewritten name to remove special characters
        rewritten_name = "".join(char for char in rewritten_name if char.isalnum() or char.isspace() or char in (',', '.', '-', '!', '?'))
        # Ensure the rewritten name is within 60 characters
        if len(rewritten_name) > 60:
            rewritten_name = rewritten_name[:57] + "..." # Truncate and add ellipsis if still too long
        return rewritten_name
    except Exception as e:
        print(f"\033[91m[ERROR]\033[0m Error rewriting product name with Gemini API: {e}. Returning original name.", flush=True)
        return product_name

def extract_asin_from_url(url):
    """Extracts the ASIN from an Amazon product URL."""
    import re
    match = re.search(r"[/dp/|/gp/product/]([A-Z0-9]{10})", url)
    if match:
        return match.group(1)
    return None

if __name__ == "__main__":
    main()
