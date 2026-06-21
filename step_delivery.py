# step_delivery.py — ステップ配信スケジューラー

import logging
from datetime import datetime, timedelta
from linebot.v3.messaging import MessagingApi, PushMessageRequest
from models import db, User

logger = logging.getLogger(__name__)

# ───────────────────────────────────────
# ステップ配信タイミング設定
# ───────────────────────────────────────
STEPS = [
    {
        "flag":    "step1_sent",
        "delay":   timedelta(days=1),   # 1日後
        "label":   "Step1（ご登録ありがとう）",
        "getter":  "get_step1_message",
    },
    {
        "flag":    "step2_sent",
        "delay":   timedelta(days=2),   # 2日後
        "label":   "Step2（あの頃の自信）",
        "getter":  "get_step2_message",
    },
    {
        "flag":    "step3_sent",
        "delay":   timedelta(days=3),   # 3日後
        "label":   "Step3（なぜマッサージではダメか）",
        "getter":  "get_step3_message",
    },
    {
        "flag":    "step4_sent",
        "delay":   timedelta(days=4),   # 4日後
        "label":   "Step4（富山の男性を元気にしたい）",
        "getter":  "get_step4_message",
    },
    {
        "flag":    "step5_sent",
        "delay":   timedelta(days=5),   # 5日後
        "label":   "Step5（ついに募集開始）",
        "getter":  "get_step5_message",
    },
    {
        "flag":    "step6_sent",
        "delay":   timedelta(days=6),   # 6日後
        "label":   "Step6（本日受付開始・残りわずか）",
        "getter":  "get_step6_message",
    },
]


def check_and_send_steps(messaging_api: MessagingApi) -> None:
    """
    1時間ごとに呼ばれる。
    各ユーザーの followed_at からの経過時間を見て、
    未送信のステップメッセージを Push 送信する。
    """
    now = datetime.utcnow()
    users = User.query.filter_by(is_blocked=False).all()
    total_sent = 0

    for user in users:
        elapsed = now - user.followed_at

        for step in STEPS:
            flag   = step["flag"]
            delay  = step["delay"]
            label  = step["label"]
            getter = step["getter"]

            # 送信済み or まだ時間が来ていない → スキップ
            if getattr(user, flag) or elapsed < delay:
                continue

            try:
                from messages import (
                    get_step1_message,
                    get_step2_message,
                    get_step3_message,
                    get_step4_message,
                    get_step5_message,
                    get_step6_message,
                )
                fn_map = {
                    "get_step1_message": get_step1_message,
                    "get_step2_message": get_step2_message,
                    "get_step3_message": get_step3_message,
                    "get_step4_message": get_step4_message,
                    "get_step5_message": get_step5_message,
                    "get_step6_message": get_step6_message,
                }
                messages = fn_map[getter](user.display_name or "お客様")

                messaging_api.push_message(
                    PushMessageRequest(to=user.line_user_id, messages=messages)
                )
                setattr(user, flag, True)
                total_sent += 1
                logger.info(f"{label} 送信完了: {user.display_name} ({user.line_user_id})")

            except Exception as e:
                logger.error(
                    f"{label} 送信エラー: {user.line_user_id} — {e}"
                )

            # 1ユーザーに1回のステップだけ送る（次のステップは次回チェックで）
            break

    if total_sent:
        db.session.commit()
        logger.info(f"ステップ配信完了: {total_sent}件")
    else:
        logger.debug("ステップ配信: 送信対象なし")
