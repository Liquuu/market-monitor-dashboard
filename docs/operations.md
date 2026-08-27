# 最小運用手順

## 手動でデータを更新する

1. GitHubリポジトリの **Actions** を開く
2. `Update intraday market data` または `Update weekly indicators` を選ぶ
3. **Run workflow** から `main` ブランチで実行する
4. 実行完了後、`data/` に自動コミットが作成されたことを確認する

市場休場中など、取得元のタイムスタンプが前回と同じ場合は成功してもコミットされません。これは正常動作です。

## 失敗した場合

- Actionsの失敗したステップを確認し、一時的なYahoo Finance側の問題なら **Re-run jobs** で再実行する
- JSON更新は一時ファイルから置き換えるため、取得や計算に失敗しても既存の公開データは維持される
- `data/latest.json` や `data/history/*.json` を手作業で直す場合は、JSON構文を確認してからコミットする

## 最低限のローカル確認

```powershell
python -m pip install -r requirements.txt
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

フロントエンドのJavaScript構文は、Node.jsがある環境で次のコマンドでも確認できます。

```powershell
node --check assets/js/app.js
```

## 定期実行について

GitHubの仕様上、スケジュール実行は指定時刻より遅れる場合があります。また、Publicリポジトリは60日間活動がないとスケジュールが自動停止する場合があるため、Actions画面で状態を確認してください。
