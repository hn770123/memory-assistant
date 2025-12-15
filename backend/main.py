"""
==============================================================================
main.py - FastAPI アプリケーションのメインファイル
==============================================================================

【このファイルの役割】
Webアプリケーションのエントリーポイント（入口）です。
以下を定義しています：
1. FastAPIアプリケーションの作成
2. APIエンドポイント（URLとその処理）の定義
3. 静的ファイル（HTML、CSS、JS）の配信設定

【FastAPIとは？】
Python用の高速なWebフレームワークです。
特徴：
- 自動的にAPIドキュメント（Swagger UI）を生成
- 型ヒントを活用した自動バリデーション
- 非同期処理（async/await）のサポート
- 高いパフォーマンス

【APIエンドポイントとは？】
クライアント（ブラウザなど）がアクセスするURLのことです。
例：
- GET /health → ヘルスチェック
- POST /chat → チャット送信
- GET /api/profiles → プロフィール一覧取得

【HTTPメソッドの意味】
- GET: データを取得する（読み取り専用）
- POST: 新しいデータを作成する
- PUT: 既存のデータを更新する
- DELETE: データを削除する
==============================================================================
"""

# --------------------------------------------------
# 必要なライブラリのインポート
# --------------------------------------------------
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
# FastAPI: アプリケーション本体
# HTTPException: HTTPエラーを発生させる（404 Not Foundなど）
# Depends: 依存性注入（DBセッションを自動的に渡す仕組み）
# BackgroundTasks: バックグラウンドで処理を実行

from fastapi.staticfiles import StaticFiles  # 静的ファイル（HTML等）を配信
from fastapi.responses import HTMLResponse    # HTMLを返すレスポンス
from sqlalchemy.orm import Session            # DBセッションの型
from pathlib import Path                      # ファイルパス操作
from typing import List                       # 型ヒント

# ローカルモジュールのインポート
from models.database import init_db, get_db, SessionLocal
from models import schemas
from services.llm_service import LLMService
from services.memory_service import MemoryService


# ==================================================
# FastAPIアプリケーションの作成
# ==================================================

app = FastAPI(
    title="Memory Assistant",     # アプリケーション名
    version="2.0.0",              # バージョン
    description="記憶を持つAIアシスタント"  # 説明
)
# FastAPIインスタンスを作成
# この app オブジェクトに対してエンドポイントを追加していく


# ==================================================
# 静的ファイルの配信設定
# ==================================================

# /static というURLパスで、staticディレクトリ内のファイルを配信
# 例: /static/style.css → static/style.css ファイルを返す
app.mount("/static", StaticFiles(directory="static"), name="static")


# ==================================================
# 初期化処理
# ==================================================

# アプリケーション起動時にデータベースを初期化
# テーブルが存在しなければ作成する
init_db()

# LLMサービスのインスタンスを作成（グローバル変数）
# 全リクエストで共有するため、ここで1回だけ作成
llm_service = LLMService()


# ==================================================
# バックグラウンドタスク
# ==================================================

