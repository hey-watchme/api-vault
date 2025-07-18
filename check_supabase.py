#!/usr/bin/env python3
"""
Supabaseのaudio_filesテーブル構造を確認するスクリプト
"""

from supabase import create_client, Client
from dotenv import load_dotenv
import os

# .envファイルを読み込む
load_dotenv()

# Supabase設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Supabase環境変数が設定されていません")
    exit(1)

# Supabaseクライアントの初期化
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=== Supabaseテーブル確認 ===")
print(f"URL: {SUPABASE_URL}")
print()

try:
    # audio_filesテーブルから1件取得してカラム構造を確認
    result = supabase.table("audio_files").select("*").limit(1).execute()
    
    if result.data:
        print("✅ audio_filesテーブルが存在します")
        print("\n既存のカラム:")
        for key in result.data[0].keys():
            print(f"  - {key}")
    else:
        print("⚠️  audio_filesテーブルは存在しますが、データがありません")
        
except Exception as e:
    error_message = str(e)
    if "audio_files" in error_message and "not find" in error_message:
        print("❌ audio_filesテーブルが存在しません")
        print("\nテーブルを作成する必要があります。以下のSQLをSupabaseで実行してください：")
        print("""
CREATE TABLE audio_files (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    device_id TEXT NOT NULL,
    recorded_at TIMESTAMPTZ NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes INTEGER,
    duration_seconds REAL,
    transcriber_status TEXT DEFAULT 'pending',
    behavior_status TEXT DEFAULT 'pending',
    emotion_status TEXT DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- インデックスの作成
CREATE INDEX idx_audio_files_device_id ON audio_files(device_id);
CREATE INDEX idx_audio_files_recorded_at ON audio_files(recorded_at);
CREATE INDEX idx_audio_files_transcriber_status ON audio_files(transcriber_status);
CREATE INDEX idx_audio_files_behavior_status ON audio_files(behavior_status);
CREATE INDEX idx_audio_files_emotion_status ON audio_files(emotion_status);
        """)
    else:
        print(f"❌ エラーが発生しました: {error_message}")

print("\n=== テスト挿入 ===")
try:
    # テストデータの挿入を試みる
    test_data = {
        "device_id": "test_device",
        "recorded_at": "2025-07-18T14:30:00+00:00",
        "file_path": "files/test_device/2025-07-18/14-30/audio.wav"
    }
    
    # まず基本的なカラムのみで試す
    result = supabase.table("audio_files").insert(test_data).execute()
    print("✅ 基本カラムでの挿入成功")
    print(f"挿入されたID: {result.data[0]['id']}")
    
    # 削除（テストデータなので）
    supabase.table("audio_files").delete().eq("id", result.data[0]['id']).execute()
    print("✅ テストデータを削除しました")
    
except Exception as e:
    print(f"❌ 挿入エラー: {str(e)}")
    print("\n必要なカラムが不足している可能性があります。")