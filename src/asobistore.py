import re
from datetime import datetime, timedelta

from bs4 import BeautifulSoup
import requests
from dateutil import tz

from models import DeadlineEntry

ASOBISTORE_URL: str = (
    "https://shop.asobistore.jp/product/catalog/s/simekiri/n/120/sime/1/cf113/118/p"
)


def parse_asobistore_items(html: str) -> list[DeadlineEntry]:
    """アソビストアの HTML から商品情報を抽出する。

    Args:
        html (str): 取得した HTML 文字列。

    Returns:
        list[DeadlineEntry]: 抽出した商品エントリのリスト。
    """

    soup = BeautifulSoup(html, "html.parser")
    entries: list[DeadlineEntry] = []
    base_url = "https://shop.asobistore.jp"

    for item_box in soup.select("div.item_box"):
        name_tag = item_box.select_one(".text_area .name.product_name_area a")
        if not name_tag:
            continue
        title = name_tag.get_text(strip=True)
        url = name_tag.get("href")
        if url and not url.startswith("http"):
            url = base_url + url
        deadline_text = None
        for mark in item_box.select(".icon .shimekiri_mark"):
            text = mark.get_text(strip=True)
            if text.startswith("あと") and "日" in text:
                deadline_text = text
                break
        if not deadline_text:
            continue
        m = re.search(r"あと(\d+)日", deadline_text)
        if m:
            days = int(m.group(1))
        else:
            days = 0
        jst = tz.gettz("Asia/Tokyo")
        now = datetime.now(tz=jst)
        deadline = (now + timedelta(days=days)).replace(hour=23, minute=59, second=0, microsecond=0)
        entries.append(DeadlineEntry(title=title, url=url, deadline=deadline))

    return entries


def get_asobistore_items() -> list[DeadlineEntry]:
    """アソビストアから締切間近の商品を取得する。

    Returns:
        list[DeadlineEntry]: 締切情報付きの商品エントリの一覧。

    Raises:
        requests.HTTPError: HTTP リクエストに失敗した場合。
    """

    ret = []
    for i in range(5):
        response = requests.get(f"{ASOBISTORE_URL}/{i}", timeout=10)
        response.raise_for_status()
        ret_i = parse_asobistore_items(response.text)
        if ret_i:
            ret.extend(ret_i)
        else:
            break
    return ret
