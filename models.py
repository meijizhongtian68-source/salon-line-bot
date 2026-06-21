# models.py — データベースモデル定義

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()


class User(db.Model):
    """LINE 登録ユーザー"""
    __tablename__ = 'users'

    id            = db.Column(db.Integer, primary_key=True)
    line_user_id  = db.Column(db.String(100), unique=True, nullable=False, index=True)
    display_name  = db.Column(db.String(200), default='')
    followed_at   = db.Column(db.DateTime, default=datetime.utcnow)
    is_blocked    = db.Column(db.Boolean, default=False)

    # ステップ配信 送信済みフラグ
    step1_sent = db.Column(db.Boolean, default=False)  # 翌日
    step2_sent = db.Column(db.Boolean, default=False)  # 3日後
    step3_sent = db.Column(db.Boolean, default=False)  # 7日後
    step4_sent = db.Column(db.Boolean, default=False)  # 8日後
    step5_sent = db.Column(db.Boolean, default=False)  # 9日後

    reservations = db.relationship('Reservation', backref='user', lazy=True)

    def __repr__(self):
        return f'<User {self.display_name}>'


class Reservation(db.Model):
    """予約データ"""
    __tablename__ = 'reservations'

    id         = db.Column(db.Integer, primary_key=True)
    user_id    = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    menu_name  = db.Column(db.String(100))
    menu_price = db.Column(db.String(20))
    date       = db.Column(db.String(20))   # YYYY-MM-DD
    time_slot  = db.Column(db.String(10))   # HH:MM
    status     = db.Column(db.String(20), default='confirmed')  # confirmed / cancelled
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Reservation {self.menu_name} {self.date} {self.time_slot}>'


class ConversationState(db.Model):
    """予約フローの会話ステート管理"""
    __tablename__ = 'conversation_states'

    id              = db.Column(db.Integer, primary_key=True)
    line_user_id    = db.Column(db.String(100), unique=True, nullable=False, index=True)
    state           = db.Column(db.String(50), default='idle')
    # 予約フロー中の一時データ
    temp_menu       = db.Column(db.String(100))
    temp_menu_price = db.Column(db.String(20))
    temp_date       = db.Column(db.String(20))
    temp_time       = db.Column(db.String(10))
    updated_at      = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<ConversationState {self.line_user_id}: {self.state}>'
