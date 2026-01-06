import os
import csv
import time
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup

def setup_driver(headless=True):
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
    return driver

def load_cookies(driver, cookies_file='cookies.json'):
    try:
        with open(cookies_file, 'r') as f:
            cookies = json.load(f)

        driver.get("https://www.geeksforgeeks.org")
        time.sleep(2)

        for cookie in cookies:
            try:
                if 'expiry' in cookie and cookie['expiry']:
                    cookie['expiry'] = int(cookie['expiry'])

                driver.add_cookie(cookie)
            except Exception as e:
                pass

        print("Cookies loaded")
        return True

    except Exception as e:
        print(f"Cookie error: {e}")
        return False

def scrape_course_tracks(driver, course_url, cookies_file='cookies.json'):
    if not load_cookies(driver, cookies_file):
        print("Cookie load failed")
        return []

    print(f"Loading course: {course_url}")
    driver.get(course_url)

    time.sleep(3)

    page_text = driver.page_source.lower()
    if "login" in page_text or "sign in" in page_text or "please click on login button" in page_text:
        print("Auth failed")
        return []

    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'batch_individual_tab__type___wbkY'))
        )
    except Exception as e:
        print("Page load timeout")
        return []

    tracks = []

    # Find all category sections
    category_sections = driver.find_elements(By.CLASS_NAME, 'batch_individual_tab__type___wbkY')
    print(f"Found {len(category_sections)} category sections")

    for section_idx, section in enumerate(category_sections):
        try:
            # Get category name
            category_header = section.find_element(By.CLASS_NAME, 'batch_category_header___igBF')
            category_title_elem = category_header.find_element(By.TAG_NAME, 'h3')
            category_name = category_title_elem.text.strip()
            print(f"\nProcessing category: {category_name}")

            # Check if category is collapsed and expand if needed
            header_classes = category_header.get_attribute('class')
            if 'batch_open__FkoHN' not in header_classes:
                print(f"  Category {category_name} is collapsed, expanding...")
                category_header.click()
                time.sleep(2)  # Wait for expansion
                # Re-check if expanded
                header_classes = category_header.get_attribute('class')
                if 'batch_open__FkoHN' not in header_classes:
                    print(f"  Failed to expand {category_name}, skipping...")
                    continue

            # Check if this category has tabs
            try:
                tab_menu = section.find_element(By.CLASS_NAME, 'ui.pointing.secondary.menu')
                tabs = tab_menu.find_elements(By.CLASS_NAME, 'item')

                # Process each tab
                for tab_idx, tab in enumerate(tabs):
                    try:
                        tab_name = tab.text.strip()
                        print(f"  Processing tab: {tab_name}")

                        # Click tab if not already active
                        if 'active' not in tab.get_attribute('class'):
                            tab.click()
                            time.sleep(2)  # Wait for content to load

                        # Wait for tracks to load
                        try:
                            WebDriverWait(driver, 5).until(
                                lambda d: len(d.find_elements(By.CLASS_NAME, 'batch_item__ndA6j')) > 0
                            )
                        except:
                            print(f"    No tracks found in {tab_name} tab")
                            continue

                        # Scrape tracks from this tab
                        tab_tracks = scrape_tracks_from_current_view(driver, category_name, tab_name)
                        tracks.extend(tab_tracks)
                        print(f"    Found {len(tab_tracks)} tracks in {tab_name}")

                    except Exception as e:
                        print(f"    Error processing tab {tab_idx}: {e}")
                        continue

            except:
                # Category doesn't have tabs, scrape directly
                print(f"  No tabs found, scraping directly")
                try:
                    # Wait for tracks to load
                    WebDriverWait(driver, 5).until(
                        lambda d: len(d.find_elements(By.CLASS_NAME, 'batch_item__ndA6j')) > 0
                    )
                    category_tracks = scrape_tracks_from_current_view(driver, category_name, "Default")
                    tracks.extend(category_tracks)
                    print(f"  Found {len(category_tracks)} tracks")
                except Exception as e:
                    print(f"  Error scraping category {category_name}: {e}")
                    continue

        except Exception as e:
            print(f"Error processing category {section_idx}: {e}")
            continue

    print(f"\nTotal tracks found: {len(tracks)}")
    return tracks

