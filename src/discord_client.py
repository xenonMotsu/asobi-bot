import requests

from config import is_debug


def send_discord(webhook_url: str, content: str) -> None:
    """Webhook を使って Discord にメッセージを送信する。

    Args:
        webhook_url (str): Discord の Webhook URL。
        content (str): 送信するメッセージ本文。

    Raises:
        RuntimeError: 送信が HTTP ステータス 204 以外で失敗した場合。
    """

    if is_debug():
        print(f"DEBUG: Sending to {webhook_url} with content:\n{content}")
        return
    ret = requests.post(webhook_url, json={"content": content}, timeout=10)
    if ret.status_code != 204:
        print(f"Failed to send Discord message: {ret.status_code} {ret.text}")
        raise RuntimeError(f"Discord webhook failed with status {ret.status_code}")
