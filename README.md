# WatchMe Vault API

WatchMe プロジェクト用のファイル受け渡しAPIです。

音声データ（WAV）と各種解析結果（JSON）をユーザー・日付単位で管理し、iOSアプリ・Streamlit・Webダッシュボード間のデータ授受を安全に行います。

## ⚠️ 重要な制限事項

**このローカル環境は「コード編集専用」です。以下の点にご注意ください：**

- 🎯 **目的**: app.pyのコード編集とバージョン管理のみ
- 🚫 **動作保証なし**: ローカルで動作しなくても問題ありません
- 🔒 **本番優先**: 本番環境の動作に影響を与えない構成を維持します
- ⚡ **カスタマイズ禁止**: ローカル環境の過度なカスタマイズは避けてください

## プロジェクト構造

### サーバー環境（本番）
```
/home/ubuntu/
├── watchme_api/          # このGitHubリポジトリ
│   ├── app.py           # メインAPIサーバー
│   ├── requirements.txt # 依存関係
│   ├── README.md        # このファイル
│   └── LOCAL_DEV.md     # ローカル開発ガイド
└── data/
    └── data_accounts/   # 実際のデータストレージ
```

### ローカル開発環境（コード編集用）
```
vault/                   # 開発用コンテナ
├── watchme_api/         # GitHubリポジトリ（このフォルダ）
│   ├── app.py          # 編集対象のコード
│   ├── requirements.txt # 本番と同じ依存関係
│   ├── README.md       # このファイル
│   └── LOCAL_DEV.md    # ローカル開発ガイド
└── data/               # ローカル開発用データ（Git管理外）
    └── data_accounts/  # データ構造のミラー
```

## 本番環境での起動

サーバー上（本番環境）でのみ実行してください：

```bash
# GitHubからクローン（初回のみ）
git clone git@github.com:matsumotokaya/watchme-vault-api.git watchme_api
cd watchme_api

# 依存関係のインストール
pip install -r requirements.txt

# アプリケーション起動
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

## ローカル開発環境での作業

⚠️ **ローカル環境は動作確認目的ではありません。コード編集のみに使用してください。**

### コード編集のワークフロー

```bash
# 1. 最新コードを取得
cd vault/watchme_api
git pull origin main

# 2. app.py を編集
# （お好みのエディタでapp.pyを編集）

# 3. 変更をコミット・プッシュ
git add .
git commit -m "修正内容の説明"
git push origin main
```

### ローカル動作テスト（任意・非推奨）

動作テストは本番環境で行うことを強く推奨しますが、必要な場合のみ：

```bash
cd vault/watchme_api
WATCHME_LOCAL_DEV=1 uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**注意**: ローカルでエラーが発生しても、本番環境では正常動作する可能性があります。

## 🔑 主要エンドポイント

### **Core API: 外部サービス連携用ダウンロード (最重要)**

#### `GET /download` - 時間スロット指定によるファイル取得
**OpenSMILE、Whisper API等の外部サービスが使用する中核エンドポイント**

**パラメータ:**
- `user_id`: ユーザーID (例: user123)
- `date`: 日付 (YYYY-MM-DD形式, 例: 2025-06-25)
- `slot`: 時間スロット (HH-MM形式, 例: 20-30)
- `type`: ファイル種別 (省略時=wav, json指定可能)

**使用例:**
```bash
# 🎵 WAVファイルの取得 (OpenSMILE/Whisper APIから)
curl "https://api.hey-watch.me/download?user_id=user123&date=2025-06-25&slot=20-30"

# 📄 JSONファイルの取得 (解析結果取得時)
curl "https://api.hey-watch.me/download?user_id=user123&date=2025-06-25&slot=20-30&type=json"
```

**重要:** このエンドポイントがWatchMeエコシステムの**データ中継拠点**として機能

#### `GET /download-file` - 完全ファイルパス指定
**管理者向け・デバッグ用の直接ファイルアクセス**

