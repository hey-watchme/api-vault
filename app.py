# app.py ― WatchMe File Receiver
#   1) /upload                        : 30 分スロット WAV 保存
#   2) /upload-transcription          : 文字起こし JSON 保存
#   3) /download                      : 個別 WAV 取得
#   4a) /upload-prompt                : プロンプト JSON 保存
#   4b) /status (+HTML / StaticFiles) : ディレクトリ一覧 & ファイル配信
#   5) /upload/analysis/emotion-timeline : ChatGPT 分析結果 JSON 保存

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from datetime import datetime
from pathlib import Path
from typing import List
import pytz
import os
import shutil

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
# 4b) 正しいツリー表示版 /status HTML
# =========================================
from datetime import datetime
from pathlib import Path
from typing import List

def _sort_dates(dates: List[str]) -> List[str]:
    def to_dt(s: str):
        try:
            return datetime.strptime(s, "%Y-%m-%d")
        except ValueError:
            return datetime.min
    return sorted(dates, key=to_dt, reverse=True)

def _walk_dir(path: Path, indent_lvl: int, lines: List[str]):
    ind = "    " * indent_lvl
    # 1) フォルダを先に昇順で
    for d in sorted([p for p in path.iterdir() if p.is_dir()]):
        lines.append(f"{ind}📂 {d.name}/")
        _walk_dir(d, indent_lvl + 1, lines)          # 再帰で深掘り
    # 2) ファイルを後に昇順で
    for f in sorted([p for p in path.iterdir() if p.is_file()]):
        lines.append(f"{ind}📄 {f.name}")

@app.get("/status", response_class=HTMLResponse)
async def status_all():
    if not os.path.exists(BASE_DIR):
        return "<h2>データフォルダが存在しません</h2>"

    html: List[str] = ["<h2>全ユーザーのデータ一覧</h2><pre>"]
    base = Path(BASE_DIR)

    # ── USER 層 ──
    for user_dir in sorted(p for p in base.iterdir() if p.is_dir()):
        html.append(f"👤 {user_dir.name}/")

        # ── DATE 層 (降順) ──
        for date_name in _sort_dates([d.name for d in user_dir.iterdir() if d.is_dir()]):
            date_path = user_dir / date_name
            html.append(f"  📅 {date_name}/")
            _walk_dir(date_path, 2, html)            # indent_lvl=2 で再帰開始
            html.append("")

    html.append("</pre>")
    return "\n".join(html)


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
