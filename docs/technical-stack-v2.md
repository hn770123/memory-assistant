# 人間的記憶システムを持つAIアシスタント v2

## 完全な技術スタックと実装ガイド（MCP統合版）

---

## 目的

ローカルで動作するLLMを活用した、人間的な記憶システムを持つAIアシスタントを構築する。
ユーザーとの会話から重要な情報を自律的に記憶し、長期的な関係性を構築できるシステムを目指す。

---

## 設計思想

### 従来の課題

1. **記憶の過剰読み込み**: 毎回全ての記憶をコンテキストに含めると、トークン消費が増大
2. **単純な記憶判定**: 文字列マッチングでは記憶すべき内容を正確に判定できない
3. **コンテキスト肥大化**: 長い会話履歴がコンテキストを圧迫

### v2での解決策

1. **MCPによるオンデマンドアクセス**: LLMが必要な時に必要な記憶だけをDBから取得
2. **LLMによる記憶判定**: 記憶すべき内容をLLM自身が判定・抽出
3. **会話区切り機能**: 画面には履歴を残しつつ、コンテキストは区切りでリセット

---

## システム全体像

```
┌─────────────────────────────────────────────────────────────┐
│                フロントエンド (UI)                          │
│           Electron + React + Tailwind CSS                   │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 会話履歴表示（区切り線で視覚的に分離）                │  │
│  │ ───────────── 区切り ─────────────                   │  │
│  │ （区切り以前の履歴は表示されるがLLMに送信されない）   │  │
│  └──────────────────────────────────────────────────────┘  │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP (REST API)
┌──────────────────────▼──────────────────────────────────────┐
│                  バックエンド (Python)                       │
│                       FastAPI                                │
├──────────────────────────────────────────────────────────────┤
│  ┌────────────────┐     ┌─────────────────────────────────┐ │
│  │  Chat Handler  │────▶│  Memory Extraction Service      │ │
│  │                │     │  (LLMで記憶すべき内容を判定)    │ │
│  └───────┬────────┘     └──────────────┬──────────────────┘ │
│          │                             │                     │
│          ▼                             ▼                     │
│  ┌────────────────┐     ┌─────────────────────────────────┐ │
│  │  LLM Service   │     │       MCP Server                │ │
│  │   (Ollama)     │◀───▶│  (DB操作をLLMに公開)            │ │
│  └────────────────┘     └──────────────┬──────────────────┘ │
│                                        │                     │
│                         ┌──────────────▼──────────────────┐ │
│                         │        SQLite Database          │ │
│                         │  (memories, goals, profiles)    │ │
│                         └─────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## MCPサーバー設計

### MCPとは

Model Context Protocol (MCP) は、LLMに外部ツールやデータソースへのアクセスを提供する標準プロトコル。
LLMが必要に応じてDBを検索・操作できるようになる。

### 公開するTools

```yaml
memory_search:
  description: "記憶を検索する"
  parameters:
    query: string      # 検索キーワードまたは自然言語クエリ
    category: string?  # personality, preference, fact, goal など
    limit: integer?    # 取得件数（デフォルト: 5）
  returns:
    memories: array    # マッチした記憶のリスト

memory_store:
  description: "新しい記憶を保存する"
  parameters:
    content: string    # 記憶する内容
    category: string   # カテゴリ
    importance: float? # 重要度 0.0-1.0
  returns:
    success: boolean
    memory_id: integer

goal_list:
  description: "ユーザーの目標一覧を取得する"
  parameters:
    status: string?    # active, completed, all
  returns:
    goals: array

goal_update:
  description: "目標の進捗を更新する"
  parameters:
    goal_id: integer
    progress: integer? # 0-100
    status: string?    # active, completed
  returns:
    success: boolean

user_profile_get:
  description: "ユーザープロフィールを取得する"
  parameters:
    keys: array?       # 特定のキーのみ取得（省略時は全て）
  returns:
    profile: object
