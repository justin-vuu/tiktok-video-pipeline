import base64
import io
import json
import os
import shutil
import sys
import threading
import time
import wave
from unittest.mock import Mock

import pytest
from PIL import Image

from studio import engine, server


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "JOBS", tmp_path)
    monkeypatch.setattr(server, "jobs", {})
    monkeypatch.setattr(server, "events", {})
    monkeypatch.setattr(server, "executor", Mock())
    return server.app.test_client()


@pytest.mark.parametrize("changes", [
    {"topic": ""}, {"topic": "x" * 601}, {"topic": []},
    {"style": ["story"]}, {"style": "unknown"}, {"provider": "bash"},
    {"voice": "bad"}, {"duration": 29}, {"duration": True},
    {"music": "false"}, {"subtitles": 1}, {"images": "dalle"}, {"images": ["gemini"]},
    {"layout": "grid"}, {"layout": ["frame"]}, {"channel": "x" * 29}, {"channel": 5},
])
def test_invalid_input_does_not_start_job(client, changes):
    response = client.post("/api/jobs", json={"topic": "Học cách buông bỏ", **changes})
    assert response.status_code == 400
    assert response.json["error"]
    server.executor.submit.assert_not_called()


def test_local_origin_and_host_checks(client):
    assert client.post("/api/jobs", json={"topic": "Chủ đề"}, headers={"Origin": "https://evil.example"}).status_code == 403
    assert client.get("/api/jobs", headers={"Host": "evil.example"}).status_code == 403
    assert client.post("/api/jobs", data="topic=abc").status_code == 415


def test_single_job_and_cancel(client, monkeypatch):
    monkeypatch.setattr(server.shutil, "which", lambda name: f"/bin/{name}")
    monkeypatch.setattr(server, "FONT", engine.FONT)
    response = client.post("/api/jobs", json={"topic": "Đi chậm lại"})
    assert response.status_code == 202
    job_id = response.json["id"]
    assert client.post("/api/jobs", json={"topic": "Đi tiếp nhé"}).status_code == 409
    assert client.post(f"/api/jobs/{job_id}/cancel", json={}).status_code == 200
    assert server.events[job_id].is_set()
    assert server.executor.submit.call_count == 1


def test_retry_preserves_script_and_rejects_finished_jobs(client):
    job_id = "a" * 32
    folder = server.JOBS / job_id
    folder.mkdir()
    script = folder / "script.json"
    script.write_text('{"title":"saved"}')
    server.jobs[job_id] = {"id": job_id, "status": "error"}
    assert client.post(f"/api/jobs/{job_id}/retry", json={}).status_code == 202
    assert script.read_text() == '{"title":"saved"}'
    assert not server.events[job_id].is_set()
    server.jobs[job_id]["status"] = "done"
    assert client.post(f"/api/jobs/{job_id}/retry", json={}).status_code == 400


def test_download_allowlist_and_range(client):
    job_id = "b" * 32
    folder = server.JOBS / job_id
    folder.mkdir()
    (folder / "final.mp4").write_bytes(b"0123456789")
    (folder / "job.json").write_text("{}")
    server.jobs[job_id] = {"id": job_id, "status": "done"}
    assert client.get(f"/media/{job_id}/job.json").status_code == 404
    response = client.get(f"/media/{job_id}/final.mp4", headers={"Range": "bytes=2-5"})
    assert response.status_code == 206
    assert response.data == b"2345"
    assert "attachment" in client.get(f"/media/{job_id}/final.mp4?download=1").headers["Content-Disposition"]


def test_restart_marks_running_job_interrupted(client):
    job_id = "c" * 32
    folder = server.JOBS / job_id
    folder.mkdir()
    engine.save_json(folder / "job.json", {"id": job_id, "status": "running"})
    server.load_jobs()
    assert server.jobs[job_id]["status"] == "interrupted"
    assert json.loads((folder / "job.json").read_text())["status"] == "interrupted"


