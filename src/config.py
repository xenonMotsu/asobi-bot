import os
import sys


def is_debug() -> bool:
    """デバッグ環境かどうかを判定する。

    Returns:
        bool: コマンドライン引数に ``--DEBUG`` が含まれている場合は ``True``。
    """

    return "--DEBUG" in sys.argv


def load_alert_days() -> list[int]:
    """環境変数から通知する日数を読み込む。

    Returns:
        list[int]: 通知対象となる日数の昇順リスト。環境変数 ``ALERT_DAYS`` が未設定
        または解析に失敗した場合は ``[0, 1, 7]`` を返す。
    """

    value: str | None = os.getenv("ALERT_DAYS")
    if value:
        try:
            days: list[int] = sorted({int(v.strip()) for v in value.split(",") if v.strip()})
            return days
        except ValueError:
            pass
    return [0, 1, 7]
