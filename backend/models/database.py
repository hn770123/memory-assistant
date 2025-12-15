"""
==============================================================================
database.py - データベースモデル定義ファイル
==============================================================================

【このファイルの役割】
SQLAlchemy ORM（Object-Relational Mapping）を使って、
Pythonのクラスとデータベースのテーブルを対応付けます。

【ORMとは？】
通常、データベースを操作するにはSQL文を書く必要があります：
  例: SELECT * FROM users WHERE id = 1

ORMを使うと、Pythonのオブジェクトとして扱えます：
  例: user = db.query(User).filter(User.id == 1).first()

これにより、Pythonプログラマーがデータベースを扱いやすくなります。

【SQLAlchemyの主要な概念】
1. Engine: データベースへの接続を管理
2. Session: データベースとの対話（クエリ実行、データ保存など）
3. Base: すべてのモデルクラスの親クラス
4. Column/Mapped: テーブルの列（カラム）を定義
==============================================================================
"""

# --------------------------------------------------
# 必要なライブラリのインポート
# --------------------------------------------------
from sqlalchemy import (
    create_engine,    # データベースエンジン作成用
    Column,           # カラム定義（古い書き方、後方互換性のため残っている）
    Integer,          # 整数型
    String,           # 文字列型（短いテキスト）
    Text,             # テキスト型（長いテキスト）
    Date,             # 日付型（年月日）
    DateTime,         # 日時型（年月日時分秒）
    Boolean,          # 真偽値型（True/False）
    Float,            # 浮動小数点数型
    ForeignKey        # 外部キー（他テーブルへの参照）
)
from sqlalchemy.orm import (
    DeclarativeBase,  # モデルの基底クラスを作るため
    sessionmaker,     # セッション（DB接続）を作るファクトリ
    Mapped,           # 型ヒント付きカラム定義（新しい書き方）
    mapped_column     # カラムを定義するデコレータ
)
from sqlalchemy.sql import func  # SQL関数（NOW()など）を使うため
from datetime import datetime    # Python標準の日時クラス
from typing import Optional      # 「None も許容する」型ヒント
import json                      # JSONデータの変換用


# ==================================================
# データベース接続設定
# ==================================================

# データベースファイルのパス
# sqlite:/// は「SQLiteデータベースを使う」という意味
# ./database.db は「現在のディレクトリにdatabase.dbというファイルを作る」
SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

# エンジンの作成
# エンジンは「データベースへの接続方法」を管理するオブジェクト
#
# connect_args={"check_same_thread": False} の説明:
# SQLiteは通常、同じスレッドからしかアクセスできない制限があります。
# FastAPIは複数のリクエストを並行処理するので、この制限を解除しています。
# ※ PostgreSQLなど他のDBでは不要
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

# セッションファクトリの作成
# SessionLocal() を呼ぶたびに新しいDBセッションが作られます
#
# autocommit=False: 明示的に commit() を呼ぶまでDBに反映しない
# autoflush=False: クエリ実行前に自動でflushしない
# bind=engine: どのデータベースに接続するか
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# ==================================================
# ベースクラスの定義
# ==================================================

class Base(DeclarativeBase):
    """
    すべてのモデルクラスの親クラス

    【DeclarativeBaseとは？】
    SQLAlchemyの「宣言的ベース」という仕組みで、
    このクラスを継承したクラスは自動的にDBテーブルとして認識されます。

    使い方:
      class MyModel(Base):
          __tablename__ = "my_table"
          ...
    """
    pass


# ==================================================
# モデル定義（テーブル設計）
# ==================================================

