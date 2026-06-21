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
SALON_NAME    = "男の専門整体『KILIG』"
SALON_ADDRESS = "南富山駅より車で3分"   # 予約確定後のみ送信
SALON_PHONE   = ""
SALON_HOURS   = "火・水 9:00〜18:00 / 金・土・日 13:00〜21:00"
SALON_MAP_URL = "https://maps.google.com/maps?q=南富山駅"

# メニュー定義
MENUS = [
    {"name": "血流改善×深部筋膜リリース", "price": "初回¥9,900（通常¥33,000）", "duration": "カウンセリング含めて2時間"},
]

# 予約時間スロット
TIME_SLOTS = ["9:00", "11:00", "13:00", "15:00", "17:00", "19:00"]

# 定休日（0=月, 1=火, ..., 6=日）
CLOSED_WEEKDAYS = [0, 3]  # 月・木定休

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
    return [TextMessage(text=(
        "【ご登録ありがとうございます！】\n\n"
        "オーナーのみきです。\n\n"
        "この度はLINE登録ありがとうございます。\n\n"
        "「最近、朝の元気がなくなってきた…」\n"
        "「もう歳のせいだから仕方ない」\n\n"
        "そんな風に諦めていませんか？\n\n"
        "実は、看護師として8年間、\n"
        "多くの患者様と接する中で気づいたことがあります。\n\n"
        "それは、多くの不調が「血流の滞り」から\n"
        "きているということです。\n\n"
        "病院では薬で症状を抑えることはできても、\n"
        "体本来の活力を取り戻すのは難しいのが現実です。\n\n"
        "でも、諦める必要はありません。\n\n"
        "北陸で唯一の、サラシと布を使った\n"
        "「血流特化の施術」で、\n"
        "20代のような自信と活力を取り戻すお手伝いをします。\n\n"
        "明日から、なぜ「歳のせい」ではないのか、\n"
        "その秘密をお伝えしていきますね。\n"
        "どうぞお楽しみに！"
    ))]


# ─────────────────────────────────────────
# Step 2: お客様の声（3日後）
# ─────────────────────────────────────────
def get_step2_message(name: str) -> list:
    return [TextMessage(text=(
        "【「あの頃」の自信、取り戻しませんか？】\n\n"
        "おはようございます！\n"
        "オーナーのみきです。\n\n"
        "もし、朝起きた瞬間に\n"
        "「今日も一日、力がみなぎっている！」\n"
        "と感じられたら、あなたの生活はどう変わりますか？\n\n"
        "・仕事への集中力が格段に上がる\n"
        "・趣味やプライベートを全力で楽しめる\n"
        "・男としての自信が、立ち振る舞いに表れる\n\n"
        "「朝立ち」は、単なる現象ではなく\n"
        "心身の健康と活力のバロメーターです。\n\n"
        "私のサロンに通われるお客様からは、\n"
        "「諦めていた気持ちが前向きになった！」\n"
        "「毎日がエネルギッシュになった」\n"
        "というお声をたくさんいただいています。\n\n"
        "血流が整い、体が内側から目覚めると、\n"
        "人生の質そのものが変わります。\n\n"
        "明日は、なぜ今まであなたの悩みが\n"
        "解決しなかったのか、その真相をお話しします。"
    ))]


# ─────────────────────────────────────────
# Step 3: 初回限定クーポン（7日後）
# ─────────────────────────────────────────
def get_step3_message(name: str) -> list:
    return [TextMessage(text=(
        "【なぜ、マッサージや薬ではダメなのか？】\n\n"
        "こんばんは！\n"
        "オーナーの美紀です。\n\n"
        "「疲れが取れないからマッサージに行く」\n"
        "「元気がほしいから薬を飲む」\n\n"
        "それ、実は「対症療法」にすぎないかもしれません。\n\n"
        "看護師時代、糖尿病や高血圧で\n"
        "大量の薬を飲んでいる患者様をたくさん見てきました。\n"
        "でも、それでは根本的な解決にはならなかった。\n\n"
        "一番大切なのは、\n"
        "血液を体の隅々まで届ける「巡りの力」です。\n\n"
        "当サロンで「サラシや布」を使うのは、\n"
        "手技だけでは届かない深部の巡りに\n"
        "アプローチするためです。\n\n"
        "力任せの指圧ではなく、布の弾力を使い\n"
        "優しく、かつ確実に血流を促す。\n\n"
        "これが、北陸で当サロンだけが提供している\n"
        "「活力を呼び覚ます」秘訣なんです。\n\n"
        "明日は、私がなぜこの活動を\n"
        "富山で始めたのか、その想いを聞いてください。"
    ))]


