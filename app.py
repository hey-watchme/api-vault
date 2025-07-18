# =========================================
# app.py ― WatchMe Vault API (S3移行版)
#
# 本アプリケーションは、WatchMe プロジェクトにおける
# 音声データをS3に保存し、メタデータをSupabaseで管理する
# シンプルなファイルアップロードAPIです。
#
# 📦 名称：**WatchMe Vault API**
# 📁 役割：WAVファイルをS3にアップロードし、
#          Supabaseにメタデータを登録することで、
#          後続の処理API（transcriber, behavior, emotion）が
#          処理対象を発見できるようにする
#
# 🔹 主要機能：
#     - iOSデバイスからのWAVファイルアップロード
#     - S3への音声データ保存
#     - Supabaseへのメタデータ登録
#
# 🔧 データ構造（S3）：
#     files/{device_id}/{YYYY-MM-DD}/{HH-MM}/audio.wav
#
# =========================================

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from datetime import datetime
import os
import re
import boto3
from botocore.exceptions import ClientError
from supabase import create_client, Client
from typing import Optional
import pytz
from dotenv import load_dotenv

# .envファイルを読み込む
load_dotenv()

# =========================================
# 基本設定
# =========================================
app = FastAPI(title="WatchMe Vault API - S3 Storage")

# AWS S3設定
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "watchme-vault")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Supabase設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# S3クライアントの初期化
s3_client = None
if AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY:
    s3_client = boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_REGION
    )

# Supabaseクライアントの初期化
supabase_client: Optional[Client] = None
if SUPABASE_URL and SUPABASE_KEY:
    supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =========================================
# ヘルスチェックエンドポイント
# =========================================
@app.get("/health")
async def health_check():
    """APIの死活監視用エンドポイント"""
    status = {
        "status": "healthy",
        "timestamp": datetime.now(pytz.UTC).isoformat(),
        "s3_configured": s3_client is not None,
        "supabase_configured": supabase_client is not None
    }
    return JSONResponse(content=status)

@app.get("/status")
async def status():
    """APIステータス確認用エンドポイント（/healthのエイリアス）"""
    return await health_check()

# =========================================
# メインアップロードエンドポイント
# =========================================
@app.post("/upload")
async def upload_file(
    request: Request,
    file: UploadFile = File(...),
    device_id: str = Form(...),
):
    """
    WAVファイルをS3にアップロードし、Supabaseにメタデータを登録する
    
    必須:
    - X-File-Pathヘッダー: device_id/YYYY-MM-DD/raw/HH-MM.wav形式
    - device_id: デバイスID
    - file: WAVファイル
    """
    
    # S3クライアントの確認
    if not s3_client:
        raise HTTPException(
            status_code=500,
            detail="S3 client not configured. Please set AWS credentials."
        )
    
    # Supabaseクライアントの確認
    if not supabase_client:
        raise HTTPException(
            status_code=500,
            detail="Supabase client not configured. Please set Supabase credentials."
        )
    
    # X-File-Pathヘッダーから保存パスを取得
    file_path = request.headers.get("X-File-Path")
    
    if not file_path:
        raise HTTPException(
            status_code=400,
            detail="X-File-Path header is required for audio file uploads"
        )
    
    # パス形式の検証（device_id/YYYY-MM-DD/raw/HH-MM.wav）
    path_pattern = r'^([a-zA-Z0-9_-]+)/(\d{4}-\d{2}-\d{2})/raw/(\d{2}-\d{2})\.wav$'
    match = re.match(path_pattern, file_path)
    
    if not match:
        raise HTTPException(
            status_code=400, 
            detail="Invalid file path format. Expected: device_id/YYYY-MM-DD/raw/HH-MM.wav"
        )
    
    # パス要素の抽出
    path_device_id, date, time_block = match.groups()
    
    # device_idの一致確認
    if path_device_id != device_id:
        raise HTTPException(
            status_code=400,
            detail="Device ID in path does not match the provided device_id parameter"
        )
    
    # パストラバーサル攻撃の防御
    path_parts = file_path.split('/')
    if any('..' in part or part.startswith('/') or part.startswith('\\') for part in path_parts):
        raise HTTPException(
            status_code=400, 
            detail="Invalid path components detected"
        )
    
    # 新しいS3パス構造の構築
    # files/{device_id}/{YYYY-MM-DD}/{HH-MM}/audio.wav
    s3_key = f"files/{device_id}/{date}/{time_block}/audio.wav"
    
    try:
        # ファイルサイズ制限チェック（100MB）
        file_content = await file.read()
        file_size = len(file_content)
        
        if file_size > 100 * 1024 * 1024:  # 100MB
            raise HTTPException(
                status_code=413,
                detail="File size exceeds limit (100MB)"
            )
        
        # S3へアップロード
        s3_client.put_object(
            Bucket=S3_BUCKET_NAME,
            Key=s3_key,
            Body=file_content,
            ContentType='audio/wav'
        )
        
        # 録音開始時刻の計算
        # date (YYYY-MM-DD) と time_block (HH-MM) から datetime を作成
        hour, minute = map(int, time_block.split('-'))
        recorded_at = datetime.strptime(f"{date} {hour:02d}:{minute:02d}:00", "%Y-%m-%d %H:%M:%S")
        recorded_at = pytz.UTC.localize(recorded_at)
        
        # Supabaseにメタデータを登録
        # 基本的なカラムのみで登録（既存のテーブル構造に合わせる）
        audio_file_data = {
            "device_id": device_id,
            "recorded_at": recorded_at.isoformat(),
            "file_path": s3_key
        }
        
        # オプションカラムがあるか確認して追加
        # （将来的にカラムが追加された場合に対応）
        optional_fields = {
            "file_size_bytes": file_size,
            "duration_seconds": None,
            "transcriber_status": "pending",
            "behavior_status": "pending", 
            "emotion_status": "pending"
        }
        
        # Supabaseへの挿入
        result = supabase_client.table("audio_files").insert(audio_file_data).execute()
        
        # レスポンス
        response_data = {
            "status": "ok",
            "s3_key": s3_key,
            "device_id": device_id,
            "recorded_at": recorded_at.isoformat(),
            "file_size_bytes": file_size,
            "method": "s3_upload"
        }
        
        # Supabaseの結果からIDを取得（存在する場合）
        if result.data and len(result.data) > 0:
            if "id" in result.data[0]:
                response_data["supabase_id"] = result.data[0]["id"]
        
        return JSONResponse(response_data)
        
    except ClientError as e:
        # S3エラー
        raise HTTPException(
            status_code=500,
            detail=f"S3 upload failed: {str(e)}"
        )
    except Exception as e:
        # その他のエラー
        raise HTTPException(
            status_code=500,
            detail=f"Upload failed: {str(e)}"
        )

