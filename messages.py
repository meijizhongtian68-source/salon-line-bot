# messages.py — メッセージテンプレート（Flex Message）

import json
from datetime import datetime, timedelta
from linebot.v3.messaging import (
    TextMessage, FlexMessage, FlexBubble, FlexCarousel,
    QuickReply, QuickReplyItem,
    PostbackAction, URIAction,
)

# ============================================================
# ★ サロン情報 ── ここをご自身のサロン情報に書き換えてください ★
# ============================================================
SALON_NAME    = "Beauty Salon BLOOM"
SALON_ADDRESS = "東京都渋谷区○○1-2-3"
SALON_PHONE   = "03-XXXX-XXXX"
SALON_HOURS   = "10:00〜20:00（火曜定休）"
SALON_MAP_URL = "https://maps.google.com/maps?q=東京都渋谷区"

# メニュー定義
MENUS = [
    {"name": "カット",         "price": "¥5,500",  "duration": "60分"},
    {"name": "カラー",         "price": "¥8,800",  "duration": "90分"},
    {"name": "カット＋カラー", "price": "¥13,200", "duration": "120分"},
    {"name": "パーマ",         "price": "¥11,000", "duration": "120分"},
    {"name": "トリートメント", "price": "¥3,300",  "duration": "30分"},
]

# 予約時間スロット
TIME_SLOTS = ["10:00", "11:00", "12:00", "13:00", "14:00",
              "15:00", "16:00", "17:00", "18:00"]

# 定休日（0=月, 1=火, ..., 6=日）
CLOSED_WEEKDAYS = [1]  # 火曜定休

WEEKDAY_JP = ["月", "火", "水", "木", "金", "土", "日"]
# ============================================================


def get_available_dates(days: int = 7) -> list:
    """翌日から最大 days 件の営業日リストを返す"""
    result = []
    d = datetime.now().date() + timedelta(days=1)
    while len(result) < days:
        if d.weekday() not in CLOSED_WEEKDAYS:
            result.append(d)
        d += timedelta(days=1)
    return result


def _flex(alt_text: str, contents: dict) -> FlexMessage:
    """dict → FlexMessage 変換ユーティリティ"""
    content_type = contents.get("type", "bubble")
    if content_type == "carousel":
        container = FlexCarousel.model_validate_json(json.dumps(contents))
    else:
        container = FlexBubble.model_validate_json(json.dumps(contents))
    return FlexMessage(alt_text=alt_text, contents=container)


# ─────────────────────────────────────────
# Step 0: ウェルカムメッセージ（友だち追加直後）
# ─────────────────────────────────────────
def get_welcome_message(name: str) -> list:
    return [
        _flex(
            f"{name}さん、ご登録ありがとうございます！",
            {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "paddingAll": "xl",
                    "contents": [
                        {
                            "type": "text",
                            "text": f"🌸 {name}さん、はじめまして！",
                            "weight": "bold",
                            "size": "lg",
                            "wrap": True,
                            "color": "#333333",
                        },
                        {
                            "type": "text",
                            "text": f"{SALON_NAME} の公式LINEへようこそ✨",
                            "size": "sm",
                            "color": "#666666",
                            "wrap": True,
                        },
                        {"type": "separator", "margin": "lg"},
                        {
                            "type": "text",
                            "text": "このアカウントでできること",
                            "weight": "bold",
                            "size": "sm",
                            "margin": "lg",
                            "color": "#333333",
                        },
                        {
                            "type": "text",
                            "text": (
                                "✅ かんたんオンライン予約\n"
                                "✅ お得なクーポンの受け取り\n"
                                "✅ 最新メニュー・空き状況のお知らせ"
                            ),
                            "size": "sm",
                            "wrap": True,
                            "color": "#444444",
                            "margin": "sm",
                        },
                    ],
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#E75480",
                            "action": {
                                "type": "postback",
                                "label": "📅 今すぐ予約する",
                                "data": "action=start_reservation",
                            },
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {
                                "type": "postback",
                                "label": "💇 メニュー・料金を見る",
                                "data": "action=show_menu",
                            },
                        },
                    ],
                },
            },
        )
    ]


