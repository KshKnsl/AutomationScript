!pip install selenium beautifulsoup4 webdriver-manager

# Install Chrome browser
!apt-get update
!apt-get install -y chromium-browser

# Set up Chrome options for Colab
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def setup_driver_colab(headless=True):
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--remote-debugging-port=9222')

    # Use Colab's Chrome
    options.binary_location = '/usr/bin/chromium-browser'

    try:
        driver = webdriver.Chrome(options=options)
        return driver
    except Exception as e:
        print(f"ChromeDriver error: {e}")
        return None