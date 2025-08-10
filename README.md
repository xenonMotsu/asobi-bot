# README

## 概要
このプロジェクトは、**アソビストア**および**アソビチケット**の締切間近情報を毎日JST21:00にチェックし、Discordチャンネルに自動通知します。GitHub ActionsとDiscord Webhookを活用するため、無料で運用可能です。

## 通知対象
- アソビストア
  - アイドルマスター関連 締切間近
- アソビチケット
  - 現在申込可能な受付で、締切間近

## 必要環境
- GitHubアカウント
- Discord Webhook URL
- （ローカル開発用）Python 3.11以上

## セットアップ手順
1. リポジトリをクローンまたは作成し、このコード一式を配置
2. DiscordでWebhook URLを作成
   - Discordのチャンネル設定 → Webhook → 新規作成
3. リポジトリのSecretsにWebhook URLを設定
   - `Settings` → `Secrets and variables` → `Actions` → `New repository secret`
   - 名前: `DISCORD_WEBHOOK_URL`
   - 値: Discordで作成したWebhook URL
4. 初回はGitHub Actionsの`Run workflow`で手動実行して動作確認
5. 以降は毎日JST21:00に自動実行されます

## 技術概要
- スケジューラ: GitHub Actionsのcron機能
- 実行環境: Ubuntu (GitHubホストランナー)
- スクレイピング: requests + BeautifulSoup4 + lxml
- 日時処理: python-dateutil
- 通知: Discord Webhook API

## 注意事項
- 対象サイトのDOM構造が変わると、パース処理が失敗します。その場合は`src/main.py`内の`parse_asobistore_items`と`parse_ticket_event`のセレクタや正規表現を修正してください。
- スクレイピングは対象サイトの利用規約やrobots.txtに従って行ってください。
- GitHub Actionsのスケジュールは厳密な時刻保証はなく、数分の遅延が発生することがあります。

## ローカルでの動作確認
```bash
python -m venv venv
source venv/bin/activate
pip install -r src/requirements.txt
export DISCORD_WEBHOOK_URL="<Webhook URL>"
python src/main.py
```
