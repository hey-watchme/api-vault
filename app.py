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
import json
from dateutil import parser as date_parser

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
    metadata: str = Form(...),
):
    """
    WAVファイルをS3にアップロードし、Supabaseにメタデータを登録する
    
    必須:
    - metadata: JSON形式のメタデータ（device_id, recorded_atを含む）
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
    
    # metadata JSONのパース
    try:
        metadata_dict = json.loads(metadata)
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=400,
            detail="Invalid metadata JSON format"
        )
    
    # 必須フィールドの確認
    if "device_id" not in metadata_dict:
        raise HTTPException(
            status_code=400,
            detail="device_id is required in metadata"
        )
    
    if "recorded_at" not in metadata_dict:
        raise HTTPException(
            status_code=400,
            detail="recorded_at is required in metadata"
        )
    
    device_id = metadata_dict["device_id"]
    recorded_at_str = metadata_dict["recorded_at"]
    
    # デバッグログ
    print(f"📊 受信したメタデータ: device_id={device_id}, recorded_at={recorded_at_str}")
    
    # recorded_atのパース（ISO 8601形式）
    # 重要: ユーザーが録音したローカル時間を保持するため、タイムゾーン変換は行わない
    try:
        recorded_at = date_parser.isoparse(recorded_at_str)
        print(f"📊 パース後のrecorded_at（ユーザーのローカル時間）: {recorded_at}")
        
        # タイムゾーン情報が含まれているか確認
        if recorded_at.tzinfo is None:
            # タイムゾーン情報がない場合は警告を出す
            print(f"⚠️ 警告: recorded_atにタイムゾーン情報が含まれていません: {recorded_at_str}")
            # デフォルトでUTCとして扱う（後方互換性のため）
            recorded_at = pytz.UTC.localize(recorded_at)
            print(f"📊 UTCタイムゾーンを仮定: {recorded_at}")
        else:
            # タイムゾーン情報がある場合は、そのまま保持する（変換しない）
            print(f"📊 タイムゾーン情報を保持: {recorded_at} (UTC offset: {recorded_at.strftime('%z')})")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid recorded_at format. Expected ISO 8601: {str(e)}"
        )
    
    # recorded_atから日付と時刻ブロックを抽出
    # 重要: ユーザーのローカル時間のまま処理する（タイムゾーン変換なし）
    # S3のパス生成では、クライアントから送られてきたタイムスタンプが持つ
    # ローカルの時刻情報をそのまま使用します
    # 例: "2025-07-19T14:15:00+09:00" → パスは "14-00" (UTCの05-00ではない)
    
    # タイムゾーン変換を行わず、recorded_atオブジェクトの時刻をそのまま使用
    year = recorded_at.year
    month = recorded_at.month
    day = recorded_at.day
    hour = recorded_at.hour    # ユーザーのローカル時間の「時」
    minute = recorded_at.minute  # ユーザーのローカル時間の「分」
    
    # パス用の日付文字列
    date = f"{year:04d}-{month:02d}-{day:02d}"
    
    # 時刻を30分スロットに変換（00-00, 00-30, 01-00, ... 23-30）
    # 例: 14:15 → 14-00, 14:45 → 14-30
    slot_minute = 0 if minute < 30 else 30
    time_block = f"{hour:02d}-{slot_minute:02d}"
    
    print(f"📊 S3パス生成（ユーザーのローカル時間をそのまま使用）:")
    print(f"   入力: {recorded_at_str}")
    print(f"   日付: {date}, 時刻スロット: {time_block}")
    
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
        
        # recorded_atは既にmetadataから取得済み
        
        # Supabaseにメタデータを登録
        # 基本的なカラムのみで登録（既存のテーブル構造に合わせる）
        # 重要: recorded_atはユーザーのローカル時間をそのまま保存
        audio_file_data = {
            "device_id": device_id,
            "recorded_at": recorded_at.isoformat(),  # タイムゾーン情報を含むISO8601形式
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
            "recorded_at": recorded_at.isoformat(),  # ユーザーのローカル時間を返す
            "file_size_bytes": file_size,
            "method": "s3_upload",
            "timezone_info": recorded_at.strftime("%z") if recorded_at.tzinfo else "unknown"
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
            <p><strong>必須:</strong> metadata JSON（device_id, recorded_atを含む）</p>
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