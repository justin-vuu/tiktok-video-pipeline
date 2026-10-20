from __future__ import annotations

import base64
import binascii
import io
import json
import os
import re
import shutil
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, request, send_file, send_from_directory

from studio.catalog import STYLES
from studio.engine import (
    Cancelled, FONT, IMAGE_MODES, JOBS, LAYOUTS, ROOT, gemini_downloads, image_version, pipeline,
    save_json, save_scene_image,
)

app = Flask(__name__, static_folder=str(ROOT / "studio" / "static"), static_url_path="/static")
app.config["MAX_CONTENT_LENGTH"] = 16_384
lock = threading.RLock()
executor = ThreadPoolExecutor(max_workers=1)
events = {}
jobs = {}
JOBS.mkdir(parents=True, exist_ok=True)

def load_jobs():
    for saved in JOBS.glob("*/job.json"):
        try:
            job = json.loads(saved.read_text())
            if job["status"] in {"queued", "running"}:
                job.update(status="interrupted", message="Lần chạy trước bị ngắt. Bấm thử lại để tiếp tục.")
                save_json(saved, job)
            jobs[job["id"]] = job
        except (ValueError, KeyError, OSError):
            continue


@app.before_request
def local_only():
    if request.host.split(":")[0] not in {"127.0.0.1", "localhost"}:
        abort(403)
    if request.method == "POST" and request.path.endswith("/image"):
        request.max_content_length = 24 * 1024 * 1024
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        origin = request.headers.get("Origin")
        if origin and urlparse(origin).netloc != request.host:
            abort(403)
        if not request.is_json:
            abort(415)


@app.after_request
def security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "same-origin"
    response.headers["X-Frame-Options"] = "DENY"
    if request.path.startswith("/api/"):
        response.headers["Cache-Control"] = "no-store"
    return response


@app.errorhandler(400)
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(413)
@app.errorhandler(415)
def http_error(error):
    return jsonify(error={400: "Yêu cầu chưa hợp lệ.", 403: "Chỉ chấp nhận truy cập từ web trên máy này.",
                          404: "Không tìm thấy nội dung.", 413: "Nội dung hoặc ảnh quá lớn.",
                          415: "Yêu cầu phải có định dạng JSON."}.get(error.code, "Có lỗi xảy ra.")), error.code


@app.get("/")
def index():
    return send_from_directory(app.static_folder, "index.html")


@app.get("/api/health")
def health():
    return jsonify(
        providers={name: bool(shutil.which(name)) for name in ("claude", "codex")},
        ffmpeg=bool(shutil.which("ffmpeg") and shutil.which("ffprobe")),
        font=FONT.exists(),
        local=True,
    )


@app.get("/api/jobs")
def list_jobs():
    with lock:
        return jsonify(sorted(jobs.values(), key=lambda job: job["created"], reverse=True))


def validate_options(data):
    if not isinstance(data, dict):
        raise ValueError("Nội dung không hợp lệ.")
    topic = data.get("topic", "")
    if not isinstance(topic, str) or not 3 <= len(topic.strip()) <= 600:
        raise ValueError("Nhập chủ đề từ 3 đến 600 ký tự nhé.")
    style = data.get("style", "story")
    provider = data.get("provider", "claude")
    voice = data.get("voice", "auto")
    duration = data.get("duration", 45)
    images = data.get("images", "codex")
    layout = data.get("layout", "full")
    channel = data.get("channel", "")
    if not isinstance(style, str) or style not in STYLES:
        raise ValueError("Phong cách chưa hợp lệ.")
    if provider not in ("claude", "codex") or voice not in ("auto", "male", "female"):
        raise ValueError("AI hoặc giọng đọc chưa hợp lệ.")
    if type(duration) is not int or duration not in (30, 45, 60):
        raise ValueError("Chọn thời lượng 30, 45 hoặc 60 giây.")
    if not isinstance(images, str) or images not in IMAGE_MODES:
        raise ValueError("Nguồn ảnh chưa hợp lệ.")
    if not isinstance(layout, str) or layout not in LAYOUTS:
        raise ValueError("Bố cục video chưa hợp lệ.")
    if not isinstance(channel, str) or len(channel.strip()) > 28:
        raise ValueError("Tên kênh tối đa 28 ký tự.")
    for name in ("music", "subtitles"):
        if name in data and not isinstance(data[name], bool):
            raise ValueError("Tùy chọn nhạc và phụ đề phải là bật hoặc tắt.")
    return dict(topic=topic.strip(), style=style, provider=provider, voice=voice, duration=duration,
                images=images, layout=layout, channel=" ".join(channel.split()),
                music=data.get("music", True), subtitles=data.get("subtitles", True))


