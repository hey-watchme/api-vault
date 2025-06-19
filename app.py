# app.py ― WatchMe File Receiver
#   1) /upload                        : 30 分スロット WAV 保存
#   2) /upload-transcription          : 文字起こし JSON 保存
#   3) /download                      : 個別 WAV 取得
#   4a) /upload-prompt                : プロンプト JSON 保存
#   4b) /status (+HTML / StaticFiles) : ディレクトリ一覧 & ファイル配信
#   5) /upload/analysis/emotion-timeline : ChatGPT 分析結果 JSON 保存

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
# 5) ChatGPT 分析 JSON アップロード
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
# 🔊 SEDタイムライン JSON アップロード
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
