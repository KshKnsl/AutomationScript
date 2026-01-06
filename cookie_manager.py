import os
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

def save_cookies(driver, filename):
    cookies = driver.get_cookies()
    with open(filename, 'w') as f:
        json.dump(cookies, f, indent=2)
    print(f"Cookies saved to {filename}")

def load_cookies(driver, filename):
    try:
        with open(filename, 'r') as f:
            cookies = json.load(f)

        driver.get("https://www.geeksforgeeks.org")

        for cookie in cookies:
            try:
                driver.add_cookie(cookie)
            except Exception as e:
                pass

        print("Cookies loaded")
        return True
    except Exception as e:
        print(f"Cookie error: {e}")
        return False

def setup_authenticated_driver(cookies_file=None, headless=False):
    options = Options()
    if headless:
        options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')

    chromedriver_path = 'chromedriver.exe'
    if os.path.exists(chromedriver_path):
        service = Service(chromedriver_path)
    else:
        try:
            service = Service(ChromeDriverManager().install())
        except Exception as e:
            print(f"ChromeDriver error: {e}")
            return None
    driver = webdriver.Chrome(service=service, options=options)

    if cookies_file and os.path.exists(cookies_file):
        load_cookies(driver, cookies_file)

    return driver

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_file = os.path.join(base_dir, 'cookies.json')

    print("Cookie Manager - Save cookies after manual login")

    driver = setup_authenticated_driver(headless=False)
    if not driver:
        print("Browser setup failed")
        return

    try:
        driver.get("https://www.geeksforgeeks.org")
        print("Log in manually in the browser window...")
        input("Press Enter after logging in to save cookies...")

        save_cookies(driver, cookies_file)
        print("Cookies saved!")

    finally:
        driver.quit()

if __name__ == '__main__':
    main()