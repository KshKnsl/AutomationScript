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

READING_TIME_SECONDS = 1

class ArticleAutomater:
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

        if self.cookies_file and os.path.exists(self.cookies_file):
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

    def save_cookies(self):
        cookies = self.driver.get_cookies()
        with open(self.cookies_file, 'w') as f:
            json.dump(cookies, f, indent=2)
        print(f"Cookies saved to {self.cookies_file}")

    def test_authentication(self):
        try:
            self.driver.get("https://www.geeksforgeeks.org/batch/dsa-jiit")
            time.sleep(3)

            page_text = self.driver.page_source.lower()
            if "login" in page_text or "sign in" in page_text:
                print("Authentication failed - cookies may be expired")
                return False
            else:
                print("Authentication successful")
                return True

        except Exception as e:
            print(f"Auth test error: {e}")
            return False

    def refresh_authentication(self):
        """Handle re-authentication when cookies are invalid"""
        print("Please log in manually in the browser window...")
        input("Press Enter after logging in to save new cookies...")

        self.save_cookies()
        print("New cookies saved!")

        return self.test_authentication()

    def load_article(self, url):
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

        print("Article loaded successfully")
        return True

    def study_articles_session(self, items_csv, completed_csv):
        articles = []
        completed_urls = set()

        if os.path.exists(completed_csv):
            with open(completed_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get('url'):
                        completed_urls.add(row['url'])

        with open(items_csv, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row.get('type') == 'article' and row.get('url'):
                    articles.append(row)

        pending_articles = [article for article in articles if article['url'] not in completed_urls]

        print(f"Found {len(articles)} total articles")
        print(f"Already completed: {len(completed_urls)}")
        print(f"Remaining to read: {len(pending_articles)}")

        if not pending_articles:
            print("All articles have been read! 🎉")
            return

        for i, article in enumerate(pending_articles, 1):
            title = article.get('title', 'Unknown')
            url = article['url']
            if not url.startswith('http'):
                url = f"https://www.geeksforgeeks.org{url}"

            print(f"[{i}/{len(pending_articles)}] {title}")

            success = self.load_article(url)
            if not success:
                continue

            print(f"Reading for {READING_TIME_SECONDS}s...")
            time.sleep(READING_TIME_SECONDS)

            marked_complete = self.mark_article_complete()
            if marked_complete:
                self.add_to_completed(completed_csv, article)
                print(f"✅ Article completed and tracked: {title}")
            else:
                print(f"⚠️  Article read but could not mark as complete: {title}")

            print(f"Done article {i}")

        print("Study session complete")

    def add_to_completed(self, completed_csv, article):
        """Add completed article to tracking CSV"""
        try:
            file_exists = os.path.exists(completed_csv)
            with open(completed_csv, 'a', newline='', encoding='utf-8') as f:
                fieldnames = ['title', 'url', 'type', 'completed_at']
                writer = csv.DictWriter(f, fieldnames=fieldnames)

                if not file_exists:
                    writer.writeheader()

                writer.writerow({
                    'title': article.get('title', 'Unknown'),
                    'url': article['url'],
                    'type': article.get('type', 'article'),
                    'completed_at': time.strftime('%Y-%m-%d %H:%M:%S')
                })
        except Exception as e:
            print(f"Error tracking completed article: {e}")

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
                return True
            else:
                print("Could not mark as read")
                return False

        except Exception as e:
            print(f"Mark error: {e}")
            return False

    def close(self):
        if self.driver:
            self.driver.quit()

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    cookies_file = os.path.join(base_dir, 'cookies.json')
    items_csv = os.path.join(base_dir, 'module_items.csv')
    completed_csv = os.path.join(base_dir, 'completed_articles.csv')

    if not os.path.exists(cookies_file):
        print("No cookies.json")
        return

    if not os.path.exists(items_csv):
        print("No module_items.csv")
        return

    accelerator = ArticleAutomater(cookies_file)

    print("Article Automater Starting...")

    if accelerator.setup_driver(headless=True):
        if accelerator.test_authentication():
            accelerator.study_articles_session(items_csv, completed_csv)
        else:
            print("Authentication failed. Attempting to refresh cookies...")
            accelerator.close()
            accelerator.setup_driver(headless=False)
            if accelerator.refresh_authentication():
                accelerator.close()
                accelerator.setup_driver(headless=True)
                accelerator.study_articles_session(items_csv, completed_csv)
            else:
                print("Re-authentication failed")
    else:
        print("Setup failed")

    accelerator.close()

if __name__ == '__main__':
    main()