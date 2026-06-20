# reservation.py — 予約フロー ステートマシン

import logging
from linebot.v3.messaging import TextMessage
from models import db, User, Reservation, ConversationState

logger = logging.getLogger(__name__)

# ───────────────────────────────────────
# 状態定義
# ───────────────────────────────────────
STATE_IDLE            = "idle"
STATE_SELECT_MENU     = "selecting_menu"
STATE_SELECT_DATE     = "selecting_date"
STATE_SELECT_TIME     = "selecting_time"
STATE_CONFIRMING      = "confirming"

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


def _invalid_step_msg() -> list:
    return [TextMessage(text="最初からやり直します🙇\nご希望のメニューを選んでください。")]


# ───────────────────────────────────────
# Postback イベント処理
# ───────────────────────────────────────

def process_postback(user_id: str, data: str) -> list:
    """
    ボタン操作（Postback）を受け取り、次のメッセージリストを返す。
    """
    params = _parse_data(data)
    action = params.get("action", "")

    state = _get_state(user_id)
    user  = User.query.filter_by(line_user_id=user_id).first()
    name  = (user.display_name or "お客様") if user else "お客様"

    # ─── 予約開始 ───
    if action == "start_reservation":
        _reset_state(state)
        state.state = STATE_SELECT_MENU
        db.session.commit()

        from messages import get_menu_select_message
        return get_menu_select_message()

    # ─── メニュー一覧表示 ───
    elif action == "show_menu":
        from messages import get_menu_list_message
        return get_menu_list_message()

    # ─── メニュー選択 ───
    elif action == "select_menu":
        if state.state != STATE_SELECT_MENU:
            _reset_state(state)
            db.session.commit()
            return _invalid_step_msg()

        state.temp_menu       = params.get("name", "")
        state.temp_menu_price = params.get("price", "")
        state.state           = STATE_SELECT_DATE
        db.session.commit()

        from messages import get_date_select_message
        return get_date_select_message(state.temp_menu)

    # ─── 日程選択 ───
    elif action == "select_date":
        if state.state != STATE_SELECT_DATE:
            _reset_state(state)
            db.session.commit()
            return _invalid_step_msg()

        state.temp_date = params.get("date", "")
        state.state     = STATE_SELECT_TIME
        db.session.commit()

        from messages import get_time_select_message
        return get_time_select_message(state.temp_date)

    # ─── 時間選択 ───
    elif action == "select_time":
        if state.state != STATE_SELECT_TIME:
            _reset_state(state)
            db.session.commit()
            return _invalid_step_msg()

        state.temp_time = params.get("time", "")
        state.state     = STATE_CONFIRMING
        db.session.commit()

        from messages import get_confirm_message
        return get_confirm_message(
            state.temp_menu,
            state.temp_menu_price,
            state.temp_date,
            state.temp_time,
        )

    # ─── 予約確定 ───
    elif action == "confirm_reservation":
        if state.state != STATE_CONFIRMING:
            _reset_state(state)
            db.session.commit()
            return _invalid_step_msg()

        # DB に保存
        if user:
            reservation = Reservation(
                user_id    = user.id,
                menu_name  = state.temp_menu,
                menu_price = state.temp_menu_price,
                date       = state.temp_date,
                time_slot  = state.temp_time,
                status     = "confirmed",
            )
            db.session.add(reservation)
            logger.info(
                f"予約確定: {name} / {state.temp_menu} "
                f"/ {state.temp_date} {state.temp_time}"
            )

        # 一時データを保持したまま状態リセット（完了メッセージ用に使う）
        menu_name  = state.temp_menu or ""
        date_str   = state.temp_date or ""
        time_slot  = state.temp_time or ""
        _reset_state(state)
        db.session.commit()

        from messages import get_complete_message
        return get_complete_message(name, menu_name, date_str, time_slot)

    # ─── やり直し ───
    elif action in ("restart_reservation", "cancel_reservation"):
        _reset_state(state)
        state.state = STATE_SELECT_MENU
        db.session.commit()

        from messages import get_menu_select_message
        return get_menu_select_message()

    return []


# ───────────────────────────────────────
# テキストメッセージ処理
# ───────────────────────────────────────

def process_text(user_id: str, text: str) -> list:
    """
    キーワードを検出して予約フロー or メニュー表示を開始する。
    """
    t = text.strip().lower()

    if any(k in t for k in TRIGGER_RESERVATION):
        state = _get_state(user_id)
        _reset_state(state)
        state.state = STATE_SELECT_MENU
        db.session.commit()

        from messages import get_menu_select_message
        return get_menu_select_message()

    if any(k in t for k in TRIGGER_MENU):
        from messages import get_menu_list_message
        return get_menu_list_message()

    # その他のメッセージには返答しない（サロンの裁量に委ねる）
    return []
