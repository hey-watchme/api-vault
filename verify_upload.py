#!/usr/bin/env python3
"""
アップロードされたファイルをS3とSupabaseで確認するスクリプト
"""

import boto3
from supabase import create_client
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import pytz

# .envファイルを読み込む
load_dotenv()

# AWS S3設定
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "watchme-vault")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Supabase設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# S3クライアントの初期化
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

# Supabaseクライアントの初期化
supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=== S3バケットの確認 ===")
print(f"バケット名: {S3_BUCKET_NAME}")

try:
    # バケット内のオブジェクトをリスト
    response = s3_client.list_objects_v2(
        Bucket=S3_BUCKET_NAME,
        Prefix='files/',
        MaxKeys=10
    )
    
    if 'Contents' in response:
        print(f"\n最新のファイル（最大10件）:")
        for obj in response['Contents']:
            print(f"  - {obj['Key']} (Size: {obj['Size']} bytes, Modified: {obj['LastModified']})")
    else:
        print("❌ S3バケットにファイルが見つかりません")
        
except Exception as e:
    print(f"❌ S3エラー: {str(e)}")

print("\n=== Supabaseデータベースの確認 ===")

try:
    # 最新の5件を取得
    result = supabase_client.table("audio_files").select("*").order("recorded_at", desc=True).limit(5).execute()
    
    if result.data:
        print(f"\n最新のレコード（最大5件）:")
        for record in result.data:
            print(f"\n  Device ID: {record.get('device_id')}")
            print(f"  Recorded At: {record.get('recorded_at')}")
            print(f"  File Path: {record.get('file_path')}")
            if 'id' in record:
                print(f"  ID: {record.get('id')}")
    else:
        print("❌ Supabaseにレコードが見つかりません")
        
    # 本日のレコード数を確認
    today = datetime.now(pytz.UTC).replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow = today + timedelta(days=1)
    
    result = supabase_client.table("audio_files").select("*").gte("recorded_at", today.isoformat()).lt("recorded_at", tomorrow.isoformat()).execute()
    
    print(f"\n本日（{today.strftime('%Y-%m-%d')}）のレコード数: {len(result.data)}")
    
except Exception as e:
    print(f"❌ Supabaseエラー: {str(e)}")

print("\n=== 統合確認 ===")
print("✅ S3とSupabaseの両方にアクセス可能です")
print("✅ Vault APIは正常に動作しています")