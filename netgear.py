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
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException


def _is_login_page(driver):
    try:
        if "/login" in (driver.current_url or ""):
            return True
        return bool(driver.find_elements(By.ID, "username")) or bool(driver.find_elements(By.ID, "password"))
    except Exception:
        return False

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
base_url = os.getenv("NETGEAR_BASE_URL", "http://10.53.1.1").rstrip("/")
browser.get(f"{base_url}/index.html")

import time
time.sleep(2)

try:
    wait = WebDriverWait(browser, 10)
    
    print("Page title:", browser.title)
    # print("\n=== Page Source ===")
    # print(browser.page_source)
    # print("===================\n")
    
    try:
        username_field = wait.until(EC.presence_of_element_located((By.ID, "username")))
        print(f"Username field found: {username_field is not None}")
        username = os.getenv("NETGEAR_USERNAME") or os.getenv("USER")
        password = os.getenv("NETGEAR_PASSWORD") or os.getenv("PASSWORD")
        if not username or not password:
            raise RuntimeError(
                "Missing credentials. Set NETGEAR_USERNAME and NETGEAR_PASSWORD (recommended), "
                "or USER and PASSWORD."
            )
        username_field.clear()
        username_field.send_keys(username)

        password_field = wait.until(EC.presence_of_element_located((By.ID, "password")))
        print(f"Password field found: {password_field is not None}")
        password_field.clear()
        password_field.send_keys(password)

        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "div.loginButton div a")))
        print(f"Login button found: {login_button is not None}")
        try:
            login_button.click()
        except Exception:
            browser.execute_script("arguments[0].click();", login_button)

        try:
            password_field.send_keys(Keys.ENTER)
        except Exception:
            pass

        time.sleep(2)
        
        print("Waiting for login to complete...")
        try:
            WebDriverWait(browser, 15).until(
                lambda d: ("/login" not in (d.current_url or ""))
                or (len(d.find_elements(By.ID, "username")) == 0 and len(d.find_elements(By.ID, "password")) == 0)
            )
        except TimeoutException:
            pass

        print(f"Current URL after login: {browser.current_url}")
        print(f"Cookies after login: {browser.get_cookies()}")

        try:
            local_storage = browser.execute_script(
                "var ls = {}; for (var i=0;i<localStorage.length;i++){var k=localStorage.key(i); ls[k]=localStorage.getItem(k);} return ls;"
            )
            session_storage = browser.execute_script(
                "var ss = {}; for (var i=0;i<sessionStorage.length;i++){var k=sessionStorage.key(i); ss[k]=sessionStorage.getItem(k);} return ss;"
            )
            print(f"localStorage keys: {list(local_storage.keys())}")
            print(f"sessionStorage keys: {list(session_storage.keys())}")
        except Exception as e:
            print(f"Failed to read storage: {e}")

        if "/login" in (browser.current_url or ""):
            possible_error_selectors = [
                ".el-message__content",
                ".el-form-item__error",
                "div[role='alert']",
                ".error",
            ]
            for css in possible_error_selectors:
                elements = browser.find_elements(By.CSS_SELECTOR, css)
                texts = [e.text for e in elements if (e.text or "").strip()]
                if texts:
                    print(f"Login error UI ({css}): {texts}")
                    break

        candidate_urls = [
            f"{base_url}/connectionStatus",
            # f"{base_url}/#/connectionStatus",
            # f"{base_url}/#/ConnectionStatus",
            # f"{base_url}/#/status",
            # f"{base_url}/#/dashboard",
            # f"{base_url}/#/home",
        ]
        reached = False
        for url in candidate_urls:
            browser.get(url)
            print(f"Navigated to: {url}")
            time.sleep(2)
            print(f"Page URL: {browser.current_url}")
            print(f"Page title: {browser.title}")
            if not _is_login_page(browser):
                reached = True
                break

        if not reached:
            raise RuntimeError(
                "Could not reach an authenticated status page after login. "
                "Still on login page for all candidate URLs."
            )

        disconnect_button = wait.until(EC.element_to_be_clickable((By.ID, "disconnect")))
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

        max_retries = int(os.getenv("IPV6_MAX_RETRIES", "5"))
        retry_delay = float(os.getenv("IPV6_RETRY_DELAY", "2"))
        timeout = float(os.getenv("IPV6_TIMEOUT", "5"))

        urls_env = os.getenv("IPV6_CHECK_URLS", "").strip()
        urls = [u.strip() for u in urls_env.split(",") if u.strip()] if urls_env else [
            "https://api6.ipify.org",
            "https://ifconfig.co/ip",
            "https://ident.me",
            "https://api-ipv6.ip.sb/ip",
        ]

        last_error = None
        for attempt in range(1, max_retries + 1):
            print(f"Attempt {attempt}/{max_retries}...")
            for url in urls:
                try:
                    response = requests.get(
                        url,
                        timeout=timeout,
                        headers={"User-Agent": "netgear-selenium/1.0"},
                        verify=False,
                    )
                    if response.status_code == 200:
                        ip_text = (response.text or "").strip()
                        if ip_text:
                            print(f"IPv6 address: {ip_text} (from {url})")
                            print("Network is back!")
                            last_error = None
                            break
                    print(f"IPv6 check failed via {url}. Status code: {response.status_code}")
                except requests.exceptions.RequestException as e:
                    last_error = e
                    print(f"IPv6 check error via {url}: {e}")
            if last_error is None:
                break
            if attempt < max_retries:
                print(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                print("IPv6 may not be available yet after all retries")
        
    except TimeoutException as e:
        print(f"Timed out waiting for an element: {e}")
        print(f"Current URL: {browser.current_url}")
        print("\n=== Page Source (truncated) ===")
        print(browser.page_source[:4000])
        print("==============================\n")
    except Exception as e:
        print(f"Automation failed: {e}")

finally:
    browser.quit()