def update_job(job_id, **changes):
    with lock:
        jobs[job_id].update(changes)
        save_json(JOBS / job_id / "job.json", jobs[job_id])


def work(job_id, event):
    try:
        pipeline(jobs[job_id], lambda **changes: update_job(job_id, **changes), event)
    except Cancelled:
        update_job(job_id, status="cancelled", message="Đã dừng. Có thể tiếp tục bằng nút thử lại.")
    except Exception as error:
        app.logger.exception("Video job %s failed", job_id)
        update_job(job_id, status="error", error=str(error), message="Chưa hoàn tất video.")


@app.post("/api/jobs")
def create_job():
    try:
        options = validate_options(request.get_json())
    except ValueError as error:
        return jsonify(error=str(error)), 400
    if options["images"] == "codex" and not shutil.which("codex"):
        return jsonify(error="Chế độ Codex tự vẽ cần cài và đăng nhập Codex. Hãy chọn Gemini hoặc ảnh thư viện."), 400
    if not shutil.which(options["provider"]):
        return jsonify(error="Chưa tìm thấy AI đã chọn trên máy. Thử chọn AI khác."), 400
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe") or not FONT.exists():
        return jsonify(error="Máy thiếu FFmpeg hoặc font chữ. Xem hướng dẫn cài đặt trong README."), 400
    with lock:
        if any(job["status"] in {"queued", "running"} for job in jobs.values()):
            return jsonify(error="Đang tạo một video. Đợi hoàn tất hoặc dừng video hiện tại nhé."), 409
        job_id = uuid.uuid4().hex
        job = dict(id=job_id, title=options["topic"], options=options, status="queued",
                   progress=0, stage="script", message="Chuẩn bị tạo video…",
                   created=datetime.now(timezone.utc).isoformat())
        (JOBS / job_id).mkdir()
        jobs[job_id] = job
        event = events[job_id] = threading.Event()
        save_json(JOBS / job_id / "job.json", job)
        executor.submit(work, job_id, event)
        return jsonify(job), 202


@app.get("/api/jobs/<job_id>")
def get_job(job_id):
    with lock:
        if job_id not in jobs:
            abort(404)
        return jsonify(jobs[job_id])


@app.post("/api/jobs/<job_id>/cancel")
def cancel_job(job_id):
    with lock:
        if job_id not in jobs:
            abort(404)
        if jobs[job_id]["status"] in {"running", "queued"}:
            events[job_id].set()
        return jsonify(ok=True)


def start_job(job_id, message):
    update_job(job_id, status="queued", message=message, error=None)
    event = events[job_id] = threading.Event()
    executor.submit(work, job_id, event)
    return jsonify(jobs[job_id]), 202


@app.post("/api/jobs/<job_id>/retry")
def retry_job(job_id):
    with lock:
        if job_id not in jobs:
            abort(404)
        if any(job["status"] in {"queued", "running"} for job in jobs.values()):
            return jsonify(error="Đang có một video được tạo. Hãy đợi hoặc dừng video đó."), 409
        if jobs[job_id]["status"] not in {"error", "cancelled", "interrupted"}:
            return jsonify(error="Video này không cần thử lại."), 400
        return start_job(job_id, "Tiếp tục từ bước đã lưu…")


def storyboard_job(job_id, scene=None):
    if job_id not in jobs:
        abort(404)
    job = jobs[job_id]
    if job["options"].get("images") not in ("gemini", "codex") or not job.get("storyboard"):
        abort(404)
    if job["status"] in {"queued", "running"}:
        raise PermissionError("Đang dựng video này. Đợi xong rồi đổi ảnh nhé.")
    if scene is not None and not 1 <= scene <= len(job["storyboard"]):
        abort(404)
    return job


def refresh_storyboard(job_id):
    job = jobs[job_id]
    folder = JOBS / job_id
    for item in job["storyboard"]:
        item["image"] = image_version(folder / f"scene-{item['scene']}" / "source.jpg")
    first = folder / "scene-1" / "thumb.jpg"
    if job["storyboard"][0]["image"] and first.exists():
        shutil.copy2(first, folder / "cover.jpg")
        job["cover"] = f"/media/{job_id}/cover.jpg?v={image_version(folder / 'cover.jpg')}"
    missing = sum(1 for item in job["storyboard"] if not item["image"])
    if job["status"] == "waiting_images":
        need = ("cần tạo trên Gemini." if job["options"]["images"] == "gemini"
                else "chưa có. Bấm Cho Codex vẽ tiếp hoặc tự thả ảnh vào.")
        job["message"] = (f"Còn {missing} ảnh {need}" if missing
                          else "Đủ ảnh rồi. Bấm Dựng video để ghép thành phim.")
    elif job["status"] == "done":
        job["stale"] = True
    save_json(folder / "job.json", job)
    return job