```

### MCPサーバー実装構成

```
backend/
├── mcp_server/
│   ├── __init__.py
│   ├── server.py          # MCPサーバーメイン
│   ├── tools/
│   │   ├── memory_tools.py   # 記憶関連ツール
│   │   ├── goal_tools.py     # 目標関連ツール
│   │   └── profile_tools.py  # プロフィール関連ツール
│   └── database.py        # DB接続
```

---

## 会話フロー設計

### 基本フロー

```
┌──────────────────────────────────────────────────────────────────┐
│  1. ユーザー入力を受信                                          │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  2. LLMに入力を送信（MCPツール利用可能）                        │
│     - LLMは必要に応じてmemory_searchでコンテキストを取得        │
│     - ユーザーへの応答を生成                                     │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  3. 記憶抽出LLM呼び出し                                         │
│     - 会話内容から記憶すべき情報を判定                           │
│     - 構造化された形式で抽出                                     │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  4. 記憶すべき内容がある場合                                     │
│     ├─ DBに保存                                                  │
│     └─ 会話区切りを挿入（新しいコンテキスト開始）               │
└─────────────────────────────┬────────────────────────────────────┘
                              ▼
┌──────────────────────────────────────────────────────────────────┐
│  5. 応答をユーザーに返却                                         │
└──────────────────────────────────────────────────────────────────┘
```

### 記憶判定プロンプト例

```
以下の会話から、長期的に記憶すべき情報を抽出してください。

【会話】
ユーザー: 来月から新しい職場で働くことになりました。プログラマーとして転職します。
アシスタント: おめでとうございます！新しい環境でのスタート、応援しています。

【抽出形式】
記憶すべき情報がある場合はJSON形式で出力してください：
{
  "memories": [
    {
      "content": "記憶する内容",
      "category": "fact|preference|goal|personality",
      "importance": 0.0-1.0
    }
  ]
}

記憶すべき情報がない場合は空配列を返してください：
{"memories": []}
```

---

## 会話区切り機能

### 目的

- 会話履歴の肥大化によるコンテキスト消費を防ぐ
- 画面上は履歴を残し、ユーザー体験を損なわない
- 記憶に保存された情報はMCP経由でいつでも参照可能

### 区切りのタイミング

1. **記憶保存時**: 重要な情報がDBに保存された後
2. **明示的な指示**: ユーザーが「新しい話題」等を指示した場合
3. **トークン閾値**: コンテキストが一定量を超えた場合

### 実装イメージ

```typescript
// フロントエンド: メッセージ配列の構造
interface Message {
  id: string;
  role: 'user' | 'assistant' | 'separator';
  content: string;
  timestamp: Date;
  includedInContext: boolean;  // LLMに送信するかどうか
}

// 区切り挿入
function insertSeparator(messages: Message[]): Message[] {
  // 既存メッセージのincludedInContextをfalseに
  const updated = messages.map(m => ({...m, includedInContext: false}));

  // 区切り線を追加
  updated.push({
    id: generateId(),
    role: 'separator',
    content: '--- 新しい会話 ---',
    timestamp: new Date(),
    includedInContext: false
  });

  return updated;
}
```

---

## データベース設計

### テーブル構成

```sql
-- 記憶テーブル（意味記憶・事実記憶を統合）
CREATE TABLE memories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    content TEXT NOT NULL,           -- 記憶内容
    category TEXT NOT NULL,          -- fact, preference, personality, skill
    importance REAL DEFAULT 0.5,     -- 重要度 0.0-1.0
    access_count INTEGER DEFAULT 0,  -- 参照回数（重要度調整に使用）
    last_accessed_at TIMESTAMP,      -- 最終参照日時
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 全文検索用インデックス
CREATE VIRTUAL TABLE memories_fts USING fts5(content, category);

-- 目標テーブル
CREATE TABLE goals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    deadline DATE,
    priority TEXT CHECK(priority IN ('low', 'medium', 'high')),
    status TEXT DEFAULT 'active',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ユーザープロフィール
CREATE TABLE user_profile (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 会話セッション（区切り単位）
CREATE TABLE conversation_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP,
    summary TEXT                     -- セッション要約（将来の圧縮用）
);

-- 会話ログ（UI表示用・参照用）
CREATE TABLE conversation_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER REFERENCES conversation_sessions(id),
    role TEXT NOT NULL,              -- user, assistant
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 技術スタック

### バックエンド

| 項目 | 技術 | 備考 |
|------|------|------|
| 言語 | Python 3.10+ | |
| フレームワーク | FastAPI | 非同期対応 |
| LLM | Ollama | ローカル実行 |
| MCP | mcp (Python SDK) | Anthropic公式 |
| DB | SQLite | シンプル・軽量 |
| ORM | SQLAlchemy 2.0 | |

### フロントエンド

| 項目 | 技術 | 備考 |
|------|------|------|
| フレームワーク | React 18 | |
| デスクトップ | Electron | |
| スタイリング | Tailwind CSS | |
| HTTP | axios | |