def test_caption_times_and_timestamp_rollover():
    words = [{"text": "tiếng", "start": index * .3, "end": index * .3 + .2} for index in range(17)]
    captions = engine.caption_groups(words, 5.2)
    assert len(captions) >= 3
    assert all(left["end"] <= right["start"] for left, right in zip(captions, captions[1:]))
    assert captions[-1]["end"] == 5.2
    assert engine.srt_timestamp(59.9996) == "00:01:00,000"


def test_script_rejects_unknown_photos():
    with pytest.raises(ValueError):
        engine.validate_script({"title": "Test", "scenes": [
            {"text": "Một đoạn văn đủ dài để thử.", "photo": "https://attacker.example"} for _ in range(3)
        ]})


def test_subtitles_preserve_punctuation_and_sentence_breaks():
    original = 'Mình nói “được mà”. Tối đó, mình về.'
    tokens = ["Mình", "nói", "được", "mà", "Tối", "đó", "mình", "về"]
    words = [{"text": token, "start": index, "end": index + .8} for index, token in enumerate(tokens)]
    restored = engine.restore_punctuation(words, original)
    assert " ".join(word["text"] for word in restored) == original
    captions = engine.caption_groups(restored, 8)
    assert captions[0]["text"] == 'Mình nói “được mà”.'
    assert captions[1]["text"] == "Tối đó, mình về."
    assert words[2]["text"] == "được"


def test_command_cancels_running_process():
    event = threading.Event()
    timer = threading.Timer(.3, event.set)
    timer.start()
    try:
        with pytest.raises(engine.Cancelled):
            engine.command([sys.executable, "-c", "import time; time.sleep(30)"], event)
    finally:
        timer.cancel()


