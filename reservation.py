# reservation.py — 予約フロー ステートマシン

import logging
from linebot.v3.messaging import TextMessage
from models import db, User, Reservation, ConversationState

logger = logging.getLogger(__name__)

# ───────────────────────────────────────
# 状態定義
# ───────────────────────────────────────
STATE_IDLE            = "idle"
STATE_ASKING_NAME_AGE = "asking_name_age"
STATE_ASKING_SYMPTOMS = "asking_symptoms"
STATE_ASKING_DATES    = "asking_dates"

# ───────────────────────────────────────
# テキストトリガーキーワード
# ───────────────────────────────────────
TRIGGER_RESERVATION = ["予約", "予約したい", "予約する", "book"]
TRIGGER_MENU        = ["メニュー", "料金", "値段", "menu"]


# ───────────────────────────────────────
# 内部ユーティリティ
# ───────────────────────────────────────

def _get_state(user_id: str) -> ConversationState:
    """ステートを取得（なければ作成）"""
    state = ConversationState.query.filter_by(line_user_id=user_id).first()
    if not state:
        state = ConversationState(line_user_id=user_id, state=STATE_IDLE)
        db.session.add(state)
        db.session.commit()
    return state


def _parse_data(data: str) -> dict:
    """postback data 文字列を dict にパース"""
    result = {}
    for part in data.split("&"):
        if "=" in part:
            key, _, val = part.partition("=")
            result[key] = val
    return result


def _reset_state(state: ConversationState) -> None:
    """予約フローをリセット"""
    state.state           = STATE_IDLE
    state.temp_menu       = None
    state.temp_menu_price = None
    state.temp_date       = None
    state.temp_time       = None


# ───────────────────────────────────────
# Postback イベント処理
# ───────────────────────────────────────

def process_postback(user_id: str, data: str) -> list:
    params = _parse_data(data)
    action = params.get("action", "")
    state  = _get_state(user_id)

    if action in ("start_reservation",):
        _reset_state(state)
        state.state = STATE_ASKING_NAME_AGE
        db.session.commit()
        from messages import get_reservation_ask_name_age
        return get_reservation_ask_name_age()

    if action == "show_menu":
        from messages import get_menu_list_message
        return get_menu_list_message()

    return []


# ───────────────────────────────────────
# テキストメッセージ処理
# ───────────────────────────────────────

def process_text(user_id: str, text: str) -> list:
    t     = text.strip()
    tl    = t.lower()
    state = _get_state(user_id)
    user  = User.query.filter_by(line_user_id=user_id).first()
    name  = (user.display_name or "お客様") if user else "お客様"

    # ── 予約キーワード（idle 時のみ開始）──
    if state.state == STATE_IDLE and any(k in tl for k in TRIGGER_RESERVATION):
        state.state = STATE_ASKING_NAME_AGE
        db.session.commit()
        from messages import get_reservation_ask_name_age
        return get_reservation_ask_name_age()

    # ── ① 名前・年齢を受け取る ──
    if state.state == STATE_ASKING_NAME_AGE:
        state.temp_menu = t        # 名前・年齢を保存
        state.state     = STATE_ASKING_SYMPTOMS
        db.session.commit()
        from messages import get_reservation_ask_symptoms
        return get_reservation_ask_symptoms()

    # ── ② 症状・目標を受け取る ──
    if state.state == STATE_ASKING_SYMPTOMS:
        state.temp_menu_price = t  # 症状・目標を保存
        state.state           = STATE_ASKING_DATES
        db.session.commit()
        from messages import get_reservation_ask_dates
        return get_reservation_ask_dates()

    # ── ③ 希望日時を受け取る ──
    if state.state == STATE_ASKING_DATES:
        state.temp_date = t        # 希望日時を保存
        logger.info(
            f"予約リクエスト: {name} / {state.temp_menu} "
            f"/ {state.temp_menu_price} / {state.temp_date}"
        )
        _reset_state(state)
        db.session.commit()
        from messages import get_reservation_complete_message
        return get_reservation_complete_message(name)

    # ── メニュー確認キーワード ──
    if any(k in tl for k in TRIGGER_MENU):
        from messages import get_menu_list_message
        return get_menu_list_message()

    return []
