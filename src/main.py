"""アソビストアとアソビチケットの締切通知のメインエントリーポイント。"""

from collections import defaultdict
from datetime import datetime
import os

from dateutil import tz

from config import load_alert_days
from discord_client import send_discord
from asobistore import get_asobistore_items, ASOBISTORE_URL
from ticket import get_ticket_events, ASOBITICKET_EVENTS_URL
from notifications import filter_entries, format_message
from models import DeadlineEntry


def main() -> None:
    """アソビストアとアソビチケットの締切情報を通知する。

    Raises:
        RuntimeError: Webhook URL が環境変数に設定されていない場合。
    """

    webhook_url: str | None = os.getenv("DISCORD_WEBHOOK_URL")
    if not webhook_url:
        raise RuntimeError("DISCORD_WEBHOOK_URL is not set")

    alert_days: list[int] = load_alert_days()

    jst = tz.gettz("Asia/Tokyo")
    now = datetime.now(tz=jst)

    def send_entries_by_deadline(
        section: str, entries: list[DeadlineEntry], omitted_message: str
    ) -> None:
        """締切ごとにエントリをまとめて送信する。

        Args:
            section (str): メッセージの見出し。
            entries (list[DeadlineEntry]): 送信するエントリ。
            omitted_message (str): 省略時に付加するメッセージ。
        """

        by_deadline = defaultdict(list)
        for e in entries:
            by_deadline[e.deadline.date()].append(e)
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
