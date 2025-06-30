# =========================================
# app.py ― WatchMe Vault API
#
# 本アプリケーションは、WatchMe プロジェクトにおける
# 音声データと各種解析ファイルを保存・取得するための
# FastAPI ベースのファイル受け渡しAPIです。
#
# 📦 名称：**WatchMe Vault API**
# 📁 役割：音声ファイル（WAV）や解析結果（JSON）を
#          ユーザー／日付単位のディレクトリ構成で管理し、
#          iOSアプリ・Streamlit・Webダッシュボード間の
#          データ授受を安全に行う
#
# 🔹 iOS録音アプリ用途：
#     - 音声ファイル（WAV）の送信：`/upload`
#
# 🔹 Streamlitアプリ用途（音声解析・PoC）：
#     - Whisper文字起こしJSONの送信：`/upload-transcription`
#     - ChatGPT用プロンプト（emotion-timeline）送信：`/upload-prompt`
#     - SEDタイムライン / SEDサマリーJSON送信：`/upload/analysis/sed-*`
#     - 各種JSONやWAVの表示／取得：`/view-file`, `/download-file`
#
# 🔹 Web版ダッシュボード用途（React + Vite + Tailwind）：
#     - 感情グラフの取得：`/api/users/{user_id}/logs/{date}/emotion-timeline` ← NEW!
#     - 行動グラフ（SEDサマリー）の取得：`/api/users/{user_id}/logs/{date}/sed-summary`
#     - これらのJSONは iOS / Streamlit 側から事前にアップロードされた分析結果
#
# 🔧 データ構造：
#     BASE_DIR/user_id/YYYY-MM-DD/{raw, transcriptions, sed, prompt, emotion-timeline, sed-summary}/
#     例: /home/ubuntu/data/data_accounts/user123/2025-06-21/sed-summary/result.json
#
# =========================================


from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from pathlib import Path
from typing import List
import pytz
import os
import shutil
import json
import urllib.parse

# =========================================
# 基本設定
# =========================================
# 本番環境優先の安全な環境分離
# デフォルトは本番環境設定、ローカル開発時のみ環境変数で切り替え
if os.getenv("WATCHME_LOCAL_DEV") == "1":
    # ローカル開発環境（環境変数明示時のみ）
    BASE_DIR = str(Path(__file__).parent / "data" / "data_accounts")
else:
    # 本番環境（デフォルト）
    BASE_DIR = "/home/ubuntu/data/data_accounts"

app = FastAPI(title="WatchMe File Receiver")

# StaticFiles で /status/** を公開（/status は後述 HTML が担当）
app.mount("/status", StaticFiles(directory=BASE_DIR), name="status")

# =========================================
# 1) WAV アップロード (/upload)
# =========================================
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Form("user123"),
    timestamp: str = Form(None)  # 予約：iOS の送信タイムスタンプ
):
    jst = pytz.timezone("Asia/Tokyo")
    now = datetime.now(jst)
    date_str = now.strftime("%Y-%m-%d")
    slot_min = "00" if now.minute < 30 else "30"
    slot_str = f"{now.hour:02d}-{slot_min}"

    save_dir = os.path.join(BASE_DIR, user_id, date_str, "raw")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{slot_str}.wav")

    with open(save_path, "wb") as f:
        f.write(await file.read())

    return JSONResponse({"status": "ok", "path": save_path})

# =========================================
# 2) 文字起こし JSON アップロード (/upload-transcription)
# =========================================
@app.post("/upload-transcription")
async def upload_transcription(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    date: str = Form(...),           # "2025-06-15"
    time_block: str = Form(...),     # "00-00"
):
    save_dir = os.path.join(BASE_DIR, user_id, date, "transcriptions")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"{time_block}.json")

    with open(save_path, "wb") as buf:
        buf.write(await file.read())

    return JSONResponse({"status": "success", "path": save_path})

# =========================================
# 3) 個別 WAV ダウンロード (/download)
# =========================================
@app.get("/download")
async def download_file(user_id: str, date: str, slot: str):
    file_path = f"{BASE_DIR}/{user_id}/{date}/raw/{slot}.wav"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(file_path, media_type="audio/wav", filename=f"{slot}.wav")

# =========================================
# 3b) SED JSON ダウンロード (/download-sed) - NEW!
# =========================================
@app.get("/download-sed")
async def download_sed_file(user_id: str, date: str, slot: str):
    """
    SEDファイル専用ダウンロードエンドポイント
    パス: {user_id}/{date}/sed/{slot}.json
    """
    file_path = f"{BASE_DIR}/{user_id}/{date}/sed/{slot}.json"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"SED file not found: {user_id}/{date}/sed/{slot}.json")

    return FileResponse(file_path, media_type="application/json", filename=f"{slot}.json")