**パラメータ:**
- `path`: EC2上の相対ファイルパス

**使用例:**
```bash
# 完全パス指定でのダウンロード
curl "https://api.hey-watch.me/download-file?path=user123/2025-06-25/raw/20-30.wav"
```

### **外部API連携パターン (推奨使用方法)**

#### A. OpenSMILE API からの音声取得
```python
# OpenSMILE が Vault API から WAV ファイルを取得
async def fetch_wav_from_vault(user_id, date, time_slot):
    url = f"https://api.hey-watch.me/download?user_id={user_id}&date={date}&slot={time_slot}"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            if response.status == 200:
                return await response.read()  # WAVバイナリデータ
    return None
```

#### B. Whisper API からの音声取得
```python
# Whisper API が一括で48スロットの音声を取得
time_slots = [f"{hour:02d}-{minute:02d}" for hour in range(24) for minute in [0, 30]]
for slot in time_slots:
    wav_data = await fetch_wav_from_vault("user123", "2025-06-25", slot)
    if wav_data:
        # 音声文字起こし処理...
```

### **アップロード系**
- `POST /upload` - WAV音声ファイルアップロード (iOSアプリから)
- `POST /upload-transcription` - 文字起こしJSONアップロード (Whisper APIから)
- `POST /upload-prompt` - ChatGPTプロンプトJSONアップロード
- `POST /upload/analysis/emotion-timeline` - 感情タイムラインJSONアップロード
- `POST /upload/analysis/sed-timeline` - SEDタイムラインJSONアップロード
- `POST /upload/analysis/sed-summary` - SEDサマリーJSONアップロード

### **表示・確認系**
- `GET /view-file` - JSONファイル内容表示
- `GET /status` - HTML形式のファイル一覧表示

### **API系 (Webダッシュボード用)**
- `GET /api/users/{user_id}/logs/{date}/sed-summary` - SEDサマリー取得

## 🔗 EC2データアクセスガイド

### ベースURL
- **本番環境**: `https://api.hey-watch.me`
- **ローカル開発**: `http://localhost:8000`

### 具体的なファイルアクセス例

#### 1. WAV音声ファイルの取得
```bash
# ✅ 推奨: 時間スロット指定による取得 (OpenSMILE/Whisper APIが使用)
GET https://api.hey-watch.me/download?user_id=test_user&date=2025-06-26&slot=08-30

# ⚠️ 管理者向け: ファイルパス指定での取得
GET https://api.hey-watch.me/download-file?path=test_user/2025-06-26/raw/20-30.wav
```

#### 2. JSON解析結果の取得
```bash
# ✅ 推奨: 時間スロット指定による取得 (外部APIから)
GET https://api.hey-watch.me/download?user_id=test_user&date=2025-06-26&slot=08-30&type=json

# 📋 内容表示: JSONファイル内容をレスポンス内で表示
GET https://api.hey-watch.me/view-file?file_path=test_user/2025-06-26/transcriptions/08-30.json

# 🎯 専用API: SEDサマリー取得（Webダッシュボード用）
GET https://api.hey-watch.me/api/users/test_user/logs/2025-06-26/sed-summary

# 📊 各種解析結果の表示
GET https://api.hey-watch.me/view-file?file_path=test_user/2025-06-26/emotion-timeline/emotion-timeline.json
GET https://api.hey-watch.me/view-file?file_path=test_user/2025-06-26/sed/20-30.json
GET https://api.hey-watch.me/view-file?file_path=test_user/2025-06-26/prompt/emotion-timeline_gpt_prompt.json
```

#### 3. ファイル一覧の確認
```bash
# HTML形式でのファイル一覧表示
GET https://api.hey-watch.me/status
```

### 他のAPIとの連携パターン