def scrape_tracks_from_current_view(driver, category_name, tab_name):
    """Scrape tracks from the currently visible section/tab"""
    tracks = []

    track_elements = driver.find_elements(By.CLASS_NAME, 'batch_item__ndA6j')
    print(f"    Found {len(track_elements)} track elements in {category_name} - {tab_name}")

    for elem in track_elements:
        track_data = {}

        try:
            title_elem = elem.find_element(By.CLASS_NAME, 'batch_title__XImuz')
            track_data['title'] = title_elem.text.strip()
        except:
            continue

        try:
            link_elem = elem.find_element(By.XPATH, './ancestor::a')
            track_data['url'] = link_elem.get_attribute('href')
        except:
            continue

        try:
            meta_container = elem.find_element(By.CLASS_NAME, 'batch_content_meta__8RbQN')
            meta_texts = meta_container.find_elements(By.TAG_NAME, 'p')
            for meta in meta_texts:
                text = meta.text.strip()
                if 'Videos' in text:
                    track_data['videos'] = text
                elif 'Articles' in text:
                    track_data['articles'] = text
                elif 'Problems' in text:
                    track_data['problems'] = text
                elif 'MCQ' in text:
                    track_data['mcqs'] = text
        except:
            pass

        # Add category and tab info
        track_data['category'] = category_name
        track_data['tab'] = tab_name

        if track_data and track_data.get('url'):
            tracks.append(track_data)

    return tracks

def scrape_module_items(driver, track_url, cookies_file='cookies.json'):
    if not load_cookies(driver, cookies_file):
        print("Cookie load failed")
        return []

    print(f"Loading module: {track_url}")
    driver.get(track_url)

    # Wait for page to load
    time.sleep(5)

    # Check if we're still on a login page
    page_text = driver.page_source.lower()
    if "login" in page_text or "sign in" in page_text or "please click on login button" in page_text:
        print("Auth failed for track")
        return []

    # Try to wait for sidebar tabs (for track pages)
    sidebar_found = False
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, 'sidebar_tabs__JmBlR'))
        )
        sidebar_found = True
        print("Sidebar tabs found")
    except:
        print("No sidebar tabs found, trying direct item scraping")

    items = []

    if sidebar_found:
        # Original logic for track pages with sidebar tabs
        def scrape_tab_items(tab_name, expected_type=None):
            tab_items = []
            try:
                tabs = driver.find_elements(By.CLASS_NAME, 'sidebar_tabs__JmBlR')
                target_tab = None

                for tab in tabs:
                    try:
                        p_elem = tab.find_element(By.TAG_NAME, 'p')
                        tab_text = p_elem.text.lower().strip()
                    except:
                        tab_text = tab.text.lower().strip()

                    if tab_name in tab_text:
                        target_tab = tab
                        break

                if not target_tab:
                    return tab_items

                if 'active' not in target_tab.get_attribute('class'):
                    target_tab.click()
                    time.sleep(3)

                    try:
                        WebDriverWait(driver, 10).until(
                            lambda d: len(d.find_elements(By.CLASS_NAME, 'sidebar_item__khyNp')) > 0
                        )
                    except:
                        return tab_items

                sidebar_items = driver.find_elements(By.CLASS_NAME, 'sidebar_item__khyNp')

                for item in sidebar_items:
                    item_data = {}

                    try:
                        title_elem = item.find_element(By.TAG_NAME, 'p')
                        item_data['title'] = title_elem.text.strip()
                    except:
                        continue

                    try:
                        item_data['url'] = item.get_attribute('href')
                    except:
                        continue

                    if expected_type:
                        item_data['type'] = expected_type
                    else:
                        try:
                            imgs = item.find_elements(By.TAG_NAME, 'img')
                            type_determined = False
                            for img in imgs:
                                src = img.get_attribute('src') or ''
                                if 'Article' in src or 'book-open' in src or 'Article_' in src:
                                    item_data['type'] = 'article'
                                    type_determined = True
                                    break
                                elif 'Group11' in src or 'youtube' in src or 'video' in src:
                                    item_data['type'] = 'video'
                                    type_determined = True
                                    break

                            if not type_determined:
                                try:
                                    meta_elem = item.find_element(By.CLASS_NAME, 'sidebar_meta__9J4r4')
                                    meta_text = meta_elem.text.strip()
                                    item_data['meta'] = meta_text
                                    if 'Duration' in meta_text or 'min' in meta_text or 'sec' in meta_text:
                                        item_data['type'] = 'video'
                                    elif 'Last Updated' in meta_text or any(char.isdigit() for char in meta_text if char in '0123456789-'):
                                        item_data['type'] = 'article'
                                    else:
                                        item_data['type'] = tab_name[:-1] if tab_name.endswith('s') else tab_name
                                except:
                                    item_data['type'] = tab_name[:-1] if tab_name.endswith('s') else tab_name
                        except:
                            item_data['type'] = tab_name[:-1] if tab_name.endswith('s') else tab_name

                    if not item_data.get('meta'):
                        try:
                            meta_elem = item.find_element(By.CLASS_NAME, 'sidebar_meta__9J4r4')
                            item_data['meta'] = meta_elem.text.strip()
                        except:
                            pass

                    if item_data.get('title') and item_data.get('url'):
                        tab_items.append(item_data)

            except Exception as e:
                pass

            return tab_items

        video_items = scrape_tab_items('videos', 'video')
        items.extend(video_items)

        article_items = scrape_tab_items('articles', 'article')
        items.extend(article_items)

        if len(items) < 5:
            all_items = scrape_tab_items('all')
            existing_urls = {item['url'] for item in items}
            for item in all_items:
                if item['url'] not in existing_urls:
                    items.append(item)
    else:
        # Fallback: try to scrape items directly from the page
        print("Attempting direct item scraping...")
        try:
            # Look for any links that might be articles/videos
            all_links = driver.find_elements(By.TAG_NAME, 'a')

            for link in all_links:
                href = link.get_attribute('href')
                if href and ('/batch/dsa-jiit/track/' in href or '/article/' in href or '/video/' in href):
                    title = link.text.strip()
                    if title and len(title) > 5:  # Filter out very short titles
                        item_data = {
                            'title': title,
                            'url': href,
                            'type': 'article' if '/article/' in href else 'video' if '/video/' in href else 'unknown'
                        }
                        items.append(item_data)

            # Remove duplicates
            seen_urls = set()
            unique_items = []
            for item in items:
                if item['url'] not in seen_urls:
                    seen_urls.add(item['url'])
                    unique_items.append(item)
            items = unique_items

        except Exception as e:
            print(f"Direct scraping failed: {e}")

    return items

