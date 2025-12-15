"""
==============================================================================
schemas.py - Pydanticスキーマ定義ファイル
==============================================================================

【このファイルの役割】
Pydanticを使って、APIのリクエスト/レスポンスのデータ構造を定義します。

【Pydanticとは？】
データの検証（バリデーション）と型変換を自動で行うライブラリです。

例えば、以下のようなJSONがAPIに送られてきたとき：
  {"message": "こんにちは", "model": "llama3.1:8b"}

Pydanticが自動的に：
1. 必須フィールド（message）があるか確認
2. 型が正しいか確認（messageはstr型か？）
3. デフォルト値を適用（modelが省略されたら"llama3.1:8b"を使う）
4. Pythonオブジェクトに変換

【BaseModelとは？】
Pydanticのすべてのスキーマの親クラスです。
BaseModelを継承したクラスは、自動的にバリデーション機能を持ちます。

【スキーマの命名規則】
- XxxBase: 基本スキーマ（共通フィールドを定義）
- XxxCreate: 作成時のスキーマ（POST用）
- XxxUpdate: 更新時のスキーマ（PUT/PATCH用）
- Xxx: レスポンス用スキーマ（GET用、DBから取得した値）
==============================================================================
"""

# --------------------------------------------------
# 必要なライブラリのインポート
# --------------------------------------------------
from pydantic import BaseModel   # Pydanticの基底クラス
from typing import Optional, List, Any  # 型ヒント用
from datetime import datetime    # 日時型


# ==================================================
# チャット関連のスキーマ
# ==================================================

class ChatRequest(BaseModel):
    """
    チャットリクエストのスキーマ

    【使用場面】
    POST /chat エンドポイントへのリクエストボディ

    【リクエスト例】
    {
        "message": "こんにちは、私の名前は田中です",
        "model": "llama3.1:8b"
    }

    【フィールド説明】
    - message: 必須。ユーザーが入力したメッセージ
    - model: 任意。使用するLLMモデル名。省略時は"llama3.1:8b"
    """
    message: str                    # ユーザーのメッセージ（必須）
    model: str = "llama3.1:8b"      # 使用するモデル（デフォルト値あり）


class ChatResponse(BaseModel):
    """
    チャットレスポンスのスキーマ

    【使用場面】
    POST /chat エンドポイントからのレスポンス

    【レスポンス例】
    {
        "response": "こんにちは、田中さん！",
        "model": "llama3.1:8b"
    }
    """
    response: str   # アシスタントの応答メッセージ
    model: str      # 使用されたモデル名


# ==================================================
# ユーザープロフィール関連のスキーマ
# ==================================================

class UserProfileBase(BaseModel):
    """
    ユーザープロフィールの基本スキーマ

    【継承関係の説明】
    UserProfileBase
        ├── UserProfileCreate（作成時）
        └── UserProfile（レスポンス時）

    共通のフィールド（key, value, category）をここで定義し、
    子クラスで追加フィールドを定義します。
    """
    key: str                           # プロフィールのキー（例: "name", "hobby"）
    value: str                         # プロフィールの値（例: "田中", "プログラミング"）
    category: Optional[str] = None     # カテゴリ（例: "personal", "skill"）


class UserProfileCreate(UserProfileBase):
    """
    プロフィール作成時のスキーマ

    【使用場面】
    POST /api/profiles エンドポイントへのリクエスト

    【リクエスト例】
    {
        "key": "name",
        "value": "田中太郎",
        "category": "personal"
    }

    【passの説明】
    親クラス（UserProfileBase）のフィールドをそのまま使うので、
    追加のフィールドは不要。passは「何もしない」という意味。
    """
    pass


class UserProfileUpdate(BaseModel):
    """
    プロフィール更新時のスキーマ

    【使用場面】
    PUT /api/profiles/{key} エンドポイントへのリクエスト

    【リクエスト例】
    {
        "value": "新しい値",
        "category": "skill"
    }

    【Optionalの説明】
    更新時は変更したいフィールドだけ送ればよいので、
    すべてのフィールドをOptional（任意）にしています。
    """
    value: Optional[str] = None        # 新しい値（変更しない場合はNone）
    category: Optional[str] = None     # 新しいカテゴリ（変更しない場合はNone）


class UserProfile(UserProfileBase):
    """
    プロフィールレスポンス用のスキーマ

    【使用場面】
    GET /api/profiles エンドポイントからのレスポンス

    【レスポンス例】
    {
        "key": "name",
        "value": "田中太郎",
        "category": "personal",
        "updated_at": "2024-12-14T10:00:00"
    }
    """
    updated_at: datetime  # 最終更新日時（DBから取得）

    class Config:
        """
        Pydanticの設定クラス

        【from_attributes = True とは？】
        SQLAlchemyのモデルオブジェクトから自動的にデータを取得できるようにする設定。

        これがないと、以下のような変換ができません：
            db_profile = db.query(UserProfileDB).first()  # DBモデル
            response = UserProfile.from_orm(db_profile)   # Pydanticスキーマに変換

        ※ 昔は orm_mode = True でしたが、Pydantic v2で名前が変わりました
        """
        from_attributes = True