#### A. データ送信側API（例：Streamlitアプリ）
```python
import requests

# 1. Whisper APIで音声を文字起こし
transcription_data = {"transcript": "こんにちは", "confidence": 0.95}

# 2. WatchMe Vault APIに送信
response = requests.post(
    "https://api.hey-watch.me/upload-transcription",
    params={"user_id": "test_user", "date": "2025-06-26"},
    json=transcription_data
)

# 3. ChatGPT APIで感情分析
emotion_data = {"emotions": [{"time": 0, "emotion": "happiness", "score": 0.8}]}

# 4. 感情タイムラインを送信
response = requests.post(
    "https://api.hey-watch.me/upload/analysis/emotion-timeline",
    params={"user_id": "test_user", "date": "2025-06-26"},
    json=emotion_data
)
```

#### B. データ取得側API（例：React Webダッシュボード）
```javascript
// 感情データの取得
const fetchEmotionData = async (userId, date) => {
  const response = await fetch(
    `https://api.hey-watch.me/view-file?file_path=${userId}/${date}/emotion-timeline/emotion_timeline.json`
  );
  return await response.json();
};

// SEDサマリーの取得（専用API）
const fetchSedSummary = async (userId, date) => {
  const response = await fetch(
    `https://api.hey-watch.me/api/users/${userId}/logs/${date}/sed-summary`
  );
  return await response.json();
};
```

#### C. iOSアプリからの音声アップロード
```swift
// FormDataでWAVファイルをアップロード
let url = URL(string: "https://api.hey-watch.me/upload?user_id=test_user&date=2025-06-26")!
var request = URLRequest(url: url)
request.httpMethod = "POST"

let boundary = UUID().uuidString
request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

// WAVファイルデータを含むFormDataを構築（時刻形式のファイル名）
let httpBody = createFormData(boundary: boundary, audioData: wavData, filename: "08-30.wav")
request.httpBody = httpBody
```

### 📋 レスポンス形式とエラーハンドリング

#### 成功レスポンス例
```json
// WAVファイルアップロード成功
{
  "message": "File uploaded successfully",
  "file_path": "test_user/2025-06-26/raw/08-30.wav",
  "file_size": 1234567
}

// 感情タイムラインJSON表示成功
{
  "file_path": "test_user/2025-06-26/emotion-timeline/emotion-timeline.json",
  "content": {
    "emotions": [
      {"time": 0, "emotion": "happiness", "score": 0.8}
    ]
  }
}

// SEDサマリー取得成功
{
  "file_path": "test_user/2025-06-26/sed-summary/result.json",
  "content": {
    "summary": "音響イベント分析結果",
    "events": ["speech", "music"]
  }
}
```

#### エラーレスポンス例
```json
// ファイルが見つからない場合
{
  "detail": "File not found: test_user/2025-06-26/raw/09-00.wav"
}

// 日付形式が不正な場合
{
  "detail": "Invalid date format. Expected YYYY-MM-DD"
}

// ファイルサイズ制限エラー
{
  "detail": "File size exceeds limit (100MB for WAV, 10MB for JSON)"
}
```

### 💡 データ操作の実践例

#### 完全なワークフロー例（音声解析パイプライン）
```python
import requests
import json
from datetime import datetime

# 設定
BASE_URL = "https://api.hey-watch.me"
USER_ID = "test_user"
DATE = "2025-06-26"

# 1. 音声ファイルをアップロード（iOSアプリから）
def upload_audio(wav_file_path, filename):
    with open(wav_file_path, 'rb') as f:
        files = {'file': (filename, f, 'audio/wav')}
        response = requests.post(
            f"{BASE_URL}/upload",
            params={"user_id": USER_ID, "date": DATE},
            files=files
        )
    return response.json()

# 2. 文字起こし結果をアップロード（Whisper APIから）
def upload_transcription(transcript_text):
    transcription_data = {
        "transcript": transcript_text,
        "confidence": 0.95,
        "language": "ja"
    }
    response = requests.post(
        f"{BASE_URL}/upload-transcription",
        params={"user_id": USER_ID, "date": DATE},
        json=transcription_data
    )
    return response.json()