# ─────────────────────────────────────────
# Step 1: メニュー・料金案内（翌日）
# ─────────────────────────────────────────
def get_step1_message(name: str) -> list:
    rows = []
    for i, m in enumerate(MENUS):
        if i > 0:
            rows.append({"type": "separator", "margin": "sm"})
        rows.append({
            "type": "box",
            "layout": "horizontal",
            "margin": "sm",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 4,
                    "contents": [
                        {"type": "text", "text": m["name"], "size": "sm", "weight": "bold"},
                        {"type": "text", "text": m["duration"], "size": "xs", "color": "#999999"},
                    ],
                },
                {
                    "type": "text",
                    "text": m["price"],
                    "size": "sm",
                    "flex": 2,
                    "align": "end",
                    "color": "#E75480",
                    "weight": "bold",
                },
            ],
        })

    return [
        TextMessage(text=f"{name}さん、こんにちは😊\n当サロンのメニューをご紹介します✨"),
        _flex(
            "メニュー・料金一覧",
            {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#E75480",
                    "paddingAll": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "💇‍♀️ メニュー・料金一覧",
                            "color": "#ffffff",
                            "weight": "bold",
                            "size": "lg",
                        }
                    ],
                },
                "body": {"type": "box", "layout": "vertical", "contents": rows},
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#E75480",
                            "action": {
                                "type": "postback",
                                "label": "📅 予約する",
                                "data": "action=start_reservation",
                            },
                        }
                    ],
                },
            },
        ),
    ]


# ─────────────────────────────────────────
# Step 2: お客様の声（3日後）
# ─────────────────────────────────────────
def get_step2_message(name: str) -> list:
    voices = [
        {
            "stars": "⭐⭐⭐⭐⭐",
            "text": "「カット＆カラーをお願いしました。仕上がりがとてもキレイで、友人にも褒められました！また来ます💕」",
            "author": "— Aさん（30代・女性）",
        },
        {
            "stars": "⭐⭐⭐⭐⭐",
            "text": "「パーマをかけてもらいましたが、ダメージが少なくてびっくり！スタイリストさんの提案も丁寧で大満足✨」",
            "author": "— Bさん（20代・女性）",
        },
        {
            "stars": "⭐⭐⭐⭐⭐",
            "text": "「初めて伺いましたが、カウンセリングが丁寧！理想通りのスタイルになれました🌸 次回も絶対来ます」",
            "author": "— Cさん（40代・女性）",
        },
    ]

    bubbles = [
        {
            "type": "bubble",
            "body": {
                "type": "box",
                "layout": "vertical",
                "spacing": "md",
                "paddingAll": "xl",
                "contents": [
                    {"type": "text", "text": v["stars"], "size": "md"},
                    {
                        "type": "text",
                        "text": v["text"],
                        "size": "sm",
                        "wrap": True,
                        "color": "#333333",
                    },
                    {
                        "type": "text",
                        "text": v["author"],
                        "size": "xs",
                        "color": "#888888",
                        "align": "end",
                    },
                ],
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "style": "primary",
                        "color": "#E75480",
                        "action": {
                            "type": "postback",
                            "label": "📅 予約する",
                            "data": "action=start_reservation",
                        },
                    }
                ],
            },
        }
        for v in voices
    ]

    return [
        TextMessage(text=f"{name}さん、お客様の声をお届けします🌸"),
        _flex("お客様の声", {"type": "carousel", "contents": bubbles}),
    ]


# ─────────────────────────────────────────
# Step 3: 初回限定クーポン（7日後）
# ─────────────────────────────────────────
def get_step3_message(name: str) -> list:
    return [
        TextMessage(text=f"{name}さんへ、特別なご案内です🎁"),
        _flex(
            "初回限定クーポン",
            {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "paddingAll": "xl",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🎁 初回限定クーポン",
                            "weight": "bold",
                            "size": "xl",
                            "color": "#E75480",
                        },
                        {
                            "type": "text",
                            "text": f"{name}さんへの特別プレゼントです✨",
                            "size": "sm",
                            "color": "#555555",
                            "wrap": True,
                        },
                        {"type": "separator", "margin": "lg"},
                        {
                            "type": "box",
                            "layout": "vertical",
                            "margin": "lg",
                            "backgroundColor": "#FFF0F5",
                            "cornerRadius": "md",
                            "paddingAll": "xl",
                            "contents": [
                                {
                                    "type": "text",
                                    "text": "全メニュー対象",
                                    "size": "sm",
                                    "align": "center",
                                    "color": "#888888",
                                },
                                {
                                    "type": "text",
                                    "text": "20% OFF",
                                    "size": "3xl",
                                    "weight": "bold",
                                    "color": "#E75480",
                                    "align": "center",
                                },
                                {
                                    "type": "text",
                                    "text": "初回ご来店限定",
                                    "size": "xs",
                                    "color": "#888888",
                                    "align": "center",
                                    "margin": "sm",
                                },
                            ],
                        },
                        {
                            "type": "text",
                            "text": "⚠️ ご来店の際にこのメッセージをスタッフへご提示ください",
                            "size": "xs",
                            "color": "#888888",
                            "wrap": True,
                            "margin": "lg",
                        },
                    ],
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#E75480",
                            "action": {
                                "type": "postback",
                                "label": "🌸 クーポンを使って予約する",
                                "data": "action=start_reservation",
                            },
                        }
                    ],
                },
            },
        ),
    ]


