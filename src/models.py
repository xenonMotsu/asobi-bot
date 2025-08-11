from dataclasses import dataclass
from datetime import datetime


@dataclass
class DeadlineEntry:
    """締切のあるアイテムやイベントを表すデータモデル。

    Attributes:
        title (str): アイテムまたはイベントの名称。
        url (str): 詳細ページの URL。
        deadline (datetime): 締切日時。
    """

    title: str
    url: str
    deadline: datetime
