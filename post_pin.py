import os
import json
import time
import requests
import tempfile
import shutil
import logging # Import logging module
from dotenv import load_dotenv
from selenium import webdriver
import google.generativeai as genai
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys # Import Keys for keyboard actions
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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
    print("GEMINI_API_KEY not found in .env file. Product descriptions will not be summarized.")

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
    driver.get("https://www.pinterest.com")

    # Click on the login button to open the dynamic pop-up
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "/html/body/div[1]/div[1]/header/div[2]/nav/div[2]/div[2]/button"))
    ).click()

    # Input email
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='email']"))
    ).send_keys(email)

    # Input password
    WebDriverWait(driver, 10).until(
        EC.element_to_be_clickable((By.XPATH, "//*[@id='password']"))
    ).send_keys(password)

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

    # Wait for successful login by checking for a known element on the dashboard
    # This is more robust than URL checks as URLs can vary or have redirects.
    # Using a generic data-test-id for the main content area.
    aff_deals_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[1]/div[2]/div/div/div/div[1]/div/div[1]/div/div[2]/div[1]/div[1]/h1/a"
    WebDriverWait(driver, 30).until(
        EC.visibility_of_element_located((By.XPATH, aff_deals_xpath))
    )
    aff_deals_element = driver.find_element(By.XPATH, aff_deals_xpath)
    if "Aff Deals" in aff_deals_element.text:
        print("Successfully logged in to Pinterest and 'Aff Deals' element found.")
    else:
        raise Exception("Login successful, but 'Aff Deals' element text not found.")

def sanitize_image_url(url):
    """Sanitizes an image URL by replacing '_SX679_' with '_SL1500_'."""
    return url.replace("_SX679_", "_SL1500_")

def download_images(image_urls, temp_dir):
    """Downloads a list of sanitized image URLs to a temporary directory."""
    downloaded_image_paths = []
    for i, url in enumerate(image_urls):
        sanitized_url = sanitize_image_url(url)
        try:
            response = requests.get(sanitized_url, stream=True)
            response.raise_for_status() # Raise an exception for HTTP errors
            image_path = os.path.join(temp_dir, f"image_{i+1}.jpg")
            with open(image_path, 'wb') as out_file:
                shutil.copyfileobj(response.raw, out_file)
            downloaded_image_paths.append(image_path)
            print(f"Downloaded: {sanitized_url} to {image_path}")
        except requests.exceptions.RequestException as e:
            print(f"Error downloading {sanitized_url}: {e}")
    return downloaded_image_paths