# =========================================
# ルートエンドポイント
# =========================================
@app.get("/", response_class=HTMLResponse)
async def root():
    """ルートエンドポイント - API情報表示"""
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>WatchMe Vault API</title>
        <style>
            body { 
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                margin: 40px auto;
                max-width: 800px;
                line-height: 1.6;
                color: #333;
            }
            h1 { color: #2c3e50; }
            .endpoint { 
                background: #f8f9fa;
                padding: 15px;
                margin: 10px 0;
                border-radius: 5px;
                border-left: 4px solid #007bff;
            }
            .method {
                display: inline-block;
                padding: 2px 8px;
                border-radius: 3px;
                font-weight: bold;
                font-size: 0.9em;
            }
            .post { background: #28a745; color: white; }
            .get { background: #007bff; color: white; }
            code {
                background: #e9ecef;
                padding: 2px 4px;
                border-radius: 3px;
                font-family: 'Consolas', 'Monaco', monospace;
            }
        </style>
    </head>
    <body>
        <h1>🗂️ WatchMe Vault API (S3 Storage)</h1>
        <p>WAVファイルをS3に保存し、Supabaseでメタデータを管理するシンプルなAPIです。</p>
        
        <h2>利用可能なエンドポイント</h2>
        
        <div class="endpoint">
            <span class="method post">POST</span> <code>/upload</code>
            <p>WAVファイルをS3にアップロードし、Supabaseにメタデータを登録します。</p>
            <p><strong>必須:</strong> X-File-Pathヘッダー（形式: device_id/YYYY-MM-DD/raw/HH-MM.wav）</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/health</code>
            <p>APIの死活監視用エンドポイント。S3とSupabaseの接続状態を確認できます。</p>
        </div>
        
        <div class="endpoint">
            <span class="method get">GET</span> <code>/status</code>
            <p>/healthのエイリアス。同じ情報を返します。</p>
        </div>
        
        <h2>S3パス構造</h2>
        <code>files/{device_id}/{YYYY-MM-DD}/{HH-MM}/audio.wav</code>
        
        <h2>設定状態</h2>
        <p>現在の設定状態は <a href="/health">/health</a> エンドポイントで確認できます。</p>
    </body>
    </html>
    """
    return HTMLResponse(content=html)