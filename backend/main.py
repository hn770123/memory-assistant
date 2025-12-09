"""
Memory Assistant - Phase 1
シンプルなチャット機能のみ（Ollama連携）
"""
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
import ollama
from pathlib import Path

app = FastAPI(title="Memory Assistant", version="1.0.0")

# 静的ファイル配信
app.mount("/static", StaticFiles(directory="static"), name="static")


class ChatRequest(BaseModel):
    message: str
    model: str = "llama3.1:8b"


class ChatResponse(BaseModel):
    response: str
    model: str


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
        models = ollama.list()
        return {
            "status": "healthy",
            "ollama": "connected",
            "available_models": [m.get("name", m.get("model", "unknown")) for m in models.get("models", [])]
        }
    except Exception as e:
        return {
            "status": "degraded",
            "ollama": "disconnected",
            "error": str(e)
        }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    チャットエンドポイント
    Ollamaを使ってLLMと対話
    """
    try:
        # Ollamaでチャット
        response = ollama.chat(
            model=request.model,
            messages=[
                {
                    "role": "system",
                    "content": "あなたは親しみやすく、少し忘れっぽいAIアシスタントです。"
                },
                {
                    "role": "user",
                    "content": request.message
                }
            ]
        )

        assistant_message = response["message"]["content"]

        return ChatResponse(
            response=assistant_message,
            model=request.model
        )

    except ollama.ResponseError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Ollama error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


@app.get("/models")
async def list_models():
    """利用可能なモデル一覧"""
    try:
        models = ollama.list()
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
    print("🚀 Memory Assistant - Phase 1")
    print("📍 http://localhost:8000")
    print("💡 Ollama must be running: ollama serve")
    uvicorn.run(app, host="0.0.0.0", port=8000)
