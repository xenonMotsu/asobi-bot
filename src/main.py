"""アソビストアとアソビチケットの締切通知のメインエントリーポイント。

このモジュールは対象ウェブサイトからデータを取得し、締切までの日数で
アイテムを絞り込み、Discord に通知を送信する。

各ページの解析ロジックはウェブサイトの DOM 構造に依存するため未実装の
まま TODO としてマークしている。
"""

import re
import sys
import os
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Sequence

from collections import defaultdict

import requests
from dateutil import tz

from asobiticket import fetch_asobiticket

def is_debug() -> None:
    """デバッグ環境かどうか
    
    Returns:
        bool: デバッグ環境であればTrueを返す
    """
    return "--DEBUG" in sys.argv
    

ASOBISTORE_URL: str = (
    "https://shop.asobistore.jp/product/catalog/s/simekiri/n/120/sime/1/cf113/118/p"
)
ASOBITICKET_BASE: str = "https://asobiticket2.asobistore.jp"
ASOBITICKET_EVENTS_URL: str = f"{ASOBITICKET_BASE}/booths"


@dataclass
class DeadlineEntry:
    """締切のあるアイテムやイベントを表す簡単なデータ構造。"""

    title: str
    url: str
    deadline: datetime


def load_alert_days() -> list[int]:
    """環境変数から通知する日数を読み込む。

    Returns:
        list[int]: 締切から何日前に通知するかを昇順に並べたリスト。
    """

    value: str | None = os.getenv("ALERT_DAYS")
    if value:
        try:
            days: list[int] = sorted({int(v.strip()) for v in value.split(",") if v.strip()})
            return days
        except ValueError:
            pass
    return [0, 1, 7]


def send_discord(webhook_url: str, content: str) -> None:
    """Webhook を使って Discord にメッセージを送信する。

    Args:
        webhook_url (str): Discord の Webhook URL。
        content (str): 送信するメッセージ本文。

    Returns:
        None: 返り値はない。
    """

    if is_debug():
        print(f"DEBUG: Sending to {webhook_url} with content:\n{content}")
        return
    ret = requests.post(webhook_url, json={"content": content}, timeout=10)
    if ret.status_code != 204:
        print(f"Failed to send Discord message: {ret.status_code} {ret.text}")
        raise RuntimeError(f"Discord webhook failed with status {ret.status_code}")

# ---------------------------------------------------------------------------
# パース補助関数
# ---------------------------------------------------------------------------

def parse_asobistore_items(html: str) -> list[DeadlineEntry]:
    """アソビストアの HTML から締切付きアイテムの一覧を取得する。

    Args:
        html (str): アソビストアの HTML。

    Returns:
        list[DeadlineEntry]: 締切付きアイテムのリスト。

    Raises:
        NotImplementedError: 実際のパース処理は未実装。
    """
    soup = BeautifulSoup(html, "html.parser")
    entries: list[DeadlineEntry] = []
    base_url = "https://shop.asobistore.jp"

    for item_box in soup.select("div.item_box"):
        # 商品名
        name_tag = item_box.select_one(".text_area .name.product_name_area a")
        if not name_tag:
            continue
        title = name_tag.get_text(strip=True)
        url = name_tag.get("href")
        if url and not url.startswith("http"):
            url = base_url + url

        # 締切日数の抽出
        deadline_text = None
        for mark in item_box.select(".icon .shimekiri_mark"):
            text = mark.get_text(strip=True)
            if text.startswith("あと") and "日" in text:
                deadline_text = text
                break
        if not deadline_text:
            continue
        # 例: "あと7日!" → 7
        m = re.search(r"あと(\d+)日", deadline_text)
        if m:
            days = int(m.group(1))
        else:
            days = 0
        # 今日からdays日後の23:59を締切とする
        jst = tz.gettz("Asia/Tokyo")
        now = datetime.now(tz=jst)
        deadline = (now + timedelta(days=days)).replace(hour=23, minute=59, second=0, microsecond=0)

        entries.append(DeadlineEntry(title=title, url=url, deadline=deadline))

    return entries


# ---------------------------------------------------------------------------
# データ取得関数
# ---------------------------------------------------------------------------

