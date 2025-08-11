# README

## 概要
このプロジェクトは、**アソビストア**および**アソビチケット**の締切間近情報を毎日JST19:00にチェックし、Discordチャンネルに自動通知します。GitHub ActionsとDiscord Webhookを活用するため、無料で運用可能です。

## 通知対象
- アソビストア
  - アイドルマスター関連 締切間近
- アソビチケット
  - 現在申込可能な受付で、締切間近

## 必要環境
- GitHubアカウント
- Discord Webhook URL
- （ローカル開発用）Python 3.11以上
- （ローカル開発用）[uv](https://github.com/astral-sh/uv)

## セットアップ手順
1. リポジトリをクローンまたは作成し、このコード一式を配置
2. DiscordでWebhook URLを作成
   - Discordのチャンネル設定 → Webhook → 新規作成
3. リポジトリのSecretsにWebhook URLを設定
   - `Settings` → `Secrets and variables` → `Actions` → `New repository secret`
   - 名前: `DISCORD_WEBHOOK_URL`
   - 値: Discordで作成したWebhook URL
4. 必要に応じてリポジトリ変数`ALERT_DAYS`を設定（例: `0,1,7`）
   - 締切当日・前日・1週間前に通知する設定
5. 初回はGitHub Actionsの`Run workflow`で手動実行して動作確認
6. 以降は毎日JST19:00に自動実行されます

## 技術概要
- スケジューラ: GitHub Actionsのcron機能
- 実行環境: Ubuntu (GitHubホストランナー)
- スクレイピング: requests + BeautifulSoup4 + lxml
- 日時処理: python-dateutil
- 通知: Discord Webhook API

## コード構成
- `src/main.py`: エントリーポイント
- `src/config.py`: 環境変数の読み込みやデバッグ判定
- `src/discord_client.py`: Discordへの通知送信
- `src/asobistore.py`: アソビストアのデータ取得と解析
- `src/ticket.py`: アソビチケットのデータ取得と変換
- `src/notifications.py`: エントリのフィルタリングとメッセージ整形
- `src/asobiticket.py`: Seleniumを用いたアソビチケットページのスクレイピング

## 注意事項
- 対象サイトのDOM構造に依存するパース処理はサイト変更の影響を受けやすいため、`src/asobistore.py`や`src/asobiticket.py`の処理を適宜調整してください。
- スクレイピングは対象サイトの利用規約やrobots.txtに従って行ってください。
- GitHub Actionsのスケジュールは厳密な時刻保証はなく、数分の遅延が発生することがあります。

## ローカルでの動作確認
```bash
export DISCORD_WEBHOOK_URL="<Webhook URL>"
export ALERT_DAYS="0,1,7"  # 任意
uv run python src/main.py
```
