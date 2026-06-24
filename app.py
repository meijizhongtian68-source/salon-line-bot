# app.py — メインアプリケーション（Flask + LINE Webhook）

import os
import logging
import threading
import time
from datetime import datetime

import requests as http_req
from flask import Flask, request, abort, jsonify
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

@app.route("/health")
def health():
    return "OK", 200


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
                intro_text = (
                    f"ご登録ありがとうございます😊\n"
                    f"男の専門整体「KILIG」です。\n\n"
                    f"男性特有のお悩みに特化した\n"
                    f"専門ケアを行っております。\n\n"
                    f"LINEから簡単30秒で\n"
                    f"ご予約・ご相談いただけます✨\n\n"
                    f"※回答内容は完全に秘密厳守です\n"
                    f"※答えにくい質問は飛ばしてOKです"
                )
                q1_text = (
                    f"①気になるお悩みは？\n\n"
                    f"　A. 夜中に何度もトイレに起きる\n"
                    f"　B. 勢い・持続力の衰えが気になる\n"
                    f"　C. 両方とも気になる\n"
                    f"　D. その他・相談したい"
                )
                test_messages = [TextMessage(text=intro_text), TextMessage(text=q1_text)]

                # アンケート開始状態をセット
                from models import ConversationState
                conv = ConversationState.query.filter_by(line_user_id=user_id).first()
                if not conv:
                    conv = ConversationState(line_user_id=user_id, state="survey_q1")
                    db.session.add(conv)
                else:
                    conv.state = "survey_q1"
                    conv.temp_menu = conv.temp_menu_price = conv.temp_date = conv.temp_time = None
                db.session.commit()
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
# 管理用：既存フォロワーへのアンケート一斉送信
# ───────────────────────────────────────

def _do_broadcast_survey():
    """バックグラウンドで全フォロワーにアンケートを送信"""
    with app.app_context():
        access_token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
        headers = {"Authorization": f"Bearer {access_token}"}

        # LINE API で全フォロワーID取得
        all_user_ids = []
        params = {"limit": 1000}
        while True:
            resp = http_req.get(
                "https://api.line.me/v2/bot/followers/ids",
                headers=headers, params=params
            )
            data = resp.json()
            all_user_ids.extend(data.get("userIds", []))
            if "next" not in data:
                break
            params["start"] = data["next"]

        logger.info(f"アンケート一斉送信開始: {len(all_user_ids)}人")

        message_text = (
            "こんにちは！\n"
            "男の専門整体「KILIG」オーナーのみきです😊\n\n"
            "男性特有のお悩みに特化した専門ケアを行っております。\n\n"
            "※回答内容は完全に秘密厳守です\n"
            "※答えにくい質問は飛ばしてOKです\n\n"
            "①気になるお悩みは？\n\n"
            "　A. 夜中に何度もトイレに起きる\n"
            "　B. 勢い・持続力の衰えが気になる\n"
            "　C. 両方とも気になる\n"
            "　D. その他・相談したい"
        )

        sent = 0
        errors = 0

        with _api() as client:
            api = MessagingApi(client)

            for user_id in all_user_ids:
                # DBに登録（未登録の場合）
                user = User.query.filter_by(line_user_id=user_id).first()
                if not user:
                    user = User(
                        line_user_id=user_id,
                        display_name="お客様",
                        followed_at=datetime.utcnow(),
                        step4_sent=True,
                        step5_sent=True,
                        step6_sent=True,
                    )
                    db.session.add(user)

                # アンケート状態をセット
                conv = ConversationState.query.filter_by(line_user_id=user_id).first()
                if not conv:
                    conv = ConversationState(line_user_id=user_id, state="survey_q1")
                    db.session.add(conv)
                else:
                    conv.state = "survey_q1"

                # メッセージ送信
                try:
                    api.push_message(PushMessageRequest(
                        to=user_id,
                        messages=[TextMessage(text=message_text)]
                    ))
                    sent += 1
                    time.sleep(0.05)  # レート制限対策
                except Exception as e:
                    logger.error(f"送信エラー {user_id}: {e}")
                    errors += 1

                # 50人ごとにDBコミット
                if (sent + errors) % 50 == 0:
                    db.session.commit()

        db.session.commit()
        logger.info(f"アンケート一斉送信完了: {sent}人成功, {errors}件エラー")


@app.route("/admin/broadcast-survey")
def admin_broadcast_survey():
    """既存フォロワー全員にアンケートを一斉送信（管理者専用）"""
    token = request.args.get("token", "")
    admin_token = os.getenv("ADMIN_TOKEN", "")
    if not admin_token or token != admin_token:
        abort(403)

    thread = threading.Thread(target=_do_broadcast_survey, daemon=True)
    thread.start()

    return jsonify({"status": "started", "message": "送信開始しました！Renderのログで進捗を確認してください。"})


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
# 起動時初期化（gunicorn でも動くよう __main__ の外に置く）
# ───────────────────────────────────────
with app.app_context():
    db.create_all()
    logger.info("DB テーブル作成完了")

    # ── 既存ユーザーへの新ステップ誤送信防止 ──
    # step4〜6 が未セットの既存ユーザー（step1送信済み）にフラグを立てる
    from models import User
    existing = User.query.filter(
        User.step1_sent == True,
        User.step4_sent == False,
    ).all()
    if existing:
        for u in existing:
            u.step4_sent = True
            u.step5_sent = True
            u.step6_sent = True
        db.session.commit()
        logger.info(f"既存ユーザー {len(existing)}人 の Step4〜6 をスキップ設定")

if not scheduler.running:
    pass  # ステップ配信一時停止中
    # scheduler.start()
    # logger.info("ステップ配信スケジューラー起動")

# ───────────────────────────────────────
# エントリーポイント
# ───────────────────────────────────────

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
