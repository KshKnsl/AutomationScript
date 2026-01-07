import os
import json
import csv
import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

READING_TIME_SECONDS = 1200

class AuthenticatedStudyAccelerator:
    def __init__(self, cookies_file):
        self.cookies_file = cookies_file
        self.driver = None

    def setup_driver(self, headless=True):
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
                return False
        self.driver = webdriver.Chrome(service=service, options=options)

        if cookies_file and os.path.exists(cookies_file):
            self.load_cookies()
        return True

    def load_cookies(self):
        try:
            with open(self.cookies_file, 'r') as f:
                cookies = json.load(f)

            self.driver.get("https://www.geeksforgeeks.org")
            time.sleep(2)

            for cookie in cookies:
                try:
                    if 'expiry' in cookie and cookie['expiry']:
                        cookie['expiry'] = int(cookie['expiry'])

                    self.driver.add_cookie(cookie)
                except Exception as e:
                    pass

            print("Cookies loaded")
            return True

        except Exception as e:
            print(f"Cookie error: {e}")
            return False

    def test_authentication(self):
        try:
            self.driver.get("https://www.geeksforgeeks.org/batch/dsa-jiit")
            time.sleep(3)

            page_text = self.driver.page_source.lower()
            if "login" in page_text or "sign in" in page_text:
                print("Auth failed")
                return False
            else:
                print("Auth success")
                return True

        except Exception as e:
            print(f"Auth test error: {e}")
            return False

    def speed_read_article(self, url):
        print(f"Loading: {url}")
        self.driver.get(url)

        WebDriverWait(self.driver, 10).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )

        if "login" in self.driver.page_source.lower():
            print("Access denied")
            return False

        try:
            title_elem = self.driver.find_element(By.TAG_NAME, 'h1')
            title = title_elem.text
            print(f"Article: {title}")
        except:
            title = "Unknown"
            print("Title not found")

        speed_script = """
        var controlPanel = document.createElement('div');
        controlPanel.id = 'speed-read-controls';
        controlPanel.style.cssText = `
            position: fixed; top: 10px; right: 10px; z-index: 9999;
            background: rgba(0,0,0,0.9); color: white; padding: 15px;
            border-radius: 8px; font-family: Arial, sans-serif; font-size: 14px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.3);
        `;
        controlPanel.innerHTML = `
            <div style="margin-bottom: 10px; font-weight: bold;">Speed Reading</div>
            <div>Ctrl+S: Toggle mode</div>
            <div>↑/↓: Navigate paragraphs</div>
            <div>Space: Scroll down</div>
            <div>Para: <span id="para-counter">1</span></div>
        `;
        document.body.appendChild(controlPanel);

        let currentPara = 0;
        let paragraphs = document.querySelectorAll('p');
        let speedMode = false;

        paragraphs = Array.from(paragraphs).filter(p => {
            const text = p.textContent.trim();
            return text.length > 20 && !text.includes('©') && !text.includes('Terms');
        });

        function updateDisplay() {
            document.getElementById('para-counter').textContent = currentPara + 1;
        }

        function highlightParagraph(index) {
            paragraphs.forEach(p => {
                p.style.backgroundColor = '';
                p.style.padding = '';
                p.style.borderRadius = '';
            });

            if (index >= 0 && index < paragraphs.length) {
                paragraphs[index].scrollIntoView({behavior: 'smooth', block: 'center'});
                if (speedMode) {
                    paragraphs[index].style.backgroundColor = '#ffff99';
                    paragraphs[index].style.padding = '10px';
                    paragraphs[index].style.borderRadius = '5px';
                }
            }
        }

        document.addEventListener('keydown', function(e) {
            if (e.ctrlKey && e.key === 's') {
                e.preventDefault();
                speedMode = !speedMode;

                if (speedMode) {
                    controlPanel.style.background = 'rgba(0,100,0,0.9)';
                    highlightParagraph(currentPara);
                } else {
                    controlPanel.style.background = 'rgba(0,0,0,0.9)';
                    paragraphs.forEach(p => {
                        p.style.backgroundColor = '';
                        p.style.padding = '';
                        p.style.borderRadius = '';
                    });
                }
            }

            if (speedMode) {
                if (e.key === 'ArrowDown' && currentPara < paragraphs.length - 1) {
                    e.preventDefault();
                    currentPara++;
                    highlightParagraph(currentPara);
                    updateDisplay();
                } else if (e.key === 'ArrowUp' && currentPara > 0) {
                    e.preventDefault();
                    currentPara--;
                    highlightParagraph(currentPara);
                    updateDisplay();
                } else if (e.key === ' ') {
                    e.preventDefault();
                    window.scrollBy(0, window.innerHeight * 0.8);
                }
            }
        });

        updateDisplay();
        """

        self.driver.execute_script(speed_script)
        print("Speed reading ready")
        return True

    def study_articles_session(self, items_csv):
        articles = []
        with open(items_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('type') == 'article' and row.get('url'):
                    articles.append(row)

        print(f"Found {len(articles)} articles")

        for i, article in enumerate(articles, 1):
            title = article.get('title', 'Unknown')
            url = article['url']
            if not url.startswith('http'):
                url = f"https://www.geeksforgeeks.org{url}"

            print(f"[{i}/{len(articles)}] {title}")

            success = self.speed_read_article(url)
            if not success:
                continue

            print(f"Reading for {READING_TIME_SECONDS}s...")
            time.sleep(READING_TIME_SECONDS)
            print(f"Done article {i}")

            self.mark_article_complete()

        print("Study complete")

    def mark_article_complete(self):
        try:
            js_script = """
            const buttons = document.querySelectorAll('button, [role="button"], .btn, .button, input[type="button"], input[type="submit"]');
            for (let btn of buttons) {
                const text = (btn.textContent || btn.innerText || btn.value || '').toLowerCase().trim();
                if (text.includes('mark as read') || text.includes('mark as completed') || text.includes('complete') || text.includes('read')) {
                    btn.click();
                    return true;
                }
            }

            const completeElements = document.querySelectorAll('[data-action*="complete"], [data-action*="read"], .complete, .mark-complete, .mark-read, .read');
            for (let elem of completeElements) {
                if (elem.tagName.toLowerCase() === 'button' || elem.onclick || elem.getAttribute('role') === 'button' || elem.type === 'button' || elem.type === 'submit') {
                    elem.click();
                    return true;
                }
            }

            return false;
            """

            result = self.driver.execute_script(js_script)
            if result:
                print("Marked as read")
                time.sleep(2)
            else:
                print("Could not mark as read")

        except Exception as e:
            print(f"Mark error: {e}")

    def close(self):
        if self.driver:
            self.driver.quit()

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_file = os.path.join(base_dir, 'cookies.json')
    items_csv = os.path.join(base_dir, 'module_items.csv')

    if not os.path.exists(cookies_file):
        print("No cookies.json")
        return

    if not os.path.exists(items_csv):
        print("No module_items.csv")
        return

    accelerator = AuthenticatedStudyAccelerator(cookies_file)

    print("Study Accelerator")

    if accelerator.setup_driver(headless=True):
        if accelerator.test_authentication():
            accelerator.study_articles_session(items_csv)
        else:
            print("Auth failed")
    else:
        print("Setup failed")

    accelerator.close()

if __name__ == '__main__':
    main()