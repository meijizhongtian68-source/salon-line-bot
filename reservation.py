# reservation.py — 予約フロー ステートマシン

import logging
from linebot.v3.messaging import TextMessage
from models import db, User, Reservation, ConversationState

logger = logging.getLogger(__name__)

# ───────────────────────────────────────
# 状態定義
# ───────────────────────────────────────
STATE_IDLE            = "idle"
STATE_SURVEY_Q1       = "survey_q1"
STATE_SURVEY_Q2       = "survey_q2"
STATE_SURVEY_Q3       = "survey_q3"
STATE_SURVEY_Q4       = "survey_q4"
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

    # ── 予約キーワード（いつでも予約開始可能）──
    if any(k in tl for k in TRIGGER_RESERVATION) and state.state not in [STATE_ASKING_NAME_AGE, STATE_ASKING_SYMPTOMS, STATE_ASKING_DATES]:
        state.state = STATE_ASKING_NAME_AGE
        db.session.commit()
        from messages import get_reservation_ask_name_age
        return get_reservation_ask_name_age()

    # ── idle状態でA〜Dを含む返信 → Q1回答として受け取る ──
    if state.state == STATE_IDLE:
        has_abcd = any(c in t.upper() for c in ["A", "B", "C", "D"])
        if has_abcd:
            state.temp_menu = t
            state.state = STATE_SURVEY_Q2
            db.session.commit()
            return [TextMessage(text=(
                "②お悩みの期間は？\n\n"
                "　A. 最近（1〜3ヶ月）\n"
                "　B. 半年〜1年くらい\n"
                "　C. 1年以上前から\n"
                "　D. わからない"
            ))]

    # ── アンケート Q1 ──
    if state.state == STATE_SURVEY_Q1:
        state.temp_menu = t
        state.state = STATE_SURVEY_Q2
        db.session.commit()
        return [TextMessage(text=(
            "②お悩みの期間は？\n\n"
            "　A. 最近（1〜3ヶ月）\n"
            "　B. 半年〜1年くらい\n"
            "　C. 1年以上前から\n"
            "　D. わからない"
        ))]

    # ── アンケート Q2 ──
    if state.state == STATE_SURVEY_Q2:
        state.temp_menu_price = t
        state.state = STATE_SURVEY_Q3
        db.session.commit()
        return [TextMessage(text=(
            "③これまで対策したことは？\n\n"
            "　A. 特に何もしていない\n"
            "　B. 病院で相談したことがある\n"
            "　C. サプリ・市販薬を試した\n"
            "　D. その他"
        ))]

    # ── アンケート Q3 ──
    if state.state == STATE_SURVEY_Q3:
        state.temp_date = t
        state.state = STATE_SURVEY_Q4
        db.session.commit()
        return [TextMessage(text=(
            "④ご来店のご希望は？\n\n"
            "　A. できるだけ早く\n"
            "　B. 来週中\n"
            "　C. 2週間以降\n"
            "　D. まずは相談だけしたい"
        ))]

    # ── アンケート Q4 ──
    if state.state == STATE_SURVEY_Q4:
        state.temp_time = t
        _reset_state(state)
        db.session.commit()
        return [TextMessage(text=(
            "ご回答いただいた内容をもとに\n"
            "スタッフが個別にご案内します🙌\n\n"
            "ご予約はいつでも【予約】と\n"
            "送ってください✨"
        ))]

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
