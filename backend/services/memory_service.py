"""
==============================================================================
memory_service.py - 記憶管理サービス
==============================================================================

【このファイルの役割】
データベースとのやり取りをカプセル化（隠蔽）するサービスクラスを提供します。
APIエンドポイント（main.py）から直接DBを操作せず、このサービスを経由することで：
1. コードの整理整頓（関心の分離）
2. 再利用性の向上（同じ操作を複数の場所から呼べる）
3. テストしやすさの向上

【サービスパターンとは？】
ビジネスロジック（アプリケーションの主要な処理）を
APIのエンドポイント定義から分離する設計パターンです。

例:
  main.py（エンドポイント）→ memory_service.py（ビジネスロジック）→ database.py（DB）

【CRUDとは？】
データベース操作の基本4つの頭文字：
- C: Create（作成）
- R: Read（読み取り）
- U: Update（更新）
- D: Delete（削除）
==============================================================================
"""

# --------------------------------------------------
# 必要なライブラリのインポート
# --------------------------------------------------
from sqlalchemy.orm import Session  # DBセッション型
from models.database import (
    Conversation,     # 会話モデル
    UserProfile,      # ユーザープロフィールモデル
    Goal,             # 目標モデル
    EpisodicMemory    # エピソード記憶モデル
)
from models import schemas          # Pydanticスキーマ
import json                          # JSONデータ変換用
from datetime import datetime        # 日時操作用
from typing import List, Optional    # 型ヒント用