# 3. 感情分析結果をアップロード（ChatGPT APIから）
def upload_emotion_timeline(emotions):
    emotion_data = {
        "emotions": emotions,
        "analysis_timestamp": datetime.now().isoformat()
    }
    response = requests.post(
        f"{BASE_URL}/upload/analysis/emotion-timeline",
        params={"user_id": USER_ID, "date": DATE},
        json=emotion_data
    )
    return response.json()

# 4. データを取得して表示（Webダッシュボードから）
def fetch_all_data():
    # 感情データの取得
    emotion_response = requests.get(
        f"{BASE_URL}/view-file",
        params={"file_path": f"{USER_ID}/{DATE}/emotion-timeline/emotion-timeline.json"}
    )
    
    # 文字起こしデータの取得（複数ファイル）
    transcription_08_30 = requests.get(
        f"{BASE_URL}/view-file",
        params={"file_path": f"{USER_ID}/{DATE}/transcriptions/08-30.json"}
    )
    
    # SEDサマリーの取得
    sed_summary_response = requests.get(
        f"{BASE_URL}/view-file",
        params={"file_path": f"{USER_ID}/{DATE}/sed-summary/result.json"}
    )
    
    return {
        "emotions": emotion_response.json(),
        "transcription_08_30": transcription_08_30.json(),
        "sed_summary": sed_summary_response.json()
    }

# 実行例
if __name__ == "__main__":
    # パイプライン実行
    print("1. 音声アップロード...")
    upload_result = upload_audio("sample_audio.wav", "08-30.wav")
    print(f"アップロード完了: {upload_result}")
    
    print("2. 文字起こし結果アップロード...")
    transcription_result = upload_transcription("おはようございます。今日は朝の会議があります。")
    print(f"文字起こし完了: {transcription_result}")
    
    print("3. 感情分析結果アップロード...")
    emotions = [
        {"time": 0, "emotion": "happiness", "score": 0.8},
        {"time": 2.5, "emotion": "neutral", "score": 0.6}
    ]
    emotion_result = upload_emotion_timeline(emotions)
    print(f"感情分析完了: {emotion_result}")
    
    print("4. データ取得...")
    all_data = fetch_all_data()
    print(f"取得データ: {json.dumps(all_data, indent=2, ensure_ascii=False)}")
```

#### React.jsでのリアルタイムデータ取得
```javascript
import React, { useState, useEffect } from 'react';

const EmotionDashboard = ({ userId, date }) => {
  const [emotionData, setEmotionData] = useState(null);
  const [sedData, setSedData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
      try {
        setLoading(true);
        
        // 感情データの取得
        const emotionResponse = await fetch(
          `https://api.hey-watch.me/view-file?file_path=${userId}/${date}/emotion-timeline/emotion-timeline.json`
        );
        
        if (!emotionResponse.ok) {
          throw new Error(`感情データの取得に失敗: ${emotionResponse.status}`);
        }
        
        const emotionResult = await emotionResponse.json();
        setEmotionData(emotionResult.content);
        
        // SEDサマリーの取得
        const sedResponse = await fetch(
          `https://api.hey-watch.me/api/users/${userId}/logs/${date}/sed-summary`
        );
        
        if (sedResponse.ok) {
          const sedResult = await sedResponse.json();
          setSedData(sedResult);
        }
        
      } catch (err) {
        setError(err.message);
        console.error('データ取得エラー:', err);
      } finally {
        setLoading(false);
      }
    };

    if (userId && date) {
      fetchData();
    }
  }, [userId, date]);

  if (loading) return <div>データ読み込み中...</div>;
  if (error) return <div>エラー: {error}</div>;

  return (
    <div>
      <h2>{userId}の{date}の解析結果</h2>
      {emotionData && (
        <div>
          <h3>感情タイムライン</h3>
          {emotionData.emotions?.map((emotion, index) => (
            <div key={index}>
              {emotion.time}秒: {emotion.emotion} (スコア: {emotion.score})
            </div>
          ))}
        </div>
      )}
      {sedData && (
        <div>
          <h3>音響イベント分析</h3>
          <pre>{JSON.stringify(sedData, null, 2)}</pre>
        </div>
      )}
    </div>
  );
};

