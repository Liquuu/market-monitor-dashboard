# market-monitor-dashboard

GitHub Actionsで市場データを定期取得し、GitHub Pagesで可視化し、条件一致時にDiscordへ通知する個人向けダッシュボードです。

> [!IMPORTANT]
> このプロジェクトが表示する情報は投資判断を補助する参考情報です。売買の推奨や将来の成果を保証するものではありません。

## 現在の状態

- タスク1（要件・指標定義・設定設計）完了
- タスク2（GitHub Pages用の静的サイト骨格・実運用設定）完了
- 仕様書: [`docs/specification.md`](docs/specification.md)
- 設定例: [`config/config.example.yaml`](config/config.example.yaml)
- 実運用設定: [`config/config.yaml`](config/config.yaml)

## 画面構成

- `index.html`: GitHub Pagesのエントリーポイント
- `assets/css/style.css`: レスポンシブ表示
- `assets/js/app.js`: `data/latest.json`の読み込みと表示
- `data/latest.json`: 後続タスクで市場データ取得処理が更新するファイル

現時点ではサンプルデータを表示します。市場データ取得と指標計算はタスク3で実装します。

## 実装ロードマップ

1. 要件・データソース・指標定義・通知条件を確定する
2. GitHub Pages向けの最小プロジェクトと設定ファイルを作る
3. 市場データ取得とCCI・RSI・ドローダウン計算を実装する
4. 履歴データ保存とGitHub Actionsの定期実行を実装する
5. グラフ・現在値・前回差分・ソースリンクを表示する
6. Discord Webhook通知・メンション・閾値判定を実装する
7. テスト、障害時の扱い、運用手順を整備する
8. GitHub Pagesへ公開し、実運用を確認する

## 機密情報

Discord Webhook URLはコードや設定ファイルに記載せず、GitHub ActionsのRepository Secret `DISCORD_WEBHOOK_URL` に保存します。必要に応じてメンション文字列も `DISCORD_MENTION` に保存します。
