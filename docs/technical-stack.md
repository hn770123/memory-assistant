# 人間的記憶システムを持つAIアシスタント

## 完全な技術スタックと実装ガイド

-----

## 📋 システム全体像

```
┌─────────────────────────────────────────────┐
│          フロントエンド (UI)                │
│    Electron + React + Tailwind CSS          │
└──────────────────┬──────────────────────────┘
                   │ IPC通信
┌──────────────────▼──────────────────────────┐
│        バックエンド (Python)                │
│            FastAPI                          │
├─────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐        │
│  │ LLM Engine   │  │ Memory System│        │
│  │  (Ollama)    │  │              │        │
│  └──────────────┘  └──────────────┘        │
│  ┌──────────────┐  ┌──────────────┐        │
│  │ Whisper      │  │ Database     │        │
│  │ (音声認識)    │  │  (SQLite)    │        │
│  └──────────────┘  └──────────────┘        │
└─────────────────────────────────────────────┘
```

-----

## 🛠️ 技術スタック詳細

### **1. LLM実行環境**

**Ollama** (推奨)

```bash
# インストール
curl -fsSL https://ollama.com/install.sh | sh

# モデルのダウンロード
ollama pull llama3.1:8b-instruct-q5_K_M  # 5GB, 推奨
ollama pull mistral:7b-instruct-q5_K_M   # 代替案
```

**推奨モデル:**

- `llama3.1:8b` - バランス型、日本語対応良好
- `mistral:7b` - 高速、英語強い
- `gemma2:9b` - Google製、品質高い

**量子化レベル:**

- `q5_K_M` - 品質と速度のバランス (推奨)
- `q4_K_M` - より高速だが品質やや低下
- `q8_0` - 最高品質だがVRAM多く必要

-----

### **2. バックエンド構成**

**Python 3.10+ 環境**

```bash
# 必要なパッケージ
pip install fastapi==0.104.1
pip install uvicorn[standard]==0.24.0
pip install ollama==0.1.7
pip install sqlalchemy==2.0.23
pip install pydantic==2.5.0
pip install python-multipart==0.0.6
pip install openai-whisper==20231117  # 音声認識
pip install sentence-transformers==2.2.2  # 将来のRAG用
```

**requirements.txt:**

```txt
fastapi==0.104.1
uvicorn[standard]==0.24.0
ollama==0.1.7
sqlalchemy==2.0.23
pydantic==2.5.0
python-multipart==0.0.6
openai-whisper==20231117
sentence-transformers==2.2.2
torch==2.1.0
```

-----

### **3. データベース設計**

**SQLite** (シンプル、十分高速)

```sql
-- ユーザープロフィール（意味記憶）
CREATE TABLE user_profile (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    category TEXT,  -- 'personality', 'skill', 'preference'
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 目標管理
CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    deadline DATE,
    priority TEXT CHECK(priority IN ('low', 'medium', 'high')),
    status TEXT DEFAULT 'active',  -- 'active', 'completed', 'archived'
    progress INTEGER DEFAULT 0,  -- 0-100
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- エピソード記憶（圧縮済み要約）
CREATE TABLE episodic_memory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date DATE NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    key_events TEXT,  -- JSON形式
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会話履歴（短期、定期的に圧縮）
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_message TEXT NOT NULL,
    assistant_message TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    consolidated BOOLEAN DEFAULT FALSE,  -- 記憶固定化済みか
    importance_score REAL  -- 0.0-1.0
);

-- リマインダー
CREATE TABLE reminders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,
    remind_at TIMESTAMP NOT NULL,
    recurrence TEXT,  -- 'daily', 'weekly', 'monthly', null
    status TEXT DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

-----

### **4. フロントエンド構成**

**Electron + React**

```bash
# プロジェクト作成
npx create-react-app assistant-app
cd assistant-app
npm install electron electron-builder
npm install axios
npm install tailwindcss postcss autoprefixer
npx tailwindcss Linit
```

**主要ライブラリ:**

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "electron": "^27.0.0",
    "axios": "^1.6.0",
    "tailwindcss": "^3.3.0",
    "date-fns": "^2.30.0"
  }
}
```

**代替案（よりシンプル）:**

- **Tauri + React** - より軽量、Rust製
- **Web版のみ** - Next.js + Tailwind

-----

### **5. 音声認識**

**Whisper (OpenAI)**

```python
import whisper

# モデルロード（初回のみダウンロード）
model = whisper.load_model("base")  # tiny, base, small, medium, large

# 音声認識
result = model.transcribe("audio.mp3", language="ja")
text = result["text"]
```

**モデルサイズ選択:**

