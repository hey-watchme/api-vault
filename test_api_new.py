#!/usr/bin/env python3
"""
Vault API (S3版) のテストスクリプト - 新形式対応版

使い方:
1. 環境変数を設定してください:
   - AWS_ACCESS_KEY_ID
   - AWS_SECRET_ACCESS_KEY
   - S3_BUCKET_NAME
   - SUPABASE_URL
   - SUPABASE_KEY

2. テスト用のWAVファイルを用意してください:
   python3 -c "import wave; w=wave.open('test.wav','w'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(44100); w.writeframes(b'\\x00'*88200); w.close()"

3. APIを起動してテストを実行:
   python3 test_api_new.py
"""

import requests
import json
from datetime import datetime
import os
import pytz

# APIのベースURL（ローカルテスト用）
BASE_URL = "http://localhost:8000"

def test_health_check():
    """ヘルスチェックエンドポイントのテスト"""
    print("=== Testing /health endpoint ===")
    
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        
        # 設定状態の確認
        if not data.get("s3_configured"):
            print("❌ WARNING: S3 is not configured!")
        else:
            print("✅ S3 is configured")
            
        if not data.get("supabase_configured"):
            print("❌ WARNING: Supabase is not configured!")
        else:
            print("✅ Supabase is configured")
    else:
        print(f"❌ Error: {response.text}")
    
    print()
    return response.status_code == 200

def test_upload_file():
    """ファイルアップロードエンドポイントのテスト（新形式）"""
    print("=== Testing /upload endpoint (new format with local_date and time_block) ===")
    
    # テスト用のWAVファイルが存在するか確認
    if not os.path.exists("test.wav"):
        print("❌ test.wav not found. Creating a dummy WAV file...")
        # 簡単なWAVファイルを作成
        import wave
        with wave.open('test.wav', 'w') as w:
            w.setnchannels(1)  # モノラル
            w.setsampwidth(2)  # 16bit
            w.setframerate(44100)  # 44.1kHz
            w.writeframes(b'\x00' * 88200)  # 1秒分の無音
    
    # テストデータ
    device_id = "test_device_001"
    # 日本時間で現在時刻を取得
    jst = pytz.timezone('Asia/Tokyo')
    now = datetime.now(jst)
    
    # ISO 8601形式のタイムスタンプ（タイムゾーン付き）
    recorded_at = now.isoformat()
    
    print(f"Device ID: {device_id}")
    print(f"Recorded At: {recorded_at}")
    print(f"Expected local_date: {now.strftime('%Y-%m-%d')}")
    minute = 30 if now.minute >= 30 else 0
    print(f"Expected time_block: {now.hour:02d}-{minute:02d}")
    
    # メタデータをJSON形式で準備
    metadata = {
        "device_id": device_id,
        "recorded_at": recorded_at
    }
    
    # ファイルを開いて送信
    with open("test.wav", "rb") as f:
        files = {
            "file": ("audio.wav", f, "audio/wav")
        }
        
        # フォームデータとして送信
        data = {
            "metadata": json.dumps(metadata)
        }
        
        response = requests.post(
            f"{BASE_URL}/upload",
            files=files,
            data=data
        )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {json.dumps(result, indent=2)}")
        print("✅ Upload successful!")
        
        # レスポンスから情報を表示
        print(f"  S3 Key: {result.get('s3_key')}")
        print(f"  File Size: {result.get('file_size_bytes')} bytes")
        print(f"  Timezone Info: {result.get('timezone_info')}")
        
        # Supabaseデータの確認
        print("\n=== Verifying Supabase data ===")
        print("Check your Supabase database for:")
        print(f"  - device_id: {device_id}")
        print(f"  - local_date: {now.strftime('%Y-%m-%d')}")
        print(f"  - time_block: {now.hour:02d}-{minute:02d}")
        
    else:
        print(f"❌ Error: {response.text}")
    
    print()
    return response.status_code == 200

def main():
    """メインテスト実行"""
    print("🚀 Starting Vault API Tests (New Format)\n")
    
    # APIが起動しているか確認
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=2)
    except requests.exceptions.RequestException:
        print(f"❌ Cannot connect to API. Is it running on {BASE_URL}?")
        return
    
    # テスト実行
    results = []
    
    # ヘルスチェック
    results.append(("Health Check", test_health_check()))
    
    # ファイルアップロード
    results.append(("File Upload", test_upload_file()))
    
    # 結果サマリー
    print("\n=== Test Summary ===")
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed < total:
        print("\n⚠️  Some tests failed. Check the configuration:")
        print("- Are AWS credentials set correctly?")
        print("- Is Supabase configured?")
        print("- Is the S3 bucket accessible?")
        print("- Check the new table columns (local_date, time_block) exist in Supabase")

if __name__ == "__main__":
    main()