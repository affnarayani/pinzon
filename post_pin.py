import os
import json
import time
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium_stealth import stealth

# Load environment variables from .env file
load_dotenv()
PINTEREST_EMAIL = os.getenv("PINTEREST_EMAIL")
PINTEREST_PASSWORD = os.getenv("PINTEREST_PASSWORD")

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
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
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

def main():
    if not PINTEREST_EMAIL or not PINTEREST_PASSWORD:
        print("PINTEREST_EMAIL and PINTEREST_PASSWORD must be set in the .env file.")
        return

    driver = None
    try:
        driver = setup_driver(headless) # Pass the headless variable
        login_to_pinterest(driver, PINTEREST_EMAIL, PINTEREST_PASSWORD)
        print("Waiting for 30 seconds before closing the browser...")
        time.sleep(30)
    except Exception as e:
        print(f"An error occurred: {type(e).__name__}: {e.args}")
    finally:
        if driver:
            driver.quit()
            print("Browser closed.")

if __name__ == "__main__":
    main()
