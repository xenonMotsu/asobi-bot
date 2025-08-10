# scrape_clickthrough.py
import re
import time, tempfile
from datetime import datetime
from dataclasses import dataclass
from urllib.parse import urlparse
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

BASE = "https://asobiticket2.asobistore.jp"
LIST_URL = f"{BASE}/booths"

def make_driver():
    tmp = tempfile.mkdtemp(prefix="selenium-prof-")
    o = Options()
    o.add_argument("--headless=new")              # ダメなら "--headless" に
    o.add_argument("--no-sandbox")
    o.add_argument("--disable-dev-shm-usage")
    o.add_argument("--window-size=1366,2400")
    o.add_argument(f"--user-data-dir={tmp}")
    o.add_argument("--remote-debugging-port=0")
    o.add_argument("--lang=ja-JP")
    o.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                   "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
    return webdriver.Chrome(options=o)

def accept_cookie(driver):
    # Cookieバナーを閉じる（英/日 ざっくり）
    for xp in [
        "//button[normalize-space()='Accept All Cookies']",
        "//button[contains(., 'Accept All Cookies')]",
        "//button[contains(., '同意') or contains(., '許可')]",
    ]:
        try:
            btn = WebDriverWait(driver, 2).until(EC.element_to_be_clickable((By.XPATH, xp)))
            btn.click(); time.sleep(0.4)
            break
        except Exception:
            pass

def wait_list_ready(driver):
    WebDriverWait(driver, 30).until(
        lambda d: d.execute_script("return document.readyState") == "complete"
    )
    # カード要素が並ぶまで待つ
    WebDriverWait(driver, 25).until(
        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div.booth-item[tpl-tappable]"))
    )

def grow_list_by_scrolling(driver, max_scroll=6, pause=0.8):
    last = 0
    for _ in range(max_scroll):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)
        n = len(driver.find_elements(By.CSS_SELECTOR, "div.booth-item[tpl-tappable]"))
        if n == last:
            break
        last = n

def get_uketsuke_kikan_list(d):
    """
    ページ全体から「YYYY年M月D日(曜) HH:MM 〜 YYYY年M月D日(曜) HH:MM」形式を抽出し、
    [(start_datetime, end_datetime), ...] のリストで返す
    """
    # ページ全体のテキスト
    text = d.find_element(By.TAG_NAME, "body").text

    # 正規表現パターン（例: 2025年7月31日(木) 15:00 〜 2025年8月3日(日) 9:59）
    pattern = (
        r"(\d{4}年\d{1,2}月\d{1,2}日\([^)]+\) \d{1,2}:\d{2})"
        r"\s*〜\s*"
        r"(\d{4}年\d{1,2}月\d{1,2}日\([^)]+\) \d{1,2}:\d{2})"
    )

    matches = re.findall(pattern, text)
    periods = []
    for start_str, end_str in matches:
        # 曜日部分（(木)など）を削除
        start_clean = re.sub(r"\([^)]*\)", "", start_str).strip()
        end_clean = re.sub(r"\([^)]*\)", "", end_str).strip()
        # datetime に変換
        start_dt = datetime.strptime(start_clean, "%Y年%m月%d日 %H:%M")
        end_dt = datetime.strptime(end_clean, "%Y年%m月%d日 %H:%M")
        periods.append((start_dt, end_dt))

    return periods

@dataclass
class AsobiticketData:
    title: str | None
    url: str
    uketsuke_kikan_list: list[tuple[datetime, datetime]]

def fetch_asobiticket() -> list[AsobiticketData]:
    d = make_driver()
    results:list[AsobiticketData] = []
    try:
        d.get(LIST_URL)
        accept_cookie(d)
        wait_list_ready(d)
        grow_list_by_scrolling(d)

        # カード要素を取得
        num_cards = len(d.find_elements(By.CSS_SELECTOR, "div.booth-item[tpl-tappable]"))
        # クリック対象を都度取り直す（戻った時にDOMが再構築される想定）
        for i in range(num_cards):
            # クリック対象のカードを取得
            cards = d.find_elements(By.CSS_SELECTOR, "div.booth-item[tpl-tappable]")
            card = cards[i]
            print(f"Processing card {i + 1}/{len(cards)}, {card.text.strip()}")
            # タイトル/サムネ（見えなければ空でOK）
            try:
                title = card.find_element(By.CSS_SELECTOR, ".booth-title").text.strip()
            except Exception:
                title = ""
            try:
                thumb = card.find_element(By.CSS_SELECTOR, "img").get_attribute("src") or ""
            except Exception:
                thumb = ""

            # クリック → URL変化を待つ
            before = d.current_url
            try:
                card.click()
                time.sleep(2.0)  # 少し待つ
            except Exception as e:
                print(f"Error clicking card {i + 1}: {e}")
                continue

            url = d.current_url
            # /booths/ を含む詳細遷移のみ採用
            if "/booths/" in urlparse(url).path:
                results.append(AsobiticketData(
                    title=title,
                    url=url,
                    uketsuke_kikan_list=get_uketsuke_kikan_list(d)
                ))

            # 戻って次へ
            d.back()
            wait_list_ready(d)
            # スクロールを戻す（再計算のため軽く待つ）
            time.sleep(0.3)

    finally:
        d.quit()

    return results
if __name__ == "__main__":
    data = fetch_asobiticket()
    print(f"Found {len(data)} items")
    for item in data:
        print(f"Title: {item.title}, URL: {item.url}, Periods: {item.uketsuke_kikan_list}")
        if item.uketsuke_kikan_list:
            for start, end in item.uketsuke_kikan_list:
                print(f"  - {start} to {end}")