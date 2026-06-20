# app.py — メインアプリケーション（Flask + LINE Webhook）

import os
import logging
from datetime import datetime

from flask import Flask, request, abort
from linebot.v3 import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration, ApiClient, MessagingApi,
    ReplyMessageRequest, PushMessageRequest,
    TextMessage,
)
from linebot.v3.webhooks import (
    MessageEvent, FollowEvent, UnfollowEvent, PostbackEvent,
    TextMessageContent,
)
from dotenv import load_dotenv
from messages import SALON_NAME
from apscheduler.schedulers.background import BackgroundScheduler

load_dotenv()

# ───────────────────────────────────────
# ログ設定
# ───────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

# ───────────────────────────────────────
# Flask / DB 初期化
# ───────────────────────────────────────
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL", "sqlite:///salon.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

from models import db, User, ConversationState
db.init_app(app)

# ───────────────────────────────────────
# LINE SDK 設定
# ───────────────────────────────────────
_configuration = Configuration(access_token=os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
_handler       = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))


def _api() -> ApiClient:
    """MessagingApi クライアントを返す（with 文で使う）"""
    return ApiClient(_configuration)


# ───────────────────────────────────────
# Webhook エンドポイント
# ───────────────────────────────────────

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers.get("X-Line-Signature", "")
    body      = request.get_data(as_text=True)
    logger.debug(f"Webhook body: {body[:200]}")
    try:
        _handler.handle(body, signature)
    except InvalidSignatureError:
        logger.error("Invalid signature")
        abort(400)
    return "OK"


# ───────────────────────────────────────
# 友だち追加 → ウェルカムメッセージ
# ───────────────────────────────────────

@_handler.add(FollowEvent)
def on_follow(event):
    user_id = event.source.user_id

    with app.app_context():
        with _api() as client:
            api = MessagingApi(client)

            # プロフィール取得
            try:
                profile      = api.get_profile(user_id)
                display_name = profile.display_name
            except Exception as e:
                logger.warning(f"プロフィール取得失敗 ({user_id}): {e}")
                display_name = "お客様"

            # ユーザー登録 / 再登録
            user = User.query.filter_by(line_user_id=user_id).first()
            if not user:
                user = User(
                    line_user_id=user_id,
                    display_name=display_name,
                    followed_at=datetime.utcnow(),
                )
                db.session.add(user)
            else:
                user.display_name = display_name
                user.followed_at  = datetime.utcnow()
                user.is_blocked   = False
                user.step1_sent   = False
                user.step2_sent   = False
                user.step3_sent   = False
            db.session.commit()

            # Step 0: ウェルカムメッセージ送信
            try:
                # まずシンプルなテキストでテスト
                test_messages = [TextMessage(text=f"🌸 {display_name}さん、ご登録ありがとうございます！\n{SALON_NAME}の公式LINEへようこそ✨\n\n「予約」と送ると予約できます！")]
                api.reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=test_messages,
                    )
                )
                logger.info(f"友だち追加: {display_name} ({user_id})")
            except Exception as e:
                logger.error(f"ウェルカムメッセージ送信エラー: {e}", exc_info=True)


# ───────────────────────────────────────
# ブロック
# ───────────────────────────────────────

@_handler.add(UnfollowEvent)
def on_unfollow(event):
    with app.app_context():
        user = User.query.filter_by(line_user_id=event.source.user_id).first()
        if user:
            user.is_blocked = True
            db.session.commit()
        logger.info(f"ブロック: {event.source.user_id}")


# ───────────────────────────────────────
# Postback（ボタン操作）
# ───────────────────────────────────────

@_handler.add(PostbackEvent)
def on_postback(event):
    user_id = event.source.user_id
    data    = event.postback.data

    with app.app_context():
        from reservation import process_postback
        messages = process_postback(user_id, data)

        if messages:
            with _api() as client:
                MessagingApi(client).reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=messages,
                    )
                )


# ───────────────────────────────────────
# テキストメッセージ
# ───────────────────────────────────────

@_handler.add(MessageEvent, message=TextMessageContent)
def on_message(event):
    user_id = event.source.user_id
    text    = event.message.text.strip()

    with app.app_context():
        from reservation import process_text
        messages = process_text(user_id, text)

        if messages:
            with _api() as client:
                MessagingApi(client).reply_message(
                    ReplyMessageRequest(
                        reply_token=event.reply_token,
                        messages=messages,
                    )
                )


# ───────────────────────────────────────
# バックグラウンドスケジューラー（ステップ配信）
# ───────────────────────────────────────

def _run_step_delivery():
    with app.app_context():
        from step_delivery import check_and_send_steps
        with _api() as client:
            check_and_send_steps(MessagingApi(client))


scheduler = BackgroundScheduler(timezone="Asia/Tokyo")
scheduler.add_job(
    _run_step_delivery,
    trigger="interval",
    hours=1,
    id="step_delivery",
    replace_existing=True,
)


# ───────────────────────────────────────
# エントリーポイント
# ───────────────────────────────────────

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
        logger.info("DB テーブル作成完了")

    scheduler.start()
    logger.info("ステップ配信スケジューラー起動")

    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
