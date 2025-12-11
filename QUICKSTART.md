# 🚀 Phase 1 クイックスタート

5ファイルで動くシンプルなチャットアシスタント

## 📦 ファイル構成

```
memory-assistant/
├── backend/
│   ├── main.py              # FastAPIサーバー
│   ├── requirements.txt     # Python依存関係
│   └── static/
│       └── index.html       # チャットUI
├── QUICKSTART.md           # このファイル
└── README.md               # プロジェクト概要
```

**合計: 5ファイル**

## 🔧 セットアップ（初回のみ）

### 1. Ollamaのインストール

```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# または公式サイトからダウンロード
# https://ollama.com/download
```

### 2. モデルのダウンロード

```bash
ollama pull llama3.1:8b
```

### 3. Python依存関係のインストール

```bash
cd backend
pip install -r requirements.txt
```

## ▶️ 起動方法

### ターミナル1: Ollamaを起動

```bash
ollama serve
```

### ターミナル2: アプリを起動

```bash
cd backend
python main.py
```

### ブラウザでアクセス

```
http://localhost:8000
```

## 🎯 動作確認

1. ブラウザで `http://localhost:8000` を開く
2. 右上のステータスが「オンライン」になることを確認
3. メッセージを入力して送信
4. AIから返信が来ることを確認

## ❓ トラブルシューティング

### "Ollama未接続"と表示される

```bash
# Ollamaが起動しているか確認
ollama list

# 起動していない場合
ollama serve
```

### モデルが見つからない

```bash
# インストール済みモデルを確認
ollama list

# llama3.1:8bがない場合
ollama pull llama3.1:8b
```

### ポート8000が使用中

```bash
# main.pyの最終行を編集
uvicorn.run(app, host="0.0.0.0", port=8001)  # 8001に変更
```

## 🔄 次のステップ

Phase 1が動いたら、次は記憶システム（Phase 2）の実装に進みます。

詳細は [docs/technical-stack.md](docs/technical-stack.md) を参照してください。

## 📝 API エンドポイント

- `GET /` - チャットUI
- `GET /health` - ヘルスチェック
- `POST /chat` - チャット送信
- `GET /models` - 利用可能なモデル一覧

### チャットAPIの例

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "こんにちは"}'
```

## ⚡ 特徴

- **完全ローカル実行**: インターネット不要
- **プライバシー保護**: データは全てローカル
- **シンプル**: 5ファイルで動作
- **モダンUI**: レスポンシブデザイン

---

問題があれば [GitHub Issues](https://github.com/hn770123/memory-assistant/issues) まで