def process_information_extraction(user_message: str, db: Session):
    """
    ユーザーメッセージから情報を抽出するバックグラウンドタスク

    【バックグラウンドタスクとは？】
    メインの処理（チャット応答）を返した後に、
    裏で別の処理を実行する仕組みです。

    【なぜ必要？】
    情報抽出はLLMを使うため時間がかかります。
    ユーザーを待たせないよう、応答を先に返してから
    バックグラウンドで処理します。

    【引数】
    user_message: ユーザーのメッセージ
    db: 注意！Depends(get_db)で渡されたセッションは
        リクエスト終了後にクローズされるため使えない

    【重要な注意点】
    バックグラウンドタスクでは、新しいDBセッションを作成する必要があります。
    リクエスト時のセッション（Depends(get_db)）は、
    レスポンス返却後にクローズされてしまうためです。
    """
    # バックグラウンドタスク用に新しいセッションを作成
    new_db = SessionLocal()
    try:
        # デバッグログ（最初の50文字だけ表示）
        print(f"Starting background extraction for: {user_message[:50]}...")

        # メモリサービスを新しいセッションで初期化
        memory_service = MemoryService(new_db)

        # LLMで情報を抽出
        extraction_result = llm_service.extract_information(user_message)

        # 抽出結果があれば保存
        if extraction_result.get("user_profile") or extraction_result.get("goals"):
            print(f"Extracted info: {extraction_result}")
            memory_service.save_extracted_information(extraction_result)
        else:
            print("No info extracted.")

    except Exception as e:
        # エラーが発生してもアプリは停止しない（バックグラウンドなので）
        print(f"Background extraction failed: {e}")

    finally:
        # 必ずセッションをクローズ（リソースリークを防ぐ）
        new_db.close()


# ==================================================
# メインページエンドポイント
# ==================================================

@app.get("/", response_class=HTMLResponse)
async def root():
    """
    ルートパス（/）でチャットページを返す

    【デコレータについて】
    @app.get("/") は「GETリクエストで / にアクセスされたら
    この関数を実行する」という意味。

    【async def について】
    非同期関数を定義。FastAPIは非同期処理をサポートしており、
    I/O待ち（ファイル読み込み、DB接続など）の間に
    他のリクエストを処理できる。

    【response_class について】
    レスポンスの種類を指定。HTMLResponseはContent-Typeを
    text/html に設定してくれる。
    """
    # index.htmlファイルのパスを作成
    index_path = Path("static/index.html")

    # ファイルが存在すれば内容を返す
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")

    # ファイルがない場合のフォールバック
    return "<h1>Memory Assistant</h1><p>index.html が見つかりません</p>"


@app.get("/memory", response_class=HTMLResponse)
async def memory_page():
    """
    メモリ管理ページを返す

    【用途】
    記憶システムに保存されている情報を確認・管理するためのページ。
    - プロフィール一覧
    - 目標一覧
    - 会話履歴
    の確認、追加、更新、削除ができる。
    """
    memory_path = Path("static/memory.html")

    if memory_path.exists():
        return memory_path.read_text(encoding="utf-8")

    return "<h1>Memory Management</h1><p>memory.html が見つかりません</p>"


# ==================================================
# ヘルスチェックエンドポイント
# ==================================================

@app.get("/health")
async def health_check():
    """
    アプリケーションの状態をチェックする

    【ヘルスチェックとは？】
    システムが正常に動作しているか確認するためのエンドポイント。
    監視ツールやロードバランサーがこのURLを定期的に叩いて
    システムの稼働状況を確認します。

    【戻り値の例】
    正常時:
    {
        "status": "healthy",
        "phase": "2 (Memory System)",
        "ollama": "connected",
        "available_models": ["llama3.1:8b"]
    }

    異常時:
    {
        "status": "degraded",
        "phase": "2 (Memory System)",
        "ollama": "disconnected",
        "error": "Connection refused"
    }
    """
    try:
        # Ollamaに接続してモデル一覧を取得
        models = llm_service.list_models()
        return {
            "status": "healthy",
            "phase": "2 (Memory System)",
            "ollama": "connected",
            "available_models": [
                m.get("name", m.get("model", "unknown"))
                for m in models.get("models", [])
            ]
        }
    except Exception as e:
        # Ollama接続に失敗した場合
        return {
            "status": "degraded",
            "phase": "2 (Memory System)",
            "ollama": "disconnected",
            "error": str(e)
        }


# ==================================================
# チャットエンドポイント
# ==================================================