@pytest.mark.skipif(not shutil.which("ffmpeg") or not engine.FONT.exists(), reason="Needs local media tools")
@pytest.mark.parametrize("subtitles", [True, False])
def test_real_render_with_and_without_subtitles(tmp_path, subtitles):
    Image.new("RGB", (720, 1280), "#52664b").save(tmp_path / "background.jpg")
    with wave.open(str(tmp_path / "voice.mp3"), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(22050)
        audio.writeframes(b"\0\0" * 22050)
    captions = [{"text": "Chậm lại một chút nhé.", "start": 0, "end": 1}] if subtitles else []
    output = engine.render_scene(tmp_path, 1, captions, threading.Event())
    assert output.stat().st_size > 1000
    assert 0.9 <= engine.audio_duration(output) <= 1.2


@pytest.mark.skipif(not shutil.which("ffmpeg") or not engine.FONT.exists(), reason="Needs local media tools")
def test_frame_layout_render(tmp_path):
    frame = engine.frame_loop(tmp_path, "Có những thiệt thòi chẳng ai nhìn thấy", "Kênh thử", threading.Event())
    assert 3.9 <= engine.audio_duration(frame) <= 4.1 and (tmp_path / "frame.png").exists()
    scene = tmp_path / "scene-1"
    scene.mkdir()
    Image.new("RGB", (1536, 1024), "#30343c").save(tmp_path / "source.jpg")
    engine.prepare_band(tmp_path / "source.jpg", scene / "background.jpg")
    with wave.open(str(scene / "voice.mp3"), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(22050)
        audio.writeframes(b"\0\0" * 22050 * 2)
    words = [{"text": word, "start": index * 0.3, "end": index * 0.3 + 0.25}
             for index, word in enumerate("Không phải một ngày mà là cả đời.".split())]
    captions = engine.caption_groups(words, 2, 16, 3)
    assert all(len(caption["words"]) <= 3 for caption in captions)
    output = engine.render_scene(scene, 2, captions, threading.Event(), frame=frame, offset=5.5)
    assert 1.9 <= engine.audio_duration(output) <= 2.2
    engine.frame_cover(tmp_path, tmp_path / "source.jpg", tmp_path / "cover.jpg")
    assert Image.open(tmp_path / "cover.jpg").size == (720, 1280)


def test_frame_prompt_asks_for_landscape_and_wide_thumb(tmp_path):
    script = {**engine.validate_script(GEMINI_SCRIPT, "gemini"), "layout": "frame"}
    assert "16:9" in engine.scene_prompt(script, 0) and "9:16" not in engine.scene_prompt(script, 1)
    engine.save_scene_image(tmp_path / "scene-1", io.BytesIO(png_bytes(size=(1536, 1024))))
    assert Image.open(tmp_path / "scene-1" / "thumb.jpg").size == (360, 640)


GEMINI_SCRIPT = {
    "title": "Chỗ của mình",
    "look": "Ảnh điện ảnh chân thực. Lan, nữ 27 tuổi, tóc đen ngang vai, áo sơ mi kem.",
    "scenes": [
        {"text": f"Lời đọc cảnh số {index} đủ dài.", "image": f"Lan ngồi bên bàn làm việc, cảnh {index}."}
        for index in range(1, 4)
    ],
}


def png_bytes(color="#52664b", size=(540, 960)):
    buffer = io.BytesIO()
    Image.new("RGB", size, color).save(buffer, "PNG")
    return buffer.getvalue()


def test_gemini_script_needs_look_and_scene_images():
    script = engine.validate_script(GEMINI_SCRIPT, "gemini")
    assert script["look"].startswith("Ảnh điện ảnh")
    assert all(set(scene) == {"text", "image"} for scene in script["scenes"])
    with pytest.raises(ValueError):
        engine.validate_script({**GEMINI_SCRIPT, "look": ""}, "gemini")
    with pytest.raises(ValueError):
        engine.validate_script({**GEMINI_SCRIPT, "scenes": [{"text": "Lời đọc đủ dài nhé.", "photo": "forest"}] * 3}, "gemini")


def test_gemini_pipeline_waits_for_images_with_voice_timings(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "JOBS", tmp_path)
    monkeypatch.setattr(engine, "speech", lambda scene, voice, folder, event: ([{"text": "a", "start": 0, "end": .4}], 2.5))
    job = {"id": "d" * 32, "options": {"style": "story", "voice": "auto", "images": "gemini", "provider": "claude",
                                        "music": True, "subtitles": True, "duration": 30}}
    folder = tmp_path / job["id"]
    folder.mkdir()
    engine.save_json(folder / "script.json", GEMINI_SCRIPT)
    engine.pipeline(job, job.update, threading.Event())
    assert job["status"] == "waiting_images"
    assert [(item["start"], item["end"]) for item in job["storyboard"]] == [(0, 2.5), (2.5, 5), (5, 7.5)]
    assert all(item["image"] is None for item in job["storyboard"])
    assert "9:16" in job["storyboard"][0]["prompt"] and "tóc đen ngang vai" in job["storyboard"][2]["prompt"]
    assert job["waiting_since"] > 0


@pytest.fixture
def board_job(client):
    job_id = "e" * 32
    folder = server.JOBS / job_id
    folder.mkdir()
    server.jobs[job_id] = {
        "id": job_id, "status": "waiting_images", "title": "Test", "options": {"images": "gemini"},
        "waiting_since": time.time() - 60,
        "storyboard": [{"scene": index, "start": 0, "end": 1, "text": "x", "prompt": "p", "image": None}
                       for index in range(1, 4)],
    }
    return job_id


def test_upload_scene_image_and_thumbnail(client, board_job):
    image = "data:image/png;base64," + base64.b64encode(png_bytes()).decode()
    response = client.post(f"/api/jobs/{board_job}/scenes/1/image", json={"image": image})
    assert response.status_code == 200
    assert response.json["storyboard"][0]["image"]
    assert response.json["cover"].startswith(f"/media/{board_job}/cover.jpg")
    assert response.json["message"] == "Còn 2 ảnh cần tạo trên Gemini."
    assert client.get(f"/media/{board_job}/scene-1.jpg").status_code == 200
    assert client.get(f"/media/{board_job}/scene-1/source.jpg").status_code == 404
    assert client.post(f"/api/jobs/{board_job}/scenes/1/image", json={"image": "data:image/png;base64,bm9wZQ=="}).status_code == 400
    assert client.post(f"/api/jobs/{board_job}/scenes/9/image", json={"image": image}).status_code == 404
    server.jobs[board_job]["status"] = "running"
    assert client.post(f"/api/jobs/{board_job}/scenes/2/image", json={"image": image}).status_code == 409


def test_import_gemini_downloads_in_order_then_render(client, board_job, tmp_path, monkeypatch):
    downloads = tmp_path / "downloads"
    downloads.mkdir()
    monkeypatch.setattr(engine, "DOWNLOADS", downloads)
    old = downloads / "Gemini_Generated_Image_old.png"
    old.write_bytes(png_bytes())
    os.utime(old, (time.time() - 3600,) * 2)
    (downloads / "holiday.png").write_bytes(png_bytes())
    for offset, name in enumerate(["Gemini_Generated_Image_b.png", "Gemini_Generated_Image_a (1).png"]):
        (downloads / name).write_bytes(png_bytes())
        os.utime(downloads / name, (time.time() - 10 + offset,) * 2)
    assert client.post(f"/api/jobs/{board_job}/render", json={}).status_code == 400
    result = client.post(f"/api/jobs/{board_job}/import", json={}).json
    assert [item["file"] for item in result["imported"]] == ["Gemini_Generated_Image_b.png", "Gemini_Generated_Image_a (1).png"]
    assert [bool(item["image"]) for item in result["job"]["storyboard"]] == [True, True, False]
    assert client.post(f"/api/jobs/{board_job}/import", json={}).json["imported"] == []
    (downloads / "Gemini_Generated_Image_c.png").write_bytes(png_bytes())
    assert client.post(f"/api/jobs/{board_job}/import", json={}).json["imported"][0]["scene"] == 3
    assert client.post(f"/api/jobs/{board_job}/render", json={}).status_code == 202
    assert server.executor.submit.call_count == 1
    assert client.post(f"/api/jobs/{board_job}/scenes/2/clear", json={}).status_code == 409


def codex_job(tmp_path, monkeypatch):
    monkeypatch.setattr(engine, "JOBS", tmp_path)
    monkeypatch.setattr(engine, "speech", lambda scene, voice, folder, event: ([{"text": "a", "start": 0, "end": .4}], 2.5))
    job = {"id": "f" * 32, "options": {"style": "story", "voice": "auto", "images": "codex", "provider": "claude",
                                        "music": False, "subtitles": True, "duration": 30}}
    (tmp_path / job["id"]).mkdir()
    engine.save_json(tmp_path / job["id"] / "script.json", GEMINI_SCRIPT)
    return job


def test_codex_failure_falls_back_to_storyboard(tmp_path, monkeypatch):
    job = codex_job(tmp_path, monkeypatch)
    drawn = []

    def fake_draw(script, index, folder, event):
        if index == 1:
            raise RuntimeError("AI báo giới hạn sử dụng.")
        drawn.append(index)
        engine.save_scene_image(folder / f"scene-{index + 1}", io.BytesIO(png_bytes()))

    monkeypatch.setattr(engine, "draw_scene", fake_draw)
    engine.pipeline(job, job.update, threading.Event())
    assert drawn == [0]
    assert job["status"] == "waiting_images"
    assert "cảnh 2" in job["message"] and "giới hạn" in job["message"]
    assert [bool(item["image"]) for item in job["storyboard"]] == [True, False, False]
    assert job["cover"].startswith(f"/media/{job['id']}/cover.jpg")


def test_codex_render_endpoint_allows_missing_images(client, board_job):
    server.jobs[board_job]["options"]["images"] = "codex"
    assert client.post(f"/api/jobs/{board_job}/render", json={}).status_code == 202