# ─────────────────────────────────────────
# 予約フロー: ① メニュー選択
# ─────────────────────────────────────────
def get_menu_select_message() -> list:
    items = []
    for m in MENUS:
        label = f"{m['name']} {m['price']}"
        items.append(
            QuickReplyItem(
                action=PostbackAction(
                    label=label[:20],  # QuickReply は 20 文字制限
                    data=f"action=select_menu&name={m['name']}&price={m['price']}",
                )
            )
        )
    return [
        TextMessage(
            text="💇‍♀️ ご希望のメニューを選んでください",
            quick_reply=QuickReply(items=items),
        )
    ]


# ─────────────────────────────────────────
# 予約フロー: ② 日程選択
# ─────────────────────────────────────────
def get_date_select_message(menu_name: str) -> list:
    dates = get_available_dates()
    items = [
        QuickReplyItem(
            action=PostbackAction(
                label=f"{d.month}/{d.day}({WEEKDAY_JP[d.weekday()]})",
                data=f"action=select_date&date={d.strftime('%Y-%m-%d')}",
            )
        )
        for d in dates
    ]
    return [
        TextMessage(
            text=f"【{menu_name}】\n📅 ご希望の日程を選んでください\n（火曜定休）",
            quick_reply=QuickReply(items=items),
        )
    ]


# ─────────────────────────────────────────
# 予約フロー: ③ 時間選択
# ─────────────────────────────────────────
def get_time_select_message(date_str: str) -> list:
    date = datetime.strptime(date_str, "%Y-%m-%d")
    date_label = f"{date.month}月{date.day}日({WEEKDAY_JP[date.weekday()]})"

    items = [
        QuickReplyItem(
            action=PostbackAction(
                label=slot,
                data=f"action=select_time&time={slot}",
            )
        )
        for slot in TIME_SLOTS
    ]
    return [
        TextMessage(
            text=f"🕐 {date_label}\nご希望の時間を選んでください",
            quick_reply=QuickReply(items=items),
        )
    ]


# ─────────────────────────────────────────
# 予約フロー: ④ 確認画面
# ─────────────────────────────────────────
def get_confirm_message(menu_name: str, price: str, date_str: str, time_slot: str) -> list:
    date = datetime.strptime(date_str, "%Y-%m-%d")
    date_label = f"{date.year}年{date.month}月{date.day}日({WEEKDAY_JP[date.weekday()]})"

    def row(label: str, value: str, value_color: str = "#333333") -> dict:
        return {
            "type": "box",
            "layout": "horizontal",
            "margin": "sm",
            "contents": [
                {"type": "text", "text": label, "color": "#888888", "size": "sm", "flex": 2},
                {"type": "text", "text": value, "size": "sm", "flex": 5,
                 "wrap": True, "color": value_color},
            ],
        }

    return [
        _flex(
            "予約内容の確認",
            {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#E75480",
                    "paddingAll": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "📋 予約内容の確認",
                            "color": "#ffffff",
                            "weight": "bold",
                            "size": "lg",
                        }
                    ],
                },
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "paddingAll": "lg",
                    "spacing": "sm",
                    "contents": [
                        row("メニュー", menu_name),
                        row("料金", price, "#E75480"),
                        row("日程", date_label),
                        row("時間", time_slot),
                        {"type": "separator", "margin": "md"},
                        {
                            "type": "text",
                            "text": f"📍 {SALON_ADDRESS}",
                            "size": "xs",
                            "color": "#888888",
                            "wrap": True,
                            "margin": "md",
                        },
                    ],
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "sm",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#E75480",
                            "action": {
                                "type": "postback",
                                "label": "✅ この内容で予約する",
                                "data": "action=confirm_reservation",
                            },
                        },
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {
                                "type": "postback",
                                "label": "🔄 最初からやり直す",
                                "data": "action=restart_reservation",
                            },
                        },
                    ],
                },
            },
        )
    ]


