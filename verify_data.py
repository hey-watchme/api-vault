#!/usr/bin/env python3
"""
Supabaseのaudio_filesテーブルに保存されたデータを確認するスクリプト
特にlocal_dateとtime_blockカラムの値を検証
"""

import os
from dotenv import load_dotenv
from supabase import create_client
from datetime import datetime, timedelta
import json

# .envファイルを読み込む
load_dotenv()

# Supabase設定
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    print("❌ Supabase環境変数が設定されていません")
    exit(1)

# Supabaseクライアントの初期化
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

print("=== Supabase audio_filesテーブル データ確認 ===")
print(f"URL: {SUPABASE_URL}\n")

# 最新のデータを取得（test_device_001の最新10件）
try:
    result = supabase.table("audio_files") \
        .select("*") \
        .eq("device_id", "test_device_001") \
        .order("recorded_at", desc=True) \
        .limit(10) \
        .execute()
    
    if result.data:
        print(f"✅ {len(result.data)}件のデータが見つかりました\n")
        
        for i, record in enumerate(result.data, 1):
            print(f"=== レコード {i} ===")
            print(f"device_id: {record.get('device_id')}")
            print(f"recorded_at: {record.get('recorded_at')}")
            print(f"file_path: {record.get('file_path')}")
            print(f"local_date: {record.get('local_date')} {'✅' if record.get('local_date') else '❌ 未設定'}")
            print(f"time_block: {record.get('time_block')} {'✅' if record.get('time_block') else '❌ 未設定'}")
            print(f"created_at: {record.get('created_at')}")
            print()
            
            # file_pathから期待される値を計算
            if record.get('file_path'):
                path_parts = record.get('file_path').split('/')
                if len(path_parts) >= 4:
                    expected_date = path_parts[2]  # YYYY-MM-DD
                    expected_time_block = path_parts[3]  # HH-MM
                    
                    # 実際の値と比較
                    if record.get('local_date') == expected_date:
                        print(f"  ✅ local_dateが正しく設定されています: {expected_date}")
                    else:
                        print(f"  ⚠️ local_dateが期待値と異なります: 期待値={expected_date}, 実際={record.get('local_date')}")
                    
                    if record.get('time_block') == expected_time_block:
                        print(f"  ✅ time_blockが正しく設定されています: {expected_time_block}")
                    else:
                        print(f"  ⚠️ time_blockが期待値と異なります: 期待値={expected_time_block}, 実際={record.get('time_block')}")
            print("-" * 50)
            print()
    else:
        print("❌ test_device_001のデータが見つかりません")
        
        # 全デバイスの最新5件を表示
        print("\n他のデバイスのデータを確認中...")
        result = supabase.table("audio_files") \
            .select("*") \
            .order("recorded_at", desc=True) \
            .limit(5) \
            .execute()
        
        if result.data:
            print(f"最新{len(result.data)}件のデータ:")
            for record in result.data:
                print(f"  - {record.get('device_id')}: {record.get('recorded_at')}")
                print(f"    local_date: {record.get('local_date')}, time_block: {record.get('time_block')}")
        
except Exception as e:
    print(f"❌ エラー: {e}")

print("\n=== カラム構造の確認 ===")
try:
    # 1件だけ取得してカラム構造を確認
    result = supabase.table("audio_files").select("*").limit(1).execute()
    if result.data and len(result.data) > 0:
        columns = list(result.data[0].keys())
        print("利用可能なカラム:")
        for col in columns:
            print(f"  - {col}")
except Exception as e:
    print(f"❌ カラム確認エラー: {e}")