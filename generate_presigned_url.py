#!/usr/bin/env python3
"""
S3の署名付きURL（Presigned URL）を生成するサンプル
"""

import boto3
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta

# .envファイルを読み込む
load_dotenv()

# AWS S3設定
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "watchme-vault")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# S3クライアントの初期化
s3_client = boto3.client(
    's3',
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    region_name=AWS_REGION
)

def generate_presigned_url(s3_key, expiration_hours=1):
    """
    S3オブジェクトの署名付きURLを生成
    
    Args:
        s3_key: S3のキー（例: files/device123/2025-07-18/14-30/audio.wav）
        expiration_hours: URLの有効期限（時間）
    
    Returns:
        署名付きURL
    """
    try:
        # 署名付きURLを生成
        url = s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': S3_BUCKET_NAME,
                'Key': s3_key
            },
            ExpiresIn=expiration_hours * 3600  # 秒単位
        )
        return url
    except Exception as e:
        print(f"エラー: {str(e)}")
        return None

# 使用例
if __name__ == "__main__":
    # テスト用のS3キー
    test_keys = [
        "files/test_device_001/2025-07-18/14-30/audio.wav",
        "files/test_device_001/2025-07-18/10-00/audio.wav"
    ]
    
    print("=== S3 署名付きURL生成 ===\n")
    
    for key in test_keys:
        print(f"S3キー: {key}")
        
        # 1時間有効なURLを生成
        url = generate_presigned_url(key, expiration_hours=1)
        
        if url:
            print(f"署名付きURL（1時間有効）:")
            print(f"{url}\n")
            print("このURLをブラウザに貼り付けると、音声ファイルにアクセスできます。")
            print("-" * 80)
        else:
            print("URLの生成に失敗しました。\n")
    
    # 管理画面での使用例
    print("\n=== 管理画面での実装例 ===")
    print("""
# FastAPIでの実装例
@app.get("/api/audio/presigned-url")
async def get_audio_presigned_url(
    device_id: str,
    date: str,
    time_slot: str,
    expiration_hours: int = 1
):
    s3_key = f"files/{device_id}/{date}/{time_slot}/audio.wav"
    
    url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': S3_BUCKET_NAME, 'Key': s3_key},
        ExpiresIn=expiration_hours * 3600
    )
    
    return {"presigned_url": url, "expires_in": f"{expiration_hours}時間"}
    """)