@app.post("/api/jobs/<job_id>/scenes/<int:scene>/image")
def upload_scene_image(job_id, scene):
    value = (request.get_json(silent=True) or {}).get("image")
    if not isinstance(value, str) or not value.startswith("data:image/") or "," not in value:
        return jsonify(error="Chỉ nhận file ảnh."), 400
    try:
        raw = base64.b64decode(value.split(",", 1)[1], validate=True)
    except (binascii.Error, ValueError):
        return jsonify(error="Không đọc được ảnh. Thử chọn lại file nhé."), 400
    with lock:
        try:
            storyboard_job(job_id, scene)
            save_scene_image(JOBS / job_id / f"scene-{scene}", io.BytesIO(raw))
        except PermissionError as error:
            return jsonify(error=str(error)), 409
        except ValueError as error:
            return jsonify(error=str(error)), 400
        return jsonify(refresh_storyboard(job_id))


@app.post("/api/jobs/<job_id>/scenes/<int:scene>/clear")
def clear_scene_image(job_id, scene):
    with lock:
        try:
            storyboard_job(job_id, scene)
        except PermissionError as error:
            return jsonify(error=str(error)), 409
        for name in ("source.jpg", "thumb.jpg"):
            (JOBS / job_id / f"scene-{scene}" / name).unlink(missing_ok=True)
        if scene == 1:
            (JOBS / job_id / "cover.jpg").unlink(missing_ok=True)
            jobs[job_id]["cover"] = None
        return jsonify(refresh_storyboard(job_id))


@app.post("/api/jobs/<job_id>/import")
def import_downloads(job_id):
    with lock:
        try:
            job = storyboard_job(job_id)
        except PermissionError:
            return jsonify(job=jobs[job_id], imported=[], downloads="busy")
        empty = [item["scene"] for item in job["storyboard"] if not item["image"]]
        if not empty:
            return jsonify(job=job, imported=[], downloads="ok")
        seen = job.setdefault("imported", [])
        try:
            files = gemini_downloads(job.get("waiting_since", 0), set(seen))
        except OSError:
            return jsonify(job=job, imported=[], downloads="denied")
        imported = []
        for path in files:
            if not empty:
                break
            seen.append(path.name)
            try:
                save_scene_image(JOBS / job_id / f"scene-{empty[0]}", path)
            except ValueError:
                continue
            imported.append({"scene": empty.pop(0), "file": path.name})
        if imported or files:
            job = refresh_storyboard(job_id)
        return jsonify(job=job, imported=imported, downloads="ok")


@app.post("/api/jobs/<job_id>/render")
def render_job(job_id):
    with lock:
        if any(job["status"] in {"queued", "running"} for job in jobs.values()):
            return jsonify(error="Đang có một video được tạo. Hãy đợi hoặc dừng video đó."), 409
        try:
            job = storyboard_job(job_id)
        except PermissionError as error:
            return jsonify(error=str(error)), 409
        missing = [item["scene"] for item in job["storyboard"] if not item["image"]]
        if missing and job["options"]["images"] != "codex":
            return jsonify(error=f"Còn thiếu ảnh cảnh {', '.join(map(str, missing))}."), 400
        return start_job(job_id, "Codex vẽ tiếp các cảnh còn thiếu…" if missing else "Bắt đầu dựng video…")


@app.get("/media/<job_id>/<filename>")
def media(job_id, filename):
    allowed = {"final.mp4", "cover.jpg", "script.txt", "subtitles.srt", "sources.json"}
    if not re.fullmatch(r"[a-f0-9]{32}", job_id) or job_id not in jobs:
        abort(404)
    thumbnail = re.fullmatch(r"scene-([1-9])\.jpg", filename)
    if thumbnail:
        path = JOBS / job_id / f"scene-{thumbnail[1]}" / "thumb.jpg"
    elif filename in allowed:
        path = JOBS / job_id / filename
    else:
        abort(404)
    if not path.is_file():
        abort(404)
    return send_file(path, conditional=True, as_attachment=request.args.get("download") == "1",
                     download_name=f"lang-{job_id[:8]}{path.suffix}")


def main():
    load_jobs()
    port = int(os.environ.get("STUDIO_PORT", "7860"))
    print(f"\n  LẶNG Studio → http://127.0.0.1:{port}\n", flush=True)
    app.run(host="127.0.0.1", port=port, debug=False, threaded=True)


if __name__ == "__main__":
    main()
