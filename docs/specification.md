# 市場監視ダッシュボード仕様書

更新日: 2026-08-27  
ステータス: タスク1確定仕様

## 1. 目的

NASDAQ 100と関連する恐怖・歪度・マクロ指標を定期的に記録し、ブラウザで履歴と最新状態を確認できるようにする。設定した条件に入った場合は、Discordの指定チャンネルへWebhookで通知する。

このシステムは自動売買を行わず、注文機能も持たない。

## 2. システム構成

1. GitHub Actionsが設定された時刻にPython処理を実行する。
2. Python処理が市場データを取得し、指標と前回差分を計算する。
3. 結果をJSON/CSVへ追記し、同じリポジトリへコミットする。
4. 条件判定が新たに成立した場合、Discord Webhookへ通知する。
5. GitHub Pagesが履歴ファイルを読み込み、Chart.jsで表示する。

Pagesは静的サイトとし、Webhook URLなどのSecretをブラウザへ渡さない。

## 3. 取得対象

| ID | 内容 | 初期シンボル | 初期ソース | 取得頻度 | 表示単位 |
|---|---|---|---|---|---|
| `nasdaq100` | NASDAQ 100 | `^NDX` | Yahoo Finance | 日2回＋週次計算用 | index |
| `skew` | Cboe SKEW Index | `^SKEW` | Yahoo Finance | 日2回 | index |
| `vix` | Cboe Volatility Index | `^VIX` | Yahoo Finance | 日2回 | index |
| `brent` | Brent原油先物 | `BZ=F` | Yahoo Finance | 日2回 | USD/bbl |
| `us10y` | 米国10年国債利回り | `^TNX` | Yahoo Finance | 日2回 | % |

初期実装は`yfinance`を取得アダプターとして使う。Yahoo Financeは公式に保証されたAPIではないため、取得処理は画面・計算処理から分離し、将来FRED等へ差し替え可能にする。

各画面には設定された`source_url`へのリンクを表示する。

## 4. スケジュール

基準タイムゾーンは `Asia/Tokyo` とする。

- 日次取得: 毎日 09:00、21:00 JST
- 週次指標: 毎週月曜 08:00 JST
- 手動実行: GitHub Actionsの `workflow_dispatch` でも実行可能にする

GitHub ActionsのcronはUTCで記述する。スケジュール実行は混雑等で遅延する可能性があるため、取得時刻には実行予定時刻ではなく実際の取得日時を保存する。祝日・休場日でも実行し、ソースに新しい値がない場合は後述の重複規則に従う。

## 5. 指標の定義

### 5.1 週足

NASDAQ 100の日足OHLCから `W-FRI` で週足を生成する。

- Open: 週の最初の有効なOpen
- High: 週の最大High
- Low: 週の最小Low
- Close: 週の最後の有効なClose
- 月曜実行時点で確定済みの週だけを計算対象とする

これにより、データソース側の週足境界の違いを避ける。

### 5.2 RSI

NASDAQ 100の週足CloseからWilder方式のRSIを計算する。初期期間は14週。

- 上昇幅と下落幅を分離する
- Wilder平滑化（`alpha = 1 / period`, `adjust = false`）を使う
- `RSI = 100 - 100 / (1 + 平均上昇幅 / 平均下落幅)`

### 5.3 CCI

NASDAQ 100の週足OHLCからCCIを計算する。初期期間は20週、定数は0.015。

- `Typical Price = (High + Low + Close) / 3`
- `CCI = (Typical Price - SMA) / (constant × Mean Absolute Deviation)`

### 5.4 ドローダウン

NASDAQ 100の日足Closeを使う。初期設定では取得できる全履歴の最高終値を基準とする。

- `peak = max(Close)`
- `drawdown_pct = (latest_close / peak - 1) × 100`
- 最高値時は0%、下落時は負数

`lookback_days`を設定した場合は、その期間内の最高終値へ切り替えられる。日中高値ではなく終値を使うことを画面上にも明記する。

### 5.5 前回差分

各項目について、今回の有効値から直前に保存された有効値を引く。

- `delta = current - previous`
- 初回は `null` として `—` を表示
- 同一ソース日時・同一値のデータは履歴へ重複追加しない

