# market-monitor-dashboard

GitHub Actionsで市場データを定期取得し、GitHub Pagesで可視化し、条件一致時にDiscordへ通知する個人向けダッシュボードです。

> [!IMPORTANT]
> このプロジェクトが表示する情報は投資判断を補助する参考情報です。売買の推奨や将来の成果を保証するものではありません。

## 現在の状態

- タスク1（要件・指標定義・設定設計）完了
- タスク2（GitHub Pages用の静的サイト骨格・実運用設定）完了
- タスク3（Yahoo Finance市場データ取得・週足CCI/RSI・ドローダウン計算）完了
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
python -m market_monitor.cli --config config/config.yaml --output data/latest.json
```

取得処理は、設定された各銘柄の直近値、NASDAQ 100の日足履歴から作った確定週足のCCI・RSI、および終値最高値からのドローダウンを出力します。前回値との差分と履歴保存はタスク4で追加します。

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