def get_asobistore_items() -> list[DeadlineEntry]:
    """アソビストアからアイテムを取得して解析する。

    Returns:
        list[DeadlineEntry]: 締切付きアイテムのリスト。
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
    if is_debug():
        print(f"DEBUG: Fetched {len(ret)} items from Asobistore")
    return ret

def get_ticket_events() -> list[DeadlineEntry]:
    """アソビチケットのイベントを取得して解析する。

    Returns:
        list[DeadlineEntry]: 締切付きイベントのリスト。
    """

    events = fetch_asobiticket()
    entries: list[DeadlineEntry] = []
    for event in events:
        for start, end in event.uketsuke_kikan_list:
            # 締切は終了日時の23:59とする
            deadline = end.replace(hour=23, minute=59, second=0, microsecond=0)
            entries.append(DeadlineEntry(
                title=event.title if event.title else "(不明)",
                url=event.url, deadline=end
            ))
    return entries
# ---------------------------------------------------------------------------
# ユーティリティ関数
# ---------------------------------------------------------------------------

def filter_entries(
    entries: Sequence[DeadlineEntry], alert_days: Sequence[int], now: datetime
) -> list[DeadlineEntry]:
    """指定された通知日数に一致するエントリのみを抽出する。

    Args:
        entries (Sequence[DeadlineEntry]): 対象のエントリ。
        alert_days (Sequence[int]): 通知を行う日数。
        now (datetime): 基準となる現在時刻。

    Returns:
        list[DeadlineEntry]: 条件に合致したエントリのリスト。
    """

    alert_set = set(alert_days)
    result: list[DeadlineEntry] = []
    for entry in entries:
        delta = (entry.deadline.date() - now.date()).days
        if delta in alert_set:
            result.append(entry)
    return result


def format_message(
        section: str,
        entries: Sequence[DeadlineEntry],
        omitted_message: str = "...他にも省略されています...",
        max_display: int = 25
    ) -> str:
    """エントリのリストから Discord 用のメッセージを作成する。

    Args:
        section (str): メッセージの見出し。
        entries (Sequence[DeadlineEntry]): 表示するエントリ。
        omitted_message (str): 省略時に表示するメッセージ。
        max_display (int): 最大表示数。

    Returns:
        str: Discord に送信する文字列。
    """

    def merge_by_prefix(entries: list[DeadlineEntry], prefix_len: int) -> list[DeadlineEntry]:
        grouped = defaultdict(list)
        for e in entries:
            key = e.title[:prefix_len] if len(e.title) >= prefix_len else e.title
            grouped[key].append(e)
        merged = []
        for key, group in grouped.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                merged.append(DeadlineEntry(title=key + "...", url=group[0].url, deadline=group[0].deadline))
        return merged

    # 1日分のみを受け取る前提なので、entriesは同じ締切日のみ
    def build_lines(merged_items, omitted):
        lines = [f"**{section}**"]
        if merged_items:
            deadline_str = merged_items[0].deadline.strftime("%Y-%m-%d")
            lines.append(f"締切: {deadline_str}")
            for e in merged_items:
                lines.append(f"- [{e.title}]({e.url})")
        if omitted:
            lines.append(omitted_message)
        return lines

    # 2000字未満になるまでmax_displayを減らす
    min_display = 3
    current_max = max_display
    merged = entries[:]
    omitted = False
    while True:
        merged = entries[:]
        omitted = False
        if len(merged) > current_max:
            L = max(len(e.title) for e in merged)
            for l in range(L, 0, -1):
                merged = merge_by_prefix(merged, l)
                if len(merged) <= current_max:
                    break
            if len(merged) > current_max:
                merged = merged[:current_max]
            omitted = True
        lines = build_lines(merged, omitted)
        msg = "\n".join(lines)
        if len(msg) <= 2000 or current_max <= min_display:
            # 2000字未満、またはこれ以上減らせない
            break
        current_max -= 2
    # それでも超える場合はさらに強制的に切り詰め
    while len(msg) > 2000 and len(merged) > min_display:
        merged = merged[:len(merged)-1]
        omitted = True
        lines = build_lines(merged, omitted)
        msg = "\n".join(lines)
    # 最後の手段: 省略メッセージのみ
    if len(msg) > 2000:
        msg = f"**{section}**\n(省略されています)\n" + omitted_message
    return msg


# ---------------------------------------------------------------------------
# メインルーチン
# ---------------------------------------------------------------------------

def main() -> None:
    """全体の処理を実行するメイン関数。

    Returns:
        None: 返り値はない。
    """

    webhook_url: str | None = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")

    alert_days: list[int] = load_alert_days()

    jst = tz.gettz("Asia/Tokyo")
    now = datetime.now(tz=jst)


    def send_entries_by_deadline(section: str, entries: list[DeadlineEntry], omitted_message: str):
        # 締切日ごとにグループ化
        by_deadline = defaultdict(list)
        for e in entries:
            by_deadline[e.deadline.date()].append(e)
        # 締切日で昇順ソート
        for deadline in sorted(by_deadline.keys()):
            group = by_deadline[deadline]
            msg = format_message(
                section,
                group,
                omitted_message=omitted_message,
            )
            send_discord(webhook_url, msg)

    any_sent = False

    try:
        store_items = filter_entries(get_asobistore_items(), alert_days, now)
        if store_items:
            send_entries_by_deadline(
                "アソビストア 締切間近",
                store_items,
                omitted_message=f"...一部省略されています...\n詳細は[アソビストア]({ASOBISTORE_URL})を確認してください。",
            )
            any_sent = True
    except NotImplementedError:
        send_discord(webhook_url, "アソビストアのパースは未実装です。")
        any_sent = True

    try:
        ticket_items = filter_entries(get_ticket_events(), alert_days, now)
        if ticket_items:
            send_entries_by_deadline(
                "アソビチケット 締切間近",
                ticket_items,
                omitted_message=f"...一部省略されています...\n詳細は[アソビチケット]({ASOBITICKET_EVENTS_URL})を確認してください。",
            )
            any_sent = True
    except NotImplementedError:
        send_discord(webhook_url, "アソビチケットのパースは未実装です。")
        any_sent = True

    if not any_sent:
        no_message = ",".join(map(str, sorted(alert_days))) + "日後に締切のアイテムはありませんでした。"
        send_discord(webhook_url, no_message)

if __name__ == "__main__":
    main()