# ─────────────────────────────────────────
# 予約フロー: ⑤ 予約完了
# ─────────────────────────────────────────
def get_complete_message(name: str, menu_name: str, date_str: str, time_slot: str) -> list:
    date = datetime.strptime(date_str, "%Y-%m-%d")
    date_label = f"{date.month}月{date.day}日({WEEKDAY_JP[date.weekday()]})"

    return [
        _flex(
            "ご予約が完了しました！",
            {
                "type": "bubble",
                "body": {
                    "type": "box",
                    "layout": "vertical",
                    "spacing": "md",
                    "paddingAll": "xl",
                    "contents": [
                        {
                            "type": "text",
                            "text": "🎉 ご予約完了！",
                            "weight": "bold",
                            "size": "xl",
                            "color": "#E75480",
                            "align": "center",
                        },
                        {
                            "type": "text",
                            "text": f"{name}さんのご予約を承りました✨",
                            "size": "sm",
                            "color": "#555555",
                            "align": "center",
                            "wrap": True,
                        },
                        {"type": "separator", "margin": "lg"},
                        {
                            "type": "text",
                            "text": f"📅 {date_label}  {time_slot}〜",
                            "size": "md",
                            "weight": "bold",
                            "margin": "lg",
                            "align": "center",
                        },
                        {
                            "type": "text",
                            "text": f"💇‍♀️ {menu_name}",
                            "size": "sm",
                            "color": "#555555",
                            "align": "center",
                        },
                        {"type": "separator", "margin": "lg"},
                        {
                            "type": "text",
                            "text": (
                                "当日はお気をつけてお越しください🌸\n"
                                "ご不明点はお気軽にご連絡ください。"
                            ),
                            "size": "sm",
                            "color": "#555555",
                            "wrap": True,
                            "align": "center",
                            "margin": "md",
                        },
                    ],
                },
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "secondary",
                            "action": {
                                "type": "uri",
                                "label": "📍 アクセスを確認する",
                                "uri": SALON_MAP_URL,
                            },
                        }
                    ],
                },
            },
        )
    ]


# ─────────────────────────────────────────
# メニュー一覧（「メニューを見る」ボタン用）
# ─────────────────────────────────────────
def get_menu_list_message() -> list:
    rows = []
    for i, m in enumerate(MENUS):
        if i > 0:
            rows.append({"type": "separator", "margin": "sm"})
        rows.append({
            "type": "box",
            "layout": "horizontal",
            "margin": "sm",
            "contents": [
                {
                    "type": "box",
                    "layout": "vertical",
                    "flex": 4,
                    "contents": [
                        {"type": "text", "text": m["name"], "size": "sm", "weight": "bold"},
                        {"type": "text", "text": m["duration"], "size": "xs", "color": "#999999"},
                    ],
                },
                {
                    "type": "text",
                    "text": m["price"],
                    "size": "sm",
                    "flex": 2,
                    "align": "end",
                    "color": "#E75480",
                    "weight": "bold",
                },
            ],
        })

    return [
        _flex(
            "メニュー一覧",
            {
                "type": "bubble",
                "header": {
                    "type": "box",
                    "layout": "vertical",
                    "backgroundColor": "#E75480",
                    "paddingAll": "md",
                    "contents": [
                        {
                            "type": "text",
                            "text": "💇‍♀️ メニュー一覧",
                            "color": "#ffffff",
                            "weight": "bold",
                            "size": "lg",
                        }
                    ],
                },
                "body": {"type": "box", "layout": "vertical", "contents": rows},
                "footer": {
                    "type": "box",
                    "layout": "vertical",
                    "contents": [
                        {
                            "type": "button",
                            "style": "primary",
                            "color": "#E75480",
                            "action": {
                                "type": "postback",
                                "label": "📅 予約する",
                                "data": "action=start_reservation",
                            },
                        }
                    ],
                },
            },
        )
    ]