export default EmotionDashboard;
```

## データ構造とファイル命名規則

### 📁 本番環境
```
/home/ubuntu/data/data_accounts/
├── user_id/
│   └── YYYY-MM-DD/
│       ├── raw/              # WAV音声ファイル（30分スロット）
│       ├── transcriptions/   # 文字起こしJSON
│       ├── prompt/           # プロンプトJSON
│       ├── emotion-timeline/ # 感情タイムライン
│       ├── sed/              # SEDタイムライン
│       └── sed-summary/      # SEDサマリー
```

### ⏰ WAVファイルの命名規則（重要）

**WAVファイル名は30分間隔の時刻スロットを表しています：**

- **形式**: `HH-MM.wav`（開始時刻を表示）
- **スロット間隔**: 30分ごと
- **1日のファイル数**: 48ファイル（24時間 × 2）
- **例**:
  ```
  00-00.wav  # 00:00-00:30の音声
  00-30.wav  # 00:30-01:00の音声
  01-00.wav  # 01:00-01:30の音声
  01-30.wav  # 01:30-02:00の音声
  ...
  23-00.wav  # 23:00-23:30の音声
  23-30.wav  # 23:30-24:00の音声
  ```

**🔄 ファイル名の重要性：**
- **時間軸の基準**: ファイル名が後続処理の時間情報として機能
- **自動マッピング**: 各解析（文字起こし、SED）が同じファイル名で関連付け
- **タイムライン構築**: 感情分析やイベント検出の時系列データの基盤
- **データ整合性**: user_id + date + 時刻スロットで一意性を保証

**📋 対応ファイルの例：**
```
raw/08-30.wav                 # 08:30-09:00の音声
transcriptions/08-30.json     # 上記音声の文字起こし
sed/08-30.json               # 上記音声のSED結果
```

この命名規則により、システム全体で時刻ベースのデータ管理と処理が可能になります。

### ローカル開発環境（WATCHME_LOCAL_DEV=1時）
```
vault/data/data_accounts/
├── user_id/
│   └── YYYY-MM-DD/
│       ├── raw/              # WAV音声ファイル
│       ├── transcriptions/   # 文字起こしJSON
│       ├── prompt/           # プロンプトJSON
│       ├── emotion-timeline/ # 感情タイムライン
│       ├── sed/              # SEDタイムライン
│       └── sed-summary/      # SEDサマリー
```

## 機能と特徴

### セキュリティ
- 本番環境優先の安全な環境分離
- 環境変数による明示的な開発モード切り替え
- ローカル開発データの Git 除外

### 安定性
- 適切なエラーハンドリングとログ出力
- ファイルサイズ制限（WAV: 100MB、JSON: 10MB）
- JSON形式の検証
- 日付形式の検証
- HTMLエスケープ処理
- 包括的な例外処理

### 利用者別用途

#### 🔹 iOS録音アプリ
- 音声ファイル（WAV）の送信：`POST /upload`

#### 🔹 Streamlitアプリ（音声解析・PoC）
- Whisper文字起こしJSONの送信：`POST /upload-transcription`
- ChatGPT用プロンプト送信：`POST /upload-prompt`
- SEDタイムライン/サマリーJSON送信：`POST /upload/analysis/sed-*`
- 各種JSONやWAVの表示・取得：`GET /view-file`, `GET /download-file`

#### 🔹 Web版ダッシュボード（React + Vite + Tailwind）
- 感情グラフの取得：`GET /api/users/{user_id}/logs/{date}/emotion-timeline`
- 行動グラフ（SEDサマリー）の取得：`GET /api/users/{user_id}/logs/{date}/sed-summary`

## 🚨 開発時の重要な注意事項

### 本番環境保護のためのルール

1. **コード変更は慎重に**: app.py の修正は本番環境で稼働中です
2. **requirements.txt**: 本番環境の依存関係のため、むやみに変更しないでください  
3. **テスト**: 重要な変更は本番環境でのテストを推奨します
4. **ローカル環境のカスタマイズ**: データ構造やパス設定の変更は禁止です

### 緊急時の対応

本番環境で問題が発生した場合：
1. 即座にGitで前のバージョンに戻す
2. サーバー上で `git pull` して修正を適用
3. ローカル環境での動作確認は補助的な目的のみ

### 推奨ワークフロー

```bash
# 開発時
cd vault/watchme_api
git pull            # 最新取得
# app.py編集
git add app.py
git commit -m "説明"
git push

