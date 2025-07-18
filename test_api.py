#!/usr/bin/env python3
"""
Vault API (S3版) のテストスクリプト

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
   python3 test_api.py
"""

import requests
import json
from datetime import datetime
import os

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
    """ファイルアップロードエンドポイントのテスト"""
    print("=== Testing /upload endpoint ===")
    
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
    
    # テストデータ（現在時刻を使用して重複を避ける）
    device_id = "test_device_001"
    now = datetime.now()
    date = now.strftime("%Y-%m-%d")
    # 現在の時刻から30分単位のスロットを計算
    hour = now.hour
    minute = 30 if now.minute >= 30 else 0
    time_slot = f"{hour:02d}-{minute:02d}"
    
    # X-File-Pathヘッダーの構築
    file_path = f"{device_id}/{date}/raw/{time_slot}.wav"
    
    print(f"Device ID: {device_id}")
    print(f"File Path: {file_path}")
    
    # リクエストの準備
    headers = {
        "X-File-Path": file_path
    }
    
    data = {
        "device_id": device_id
    }
    
    # ファイルを開いて送信
    with open("test.wav", "rb") as f:
        files = {
            "file": (f"{time_slot}.wav", f, "audio/wav")
        }
        
        response = requests.post(
            f"{BASE_URL}/upload",
            headers=headers,
            data=data,
            files=files
        )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {json.dumps(data, indent=2)}")
        print("✅ Upload successful!")
        return True
    else:
        print(f"❌ Error: {response.text}")
        return False

def test_missing_header():
    """必須ヘッダーが欠けている場合のテスト"""
    print("=== Testing /upload without X-File-Path header ===")
    
    data = {
        "device_id": "test_device_001"
    }
    
    # ダミーファイルデータ
    files = {
        "file": ("test.wav", b"dummy content", "audio/wav")
    }
    
    response = requests.post(
        f"{BASE_URL}/upload",
        data=data,
        files=files
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 400:
        print(f"Response: {response.text}")
        print("✅ Correctly rejected request without X-File-Path header")
        return True
    else:
        print(f"❌ Unexpected response: {response.text}")
        return False

def test_invalid_path_format():
    """不正なパス形式のテスト"""
    print("=== Testing /upload with invalid path format ===")
    
    headers = {
        "X-File-Path": "invalid/path/format.wav"  # rawディレクトリがない
    }
    
    data = {
        "device_id": "test_device_001"
    }
    
    files = {
        "file": ("test.wav", b"dummy content", "audio/wav")
    }
    
    response = requests.post(
        f"{BASE_URL}/upload",
        headers=headers,
        data=data,
        files=files
    )
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 400:
        print(f"Response: {response.text}")
        print("✅ Correctly rejected invalid path format")
        return True
    else:
        print(f"❌ Unexpected response: {response.text}")
        return False

def main():
    """全てのテストを実行"""
    print("🚀 Starting Vault API Tests\n")
    
    # APIが起動しているか確認
    try:
        response = requests.get(BASE_URL)
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to API. Is it running on http://localhost:8000?")
        return
    
    # 各テストを実行
    tests = [
        ("Health Check", test_health_check),
        ("File Upload", test_upload_file),
        ("Missing Header", test_missing_header),
        ("Invalid Path Format", test_invalid_path_format),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"❌ Error in {test_name}: {str(e)}")
            results.append((test_name, False))
        print()
    
    # 結果のサマリー
    print("=== Test Summary ===")
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed < total:
        print("\n⚠️  Some tests failed. Check the configuration:")
        print("- Are AWS credentials set correctly?")
        print("- Is Supabase configured?")
        print("- Is the S3 bucket accessible?")

if __name__ == "__main__":
    main()