@app.post("/chat", response_model=schemas.ChatResponse)
async def chat(
    request: schemas.ChatRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    チャットメッセージを処理して応答を返す

    【処理フロー】
    1. ユーザーメッセージを受け取る
    2. 保存されている記憶（プロフィール、目標）を取得
    3. 記憶をシステムプロンプトに注入
    4. LLMで応答を生成
    5. 会話をDBに保存
    6. バックグラウンドで情報抽出を開始
    7. 応答を返す

    【引数の説明】
    request: リクエストボディ（ChatRequestスキーマ）
             FastAPIが自動的にJSONをパースしてオブジェクト化

    background_tasks: バックグラウンドタスクマネージャー
                     FastAPIが自動的に注入

    db: データベースセッション
        Depends(get_db) で自動的に作成・注入される

    【Depends()について】
    依存性注入（DI: Dependency Injection）の仕組み。
    関数の実行前に必要なオブジェクト（ここではDBセッション）を
    自動的に作成して渡してくれる。
    関数終了後は自動的にクリーンアップされる。
    """
    # メモリサービスのインスタンスを作成
    memory_service = MemoryService(db)

    try:
        # -----------------------------------------------
        # システムプロンプトの構築
        # -----------------------------------------------

        # 基本のキャラクター設定
        base_system_prompt = "あなたは親しみやすく、少し忘れっぽいAIアシスタントです。"

        # 保存されているユーザー情報と目標を取得
        memory_context = memory_service.construct_system_context()

        # システムプロンプトに記憶情報を追加
        system_prompt = base_system_prompt
        if memory_context:
            system_prompt += f"""

Here is what you know about the user and their goals (use this to personalize your response):
{memory_context}"""

        # -----------------------------------------------
        # LLMで応答を生成
        # -----------------------------------------------

        assistant_message = llm_service.chat(
            message=request.message,
            model=request.model,
            system_prompt=system_prompt
        )

        # -----------------------------------------------
        # 会話を保存
        # -----------------------------------------------

        memory_service.save_conversation(
            user_message=request.message,
            assistant_message=assistant_message
        )

        # -----------------------------------------------
        # バックグラウンドで情報抽出を実行
        # -----------------------------------------------

        # add_taskで関数と引数を登録
        # レスポンス返却後に自動的に実行される
        background_tasks.add_task(
            process_information_extraction,
            request.message,
            db
        )

        # -----------------------------------------------
        # レスポンスを返す
        # -----------------------------------------------

        return schemas.ChatResponse(
            response=assistant_message,
            model=request.model
        )

    except Exception as e:
        # エラー発生時は500エラーを返す
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )


# ==================================================
# モデル一覧エンドポイント
# ==================================================

@app.get("/models")
async def list_models():
    """
    利用可能なLLMモデルの一覧を返す

    【用途】
    フロントエンドでモデル選択UIを作る際に使用。
    Ollamaにインストールされているモデルの一覧を返す。
    """
    try:
        models = llm_service.list_models()
        return {
            "models": [
                {
                    "name": m.get("name", m.get("model", "unknown")),
                    "size": m.get("size", 0),
                    "modified_at": m.get("modified_at", "")
                }
                for m in models.get("models", [])
            ]
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list models: {str(e)}"
        )


# ==================================================
# メモリ管理API - 統計情報
# ==================================================

@app.get("/api/memory/stats", response_model=schemas.MemoryStats)
async def get_memory_stats(db: Session = Depends(get_db)):
    """
    メモリの統計情報を取得する

    【戻り値】
    - profile_count: 保存されているプロフィール数
    - goal_count: 目標の総数
    - conversation_count: 会話履歴数
    - active_goals: アクティブな目標数
    """
    memory_service = MemoryService(db)
    return memory_service.get_memory_stats()


# ==================================================
# メモリ管理API - プロフィール（ユーザー情報）
# ==================================================

@app.get("/api/profiles", response_model=List[schemas.UserProfile])
async def get_profiles(db: Session = Depends(get_db)):
    """
    すべてのプロフィールを取得する

    【戻り値の例】
    [
        {"key": "name", "value": "田中太郎", "category": "personal", "updated_at": "..."},
        {"key": "hobby", "value": "プログラミング", "category": "preference", "updated_at": "..."}
    ]

    【response_model について】
    List[schemas.UserProfile] は「UserProfileのリストを返す」という意味。
    FastAPIはこの情報を使って:
    1. レスポンスデータを自動的にバリデーション
    2. APIドキュメントを生成
    """
    memory_service = MemoryService(db)
    return memory_service.get_all_user_profiles()


@app.post("/api/profiles", response_model=schemas.UserProfile)
async def create_profile(
    profile: schemas.UserProfileCreate,
    db: Session = Depends(get_db)
):
    """
    新しいプロフィールを作成する

    【リクエストボディの例】
    {
        "key": "favorite_food",
        "value": "ラーメン",
        "category": "preference"
    }

    【注意】
    同じキーが既に存在する場合は上書きされる（Upsert動作）
    """
    memory_service = MemoryService(db)
    return memory_service.update_user_profile(
        key=profile.key,
        value=profile.value,
        category=profile.category
    )


@app.put("/api/profiles/{key}", response_model=schemas.UserProfile)
async def update_profile(
    key: str,
    profile: schemas.UserProfileUpdate,
    db: Session = Depends(get_db)
):
    """
    指定キーのプロフィールを更新する

    【パスパラメータについて】
    {key} の部分はURLの一部として指定される。
    例: PUT /api/profiles/name → key = "name"

    【リクエストボディの例】
    {
        "value": "新しい値",
        "category": "new_category"
    }
    """
    memory_service = MemoryService(db)

    # 既存のプロフィールを取得
    existing = memory_service.get_user_profile(key)
    if not existing:
        # 見つからない場合は404エラー
        raise HTTPException(status_code=404, detail=f"Profile '{key}' not found")

    # 更新値を決定（指定されていればその値、なければ既存の値を維持）
    new_value = profile.value if profile.value is not None else existing.value
    new_category = profile.category if profile.category is not None else existing.category

    return memory_service.update_user_profile(
        key=key,
        value=new_value,
        category=new_category
    )


@app.delete("/api/profiles/{key}")
async def delete_profile(key: str, db: Session = Depends(get_db)):
    """
    指定キーのプロフィールを削除する

    【戻り値】
    {"deleted": true} または 404エラー
    """
    memory_service = MemoryService(db)
    if memory_service.delete_user_profile(key):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail=f"Profile '{key}' not found")


@app.post("/api/profiles/batch-delete")
async def delete_profiles_batch(
    request: schemas.DeleteRequest,
    db: Session = Depends(get_db)
):
    """
    複数のプロフィールを一括削除する

    【リクエストボディの例】
    {
        "keys": ["old_info", "temp_data", "test"]
    }

    【戻り値】
    {"deleted_count": 3}
    """
    memory_service = MemoryService(db)
    deleted_count = memory_service.delete_profiles_batch(request.keys)
    return {"deleted_count": deleted_count}


# ==================================================
# メモリ管理API - 目標
# ==================================================

@app.get("/api/goals", response_model=List[schemas.Goal])
async def get_goals(db: Session = Depends(get_db)):
    """
    すべての目標を取得する
    """
    memory_service = MemoryService(db)
    return memory_service.get_all_goals()


@app.get("/api/goals/{goal_id}", response_model=schemas.Goal)
async def get_goal(goal_id: int, db: Session = Depends(get_db)):
    """
    指定IDの目標を取得する

    【パスパラメータについて】
    goal_id: int と型指定することで、
    FastAPIが自動的に文字列を整数に変換してくれる。
    変換できない場合は422エラーが自動的に返される。
    """
    memory_service = MemoryService(db)
    goal = memory_service.get_goal(goal_id)
    if not goal:
        raise HTTPException(status_code=404, detail="Goal not found")
    return goal


@app.post("/api/goals", response_model=schemas.Goal)
async def create_goal(
    goal: schemas.GoalCreate,
    db: Session = Depends(get_db)
):
    """
    新しい目標を作成する

    【リクエストボディの例】
    {
        "title": "Pythonをマスターする",
        "description": "基本文法からWebアプリまで",
        "priority": "high",
        "deadline": "2024-12-31T00:00:00"
    }
    """
    memory_service = MemoryService(db)
    return memory_service.create_goal(goal)


@app.put("/api/goals/{goal_id}", response_model=schemas.Goal)
async def update_goal(
    goal_id: int,
    goal: schemas.GoalUpdate,
    db: Session = Depends(get_db)
):
    """
    指定IDの目標を更新する

    【部分更新について】
    更新したいフィールドだけを送ればOK。
    送らないフィールドは現在の値が維持される。

    【リクエストボディの例】
    {
        "progress": 50,
        "status": "active"
    }
    """
    memory_service = MemoryService(db)
    updated = memory_service.update_goal(goal_id, goal)
    if not updated:
        raise HTTPException(status_code=404, detail="Goal not found")
    return updated


@app.delete("/api/goals/{goal_id}")
async def delete_goal(goal_id: int, db: Session = Depends(get_db)):
    """
    指定IDの目標を削除する
    """
    memory_service = MemoryService(db)
    if memory_service.delete_goal(goal_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Goal not found")


@app.post("/api/goals/batch-delete")
async def delete_goals_batch(
    request: schemas.DeleteIdsRequest,
    db: Session = Depends(get_db)
):
    """
    複数の目標を一括削除する

    【リクエストボディの例】
    {
        "ids": [1, 3, 5]
    }
    """
    memory_service = MemoryService(db)
    deleted_count = memory_service.delete_goals_batch(request.ids)
    return {"deleted_count": deleted_count}


# ==================================================
# メモリ管理API - 会話履歴
# ==================================================

@app.get("/api/conversations", response_model=List[schemas.Conversation])
async def get_conversations(db: Session = Depends(get_db)):
    """
    すべての会話履歴を取得する

    【注意】
    会話数が多い場合、レスポンスが大きくなる可能性がある。
    実運用ではページネーションを実装することを推奨。
    """
    memory_service = MemoryService(db)
    return memory_service.get_all_conversations()


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: int,
    db: Session = Depends(get_db)
):
    """
    指定IDの会話を削除する
    """
    memory_service = MemoryService(db)
    if memory_service.delete_conversation(conversation_id):
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Conversation not found")


@app.post("/api/conversations/batch-delete")
async def delete_conversations_batch(
    request: schemas.DeleteIdsRequest,
    db: Session = Depends(get_db)
):
    """
    複数の会話を一括削除する
    """
    memory_service = MemoryService(db)
    deleted_count = memory_service.delete_conversations_batch(request.ids)
    return {"deleted_count": deleted_count}


# ==================================================
# アプリケーション起動
# ==================================================

if __name__ == "__main__":
    """
    このファイルが直接実行された場合にサーバーを起動する

    【__name__ == "__main__" とは？】
    Pythonでは、ファイルが直接実行された場合、__name__ は "__main__" になる。
    importされた場合は、モジュール名になる。

    この条件分岐により：
    - python main.py で実行 → サーバー起動
    - from main import app でインポート → サーバーは起動しない

    【uvicornについて】
    ASGIサーバー。FastAPIアプリケーションを実行するために必要。
    host="0.0.0.0" は全てのネットワークインターフェースで待ち受ける。
    port=8000 はポート番号。
    """
    import uvicorn

    # 起動メッセージ
    print("Memory Assistant - Phase 2")
    print("http://localhost:8000")
    print("メモリ管理ページ: http://localhost:8000/memory")
    print("Ollama must be running: ollama serve")

    # サーバー起動
    uvicorn.run(app, host="0.0.0.0", port=8000)
