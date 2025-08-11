from asobiticket import fetch_asobiticket
from models import DeadlineEntry

ASOBITICKET_BASE: str = "https://asobiticket2.asobistore.jp"
ASOBITICKET_EVENTS_URL: str = f"{ASOBITICKET_BASE}/booths"


def get_ticket_events() -> list[DeadlineEntry]:
    """アソビチケットの受付期間から締切情報を生成する。

    Returns:
        list[DeadlineEntry]: 締切付きイベントの一覧。
    """

    events = fetch_asobiticket()
    entries: list[DeadlineEntry] = []
    for event in events:
        for start, end in event.uketsuke_kikan_list:
            deadline = end.replace(hour=23, minute=59, second=0, microsecond=0)
            entries.append(
                DeadlineEntry(
                    title=event.title if event.title else "(不明)",
                    url=event.url,
                    deadline=deadline,
                )
            )
    return entries