def test_single_module(driver, track_url, cookies_file='cookies.json'):
    print(f"Testing module: {track_url}")

    items = scrape_module_items(driver, track_url, cookies_file)

    print(f"Items found: {len(items)}")

    videos = [item for item in items if item['type'] == 'video']
    articles = [item for item in items if item['type'] == 'article']

    print(f"Videos: {len(videos)}")
    print(f"Articles: {len(articles)}")

    return items

def main():
    base_dir = os.path.dirname(os.path.abspath(__file__))
    course_url = "https://www.geeksforgeeks.org/batch/dsa-jiit"

    driver = setup_driver(headless=True)

    if driver:
        try:
            test_track_url = "https://www.geeksforgeeks.org/batch/dsa-jiit/track/Java-Foundation-Data-Types-2"
            print("Testing module...")
            test_items = test_single_module(driver, test_track_url, 'cookies.json')

            if not test_items:
                print("Test failed")
                return

            print("Test passed, scraping course...")

            tracks = scrape_course_tracks(driver, course_url, 'cookies.json')

            tracks_csv = os.path.join(base_dir, 'course_tracks.csv')
            with open(tracks_csv, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'url', 'videos', 'articles', 'problems', 'mcqs', 'category', 'tab']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for track in tracks:
                    writer.writerow(track)

            print(f"Tracks saved: {len(tracks)}")

            all_items = []
            for i, track in enumerate(tracks):
                track_url = track['url']
                if track_url:
                    print(f"Processing track {i+1}/{len(tracks)}: {track['title']}")

                    max_retries = 3
                    items = []
                    for attempt in range(max_retries):
                        try:
                            items = scrape_module_items(driver, track_url, 'cookies.json')
                            if items:
                                break
                            else:
                                print(f"Attempt {attempt+1}: No items, retrying...")
                        except Exception as e:
                            print(f"Attempt {attempt+1} failed: {e}")
                            if attempt < max_retries - 1:
                                time.sleep(5)
                            else:
                                print(f"Failed after {max_retries} attempts")

                    all_items.extend(items)
                    print(f"Items in track: {len(items)}")

                    time.sleep(2)

            items_csv = os.path.join(base_dir, 'module_items.csv')
            with open(items_csv, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['type', 'title', 'url', 'meta']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in all_items:
                    writer.writerow(item)

            print(f"Total items: {len(all_items)}")

            videos = [item for item in all_items if item['type'] == 'video']
            articles = [item for item in all_items if item['type'] == 'article']
            print(f"Videos: {len(videos)}, Articles: {len(articles)}")

        finally:
            driver.quit()
    else:
        print("Fallback to local files...")
        from bs4 import BeautifulSoup

        course_file = os.path.join(base_dir, 'Courcce.html')
        if os.path.exists(course_file):
            print("Parsing course from local file...")
            tracks = parse_course_overview_local(course_file)

            tracks_csv = os.path.join(base_dir, 'course_tracks.csv')
            with open(tracks_csv, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['title', 'url', 'videos', 'articles', 'problems', 'mcqs', 'category', 'tab']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for track in tracks:
                    writer.writerow(track)

            print(f"Tracks from local: {len(tracks)}")

        module_file = os.path.join(base_dir, 'Module.html')
        if os.path.exists(module_file):
            print("Parsing module from local file...")
            items = parse_module_page_local(module_file)

            if not items:
                article_file = os.path.join(base_dir, 'Article.html')
                if os.path.exists(article_file):
                    print("Trying Article.html...")
                    items = parse_module_page_local(article_file)

            items_csv = os.path.join(base_dir, 'module_items.csv')
            with open(items_csv, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['type', 'title', 'url', 'meta']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                writer.writeheader()
                for item in items:
                    writer.writerow(item)

            print(f"Items from local: {len(items)}")

        print("For complete data, download ChromeDriver")

def parse_course_overview_local(html_file):
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    tracks = []

    track_items = soup.find_all('div', class_='batch_item__ndA6j')

    for item in track_items:
        track_data = {}

        title_elem = item.find('p', class_='batch_title__XImuz')
        if title_elem:
            track_data['title'] = title_elem.get_text(strip=True)

        link_elem = item.find_parent('a')
        if link_elem and link_elem.get('href'):
            track_data['url'] = link_elem['href']

        meta_container = item.find('div', class_='batch_content_meta__8RbQN')
        if meta_container:
            metas = meta_container.find_all('p')
            for meta in metas:
                text = meta.get_text(strip=True)
                if 'Videos' in text:
                    track_data['videos'] = text
                elif 'Articles' in text:
                    track_data['articles'] = text
                elif 'Problems' in text:
                    track_data['problems'] = text
                elif 'MCQ' in text:
                    track_data['mcqs'] = text

        if track_data:
            # Add default category/tab for local parsing
            track_data['category'] = 'Unknown'
            track_data['tab'] = 'Default'
            tracks.append(track_data)

    return tracks

def parse_module_page_local(html_file):
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f.read(), 'lxml')

    items = []

    sidebar_items = soup.find_all('a', class_=lambda x: x and 'sidebar_item__khyNp' in x)

    for item in sidebar_items:
        item_data = {}

        title_elem = item.find('p')
        if title_elem:
            item_data['title'] = title_elem.get_text(strip=True)

        if item.get('href'):
            item_data['url'] = item['href']

        imgs = item.find_all('img')
        for img in imgs:
            src = img.get('src', '')
            alt = img.get('alt', '')
            if 'Article' in src or 'article' in alt.lower():
                item_data['type'] = 'article'
                break
            elif 'Group11' in src or 'youtube' in src.lower() or 'video' in alt.lower():
                item_data['type'] = 'video'
                break

        if not item_data.get('type'):
            text_content = item.get_text().lower()
            if 'duration' in text_content or 'min' in text_content:
                item_data['type'] = 'video'
            else:
                item_data['type'] = 'article'

        meta_elem = item.find('p', class_=lambda x: x and 'meta' in x)
        if meta_elem:
            item_data['meta'] = meta_elem.get_text(strip=True)

        if item_data.get('title'):
            items.append(item_data)

    return items

if __name__ == '__main__':
    main()