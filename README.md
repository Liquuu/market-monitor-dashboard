# market-monitor-dashboard

GitHub Actionsで市場データを定期取得し、GitHub Pagesで可視化し、条件一致時にDiscordへ通知する個人向けダッシュボードです。

> [!IMPORTANT]
> このプロジェクトが表示する情報は投資判断を補助する参考情報です。売買の推奨や将来の成果を保証するものではありません。

## 現在の状態

- タスク1（要件・指標定義・設定設計）完了
- タスク2（GitHub Pages用の静的サイト骨格・実運用設定）完了
- タスク3（Yahoo Finance市場データ取得・週足CCI/RSI・ドローダウン計算）完了
- タスク4（履歴保存・前回差分・GitHub Actions定期実行）完了
- 仕様書: [`docs/specification.md`](docs/specification.md)
- 設定例: [`config/config.example.yaml`](config/config.example.yaml)
- 実運用設定: [`config/config.yaml`](config/config.yaml)

## 画面構成

- `index.html`: GitHub Pagesのエントリーポイント
- `assets/css/style.css`: レスポンシブ表示
- `assets/js/app.js`: `data/latest.json`の読み込みと表示
- `data/latest.json`: 後続タスクで市場データ取得処理が更新するファイル

`data/latest.json` は初期状態ではサンプルです。次のコマンドでYahoo Financeから取得し、実データに更新できます。

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
python -m market_monitor.cli --scope all
```

取得処理は、設定された各銘柄の直近値、NASDAQ 100の日足履歴から作った確定週足のCCI・RSI、および終値最高値からのドローダウンを出力します。前回値との差分と履歴も同時に保存します。

## 定期実行と履歴

- `.github/workflows/update-intraday.yml`: 毎日09:00・21:00（Asia/Tokyo）
- `.github/workflows/update-weekly.yml`: 毎週月曜08:00（Asia/Tokyo）
- `data/history/intraday.json`: 直近値とドローダウンの履歴
- `data/history/weekly.json`: 初回取得時に遡及生成する最大10年分の週足CCI・RSI履歴

両ワークフローはActions画面から手動実行もできます。取得元タイムスタンプが前回と同じ場合は履歴追記と自動コミットを省略します。履歴の保持年数や重複判定は `config/config.yaml` の `storage` で変更できます。

実行時刻を変更する場合は、各ワークフローの `cron` を編集します。`timezone: Asia/Tokyo` を指定しているため、cronは日本時間のまま記述できます。

テストは次のコマンドで実行できます。

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

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
