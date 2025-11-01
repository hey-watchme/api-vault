#!/usr/bin/env python3
"""
SKIP機能の単体テスト
determine_initial_status関数が正しく動作するかをテスト
"""

# app.pyから関数と設定をインポート
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 環境変数の設定（テスト用）
os.environ['SUPABASE_URL'] = 'https://dummy.supabase.co'
os.environ['SUPABASE_KEY'] = 'dummy_key'
os.environ['AWS_ACCESS_KEY_ID'] = 'dummy_key'
os.environ['AWS_SECRET_ACCESS_KEY'] = 'dummy_key'

from app import determine_initial_status, SKIP_ENABLED, SKIP_DEVICE_IDS, SKIP_HOURS

def test_skip_function():
    """SKIP機能のテスト"""

    print("=" * 60)
    print("SKIP機能テスト")
    print("=" * 60)
    print(f"\n現在の設定:")
    print(f"  SKIP_ENABLED: {SKIP_ENABLED}")
    print(f"  SKIP_DEVICE_IDS: {SKIP_DEVICE_IDS}")
    print(f"  SKIP_HOURS: {SKIP_HOURS}")
    print()

    # テストケース
    test_cases = [
        # (device_id, time_block, expected_result, description)
        ('9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93', '23-00', 'skipped', '対象デバイス・夜23時'),
        ('9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93', '00-30', 'skipped', '対象デバイス・深夜0時30分'),
        ('9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93', '03-00', 'skipped', '対象デバイス・深夜3時'),
        ('9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93', '05-30', 'skipped', '対象デバイス・朝5時30分'),
        ('9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93', '06-00', 'pending', '対象デバイス・朝6時（スキップ時間外）'),
        ('9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93', '14-30', 'pending', '対象デバイス・昼14時30分'),
        ('9f7d6e27-98c3-4c19-bdfb-f7fda58b9a93', '22-30', 'pending', '対象デバイス・夜22時30分（スキップ時間外）'),
        ('different-device-id', '23-00', 'pending', '非対象デバイス・夜23時'),
        ('different-device-id', '03-00', 'pending', '非対象デバイス・深夜3時'),
    ]

    passed = 0
    failed = 0

    for device_id, time_block, expected, description in test_cases:
        print(f"\nテスト: {description}")
        print(f"  入力: device_id='{device_id}', time_block='{time_block}'")
        print(f"  期待値: '{expected}'")

        result = determine_initial_status(device_id, time_block)

        if result == expected:
            print(f"  結果: ✅ 成功 ('{result}')")
            passed += 1
        else:
            print(f"  結果: ❌ 失敗 ('{result}' != '{expected}')")
            failed += 1
        print("-" * 60)

    print(f"\n\n📊 テスト結果:")
    print(f"  成功: {passed}/{len(test_cases)}")
    print(f"  失敗: {failed}/{len(test_cases)}")

    if failed == 0:
        print("\n🎉 すべてのテストが成功しました！")
        return True
    else:
        print(f"\n⚠️ {failed}個のテストが失敗しました")
        return False

if __name__ == "__main__":
    success = test_skip_function()
    sys.exit(0 if success else 1)