# 本番反映（サーバー上で）
cd /home/ubuntu/watchme_api
git pull
# 必要に応じてサービス再起動
```

詳細は [LOCAL_DEV.md](LOCAL_DEV.md) を参照してください。

## 🖥️ サーバー運用（本番環境）

### systemd自動起動設定

**サーバー情報:**
- **SSH**: `ssh -i ~/watchme-key.pem ubuntu@3.24.16.82`
- **URL**: https://api.hey-watch.me
- **仮想環境**: `/home/ubuntu/venv_watchme/`

**WatchMe Vault APIは既にsystemdサービスとして設定済みです。AWSインスタンス起動時に自動でAPIが起動します。**

### サービス管理コマンド

```bash
# サービス状態確認
sudo systemctl status watchme-vault-api.service

# サービス停止
sudo systemctl stop watchme-vault-api.service

# サービス再起動
sudo systemctl restart watchme-vault-api.service

# サービス開始
sudo systemctl start watchme-vault-api.service

# ログ確認（リアルタイム）
sudo journalctl -u watchme-vault-api.service -f

# ログ確認（最新20行）
sudo journalctl -u watchme-vault-api.service -n 20
```

### サービス設定ファイル

**場所**: `/etc/systemd/system/watchme-vault-api.service`

```ini
[Unit]
Description=WatchMe Vault API Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=ubuntu
Group=ubuntu
WorkingDirectory=/home/ubuntu/watchme_api
Environment=PATH=/home/ubuntu/venv_watchme/bin:/usr/local/bin:/usr/bin:/bin
Environment=PYTHONPATH=/home/ubuntu/venv_watchme/lib/python3.12/site-packages
ExecStart=/home/ubuntu/venv_watchme/bin/uvicorn app:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal
SyslogIdentifier=watchme-vault-api

[Install]
WantedBy=multi-user.target
```

### 本番環境でのコード更新手順

```bash
# 1. サーバーにSSH接続
ssh -i ~/watchme-key.pem ubuntu@3.24.16.82

# 2. 最新コードを取得
cd /home/ubuntu/watchme_api
git pull origin main

# 3. サービス再起動（必要に応じて）
sudo systemctl restart watchme-vault-api.service

# 4. 動作確認
sudo systemctl status watchme-vault-api.service
curl -s http://localhost:8000/status | head -5
```

### トラブルシューティング

#### APIが起動しない場合
```bash
# 1. ログを確認
sudo journalctl -u watchme-vault-api.service -n 50

# 2. ポート使用状況確認
sudo lsof -i :8000

# 3. 手動起動テスト
cd /home/ubuntu/watchme_api
source /home/ubuntu/venv_watchme/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8000
```

#### サービス設定変更後
```bash
# 設定ファイル変更後は必須
sudo systemctl daemon-reload
sudo systemctl restart watchme-vault-api.service
```