from collections import defaultdict
from datetime import datetime
from typing import Sequence

from models import DeadlineEntry


def filter_entries(
    entries: Sequence[DeadlineEntry], alert_days: Sequence[int], now: datetime
) -> list[DeadlineEntry]:
    """通知対象の日数に該当するエントリを抽出する。

    Args:
        entries (Sequence[DeadlineEntry]): 全てのエントリ。
        alert_days (Sequence[int]): 通知対象の日数リスト。
        now (datetime): 現在時刻。

    Returns:
        list[DeadlineEntry]: 条件に一致したエントリのリスト。
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
    max_display: int = 25,
) -> str:
    """Discord 送信用のメッセージを整形する。

    Args:
        section (str): メッセージの見出し。
        entries (Sequence[DeadlineEntry]): 表示するエントリ。
        omitted_message (str, optional): 件数を省略した際に追加する文言。
            デフォルトは "...他にも省略されています..."。
        max_display (int, optional): 表示する最大件数。デフォルトは 25。

    Returns:
        str: 整形されたメッセージ。
    """

    def merge_by_prefix(entries: list[DeadlineEntry], prefix_len: int) -> list[DeadlineEntry]:
        """タイトルの先頭部分でエントリをまとめる。

        Args:
            entries (list[DeadlineEntry]): 対象エントリ。
            prefix_len (int): 比較するタイトルの文字数。

        Returns:
            list[DeadlineEntry]: まとめた結果のエントリ。
        """

        grouped = defaultdict(list)
        for e in entries:
            key = e.title[:prefix_len] if len(e.title) >= prefix_len else e.title
            grouped[key].append(e)
        merged = []
        for key, group in grouped.items():
            if len(group) == 1:
                merged.append(group[0])
            else:
                merged.append(
                    DeadlineEntry(
                        title=key + "...", url=group[0].url, deadline=group[0].deadline
                    )
                )
        return merged

    def build_lines(merged_items: list[DeadlineEntry], omitted: bool) -> list[str]:
        """メッセージの行リストを構築する。

        Args:
            merged_items (list[DeadlineEntry]): 表示するエントリ。
            omitted (bool): 件数が省略されているかどうか。

        Returns:
            list[str]: メッセージの各行。
        """

        lines = [f"**{section}**"]
        if merged_items:
            deadline_str = merged_items[0].deadline.strftime("%Y-%m-%d")
            lines.append(f"締切: {deadline_str}")
            for e in merged_items:
                lines.append(f"- [{e.title}]({e.url})")
        if omitted:
            lines.append(omitted_message)
        return lines

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
            break
        current_max -= 2
    while len(msg) > 2000 and len(merged) > min_display:
        merged = merged[: len(merged) - 1]
        omitted = True
        lines = build_lines(merged, omitted)
        msg = "\n".join(lines)
    if len(msg) > 2000:
        msg = f"**{section}**\n(省略されています)\n" + omitted_message
    return msg