def main():
    if not PINTEREST_EMAIL or not PINTEREST_PASSWORD:
        print("PINTEREST_EMAIL and PINTEREST_PASSWORD must be set in the .env file.")
        return

    driver = None
    temp_image_dir = os.path.join(os.getcwd(), "temp") # Use a local 'temp' folder
    try:
        # Ensure the temp directory exists
        os.makedirs(temp_image_dir, exist_ok=True)
        print(f"Temporary directory created/ensured: {temp_image_dir}")

        driver = setup_driver(headless)
        login_to_pinterest(driver, PINTEREST_EMAIL, PINTEREST_PASSWORD)

        # Load product data
        with open('test_test.json', 'r', encoding='utf-8') as f:
            products = json.load(f)

        # Filter out already published products
        unpublished_products = [p for p in products if p.get("published") != True]

        if not unpublished_products:
            print("No unpublished products found in test_test.json. Exiting.")
            return

        # Process only one product per run
        product = unpublished_products[0]
        
        product_name = product.get("product_name", "No Name")
        product_details = product.get("product_details", "No Description")
        image_urls = [product[f"image_url_{i}"] for i in range(1, 6) if f"image_url_{i}" in product]

        print(f"\nProcessing product: {product_name}")

        # Download images
        downloaded_paths = download_images(image_urls, temp_image_dir)

        if not downloaded_paths:
            print(f"No images downloaded for {product_name}. Skipping pin creation.")
            shutil.rmtree(temp_image_dir)
            return # Exit main function if no images downloaded

        # Navigate to pin builder
        driver.get("https://in.pinterest.com/pin-builder/")
        WebDriverWait(driver, 20).until(
            EC.presence_of_element_located((By.XPATH, "//*[contains(@id, 'media-upload-input')]"))
        )
        print("Navigated to pin builder page.")

        # Upload images
        # The input element for file upload is usually hidden, so we find it by its ID pattern
        # and send keys (file paths) to it.
        file_input_xpath = "//*[starts-with(@id, 'media-upload-input')]"
        file_input_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, file_input_xpath))
        )
        # Join all image paths with newline for multiple file upload
        file_input_element.send_keys("\n".join(downloaded_paths[::-1])) # Reversed order as requested
        print(f"Uploaded {len(downloaded_paths)} images in reversed order.")

        # Implement keyboard interaction for carousel/collage pop-up
        # Wait for the pop-up to appear (e.g., by waiting for a common element in the pop-up)
        # Since direct XPath clicks failed, we'll rely on a short sleep and keyboard actions.
        time.sleep(3) # Give some time for the pop-up to fully load

        # Press TAB to navigate to the first option (carousel)
        driver.switch_to.active_element.send_keys(Keys.TAB)
        time.sleep(2) # 2 seconds delay as requested

        # Press ENTER to select the carousel option
        driver.switch_to.active_element.send_keys(Keys.ENTER)
        print("Selected carousel option via keyboard.")
        time.sleep(2) # 2 seconds delay as requested

        # Press TAB twice to navigate to the confirmation button
        driver.switch_to.active_element.send_keys(Keys.TAB)
        time.sleep(2) # 2 seconds delay as requested
        driver.switch_to.active_element.send_keys(Keys.TAB)
        time.sleep(2) # 2 seconds delay as requested

        # Press ENTER to confirm
        driver.switch_to.active_element.send_keys(Keys.ENTER)
        print("Confirmed carousel selection via keyboard.")
        time.sleep(3) # Wait for the pop-up to close and page to update

        # Rewrite product name using Gemini API if key is available
        rewritten_product_name = product_name
        if GEMINI_API_KEY:
            rewritten_product_name = rewrite_product_name_with_gemini(product_name)
            print(f"Rewritten product name (Gemini): {rewritten_product_name}")
        else:
            print("GEMINI_API_KEY not found. Using original product name for title and alt text.")

        # Enter product name
        title_input_xpath = "//*[starts-with(@id, 'pin-draft-title')]"
        title_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, title_input_xpath))
        )
        title_element.send_keys(rewritten_product_name)
        print(f"Entered product name: {rewritten_product_name}")

        # Enter product description
        description_input_xpath = "//*[starts-with(@id, 'pin-draft-description')]"
        description_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, description_input_xpath))
        )
        # Remove <p> tags and replace with double newline
        cleaned_description = product_details.replace("<p>", "").replace("</p>", "\n\n").strip()

        # Summarize product details using Gemini API if key is available
        if GEMINI_API_KEY:
            summarized_description = summarize_product_details(cleaned_description)
            description_element.send_keys(summarized_description)
            print(f"Entered summarized product description: {summarized_description}")
        else:
            description_element.send_keys(cleaned_description)
            print("Entered original product description (Gemini API not configured).")
        
        time.sleep(15) # Wait 15 seconds after entering description as requested

        # Click button after product details
        button_after_description_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div[2]/div/div[2]/div/div/div[1]/div[4]/div/button"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, button_after_description_xpath))
        ).click()
        print("Clicked button after product description.")
        # Removed time.sleep(2) as 15-second wait is now before alt-text field

        # Enter product name in alt-text field
        alt_text_input_xpath = "//*[starts-with(@id, 'pin-draft-alttext')]"
        alt_text_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, alt_text_input_xpath))
        )
        alt_text_element.send_keys(rewritten_product_name)
        print(f"Entered rewritten product name in alt-text field: {rewritten_product_name}")
        time.sleep(2) # Wait 2 seconds as requested

        # Trim and affiliate product URL
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
        print(f"Entered product URL with affiliate ID: {final_url}")
        time.sleep(2) # Wait 2 seconds as requested

        # Ensure carousel control checkbox is checked
        carousel_checkbox_xpath = "//*[@id='pin-draft-carousel-control']"
        carousel_checkbox = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, carousel_checkbox_xpath))
        )
        if not carousel_checkbox.is_selected():
            carousel_checkbox.click()
            print("Carousel control checkbox checked.")
        else:
            print("Carousel control checkbox already checked.")
        time.sleep(2) # Wait 2 seconds as requested

        # Select "Mobiles" from dropdown
        dropdown_button_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div[1]/div/div[2]/div/div/div/div[1]/div"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, dropdown_button_xpath))
        ).click()
        print("Clicked dropdown to select board.")
        time.sleep(2) # Wait for dropdown to open

        time.sleep(2) # Wait for 2 seconds before accessing dropdown elements
        mobiles_option_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div[1]/div/div[2]/div/div/div[2]/div/div/div/div/div/div/div/div/div[2]/div[2]/div/div/div/div[2]/div"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, mobiles_option_xpath))
        ).click()
        print("Selected 'Mobiles' from dropdown.")
        time.sleep(2) # Wait for selection to register

        # Click publish button
        publish_button_xpath = "/html/body/div[1]/div[1]/div/div[3]/div/div/div/div[2]/div[2]/div/div/div/div/div/div/div/div/div/div[1]/div/div[2]/div/div/div/div[2]"
        WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, publish_button_xpath))
        ).click()
        print("Clicked publish button.")
        time.sleep(5) # Give time for publishing to complete

        # Update mobile_phones.json with "published": True
        # Read the content of test_test.json again to ensure it's fresh
        with open('test_test.json', 'r+', encoding='utf-8') as f:
            all_products_data = json.load(f)
            # Find the product that was just processed and mark it as published
            for i, p in enumerate(all_products_data):
                if p.get("product_url") == product.get("product_url") and "published" not in p:
                    all_products_data[i]["published"] = True
                    break
            f.seek(0) # Rewind to the beginning of the file
            json.dump(all_products_data, f, indent=4, ensure_ascii=False)
            f.truncate() # Truncate any remaining old content
        print(f"Product '{product_name}' marked as published in test_test.json.")

        # The loop is already effectively broken by processing only the first unpublished product.
        pass

    except Exception as e:
        print(f"An error occurred: {type(e).__name__}: {e.args}")
    finally:
        if driver:
            print("Waiting for 30 seconds before closing the browser...")
            time.sleep(30) # Wait 30 seconds as requested
            driver.quit()
            print("Browser closed.")
        if temp_image_dir and os.path.exists(temp_image_dir):
            for filename in os.listdir(temp_image_dir):
                file_path = os.path.join(temp_image_dir, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f"Failed to delete {file_path}. Reason: {e}")
            print(f"Final cleanup: Cleared contents of temporary directory: {temp_image_dir}")

