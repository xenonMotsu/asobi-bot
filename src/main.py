"""アソビストアとアソビチケットの締切通知のメインエントリーポイント。

このモジュールは対象ウェブサイトからデータを取得し、締切までの日数で
アイテムを絞り込み、Discord に通知を送信する。

各ページの解析ロジックはウェブサイトの DOM 構造に依存するため未実装の
まま TODO としてマークしている。
"""

import sys
import os
from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

import requests
from dateutil import tz

def is_debug() -> None:
    """デバッグ環境かどうか
    
    Returns:
        bool: デバッグ環境であればTrueを返す
    """
    return "--DEBUG" in sys.argv
    

ASOBISTORE_URL: str = (
    "https://shop.asobistore.jp/product/catalog/s/simekiri/sime/1/cf113/118/n/120#a1"
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
    requests.post(webhook_url, json={"content": content}, timeout=10)


# ---------------------------------------------------------------------------
# パース補助関数（未実装）
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

    raise NotImplementedError


def parse_ticket_event_list(html: str) -> list[str]:
    """イベント一覧ページを解析し、各イベントの URL を取得する。

    Args:
        html (str): イベント一覧ページの HTML。

    Returns:
        list[str]: 各イベントページの URL リスト。

    Raises:
        NotImplementedError: 実際のパース処理は未実装。
    """

    raise NotImplementedError


def parse_ticket_event(html: str) -> list[DeadlineEntry]:
    """イベントページを解析し、締切がある受付情報を取得する。

    Args:
        html (str): イベントページの HTML。

    Returns:
        list[DeadlineEntry]: 締切付き受付情報のリスト。

    Raises:
        NotImplementedError: 実際のパース処理は未実装。
    """

    raise NotImplementedError


# ---------------------------------------------------------------------------
# データ取得関数
# ---------------------------------------------------------------------------

def get_asobistore_items() -> list[DeadlineEntry]:
    """アソビストアからアイテムを取得して解析する。

    Returns:
        list[DeadlineEntry]: 締切付きアイテムのリスト。
    """

    response = requests.get(ASOBISTORE_URL, timeout=10)
    response.raise_for_status()
    return parse_asobistore_items(response.text)


def get_ticket_events() -> list[DeadlineEntry]:
    """アソビチケットからイベントを取得して解析する。

    Returns:
        list[DeadlineEntry]: 締切付きイベントのリスト。
    """

    response = requests.get(ASOBITICKET_EVENTS_URL, timeout=10)
    response.raise_for_status()

    event_urls: list[str] = parse_ticket_event_list(response.text)

    entries: list[DeadlineEntry] = []
    for url in event_urls:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        entries.extend(parse_ticket_event(resp.text))
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


def format_message(section: str, entries: Sequence[DeadlineEntry]) -> str:
    """エントリのリストから Discord 用のメッセージを作成する。

    Args:
        section (str): メッセージの見出し。
        entries (Sequence[DeadlineEntry]): 表示するエントリ。

    Returns:
        str: Discord に送信する文字列。
    """

    lines = [f"**{section}**"]
    for e in entries:
        deadline = e.deadline.strftime("%Y-%m-%d %H:%M")
        lines.append(f"- {e.title} | 締切: {deadline} | <{e.url}>")
    return "\n".join(lines)


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

    messages: list[str] = []

    try:
        store_items = filter_entries(get_asobistore_items(), alert_days, now)
        if store_items:
            messages.append(format_message("アソビストア 締切間近", store_items))
    except NotImplementedError:
        messages.append("アソビストアのパースは未実装です。")

    try:
        ticket_items = filter_entries(get_ticket_events(), alert_days, now)
        if ticket_items:
            messages.append(format_message("アソビチケット 締切間近", ticket_items))
    except NotImplementedError:
        messages.append("アソビチケットのパースは未実装です。")

    if messages:
        send_discord(webhook_url, "\n\n".join(messages))


if __name__ == "__main__":
    main()