# ─────────────────────────────────────────
# Step 4: オーナーの想い（8日後）
# ─────────────────────────────────────────
def get_step4_message(name: str) -> list:
    return [TextMessage(text=(
        "【富山の男性を、もっと元気にしたい】\n\n"
        "こんにちは！\n"
        "オーナーの美紀です。\n\n"
        "実はこのサロン、最初は女性専用でスタートしました。\n"
        "でも、活動を続ける中で気づいたんです。\n\n"
        "「富山には、男性が本当に心身をケアできる場所が圧倒的に少ない」ということに。\n\n"
        "男性特有の悩みは、誰にも相談できず、\n"
        "一人で「年齢のせい」にしてしまいがちです。\n\n"
        "元看護師だからこそ、\n"
        "あなたの体を医学的視点と、\n"
        "温かいケアの両面からサポートしたい。\n\n"
        "「ここに来れば、また頑張れる」\n"
        "そう思っていただける場所を富山に作りたい。\n"
        "その一心で、毎日施術に向き合っています。\n\n"
        "いよいよ明日、\n"
        "あなたへの「特別な提案」をさせていただきます。\n"
        "チェックを忘れないでくださいね！"
    ))]


# ─────────────────────────────────────────
# Step 5: 初回限定募集案内（9日後）
# ─────────────────────────────────────────
def get_step5_message(name: str) -> list:
    return [TextMessage(text=(
        "【ついに明日、募集を開始します！】\n\n"
        "こんばんは！\n"
        "オーナーの美紀です。\n\n"
        "これまで、血流の大切さと\n"
        "私の想いをお伝えしてきました。\n\n"
        "「本気で自分を変えたい」\n"
        "「もう一度、あの頃の活力を取り戻したい」\n\n"
        "そう願うあなたのために、\n"
        "特別な体験枠をご用意しました。\n\n"
        "北陸では当サロンだけの特殊な施術を、\n"
        "まずは一人でも多くの方に体感してほしい。\n"
        "その想いから、赤字覚悟の特典をご用意しました。\n\n"
        "＝＝＝＝＝＝＝＝＝＝＝＝\n"
        "◆初回限定・特別体験\n"
        "通常1回 33,000円\n"
        "↓\n"
        "【新規価格 1回19,800円】\n"
        "↓\n"
        "【特別価格 1回9,900円】\n"
        "＝＝＝＝＝＝＝＝＝＝＝＝\n\n"
        "ただし、一人ひとりと看護師の視点で\n"
        "丁寧に向き合うため、【1日限定3名様】まで。\n"
        "また事前決済してくれる方限定とさせていただきます。\n\n"
        "今のうちに、カレンダーにチェックしておいてくださいね！"
    ))]


# ─────────────────────────────────────────
# Step 6: 本日受付開始（10日後）
# ─────────────────────────────────────────
def get_step6_message(name: str) -> list:
    return [TextMessage(text=(
        "【本日受付開始！残りわずかです】\n\n"
        "おはようございます！\n"
        "オーナーのみきです。\n\n"
        "お待たせいたしました。\n"
        "北陸唯一の血流改善メニュー、\n"
        "特別価格での受付を開始します！\n\n"
        "「歳のせい」という言葉で\n"
        "あなたの可能性に蓋をするのは、今日で終わりにしましょう。\n\n"
        "看護師としての経験と、\n"
        "サラシを使った独自の技術。\n"
        "そのすべてを注いで、あなたの活力を引き出します。\n\n"
        "＝＝＝＝＝＝＝＝＝＝＝＝\n"
        "通常1回 33,000円\n"
        "↓\n"
        "【新規価格 1回19,800円】\n"
        "↓\n"
        "【特別価格 1回 9,900円】\n"
        "事前決済してくれる方限定とさせていただきます。\n"
        "＝＝＝＝＝＝＝＝＝＝＝＝\n\n"
        "▼今すぐ予約して自信を取り戻す\n"
        "「予約」と返信してください\n\n"
        "枠が埋まり次第、終了となります。\n"
        "あなたの人生が前向きに変わる瞬間を、\n"
        "全力でサポートさせていただきます！"
    ))]


def _get_step3_coupon(name: str) -> list:
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
# Q&A 予約フロー
# ─────────────────────────────────────────
def get_reservation_ask_name_age() -> list:
    return [TextMessage(text=(
        "ご予約ありがとうございます😊\n\n"
        "【血流改善×深部筋膜リリース】\n"
        "初回¥9,900（通常¥33,000）\n"
        "カウンセリング含めて2時間\n\n"
        "①お名前と年齢を教えてください🙏"
    ))]


def get_reservation_ask_symptoms() -> list:
    return [TextMessage(text=(
        "ありがとうございます！\n\n"
        "②改善したい症状・目標を教えてください💪\n\n"
        "例：ED改善、血流改善、疲労回復など"
    ))]


def get_reservation_ask_dates() -> list:
    return [TextMessage(text=(
        "承知しました！\n\n"
        "③ご来店希望日時を第3希望までお知らせください📅\n\n"
        "営業日：火・水 9:00〜18:00\n"
        "　　　　金・土・日 13:00〜21:00\n\n"
        "例）\n"
        "第1希望：○月○日（曜日）○時\n"
        "第2希望：○月○日（曜日）○時\n"
        "第3希望：○月○日（曜日）○時"
    ))]


def get_reservation_complete_message(name: str) -> list:
    return [TextMessage(text=(
        f"{name}さん、ご予約リクエストありがとうございます！\n\n"
        "内容を確認の上、担当者より折り返しご連絡いたします😊\n\n"
        "お気軽にお待ちください✨"
    ))]


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
