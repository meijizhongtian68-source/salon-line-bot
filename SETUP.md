# サロン LINE Bot セットアップガイド

## 構成ファイル一覧

```
salon-line-bot/
├── app.py            # メインサーバー（Flask + Webhook）
├── models.py         # データベースモデル
├── messages.py       # メッセージテンプレート（★カスタマイズここ）
├── step_delivery.py  # ステップ配信スケジューラー
├── reservation.py    # 予約フロー ステートマシン
├── requirements.txt
├── .env.example
└── Procfile          # Heroku デプロイ用
```

---

## ステップ配信フロー

```
[友だち追加]
     ↓ 即時
 Step 0: ウェルカム + 予約ボタン
     ↓ 翌日
 Step 1: メニュー・料金案内
     ↓ 3日後
 Step 2: お客様の声（カルーセル）
     ↓ 7日後
 Step 3: 初回限定 20%OFF クーポン + 予約 CTA
```

## 予約フロー

```
「予約」と送る or ボタンをタップ
     ↓
① メニュー選択（クイックリプライ）
     ↓
② 日程選択（翌日〜7営業日、クイックリプライ）
     ↓
③ 時間選択（10:00〜18:00、クイックリプライ）
     ↓
④ 確認画面（Flex Message）
     ↓
⑤ 予約完了メッセージ → DB に保存
```

---

## セットアップ手順

### 1. LINE Developers でチャネル作成

1. https://developers.line.biz/ にログイン
2. 新規プロバイダー → 「Messaging API」チャネル作成
3. チャネル基本設定から **Channel secret** を取得
4. Messaging API 設定から **Channel access token** を発行

### 2. ローカル環境の準備

```bash
cd salon-line-bot

# 仮想環境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 依存パッケージ
pip install -r requirements.txt

# 環境変数設定
cp .env.example .env
# .env を編集して LINE_CHANNEL_ACCESS_TOKEN と LINE_CHANNEL_SECRET を入力
```

### 3. DB 初期化 & サーバー起動

```bash
python app.py
```

### 4. Webhook URL を設定（ngrok でローカルテスト）

```bash
ngrok http 5000
# → https://xxxx.ngrok.io が発行される
```

LINE Developers の Messaging API 設定で:
```
Webhook URL: https://xxxx.ngrok.io/webhook
```
「Webhookの利用」をオン → 「検証」ボタンで確認。

---

## カスタマイズ

`messages.py` の上部を編集してください：

```python
SALON_NAME    = "あなたのサロン名"
SALON_ADDRESS = "住所"
SALON_PHONE   = "電話番号"
SALON_MAP_URL = "Google Maps URL"

MENUS = [
    {"name": "メニュー名", "price": "¥0,000", "duration": "00分"},
    ...
]

TIME_SLOTS = ["10:00", "11:00", ...]  # 営業時間スロット
CLOSED_WEEKDAYS = [1]                  # 0=月, 1=火, ..., 6=日
```

ステップ配信のタイミングは `step_delivery.py` の `STEPS` で変更できます。

---

## 本番デプロイ（Heroku）

```bash
heroku create your-salon-bot
heroku config:set LINE_CHANNEL_ACCESS_TOKEN=xxx
heroku config:set LINE_CHANNEL_SECRET=xxx
heroku config:set DATABASE_URL=postgresql://...  # Heroku Postgres アドオン
git push heroku main
```

---

## DB に保存される予約データ

管理者が予約一覧を確認したい場合、SQLite なら：

```bash
sqlite3 salon.db
SELECT u.display_name, r.menu_name, r.date, r.time_slot, r.status
FROM reservations r JOIN users u ON r.user_id = u.id
ORDER BY r.date, r.time_slot;
```