## 6. 保存形式

生成物は次の責務に分ける。

- `data/latest.json`: 画面の最新カード用
- `data/intraday.csv`: 日2回取得する5項目の履歴
- `data/weekly.csv`: NASDAQ 100週足OHLC、RSI、CCI
- `data/alert_state.json`: 条件ごとの発報状態と最終通知日時
- `data/status.json`: 最終成功日時、データ鮮度、項目別エラー

保存時刻はISO 8601形式とし、UTCの `observed_at` とJST表示用日時を区別する。値が取得できなかった項目で以前の値を上書きしない。

履歴の初期保持期間は日次系5年、週次系10年とし、設定で変更できるようにする。

## 7. 表示要件

### 最新値カード

- SKEW
- VIX
- NASDAQ 100ドローダウン
- Brent原油価格
- 米国10年国債利回り
- 最新値、前回差分、データ日時、鮮度状態、ソースリンク

### チャート

- NASDAQ 100週足Close
- 週足CCI（初期ガイド: +100、-100）
- 週足RSI（初期ガイド: 70、30）
- SKEW、VIX、ドローダウン、Brent、米10年金利の時系列

モバイルとPCで閲覧可能にし、取得失敗時は古い値を最新値のように見せず「更新遅延」を表示する。

## 8. Discord通知

### 機密情報

- `DISCORD_WEBHOOK_URL`: GitHub Repository Secret（必須）
- `DISCORD_MENTION`: GitHub Repository Secret（任意）

Webhook URLを設定ファイル、履歴、ログ、Pages生成物へ書き込まない。通知失敗時も完全なURLをログへ出力しない。

### 条件

1つの項目に上限・下限を複数設定できる。初期のサンプル条件は誤通知防止のため `enabled: false` とする。

- `operator`: `gte`, `gt`, `lte`, `lt`
- `threshold`: 判定値
- `message`: 任意の通知文
- `notify_on`: 初期値 `enter`（正常域から条件成立へ入った時だけ通知）
- `cooldown_hours`: 再通知を許す最短間隔

通知には項目名、現在値、閾値、前回値、差分、取得日時、ダッシュボードURL、ソースURLを含める。

複数条件が同時成立した場合は原則1メッセージへまとめる。条件から外れた時は内部状態を正常へ戻す。回復通知は将来 `notify_recovery` で有効化できるようにする。

Discordの `allowed_mentions` を明示し、設定されたユーザーまたはロール以外への意図しないメンションを防ぐ。

## 9. 失敗時の扱い

- 一部項目だけ失敗: 成功項目を保存し、失敗項目を`status.json`へ記録
- 全項目失敗: 履歴を更新せず、Actionを失敗終了
- Discord通知失敗: 市場データは保存し、Actionを失敗または警告扱いにする（実装時に選択可能）
- コミット競合: 最新ブランチを取り込み、重複排除して限定回数再試行
- データ鮮度超過: 画面に警告表示し、古い値を通知判定へ使わない

## 10. セキュリティと権限

- Workflowの `permissions` は原則 `contents: write`、Pagesデプロイ時のみ必要な権限を追加
- Pull Request由来の任意コードにSecretsを渡さない
- 外部Actionは極力減らし、使用時はバージョンまたはコミットSHAを固定
- Secretsや認証情報を例外メッセージへ含めない
- Pagesへ公開される閾値・通知文・市場履歴には秘密情報を置かない

## 11. 設定変更方針

通常の変更は `config/config.yaml` の編集だけで行えるようにする。

- シンボルとソースリンク
- 取得時刻
- RSI/CCI期間
- ドローダウン参照期間
- 履歴保持期間
- 通知条件、文面、再通知間隔
- チャートのガイド値と表示期間

Secret名自体は設定可能だが、Secret値はYAMLへ記載しない。

## 12. タスク1の完了条件

- 取得対象と初期シンボルが定義されている
- 週足、RSI、CCI、ドローダウン、前回差分が再現可能な式で定義されている
- スケジュールとタイムゾーンが定義されている
- Discordの判定・再送抑止・Secret管理が定義されている
- 次工程で読み込めるYAML設定例がある
- 失敗時とデータ鮮度の扱いが定義されている