# ==================================================
# 目標（Goal）関連のスキーマ
# ==================================================

class GoalBase(BaseModel):
    """
    目標の基本スキーマ

    【フィールド説明】
    - title: 目標のタイトル（必須）
    - description: 詳細説明（任意）
    - deadline: 締め切り日時（任意）
    - priority: 優先度 "low"/"medium"/"high"（任意）
    - status: ステータス "active"/"completed"/"archived"
    - progress: 進捗率 0-100（デフォルト0）
    """
    title: str                              # 目標タイトル（必須）
    description: Optional[str] = None       # 詳細説明
    deadline: Optional[datetime] = None     # 締め切り
    priority: Optional[str] = None          # 優先度
    status: str = 'active'                  # ステータス
    progress: int = 0                       # 進捗率（0-100）


class GoalCreate(GoalBase):
    """
    目標作成時のスキーマ

    【使用場面】
    POST /api/goals エンドポイントへのリクエスト

    【リクエスト例】
    {
        "title": "Pythonをマスターする",
        "description": "基本文法からWebアプリまで",
        "deadline": "2024-12-31T00:00:00",
        "priority": "high"
    }
    """
    pass


class GoalUpdate(BaseModel):
    """
    目標更新時のスキーマ

    【使用場面】
    PUT /api/goals/{id} エンドポイントへのリクエスト

    【リクエスト例】
    {
        "progress": 50,
        "status": "active"
    }

    すべてのフィールドがOptionalなので、
    変更したいフィールドだけ送ればOK。
    """
    title: Optional[str] = None
    description: Optional[str] = None
    deadline: Optional[datetime] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None


class Goal(GoalBase):
    """
    目標レスポンス用のスキーマ

    【レスポンス例】
    {
        "id": 1,
        "title": "Pythonをマスターする",
        "description": "基本文法からWebアプリまで",
        "deadline": "2024-12-31T00:00:00",
        "priority": "high",
        "status": "active",
        "progress": 30,
        "created_at": "2024-12-01T10:00:00",
        "updated_at": "2024-12-14T15:30:00"
    }
    """
    id: int                 # 目標ID（DBで自動採番）
    created_at: datetime    # 作成日時
    updated_at: datetime    # 更新日時

    class Config:
        from_attributes = True


# ==================================================
# 会話（Conversation）関連のスキーマ
# ==================================================

class ConversationBase(BaseModel):
    """
    会話の基本スキーマ

    【フィールド説明】
    - user_message: ユーザーのメッセージ
    - assistant_message: アシスタントの応答
    - consolidated: 統合済みフラグ（エピソード記憶に移動済みか）
    - importance_score: 重要度スコア（0.0〜1.0）
    """
    user_message: str                           # ユーザーのメッセージ
    assistant_message: str                      # アシスタントの応答
    consolidated: bool = False                  # 統合済みフラグ
    importance_score: Optional[float] = None    # 重要度（0.0〜1.0）


class ConversationCreate(ConversationBase):
    """
    会話作成時のスキーマ

    【使用場面】
    通常、会話はチャットエンドポイント経由で自動保存されるので、
    直接このスキーマを使うことは少ない。
    """
    pass


class Conversation(ConversationBase):
    """
    会話レスポンス用のスキーマ

    【レスポンス例】
    {
        "id": 1,
        "user_message": "こんにちは",
        "assistant_message": "こんにちは！今日はどんなお手伝いをしましょうか？",
        "timestamp": "2024-12-14T10:00:00",
        "consolidated": false,
        "importance_score": 0.3
    }
    """
    id: int              # 会話ID
    timestamp: datetime  # 会話日時

    class Config:
        from_attributes = True


# ==================================================
# 一括削除用のスキーマ
# ==================================================

class DeleteRequest(BaseModel):
    """
    複数アイテム削除用のスキーマ

    【使用場面】
    DELETE /api/profiles/batch などで複数アイテムを一度に削除

    【リクエスト例】
    {
        "keys": ["hobby", "skill_python", "old_info"]
    }

    【なぜ一括削除が必要か？】
    1つずつAPIを呼ぶより効率的。
    ネットワーク通信回数が減り、高速に処理できる。
    """
    keys: List[str]  # 削除するキーのリスト


class DeleteIdsRequest(BaseModel):
    """
    複数ID削除用のスキーマ

    【使用場面】
    DELETE /api/goals/batch などでID指定で複数削除

    【リクエスト例】
    {
        "ids": [1, 3, 5]
    }
    """
    ids: List[int]  # 削除するIDのリスト


# ==================================================
# 統計情報用のスキーマ
# ==================================================

class MemoryStats(BaseModel):
    """
    メモリ統計情報のスキーマ

    【使用場面】
    GET /api/memory/stats エンドポイントからのレスポンス

    【レスポンス例】
    {
        "profile_count": 15,
        "goal_count": 3,
        "conversation_count": 120,
        "active_goals": 2
    }

    【用途】
    メモリ管理ページのダッシュボードに表示する統計情報
    """
    profile_count: int      # 保存されているプロフィール数
    goal_count: int         # 目標の総数
    conversation_count: int # 会話履歴の総数
    active_goals: int       # アクティブな目標数