### 推奨LLMモデル

| 用途 | モデル | 備考 |
|------|--------|------|
| メイン会話 | llama3.1:8b-instruct-q5_K_M | バランス型 |
| 記憶抽出 | llama3.1:8b-instruct-q4_K_M | 高速版でも可 |
| 将来の圧縮 | 同上 | |

---

## プロジェクト構造

```
memory-assistant/
├── backend/
│   ├── main.py                 # FastAPIエントリーポイント
│   ├── config.py               # 設定
│   ├── models/
│   │   ├── database.py         # SQLAlchemyモデル
│   │   └── schemas.py          # Pydanticスキーマ
│   ├── services/
│   │   ├── llm_service.py      # Ollama連携
│   │   └── memory_extraction.py # 記憶抽出サービス
│   ├── mcp_server/
│   │   ├── server.py           # MCPサーバー
│   │   └── tools/              # MCPツール群
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ChatInterface.tsx
│   │   │   ├── MessageList.tsx
│   │   │   ├── Separator.tsx   # 区切り表示
│   │   │   └── MemoryPanel.tsx
│   │   ├── hooks/
│   │   │   └── useChat.ts      # 会話管理
│   │   ├── services/
│   │   │   └── api.ts
│   │   └── App.tsx
│   ├── electron/
│   │   └── main.ts
│   └── package.json
│
├── docs/
│   ├── technical-stack.md      # 旧設計書
│   └── technical-stack-v2.md   # 本ドキュメント
│
└── README.md
```

---

## 開発フェーズ

### Phase 1: MCPサーバー構築

**目標**: LLMからDBを操作できる基盤を構築

**タスク**:
1. MCPサーバーの基本構造作成
2. memory_search / memory_store ツール実装
3. goal_list / goal_update ツール実装
4. user_profile_get ツール実装
5. Ollamaとの連携確認

**成果物**:
- LLMがMCP経由でDBを読み書きできる

---

### Phase 2: 記憶抽出サービス

**目標**: 会話から記憶すべき内容をLLMで判定・抽出

**タスク**:
1. 記憶抽出用プロンプトの設計
2. 抽出サービスの実装
3. 抽出結果のDB保存処理
4. カテゴリ分類ロジック

**成果物**:
- 会話内容から自動で記憶を抽出・保存

---

### Phase 3: 会話区切り機能

**目標**: コンテキスト管理と履歴表示の分離

**タスク**:
1. セッション管理の実装
2. 区切り挿入ロジック
3. フロントエンドでの区切り表示
4. コンテキスト送信のフィルタリング

**成果物**:
- 画面には履歴が残るがコンテキストは区切られる

---

### Phase 4: 統合・最適化

**目標**: 全体の統合とユーザー体験の向上

**タスク**:
1. メイン会話フローの統合
2. エラーハンドリング強化
3. パフォーマンスチューニング
4. UI/UX改善

**成果物**:
- 完全に動作する記憶システム

---

### Phase 5: 記憶圧縮（将来）

**目標**: 長期記憶の効率的な管理

**タスク**:
1. 類似記憶の統合
2. 古い記憶の要約・圧縮
3. 重要度に基づく記憶の整理
4. セッション要約の生成

**成果物**:
- 記憶の自動整理・圧縮

---

## システムプロンプト設計

### メイン会話用

```
あなたはユーザーの個人アシスタントです。

ユーザーについて知りたいことがある場合は、memory_search ツールを使って記憶を検索してください。
ユーザーの目標を確認したい場合は、goal_list ツールを使ってください。

応答は簡潔かつ親しみやすくしてください。
```

**注意**: 「忘れっぽい」等のキャラクター設定はシステムプロンプトに含めない。
記憶管理はMCPツールで行うため、LLMの振る舞いとしての記憶制限は不要。

---

## セキュリティ・プライバシー

- 全てローカルで実行
- インターネット接続不要（モデルダウンロード後）
- 記憶データはローカルSQLiteに保存
- 外部サービスへのデータ送信なし

---

## システム要件

### 最小要件

- CPU: 4コア以上
- RAM: 16GB
- GPU: 8GB VRAM以上（推奨）
- ストレージ: 10GB以上

### 推奨環境

- Python 3.10+
- Node.js 18+
- Ollama最新版
- CUDA 12.0+（NVIDIA GPU使用時）