class UserProfile(Base):
    """
    ユーザープロフィール（意味記憶）テーブル

    【意味記憶とは？】
    「私の名前は田中です」「私はPythonが好きです」のような、
    ユーザーに関する事実・情報を保存します。

    【テーブル構造】
    key（主キー） | value        | category    | updated_at
    ----------------------------------------------------------------
    name         | 田中太郎     | personal    | 2024-12-14 10:00:00
    hobby        | プログラミング| preference  | 2024-12-14 10:05:00

    【使用例】
    - 名前、年齢、職業などの個人情報
    - 好きなこと、嫌いなこと、趣味
    - 技術スキル、経験年数
    """
    # テーブル名（データベース内での名前）
    __tablename__ = "user_profile"

    # キー（プロフィール項目名）- 主キー
    # 例: "name", "hobby", "skill_python"
    # Mapped[str] は「このカラムはstr型」という型ヒント
    key: Mapped[str] = mapped_column(String, primary_key=True)

    # 値（プロフィールの内容）
    # Textは長い文字列も保存可能（Stringよりも大容量）
    value: Mapped[str] = mapped_column(Text)

    # カテゴリ（分類用）
    # Optional[str] は「Noneも許容する」という意味
    # 例: "personal"（個人情報）, "skill"（スキル）, "preference"（好み）
    category: Mapped[Optional[str]] = mapped_column(String)

    # 更新日時
    # server_default=func.now(): レコード作成時に現在時刻を自動設定
    # onupdate=func.now(): レコード更新時に現在時刻を自動更新
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),  # INSERT時: 現在時刻
        onupdate=func.now()          # UPDATE時: 現在時刻に更新
    )


class Goal(Base):
    """
    目標管理テーブル

    【目標とは？】
    ユーザーが達成したいことを記録します。
    締め切り、優先度、進捗状況を追跡できます。

    【テーブル構造】
    id | title          | description   | deadline   | priority | status | progress
    -----------------------------------------------------------------------------------
    1  | Python学習     | 基本文法をマスター | 2024-12-31 | high    | active | 30
    2  | 資格取得       | LPIC-1        | 2025-03-01 | medium  | active | 0

    【ステータスの種類】
    - active: 取り組み中
    - completed: 達成済み
    - archived: アーカイブ（後で見返すかも）
    """
    __tablename__ = "goals"

    # ID（自動連番）
    # autoincrement=True で自動的に1, 2, 3...と増える
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 目標のタイトル
    title: Mapped[str] = mapped_column(String)

    # 目標の詳細説明（省略可能）
    description: Mapped[Optional[str]] = mapped_column(Text)

    # 締め切り日（省略可能）
    # Date型は「年月日」のみ（時刻なし）
    deadline: Mapped[Optional[datetime]] = mapped_column(Date)

    # 優先度（省略可能）
    # 'low'（低）, 'medium'（中）, 'high'（高）
    priority: Mapped[Optional[str]] = mapped_column(String)

    # ステータス
    # default='active' で初期値を設定
    status: Mapped[str] = mapped_column(String, default='active')

    # 進捗率（0〜100）
    progress: Mapped[int] = mapped_column(Integer, default=0)

    # 作成日時
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 更新日時
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.now(),
        onupdate=func.now()
    )


class EpisodicMemory(Base):
    """
    エピソード記憶テーブル（日ごとの要約）

    【エピソード記憶とは？】
    「昨日は何をしたか」という体験・出来事の記憶です。
    毎日の会話を要約して保存し、長期記憶として活用します。

    【テーブル構造】
    id | date       | summary                     | key_events
    ----------------------------------------------------------------
    1  | 2024-12-14 | Pythonの学習について話した   | ["文法学習", "質問対応"]

    【key_eventsについて】
    JSON形式でリスト/辞書を保存します。
    SQLiteにはJSON型がないため、Text型に文字列として保存し、
    get/setメソッドで変換しています。
    """
    __tablename__ = "episodic_memory"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 日付（ユニーク制約：同じ日付は1レコードのみ）
    date: Mapped[datetime] = mapped_column(Date, unique=True)

    # その日の会話の要約
    summary: Mapped[str] = mapped_column(Text)

    # 主要な出来事（JSON文字列として保存）
    key_events: Mapped[Optional[str]] = mapped_column(Text)

    # 作成日時
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    def set_key_events(self, events: dict | list):
        """
        key_eventsをJSON文字列に変換して保存

        使用例:
            memory.set_key_events(["イベント1", "イベント2"])
            memory.set_key_events({"topic": "Python", "duration": "1時間"})
        """
        self.key_events = json.dumps(events)

    def get_key_events(self):
        """
        key_eventsをJSON文字列からPythonオブジェクトに変換して取得

        戻り値:
            リストまたは辞書（key_eventsが設定されている場合）
            None（key_eventsが未設定の場合）
        """
        if self.key_events:
            return json.loads(self.key_events)
        return None


