
"""
Memory Assistant - Phase 2
記憶システムの実装
"""
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from pathlib import Path

from models.database import init_db, get_db, SessionLocal
from models import schemas
from services.llm_service import LLMService
from services.memory_service import MemoryService

app = FastAPI(title="Memory Assistant", version="2.0.0")

# 静的ファイル配信
app.mount("/static", StaticFiles(directory="static"), name="static")

# データベース初期化
init_db()

# Services initialization
llm_service = LLMService()

def process_information_extraction(user_message: str, db: Session):
    """
    Background task to extract and save information from the user message.
    Note: In a real app, we should probably handle DB session better for background tasks 
    (creating a new one instead of passing the dependency), but for simplicity...
    Wait, passing 'db' from Depends(get_db) to background task is risky because it might be closed.
    Let's create a new session here.
    """
    # Create a new session for the background task
    new_db = SessionLocal()
    try:
        print(f"Starting background extraction for: {user_message[:50]}...")
        memory_service = MemoryService(new_db)
        extraction_result = llm_service.extract_information(user_message)
        if extraction_result.get("user_profile") or extraction_result.get("goals"):
             print(f"Extracted info: {extraction_result}")
             memory_service.save_extracted_information(extraction_result)
        else:
             print("No info extracted.")
    except Exception as e:
        print(f"Background extraction failed: {e}")
    finally:
        new_db.close()

@app.get("/", response_class=HTMLResponse)
async def root():
    """ルートパスでindex.htmlを返す"""
    index_path = Path("static/index.html")
    if index_path.exists():
        return index_path.read_text(encoding="utf-8")
    return "<h1>Memory Assistant</h1><p>index.html が見つかりません</p>"

@app.get("/health")
async def health_check():
    """ヘルスチェック"""
    try:
        # Ollamaが動いているか確認
        models = llm_service.list_models()
        return {
            "status": "healthy",
            "phase": "2 (Memory System)",
            "ollama": "connected",
            "available_models": [m.get("name", m.get("model", "unknown")) for m in models.get("models", [])]
        }
    except Exception as e:
        return {
            "status": "degraded",
            "phase": "2 (Memory System)",
            "ollama": "disconnected",
            "error": str(e)
        }

@app.post("/chat", response_model=schemas.ChatResponse)
async def chat(request: schemas.ChatRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """
    チャットエンドポイント
    MemoryServiceを使って会話を記録し、LLMServiceで応答を生成
    """
    memory_service = MemoryService(db)
    
    try:
        # システムプロンプト作成 (記憶を注入)
        base_system_prompt = "あなたは親しみやすく、少し忘れっぽいAIアシスタントです。"
        memory_context = memory_service.construct_system_context()
        
        system_prompt = base_system_prompt
        if memory_context:
            system_prompt += f"\n\nHere is what you know about the user and their goals (use this to personalize your response):\n{memory_context}"
        
        # Ollamaでチャット
        assistant_message = llm_service.chat(
            message=request.message,
            model=request.model,
            system_prompt=system_prompt
        )

        # 会話を保存
        memory_service.save_conversation(
            user_message=request.message,
            assistant_message=assistant_message
        )

        # バックグラウンドで情報抽出を実行
        background_tasks.add_task(process_information_extraction, request.message, db)

        return schemas.ChatResponse(
            response=assistant_message,
            model=request.model
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error: {str(e)}"
        )

@app.get("/models")
async def list_models():
    """利用可能なモデル一覧"""
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

if __name__ == "__main__":
    import uvicorn
    # Windows compatible print (avoiding emoji for safety if console is not utf-8)
    print("Memory Assistant - Phase 2")
    print("http://localhost:8000")
    print("Ollama must be running: ollama serve")
    uvicorn.run(app, host="0.0.0.0", port=8000)
