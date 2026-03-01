import warnings
import requests
import os
from dotenv import load_dotenv


load_dotenv()

warnings.filterwarnings("ignore")
# https://github.com/password123456/setup-selenium-with-chrome-driver-on-ubuntu_debian
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

def get_headless_driver():
    options = Options()
    headless = os.getenv("HEADLESS", "").strip().lower() not in {"0", "false", "no"}
    if headless:
        options.add_argument("--headless=new")
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument("--disable-gpu")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument('--window-size=1920x1080')
    options.add_argument('--start-maximized')
    options.add_experimental_option('prefs', {'profile.managed_default_content_settings.javascript': 1})
    options.binary_location = os.getenv("CHROME_BINARY", "/usr/bin/google-chrome")

    use_webdriver_manager = os.getenv("USE_WEBDRIVER_MANAGER", "").strip().lower() in {"1", "true", "yes"}
    if use_webdriver_manager:
        from webdriver_manager.chrome import ChromeDriverManager
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    else:
        driver = webdriver.Chrome(options=options)
    return driver

browser = get_headless_driver()
browser.get('http://10.53.1.1/index.html')

import time
time.sleep(2)

try:
    wait = WebDriverWait(browser, 10)
    
    print("Page title:", browser.title)
    print("\n=== Page Source ===")
    print(browser.page_source)
    print("===================\n")
    
    try:
        username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        print(f"Username field found: {username_field is not None}")
        username_field.send_keys(os.getenv("USER"))

        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        print(f"Password field found: {password_field is not None}")
        password_field.send_keys(os.getenv("PASSWORD"))

        login_button = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div.loginButton div a")))
        print(f"Login button found: {login_button is not None}")
        login_button.click()

        time.sleep(2)
        
        print("Waiting for login to complete...")
        time.sleep(3)
        
        print(f"Current URL after login: {browser.current_url}")
        
        browser.get('http://10.53.1.1/connectionStatus')
        print("Navigated to connection status page")
        
        time.sleep(2)
        print(f"Connection status page URL: {browser.current_url}")
        print(f"Connection status page title: {browser.title}")
        print(f"Connection status page title: {browser.page_source}")

        
        disconnect_button = wait.until(EC.presence_of_element_located((By.ID, "disconnect")))
        print(f"Disconnect button found: {disconnect_button is not None}")
        print(f"Disconnect button text: {disconnect_button.text}")

        disconnect_button.click()
        
        print("Waiting for alert after disconnect...")
        wait.until(EC.alert_is_present())
        alert = browser.switch_to.alert
        print(f"Alert text: {alert.text}")
        alert.accept()
        print("Alert accepted")
        
        time.sleep(1)

        print("\nLooking for connect and disconnect buttons...")
        connect_button = wait.until(EC.presence_of_element_located((By.ID, "connect")))
        print(f"Connect button found: {connect_button is not None}")
        print(f"Connect button text: {connect_button.text}")

        connect_button.click()
        
        print("\nVerifying IPv6 connectivity...")
        time.sleep(3)
        
        max_retries = 5
        retry_delay = 2
        
        for attempt in range(1, max_retries + 1):
            try:
                print(f"Attempt {attempt}/{max_retries}...")
                response = requests.get('https://api-ipv6.ip.sb/ip', timeout=2)
                if response.status_code == 200:
                    ipv6_address = response.text.strip()
                    print(f"IPv6 address: {ipv6_address}")
                    print("Network is back!")
                    break
                else:
                    print(f"Failed to get IPv6 address. Status code: {response.status_code}")
            except requests.exceptions.RequestException as e:
                print(f"Network verification failed: {e}")
                if attempt < max_retries:
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print("IPv6 may not be available yet after all retries")
        
    except Exception as e:
        print(f"Login button NOT found: {e}")

finally:
    browser.quit()