class MemoryService:
    """
    記憶管理サービスクラス

    【クラスの設計について】
    このクラスは「状態を持つ」設計になっています。
    __init__でDBセッションを受け取り、インスタンス変数self.dbに保存します。

    【使用例】
        db = SessionLocal()  # DBセッションを作成
        service = MemoryService(db)  # サービスのインスタンスを作成
        profiles = service.get_all_user_profiles()  # メソッドを呼び出し
        db.close()  # セッションを閉じる

    【なぜこの設計？】
    1. 同じセッションで複数の操作ができる（トランザクション管理）
    2. 依存性注入（Dependency Injection）で使いやすい
    """

    def __init__(self, db: Session):
        """
        コンストラクタ（初期化メソッド）

        【引数】
        db: SQLAlchemyのSessionオブジェクト

        【Pythonのクラスについて】
        __init__ はインスタンス作成時に自動的に呼ばれる特殊メソッド。
        self はインスタンス自身を指す（JavaやC#の this に相当）。
        """
        self.db = db  # DBセッションをインスタンス変数として保存


    # ==========================================================
    # 会話（Conversation）関連のメソッド
    # ==========================================================

    def save_conversation(
        self,
        user_message: str,
        assistant_message: str,
        importance_score: float = 0.0
    ) -> Conversation:
        """
        会話をデータベースに保存する

        【引数】
        user_message: ユーザーが送ったメッセージ
        assistant_message: アシスタントの応答
        importance_score: 会話の重要度（0.0〜1.0）

        【戻り値】
        保存されたConversationオブジェクト

        【処理の流れ】
        1. Conversationオブジェクトを作成
        2. DBセッションに追加（add）
        3. 変更を確定（commit）
        4. オブジェクトを最新状態に更新（refresh）
        5. オブジェクトを返す

        【commitとrefreshの違い】
        - commit(): 変更をDBに書き込む
        - refresh(): DBから最新データを取得してオブジェクトを更新
                    （自動生成されたIDやタイムスタンプを取得するため）
        """
        # 新しい会話オブジェクトを作成
        conversation = Conversation(
            user_message=user_message,
            assistant_message=assistant_message,
            importance_score=importance_score
        )
        # DBセッションに追加（この時点ではまだDBに保存されていない）
        self.db.add(conversation)
        # トランザクションをコミット（DBに実際に書き込み）
        self.db.commit()
        # DBから最新の状態を取得（自動生成されたIDなどを反映）
        self.db.refresh(conversation)
        return conversation

    def get_recent_conversations(self, limit: int = 10) -> List[Conversation]:
        """
        最近の会話を取得する

        【引数】
        limit: 取得する件数（デフォルト10件）

        【戻り値】
        Conversationオブジェクトのリスト（新しい順）

        【SQLAlchemyのクエリについて】
        query(Model): 対象モデルを指定
        order_by(Model.column.desc()): 降順でソート
        limit(n): 最初のn件だけ取得
        all(): 結果をリストで取得
        """
        return (
            self.db.query(Conversation)
            .order_by(Conversation.timestamp.desc())  # 新しい順にソート
            .limit(limit)  # 指定件数に制限
            .all()  # リストとして取得
        )

    def get_all_conversations(self) -> List[Conversation]:
        """
        すべての会話履歴を取得する

        【用途】
        メモリ管理ページで会話一覧を表示するとき

        【注意】
        会話数が多い場合はメモリを大量に消費する可能性あり。
        実運用ではページネーション（ページ分割）を検討すべき。
        """
        return (
            self.db.query(Conversation)
            .order_by(Conversation.timestamp.desc())
            .all()
        )

    def delete_conversation(self, conversation_id: int) -> bool:
        """
        指定IDの会話を削除する

        【引数】
        conversation_id: 削除する会話のID

        【戻り値】
        True: 削除成功
        False: 該当する会話が見つからなかった

        【delete()メソッドについて】
        SQLAlchemyでは2つの削除方法があります：
        1. db.delete(obj) - オブジェクトを指定して削除
        2. query.filter().delete() - フィルタ条件で一括削除（今回使用）
        """
        # 削除対象を検索して削除
        # delete()は削除した件数を返す
        deleted_count = (
            self.db.query(Conversation)
            .filter(Conversation.id == conversation_id)
            .delete()
        )
        self.db.commit()  # 削除を確定
        return deleted_count > 0  # 1件以上削除できたらTrue

    def delete_conversations_batch(self, ids: List[int]) -> int:
        """
        複数の会話を一括削除する

        【引数】
        ids: 削除する会話IDのリスト

        【戻り値】
        削除された件数

        【in_()について】
        SQLの IN 句に相当：
        WHERE id IN (1, 2, 3, 4, 5)
        指定したリストのいずれかに一致するレコードを対象にする
        """
        deleted_count = (
            self.db.query(Conversation)
            .filter(Conversation.id.in_(ids))  # IDがリストに含まれるもの
            .delete(synchronize_session=False)  # パフォーマンス向上のため
        )
        self.db.commit()
        return deleted_count


    # ==========================================================
    # ユーザープロフィール（UserProfile）関連のメソッド
    # ==========================================================

    def get_user_profile(self, key: str) -> Optional[UserProfile]:
        """
        指定キーのプロフィールを取得する

        【引数】
        key: プロフィールのキー（例: "name", "hobby"）

        【戻り値】
        UserProfileオブジェクト or None（見つからない場合）

        【first()について】
        最初の1件だけを取得。見つからない場合はNoneを返す。
        all()と違い、1件だけ必要な場合に効率的。
        """
        return (
            self.db.query(UserProfile)
            .filter(UserProfile.key == key)  # keyが一致するもの
            .first()  # 最初の1件（またはNone）
        )

    def update_user_profile(
        self,
        key: str,
        value: str,
        category: str = None
    ) -> UserProfile:
        """
        プロフィールを更新または作成する（Upsert操作）

        【Upsertとは？】
        Update + Insert の造語。
        - レコードが存在すれば更新（Update）
        - 存在しなければ新規作成（Insert）

        【引数】
        key: プロフィールのキー
        value: 新しい値
        category: カテゴリ（省略可）

        【戻り値】
        更新または作成されたUserProfileオブジェクト
        """
        # まず既存のプロフィールを検索
        profile = self.get_user_profile(key)

        if profile:
            # 存在する場合は更新
            profile.value = value
            if category:
                profile.category = category
        else:
            # 存在しない場合は新規作成
            profile = UserProfile(key=key, value=value, category=category)
            self.db.add(profile)

        self.db.commit()
        return profile

    def get_all_user_profiles(self) -> List[UserProfile]:
        """
        すべてのユーザープロフィールを取得する

        【戻り値】
        UserProfileオブジェクトのリスト
        """
        return self.db.query(UserProfile).all()

    def delete_user_profile(self, key: str) -> bool:
        """
        指定キーのプロフィールを削除する

        【引数】
        key: 削除するプロフィールのキー

        【戻り値】
        True: 削除成功
        False: 該当するプロフィールが見つからなかった
        """
        deleted_count = (
            self.db.query(UserProfile)
            .filter(UserProfile.key == key)
            .delete()
        )
        self.db.commit()
        return deleted_count > 0

    def delete_profiles_batch(self, keys: List[str]) -> int:
        """
        複数のプロフィールを一括削除する

        【引数】
        keys: 削除するプロフィールキーのリスト

        【戻り値】
        削除された件数
        """
        deleted_count = (
            self.db.query(UserProfile)
            .filter(UserProfile.key.in_(keys))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted_count


    # ==========================================================
    # 目標（Goal）関連のメソッド
    # ==========================================================

    def get_active_goals(self) -> List[Goal]:
        """
        アクティブな目標を取得する

        【アクティブとは？】
        status が 'active' の目標のみを対象とする。
        完了済み（completed）やアーカイブ済み（archived）は含まない。

        【戻り値】
        アクティブなGoalオブジェクトのリスト
        """
        return (
            self.db.query(Goal)
            .filter(Goal.status == 'active')
            .all()
        )

    def get_all_goals(self) -> List[Goal]:
        """
        すべての目標を取得する

        【戻り値】
        Goalオブジェクトのリスト（作成日時の新しい順）
        """
        return (
            self.db.query(Goal)
            .order_by(Goal.created_at.desc())
            .all()
        )

    def get_goal(self, goal_id: int) -> Optional[Goal]:
        """
        指定IDの目標を取得する

        【引数】
        goal_id: 目標のID

        【戻り値】
        Goalオブジェクト or None
        """
        return (
            self.db.query(Goal)
            .filter(Goal.id == goal_id)
            .first()
        )

    def create_goal(self, goal_data: schemas.GoalCreate) -> Goal:
        """
        新しい目標を作成する

        【引数】
        goal_data: GoalCreateスキーマ（Pydanticモデル）

        【戻り値】
        作成されたGoalオブジェクト

        【model_dump()について】
        Pydantic v2での新しいメソッド名。
        （v1では .dict() だった）
        スキーマオブジェクトを辞書に変換する。

        【**（アンパック演算子）について】
        辞書を展開してキーワード引数として渡す。
        例: Goal(**{"title": "Python", "priority": "high"})
        　= Goal(title="Python", priority="high")
        """
        # Pydanticスキーマを辞書に変換し、DBモデルを作成
        goal = Goal(**goal_data.model_dump())
        self.db.add(goal)
        self.db.commit()
        self.db.refresh(goal)
        return goal

    def update_goal(self, goal_id: int, goal_data: schemas.GoalUpdate) -> Optional[Goal]:
        """
        目標を更新する

        【引数】
        goal_id: 更新対象の目標ID
        goal_data: GoalUpdateスキーマ

        【戻り値】
        更新されたGoalオブジェクト or None（見つからない場合）

        【exclude_unset=True について】
        model_dump()のオプション。
        明示的にセットされていないフィールドを除外する。

        例えば、goal_data が {"progress": 50} のみを含む場合、
        他のフィールド（title, descriptionなど）は更新されない。
        """
        # 更新対象を検索
        goal = self.get_goal(goal_id)
        if not goal:
            return None  # 見つからない場合はNone

        # 更新データを辞書として取得（未設定の値は除外）
        update_data = goal_data.model_dump(exclude_unset=True)

        # 各フィールドを更新
        for key, value in update_data.items():
            # setattr(obj, "attr", value) は obj.attr = value と同じ
            setattr(goal, key, value)

        self.db.commit()
        self.db.refresh(goal)
        return goal

    def delete_goal(self, goal_id: int) -> bool:
        """
        指定IDの目標を削除する

        【引数】
        goal_id: 削除する目標のID

        【戻り値】
        True: 削除成功
        False: 該当する目標が見つからなかった
        """
        deleted_count = (
            self.db.query(Goal)
            .filter(Goal.id == goal_id)
            .delete()
        )
        self.db.commit()
        return deleted_count > 0

    def delete_goals_batch(self, ids: List[int]) -> int:
        """
        複数の目標を一括削除する

        【引数】
        ids: 削除する目標IDのリスト

        【戻り値】
        削除された件数
        """
        deleted_count = (
            self.db.query(Goal)
            .filter(Goal.id.in_(ids))
            .delete(synchronize_session=False)
        )
        self.db.commit()
        return deleted_count


    # ==========================================================
    # システムコンテキスト構築
    # ==========================================================

    def construct_system_context(self) -> str:
        """
        LLMに渡すシステムコンテキストを構築する

        【役割】
        保存されているユーザー情報と目標をテキストにまとめ、
        LLMのシステムプロンプトに追加できる形式にする。

        【なぜ必要？】
        LLMは会話のたびに記憶がリセットされます。
        過去に学習した情報（名前、目標など）を覚えておくために、
        毎回システムプロンプトに「こういう情報があります」と伝えます。

        【戻り値】
        ユーザー情報と目標を含むテキスト

        【出力例】
        ## User Profile Information:
        - name: 田中太郎
        - hobby: プログラミング

        ## Current Goals:
        - Python学習 (Deadline: 2024-12-31): 基本文法をマスター
        """
        # プロフィールと目標を取得
        profiles = self.get_all_user_profiles()
        goals = self.get_active_goals()

        # コンテキストのパーツを格納するリスト
        context_parts = []

        # プロフィール情報を追加
        if profiles:
            context_parts.append("## User Profile Information:")
            for p in profiles:
                context_parts.append(f"- {p.key}: {p.value}")

        # 目標情報を追加
        if goals:
            context_parts.append("\n## Current Goals:")
            for g in goals:
                # 締め切りがある場合のみ表示
                deadline = f"(Deadline: {g.deadline})" if g.deadline else ""
                context_parts.append(f"- {g.title} {deadline}: {g.description or ''}")

        # リストを改行で結合して返す
        return "\n".join(context_parts)


    # ==========================================================
    # LLMからの抽出情報の保存
    # ==========================================================

    def save_extracted_information(self, extraction_result: dict):
        """
        LLMが抽出した情報をデータベースに保存する

        【引数】
        extraction_result: LLMが返した抽出結果（辞書）
            {
                "user_profile": [
                    {"key": "name", "value": "田中", "category": "personal"}
                ],
                "goals": [
                    {"title": "Python学習", "description": "..."}
                ]
            }

        【呼び出しタイミング】
        バックグラウンドタスクとして、ユーザーのメッセージを処理した後に実行。
        メインの応答を遅らせないように非同期で処理する。

        【.get()メソッドについて】
        辞書からキーを取得。キーが存在しない場合はデフォルト値（ここでは[]）を返す。
        extraction_result["user_profile"] だとキーがない場合にエラーになるが、
        extraction_result.get("user_profile", []) ならエラーにならない。
        """
        # ユーザープロフィールを保存
        for p in extraction_result.get("user_profile", []):
            self.update_user_profile(
                key=p.get("key"),
                value=p.get("value"),
                category=p.get("category")
            )
            # デバッグ用ログ出力
            print(f"Saved Profile: {p.get('key')} -> {p.get('value')}")

        # 目標を保存
        for g in extraction_result.get("goals", []):
            # 重複チェック: 同じタイトルでアクティブな目標があれば追加しない
            existing = (
                self.db.query(Goal)
                .filter(Goal.title == g.get("title"), Goal.status == 'active')
                .first()
            )
            if not existing:
                # 新しい目標を作成
                new_goal = Goal(
                    title=g.get("title"),
                    description=g.get("description"),
                    priority=g.get("priority"),
                    # TODO: deadline の文字列→Date変換が必要
                )
                self.db.add(new_goal)
                print(f"New Goal Created: {g.get('title')}")

        # 変更をコミット
        self.db.commit()


    # ==========================================================
    # 統計情報
    # ==========================================================

    def get_memory_stats(self) -> dict:
        """
        メモリの統計情報を取得する

        【戻り値】
        {
            "profile_count": プロフィール数,
            "goal_count": 目標の総数,
            "conversation_count": 会話履歴数,
            "active_goals": アクティブな目標数
        }

        【count()について】
        SQLのCOUNT関数に相当。レコード数を返す。
        """
        return {
            "profile_count": self.db.query(UserProfile).count(),
            "goal_count": self.db.query(Goal).count(),
            "conversation_count": self.db.query(Conversation).count(),
            "active_goals": self.db.query(Goal).filter(Goal.status == 'active').count()
        }