class Conversation(Base):
    """
    会話履歴テーブル（短期記憶）

    【短期記憶とは？】
    最近の会話を記録して、文脈を維持するために使います。
    古い会話は定期的にエピソード記憶に統合（consolidate）されます。

    【テーブル構造】
    id | user_message | assistant_message | timestamp           | consolidated | importance_score
    -------------------------------------------------------------------------------------------------
    1  | こんにちは    | こんにちは！       | 2024-12-14 10:00:00 | false       | 0.1
    2  | 名前は田中です | 田中さんですね     | 2024-12-14 10:01:00 | false       | 0.8

    【importance_scoreについて】
    会話の重要度を0.0〜1.0で評価します。
    重要な情報（名前、目標など）は高スコアになり、
    統合処理の際に優先的に残されます。
    """
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # ユーザーのメッセージ
    user_message: Mapped[str] = mapped_column(Text)

    # アシスタントの応答
    assistant_message: Mapped[str] = mapped_column(Text)

    # 会話日時
    timestamp: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    # 統合済みフラグ
    # True = エピソード記憶に統合済み（古い会話）
    # False = まだ統合されていない（新しい会話）
    consolidated: Mapped[bool] = mapped_column(Boolean, default=False)

    # 重要度スコア（0.0〜1.0）
    # Noneの場合は未評価
    importance_score: Mapped[Optional[float]] = mapped_column(Float)


class Reminder(Base):
    """
    リマインダーテーブル

    【リマインダーとは？】
    「明日の10時に会議」のような、将来の予定や通知を管理します。
    繰り返し設定（毎日、毎週など）も可能です。

    【テーブル構造】
    id | content           | remind_at            | recurrence | status
    -------------------------------------------------------------------------
    1  | 会議に参加する      | 2024-12-15 10:00:00 | null      | pending
    2  | 薬を飲む           | 2024-12-14 21:00:00 | daily     | pending

    【statusの種類】
    - pending: 未通知（まだ時間になっていない）
    - triggered: 通知済み
    - snoozed: スヌーズ中（後で再通知）
    - dismissed: 無視/完了
    """
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # リマインダーの内容
    content: Mapped[str] = mapped_column(Text)

    # 通知日時
    remind_at: Mapped[datetime] = mapped_column(DateTime)

    # 繰り返し設定
    # 'daily'（毎日）, 'weekly'（毎週）, 'monthly'（毎月）, null（一回のみ）
    recurrence: Mapped[Optional[str]] = mapped_column(String)

    # ステータス
    status: Mapped[str] = mapped_column(String, default='pending')

    # 作成日時
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


# ==================================================
# データベース操作用の関数
# ==================================================

def init_db():
    """
    データベースを初期化する（テーブルを作成する）

    【動作説明】
    Base.metadata.create_all() は、Baseを継承したすべてのクラス
    （UserProfile, Goal, EpisodicMemory, Conversation, Reminder）
    に対応するテーブルをデータベースに作成します。

    ※すでにテーブルが存在する場合は何もしません（安全）

    【使用タイミング】
    アプリケーション起動時に一度だけ呼び出します。
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    データベースセッションを取得するジェネレータ関数

    【ジェネレータ関数とは？】
    yield を使う特殊な関数で、値を一つ返した後も状態を保持します。
    FastAPIの依存性注入（Dependency Injection）で使われます。

    【動作説明】
    1. SessionLocal() で新しいDBセッションを作成
    2. yield db でセッションを呼び出し元に渡す
    3. 呼び出し元の処理が終わったら finally ブロックが実行される
    4. db.close() でセッションを閉じる（リソース解放）

    【使用例】
    FastAPIのエンドポイントで以下のように使います：

        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()

    Depends(get_db) により、リクエストごとに自動的に
    セッションが作成され、レスポンス後にクローズされます。
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