def summarize_product_details(text):
    """Summarizes product details using the Gemini API."""
    if not GEMINI_API_KEY: # Check for API key directly as configure is called globally
        return text # Return original text if API key is not set

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            f"Concise the following product details into a professional, SEO-friendly summary of maximum 150 characters. "
            f"Ensure it covers all important aspects and is production-ready:\n\n{text}"
        )
        summary = response.text.strip()
        # Ensure the summary is within 150 characters
        if len(summary) > 150:
            summary = summary[:147] + "..." # Truncate and add ellipsis if still too long
        return summary
    except Exception as e:
        print(f"Error summarizing with Gemini API: {e}. Returning original text.")
        return text

def rewrite_product_name_with_gemini(product_name):
    """Rewrites the product name using the Gemini API for SEO-friendly title/alt text."""
    if not GEMINI_API_KEY:
        return product_name # Return original name if API key is not set

    try:
        model = genai.GenerativeModel('gemini-2.5-flash')
        response = model.generate_content(
            f"Rewrite the following product name into a professional, SEO-friendly title/alt text of maximum 60 characters. "
            f"Focus on keywords and clarity:\n\n{product_name}"
        )
        rewritten_name = response.text.strip()
        # Ensure the rewritten name is within 60 characters
        if len(rewritten_name) > 60:
            rewritten_name = rewritten_name[:57] + "..." # Truncate and add ellipsis if still too long
        return rewritten_name
    except Exception as e:
        print(f"Error rewriting product name with Gemini API: {e}. Returning original name.")
        return product_name

if __name__ == "__main__":
    main()
