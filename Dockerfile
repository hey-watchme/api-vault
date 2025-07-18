# Python 3.12のスリムイメージを使用
FROM python:3.12-slim

# 作業ディレクトリを設定
WORKDIR /app

# システムパッケージを更新（必要に応じて）
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# 依存関係ファイルをコピー
COPY requirements.txt .

# 依存関係をインストール
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションコードをコピー
COPY app.py .
COPY .env* ./

# ポート8000を公開
EXPOSE 8000

# 非rootユーザーで実行（セキュリティ向上）
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# アプリケーションを起動
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]