# =========================================
# 3c) OpenSMILE JSON ダウンロード (/download-opensmile) - NEW!
# =========================================
@app.get("/download-opensmile")
async def download_opensmile_file(user_id: str, date: str, slot: str):
    """
    OpenSMILEファイル専用ダウンロードエンドポイント
    パス: {user_id}/{date}/opensmile/{slot}.json
    """
    file_path = f"{BASE_DIR}/{user_id}/{date}/opensmile/{slot}.json"
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"OpenSMILE file not found: {user_id}/{date}/opensmile/{slot}.json")

    return FileResponse(file_path, media_type="application/json", filename=f"{slot}.json")

# =========================================
# 4a) プロンプト JSON アップロード (/upload-prompt)
# =========================================
@app.post("/upload-prompt")
async def upload_prompt(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    date: str  = Form(...)
):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json allowed")

    save_dir = os.path.join(BASE_DIR, user_id, date, "prompt")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "emotion-timeline_gpt_prompt.json")

    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    return JSONResponse({"status": "ok", "path": save_path})

# =========================================
# 新しいファイル関連エンドポイント
# =========================================

@app.get("/download-file")
async def download_file_by_path(file_path: str = Query(...)):
    """ファイルパスを指定してファイルをダウンロード"""
    full_path = os.path.join(BASE_DIR, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    filename = os.path.basename(full_path)
    
    # ファイルタイプに応じたmedia_typeを設定
    if filename.endswith('.wav'):
        media_type = "audio/wav"
    elif filename.endswith('.json'):
        media_type = "application/json"
    else:
        media_type = "application/octet-stream"
    
    return FileResponse(full_path, media_type=media_type, filename=filename)

@app.get("/view-file")
async def view_file_content(file_path: str = Query(...)):
    """JSONファイルの内容を表示"""
    full_path = os.path.join(BASE_DIR, file_path)
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    if not file_path.endswith('.json'):
        raise HTTPException(status_code=400, detail="Only JSON files can be viewed")
    
    try:
        with open(full_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{os.path.basename(file_path)} - WatchMe Vault</title>
            <style>
                body {{ font-family: 'Monaco', 'Menlo', monospace; margin: 20px; background: #f5f5f5; }}
                .header {{ background: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                .content {{ background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
                pre {{ background: #f8f8f8; padding: 15px; border-radius: 5px; overflow-x: auto; }}
                .back-link {{ color: #007bff; text-decoration: none; }}
                .back-link:hover {{ text-decoration: underline; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📄 {os.path.basename(file_path)}</h2>
                <p><strong>ファイルパス:</strong> {file_path}</p>
                <a href="/status" class="back-link">← データ一覧に戻る</a>
            </div>
            <div class="content">
                <h3>ファイル内容:</h3>
                <pre>{json.dumps(content, ensure_ascii=False, indent=2)}</pre>
            </div>
        </body>
        </html>
        """
        return HTMLResponse(html)
    
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

# =========================================
# 4b) 改良版 /status HTML（リンク付き）
# =========================================

def _sort_dates(dates: List[str]) -> List[str]:
    def to_dt(s: str):
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return datetime.min
    return sorted(dates, key=to_dt, reverse=True)

def _get_relative_path(full_path: Path, base_path: Path) -> str:
    """ベースパスからの相対パスを取得"""
    return str(full_path.relative_to(base_path))

def _walk_dir_with_links(path: Path, base_path: Path, indent_lvl: int, lines: List[str]):
    ind = "    " * indent_lvl
    
    # 1) フォルダを先に昇順で
    for d in sorted([p for p in path.iterdir() if p.is_dir()]):
        lines.append(f'{ind}📂 <span style="font-weight: bold;">{d.name}/</span>')
        _walk_dir_with_links(d, base_path, indent_lvl + 1, lines)
    
    # 2) ファイルを後に昇順で
    for f in sorted([p for p in path.iterdir() if p.is_file()]):
        relative_path = _get_relative_path(f, base_path)
        encoded_path = urllib.parse.quote(relative_path)
        
        # ファイルタイプに応じたリンクを生成
        if f.name.endswith('.wav'):
            download_link = f'/download-file?file_path={encoded_path}'
            file_link = f'<a href="{download_link}" style="color: #28a745; text-decoration: none;" title="WAVファイルをダウンロード">🎵 {f.name}</a>'
        elif f.name.endswith('.json'):
            view_link = f'/view-file?file_path={encoded_path}'
            download_link = f'/download-file?file_path={encoded_path}'
            file_link = f'<a href="{view_link}" style="color: #007bff; text-decoration: none;" title="JSONファイルを表示">📄 {f.name}</a> <a href="{download_link}" style="color: #6c757d; text-decoration: none; font-size: 0.8em;" title="ダウンロード">[DL]</a>'
        else:
            download_link = f'/download-file?file_path={encoded_path}'
            file_link = f'<a href="{download_link}" style="color: #6c757d; text-decoration: none;" title="ファイルをダウンロード">📄 {f.name}</a>'
        
        lines.append(f"{ind}{file_link}")

@app.get("/status", response_class=HTMLResponse)
async def status_all():
    if not os.path.exists(BASE_DIR):
        return "<h2>データフォルダが存在しません</h2>"

    html_lines = [
        """
        <!DOCTYPE html>
        <html>
        <head>
            <title>WatchMe Vault - データ一覧</title>
            <style>
                body { 
                    font-family: 'Monaco', 'Menlo', monospace; 
                    margin: 20px; 
                    background: #f5f5f5; 
                    line-height: 1.6;
                }
                .header { 
                    background: white; 
                    padding: 20px; 
                    border-radius: 8px; 
                    margin-bottom: 20px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .content { 
                    background: white; 
                    padding: 20px; 
                    border-radius: 8px; 
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                pre { 
                    background: #f8f8f8; 
                    padding: 15px; 
                    border-radius: 5px; 
                    overflow-x: auto;
                    font-size: 14px;
                }
                a { text-decoration: none; }
                a:hover { text-decoration: underline; }
                .legend {
                    background: #e9ecef;
                    padding: 10px;
                    border-radius: 5px;
                    margin-bottom: 15px;
                    font-size: 0.9em;
                }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🗂️ WatchMe Vault - データ一覧</h2>
                <div class="legend">
                    <strong>操作方法:</strong>
                    🎵 WAVファイル（クリックでダウンロード） | 
                    📄 JSONファイル（クリックで内容表示、[DL]でダウンロード）
                </div>
            </div>
            <div class="content">
                <pre>
        """
    ]
    
    base = Path(BASE_DIR)
    
    # ── USER 層 ──
    for user_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        html_lines.append(f'👤 <span style="font-weight: bold; color: #007bff;">{user_dir.name}/</span>')
        
        # ── DATE 層 (降順) ──
        for date_name in _sort_dates([d.name for d in user_dir.iterdir() if d.is_dir()]):
            date_path = user_dir / date_name
            html_lines.append(f'  📅 <span style="font-weight: bold; color: #28a745;">{date_name}/</span>')
            _walk_dir_with_links(date_path, base, 2, html_lines)
            html_lines.append("")
    
    html_lines.extend([
        """
                </pre>
            </div>
        </body>
        </html>
        """
    ])
    
    return "\n".join(html_lines)

# =========================================
# 5) 心理グラフ作成用 ChatGPT 分析 JSON アップロード
#    (/upload/analysis/emotion-timeline)
# =========================================
@app.post("/upload/analysis/emotion-timeline")
async def upload_emotion_timeline(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    date: str    = Form(...)
):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json allowed")

    save_dir = os.path.join(BASE_DIR, user_id, date, "emotion-timeline")
    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, "emotion-timeline.json")

    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    return JSONResponse({"status": "ok", "path": save_path})

# =========================================
# 🔊 行動グラフ作成用 SEDタイムライン JSON アップロード
#     (/upload/analysis/sed-timeline)
# =========================================
@app.post("/upload/analysis/sed-timeline")
async def upload_sed_timeline(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    date: str = Form(...),            # 例: "2025-06-18"
    time_block: str = Form(...),      # 例: "00-00"
):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files allowed")

    save_dir = os.path.join(BASE_DIR, user_id, date, "sed")
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, f"{time_block}.json")
    
    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    return JSONResponse({"status": "ok", "path": save_path})

# =========================================
# 🔊 行動グラフ保存用 SEDサマリー JSON アップロード
#     (/upload/analysis/sed-summary)
# =========================================
@app.post("/upload/analysis/sed-summary")
async def upload_sed_summary(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    date: str = Form(...)
):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files allowed")

    save_dir = os.path.join(BASE_DIR, user_id, date, "sed-summary")
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, "result.json")
    
    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    return JSONResponse({"status": "ok", "path": save_path})

# =========================================
# 4f) OpenSMILE Summary JSON アップロード - NEW!
#     (/upload/analysis/opensmile-summary)
# =========================================
@app.post("/upload/analysis/opensmile-summary")
async def upload_opensmile_summary(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    date: str = Form(...)
):
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files allowed")

    save_dir = os.path.join(BASE_DIR, user_id, date, "opensmile-summary")
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, "result.json")
    
    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    return JSONResponse({"status": "ok", "path": save_path})

# =========================================
# 🔎 Dashboard Web用 感情タイムライン JSON 取得
#     (/api/users/{user_id}/logs/{date}/emotion-timeline)
# =========================================
@app.get("/api/users/{user_id}/logs/{date}/emotion-timeline")
async def get_emotion_timeline(user_id: str, date: str):
    """
    感情タイムラインの emotion-timeline.json を返す GET API
    例: /api/users/user123/logs/2025-06-25/emotion-timeline
    """
    file_path = os.path.join(BASE_DIR, user_id, date, "emotion-timeline", "emotion-timeline.json")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Emotion timeline file not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in emotion-timeline.json")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# =========================================
# 🔎 Dashboard Web用 行動グラフ表示用 SEDサマリー JSON 取得
#     (/api/users/{user_id}/logs/{date}/sed-summary)
# =========================================
@app.get("/api/users/{user_id}/logs/{date}/sed-summary")
async def get_sed_summary(user_id: str, date: str):
    """
    SED summary の result.json を返す GET API
    例: /api/users/user123/logs/2025-06-21/sed-summary
    """
    file_path = os.path.join(BASE_DIR, user_id, date, "sed-summary", "result.json")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="SED summary file not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in result.json")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# =========================================
# 🎵 OpenSMILE特徴量 個別JSONファイル アップロード 
#     (/upload/analysis/opensmile-features)
# =========================================
@app.post("/upload/analysis/opensmile-features")
async def upload_opensmile_features(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    date: str = Form(...),            # 例: "2025-06-25"
    time_slot: str = Form(...),       # 例: "20-30"
):
    """
    OpenSMILE API から生成された個別時間スロットの特徴量JSONファイルをアップロード
    保存先: /home/ubuntu/data/data_accounts/{user_id}/{date}/opensmile/{time_slot}.json
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only .json files allowed")

    save_dir = os.path.join(BASE_DIR, user_id, date, "opensmile")
    os.makedirs(save_dir, exist_ok=True)

    save_path = os.path.join(save_dir, f"{time_slot}.json")
    
    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    return JSONResponse({"status": "ok", "path": save_path})


# =========================================
# 🔎 OpenSMILE特徴量 個別JSONファイル取得
#     (/api/users/{user_id}/logs/{date}/opensmile/{time_slot})
# =========================================
@app.get("/api/users/{user_id}/logs/{date}/opensmile/{time_slot}")
async def get_opensmile_features(user_id: str, date: str, time_slot: str):
    """
    指定された時間スロットのOpenSMILE特徴量JSONを返す GET API
    例: /api/users/user123/logs/2025-06-25/opensmile/20-30
    """
    file_path = os.path.join(BASE_DIR, user_id, date, "opensmile", f"{time_slot}.json")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"OpenSMILE features file not found for slot {time_slot}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail=f"Invalid JSON format in {time_slot}.json")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# =========================================
# 🔎 OpenSMILE特徴量 統合JSONファイル取得
#     (/api/users/{user_id}/logs/{date}/opensmile-summary)
# =========================================
@app.get("/api/users/{user_id}/logs/{date}/opensmile-summary")
async def get_opensmile_summary(user_id: str, date: str):
    """
    統合OpenSMILE特徴量JSONを返す GET API
    例: /api/users/user123/logs/2025-06-25/opensmile-summary
    """
    file_path = os.path.join(BASE_DIR, user_id, date, "opensmile", "vault_features_timeline.json")

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="OpenSMILE summary file not found")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JSONResponse(content=data)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON format in vault_features_timeline.json")

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

# =========================================
# 🔎 利用可能なOpenSMILE特徴量スロット一覧取得
#     (/api/users/{user_id}/logs/{date}/opensmile)
# =========================================
@app.get("/api/users/{user_id}/logs/{date}/opensmile")
async def list_opensmile_features(user_id: str, date: str):
    """
    指定された日付で利用可能なOpenSMILE特徴量ファイル一覧を返す GET API
    例: /api/users/user123/logs/2025-06-25/opensmile
    """
    features_dir = os.path.join(BASE_DIR, user_id, date, "opensmile")

    if not os.path.exists(features_dir):
        return JSONResponse(content={"available_slots": [], "count": 0, "has_summary": False})

    try:
        all_files = [f for f in os.listdir(features_dir) if f.endswith('.json')]
        
        # 個別ファイル（時間スロット）を抽出
        time_slot_files = [f for f in all_files if f != "vault_features_timeline.json"]
        time_slots = [f.replace('.json', '') for f in time_slot_files]
        time_slots.sort()  # 時間順にソート
        
        # 統合ファイルの存在確認
        has_summary = "vault_features_timeline.json" in all_files

        return JSONResponse(content={
            "available_slots": time_slots,
            "count": len(time_slots),
            "has_summary": has_summary,
            "directory": features_dir
        })

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing OpenSMILE features: {str(e)}")