- `tiny` - 75MB, 高速、精度やや低
- `base` - 142MB, バランス型 (推奨)
- `small` - 466MB, 高精度
- `medium` - 1.5GB, さらに高精度
- `large` - 3GB, 最高精度

**リアルタイム音声入力:**

```bash
# faster-whisper（高速版）
pip install faster-whisper==0.10.0
```

-----

## 🏗️ プロジェクト構造

```
assistant-app/
├── backend/
│   ├── main.py              # FastAPI エントリーポイント
│   ├── models/
│   │   ├── database.py      # SQLAlchemy モデル
│   │   └── schemas.py       # Pydantic スキーマ
│   ├── services/
│   │   ├── llm_service.py   # Ollama連携
│   │   ├── memory_service.py  # 記憶管理
│   │   ├── whisper_service.py # 音声認識
│   │   └── consolidation.py   # 記憶固定化
│   ├── database.db          # SQLiteファイル
│   └── requirements.txt
│
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── GoalPanel.jsx
│   │   │   ├── VoiceInput.jsx
│   │   │   └── MemoryView.jsx
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── electron.js          # Electronメイン
│   └── package.json
│
└── README.md
```

-----

## 🚀 開発フェーズ

### **Phase 1: 基礎構築 (1-2週間)**

**目標:** 基本的なチャット機能

**実装内容:**

1. Ollamaセットアップ
1. FastAPI基本構造
1. シンプルなReactチャットUI
1. Ollama連携

**成果物:**

- ローカルLLMとチャットできる

-----

### **Phase 2: 記憶システム (2-3週間)**

**目標:** 人間的記憶システムの実装

**実装内容:**

1. データベーススキーマ実装
1. 会話からの情報抽出機能
1. 構造化記憶の保存
1. 記憶を活用した応答生成

**成果物:**

- 目標、個人情報を記憶
- 過去の情報を活用した応答

-----

### **Phase 3: 記憶固定化 (1-2週間)**

**目標:** 人間の睡眠時記憶整理を模倣

**実装内容:**

1. バッチ処理システム
1. 会話の要約生成
1. エピソード記憶への変換
1. 古い会話の圧縮・削除

**成果物:**

- 定期的な記憶整理
- 長期的な記憶管理

-----

### **Phase 4: 音声機能 (1-2週間)**

**目標:** 音声入出力

**実装内容:**

1. Whisper統合
1. 音声入力UI
1. マイク権限管理
1. (オプション) 音声合成

**成果物:**

- 音声でチャット可能

-----

### **Phase 5: 高度な機能 (継続的)**

**実装内容:**

- リマインダー機能
- スケジュール連携
- UI/UX改善
- パフォーマンス最適化
- (将来) RAGシステム追加

-----

## 💡 重要な設計判断

### **RAGは後回し**

- 最初は構造化DBのみ
- 必要性を感じたら追加
- Chroma or Qdrantを検討

### **記憶の圧縮タイミング**

```python
# オプション1: 定期バッチ（深夜実行）
# - 毎日深夜2時に記憶固定化
# - 人間の睡眠サイクルを模倣

# オプション2: セッション終了時
# - チャット終了時に処理
# - よりリアルタイム

# オプション3: 閾値ベース
# - 会話が50ターンに達したら
# - メモリ効率重視
```

### **モデル選択**

```
開発初期: llama3.1:8b-q4_K_M (高速)
     ↓
本番使用: llama3.1:8b-q5_K_M (品質重視)
     ↓
将来的: 13Bモデルも検討
```

-----

## 📊 システム要件

### **最小要件**

- CPU: 4コア以上
- RAM: 16GB
- GPU: RTX 3070 Ti (8GB VRAM) ✅
- ストレージ: 10GB以上

### **推奨環境**

- OS: Windows 11 / macOS / Linux
- Python: 3.10+
- Node.js: 18+
- CUDA: 12.0+ (NVIDIA GPU用)

-----

## 🔒 セキュリティ・プライバシー

**完全ローカル実行:**

- データは全てローカルに保存
- インターネット不要（モデルDL後）
- プライバシー完全保護

**データ暗号化（オプション）:**

```bash
pip install cryptography
```

**バックアップ:**

```bash
# 定期的にDBをバックアップ
cp backend/database.db backups/database_$(date +%Y%m%d).db
```

-----

## 次のステップ

1. **環境構築**: Ollama + Python環境
1. **Phase 1開始**: 基本チャット機能
1. **動作確認**: ローカルLLMとの対話
1. **Phase 2移行**: 記憶システム実装

具体的なコード実装が必要であれば、どのフェーズから始めたいか教えてください！
