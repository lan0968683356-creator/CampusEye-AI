"""CampusEye AI: local-only, privacy-conscious anonymous occupancy demo.

Run: python app.py
Open: http://127.0.0.1:5000

No face recognition, person identification, or video recording.
All analytics are anonymous aggregates. Use only with permission and consent.
"""
from __future__ import annotations

import atexit
from collections import deque
from datetime import datetime, timedelta
import math
import os
import sys
from pathlib import Path
import sqlite3
import threading
import time
import uuid
from typing import Any

from flask import Flask, Response, jsonify, render_template, request

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None

# Packaged resources are extracted by PyInstaller; writable data stays outside the EXE.
ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
DATA_DIR = (Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "CampusEye-AI") if getattr(sys, "frozen", False) else Path(__file__).resolve().parent
DATA_DIR.mkdir(parents=True, exist_ok=True)
DB = DATA_DIR / "campuseye.sqlite3"
app = Flask(__name__, template_folder=str(ROOT / "templates"), static_folder=str(ROOT / "static"))
app.json.ensure_ascii = False
# Limit browser uploads to 150 MiB (actual videos must be smaller).
MAX_VIDEO_MB = 150
app.config["MAX_CONTENT_LENGTH"] = MAX_VIDEO_MB * 1024 * 1024
ALLOWED_VIDEO_EXTENSIONS = {".mp4", ".avi", ".mov", ".mkv"}
# ONNX model is optional until it is downloaded. When present, it is bundled
# inside the PyInstaller distribution and can run offline via OpenCV DNN.
YOLO_MODEL = ROOT / "models" / "yolov8n.onnx"


class AnonymousPersonDetector:
    """Only COCO class 0 (person); no face or identity processing."""
    def __init__(self):
        self.name = "HOG 基礎人體偵測"
        self.net = None
        self.hog = None
        if cv2 is None:
            raise RuntimeError("OpenCV 尚未安裝")
        if YOLO_MODEL.is_file():
            try:
                self.net = cv2.dnn.readNetFromONNX(str(YOLO_MODEL))
                self.net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                self.net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                self.name = "YOLOv8n 多人偵測（CPU）"
            except Exception as exc:
                raise RuntimeError(f"AI 模型載入失敗：{exc}") from exc
        else:
            self.hog = cv2.HOGDescriptor()
            self.hog.setSVMDetector(cv2.HOGDescriptor_getDefaultPeopleDetector())

    def detect(self, frame):
        """Returns (left, top, width, height, score) for anonymous people."""
        if self.net is None:
            rects, weights = self.hog.detectMultiScale(frame, winStride=(8,8), padding=(8,8), scale=1.05)
            return [(int(x), int(y), int(w), int(h), float(score))
                    for (x,y,w,h), score in zip(rects, weights) if float(score)>=0.25]
        h, w = frame.shape[:2]
        side = max(h, w)
        square = np.zeros((side, side, 3), dtype=np.uint8)
        square[:h, :w] = frame
        blob = cv2.dnn.blobFromImage(square, 1/255.0, (640,640), swapRB=True, crop=False)
        self.net.setInput(blob)
        raw = self.net.forward()
        data = np.asarray(raw)
        # Standard YOLOv8 detection output: [1,84,8400] or [1,8400,84].
        if data.ndim != 3 or data.shape[0] != 1:
            raise RuntimeError(f"不支援的模型輸出形狀：{data.shape}")
        rows = data[0]
        if rows.shape[0] in (84,85):
            rows = rows.T
        if rows.shape[1] != 84:
            raise RuntimeError(f"需要標準 YOLOv8 COCO 模型，實際輸出：{data.shape}")
        ratio = side / 640.0
        boxes, scores = [], []
        for row in rows:
            confidence = float(row[4])  # COCO class 0 = person
            if confidence < 0.30:
                continue
            cx,cy,bw,bh = map(float, row[:4])
            x = max(0, int((cx-bw/2)*ratio))
            y = max(0, int((cy-bh/2)*ratio))
            right = min(w, int((cx+bw/2)*ratio))
            bottom = min(h, int((cy+bh/2)*ratio))
            if right <= x or bottom <= y:
                continue
            boxes.append([x,y,right-x,bottom-y])
            scores.append(confidence)
        if not boxes:
            return []
        kept = cv2.dnn.NMSBoxes(boxes, scores, score_threshold=0.30, nms_threshold=0.45)
        return [(*boxes[int(i)], scores[int(i)]) for i in np.asarray(kept).reshape(-1)]

# Videos are discarded after normal analysis; clean remnants from interrupted runs.
_TEMP_VIDEO_DIR = DATA_DIR / "temporary_videos"
if _TEMP_VIDEO_DIR.exists():
    for _old_upload in _TEMP_VIDEO_DIR.iterdir():
        if _old_upload.is_file() and _old_upload.suffix.lower() in ALLOWED_VIDEO_EXTENSIONS:
            try:
                _old_upload.unlink()
            except OSError:
                pass


def connect():
    conn = sqlite3.connect(DB, timeout=5)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with connect() as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            count INTEGER NOT NULL,
            mode TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            count INTEGER NOT NULL,
            message TEXT NOT NULL,
            mode TEXT NOT NULL
        )""")
        # Keep daily peak independent of the 10-second historical sampling interval.
        # Only anonymous numbers are stored; no frames or identifying information.
        conn.execute("""CREATE TABLE IF NOT EXISTS daily_peaks (
            day TEXT PRIMARY KEY,
            count INTEGER NOT NULL
        )""")


init_db()


class Monitor:
    def __init__(self):
        self.lock = threading.RLock()
        self.running = False
        self.mode = "demo"  # camera | demo | stopped
        self.count = 0
        self.threshold = 4
        self.camera_index = 0
        self.camera = None
        self.thread = None
        self.frame_jpg = None
        self.last_tick = 0.0
        self.last_sample = 0.0
        self.last_alert = 0.0
        self.error = ""
        self.started_at = datetime.now()
        self.detector = None
        self.detector_name = "YOLOv8n 已就緒" if YOLO_MODEL.is_file() else "HOG 基礎人體偵測（尚未下載 YOLO 模型）"
        self.session = 0
        self.message = ""

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return {
                "mode": self.mode,
                "running": self.running,
                "count": self.count,
                "threshold": self.threshold,
                "camera_index": self.camera_index,
                "camera_available": cv2 is not None,
                "detector": self.detector_name,
                "message": self.message,
                "error": self.error,
                "updated_at": datetime.now().isoformat(timespec="seconds"),
            }

    def record(self, number: int):
        number = max(0, int(number))
        now = time.time()
        timestamp = datetime.now().isoformat(timespec="seconds")
        day = timestamp[:10]
        with self.lock:
            self.count = number
            current_mode = self.mode
            threshold = self.threshold
            do_sample = now - self.last_sample >= 10
            do_alert = number >= threshold and now - self.last_alert >= 60
            if do_sample:
                self.last_sample = now
            if do_alert:
                self.last_alert = now
            # Every detection can establish a new high, even between 10-second samples.
            # The UPSERT preserves the previous maximum and survives app restarts.
            with connect() as conn:
                conn.execute("""INSERT INTO daily_peaks(day, count) VALUES (?, ?)
                    ON CONFLICT(day) DO UPDATE SET count = MAX(daily_peaks.count, excluded.count)""",
                             (day, number))
                if do_sample:
                    conn.execute("INSERT INTO samples(ts, count, mode) VALUES (?, ?, ?)",
                                 (timestamp, number, current_mode))
                if do_alert:
                    conn.execute("INSERT INTO alerts(ts, count, message, mode) VALUES (?, ?, ?, ?)",
                                 (timestamp, number,
                                  "偵測人數達到設定門檻，請留意現場動線。", current_mode))

    def stop(self):
        with self.lock:
            self.running = False
            self.mode = "stopped"
            self.count = 0
            self.frame_jpg = None
            camera = self.camera
            self.camera = None
            self.session += 1
            self.message = ""
        # The capture worker owns its handle and releases it upon exit.
        # Releasing from another thread while read() runs can crash OpenCV.

    def start(self, mode: str, camera_index: int = 0) -> tuple[bool, str]:
        self.stop()
        with self.lock:
            self.error = ""
            self.message = ""
            self.mode = mode
            self.camera_index = camera_index
            self.started_at = datetime.now()
            self.last_sample = 0
            self.last_alert = 0
            session = self.session
        if mode == "demo":
            with self.lock:
                self.running = True
            self.thread = threading.Thread(target=self.demo_loop, args=(session,), daemon=True)
            self.thread.start()
            return True, "已啟動示範模式（模擬數據）"
        if cv2 is None:
            with self.lock:
                self.mode = "stopped"
                self.error = "尚未安裝 opencv-python，請先安裝 requirements.txt"
            return False, self.error
        cam = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW if os.name == "nt" else cv2.CAP_ANY)
        if not cam.isOpened():
            cam.release()
            with self.lock:
                self.mode = "stopped"
                self.error = "無法開啟攝影機，請確認鏡頭權限與攝影機編號。"
            return False, self.error
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 360)
        with self.lock:
            self.camera = cam
            self.running = True
        self.thread = threading.Thread(target=self.capture_loop, args=(cam, "camera", session), daemon=True)
        self.thread.start()
        return True, "已啟動本機攝影機匿名人數分析"

    def start_video(self, path: Path) -> tuple[bool, str]:
        self.stop()
        if cv2 is None:
            path.unlink(missing_ok=True)
            return False, "尚未安裝 opencv-python，無法分析影片。"
        cap = cv2.VideoCapture(str(path))
        if not cap.isOpened():
            cap.release()
            path.unlink(missing_ok=True)
            return False, "無法讀取影片；請嘗試 MP4（H.264 編碼）檔案。"
        with self.lock:
            self.mode = "video"
            self.running = True
            self.count = 0
            self.error = ""
            self.message = "正在分析上傳影片（不會永久儲存原始影片）"
            self.camera = cap
            self.started_at = datetime.now()
            self.last_sample = 0
            self.last_alert = 0
            session = self.session
        self.thread = threading.Thread(target=self.capture_loop,
                                       args=(cap, "video", session, path), daemon=True)
        self.thread.start()
        return True, "影片已載入，開始進行匿名人數分析"

    def demo_loop(self, session):
        while True:
            with self.lock:
                if not self.running or self.mode != "demo" or session != self.session:
                    break
                elapsed = (datetime.now() - self.started_at).total_seconds()
            synthetic = max(0, round(2.4 + 2.0 * math.sin(elapsed / 11) + 0.7 * math.sin(elapsed / 3)))
            self.record(synthetic)
            time.sleep(1)

    def capture_loop(self, cap, source: str, session: int, path: Path | None = None):
        try:
            detector = AnonymousPersonDetector()
            with self.lock:
                if session == self.session:
                    self.detector_name = detector.name
        except Exception as exc:
            cap.release()
            if path is not None:
                path.unlink(missing_ok=True)
            with self.lock:
                if session == self.session:
                    self.error = str(exc)
                    self.running = False
                    self.mode = "stopped"
                    self.camera = None
            return
        last_detect = 0.0
        recent_counts = deque(maxlen=3)
        last_boxes = []
        fps = cap.get(cv2.CAP_PROP_FPS) if source == "video" else 0
        playback_delay = min(.1, max(.03, 1.0 / fps)) if fps and math.isfinite(fps) else .05
        finished = False
        try:
            while True:
                with self.lock:
                    if not self.running or self.mode != source or self.camera is not cap or session != self.session:
                        break
                try:
                    ok, frame = cap.read()
                    if not ok:
                        if source == "video":
                            finished = True
                            break
                        with self.lock:
                            self.error = "鏡頭讀取失敗，請檢查攝影機連線。"
                        time.sleep(.4)
                        continue
                    h, w = frame.shape[:2]
                    if w > 640:
                        frame = cv2.resize(frame, (640, max(1, round(h * 640 / w))))
                    now = time.monotonic()
                    if now - last_detect >= 1.2:
                        # Person-only detections; no identity, face, or tracking data.
                        last_boxes = detector.detect(frame)
                        recent_counts.append(len(last_boxes))
                        with self.lock:
                            still_current = self.running and self.mode == source and session == self.session
                        if still_current:
                            self.record(round(sum(recent_counts) / len(recent_counts)))
                        last_detect = now
                    with self.lock:
                        count = self.count
                    for x, y, ww, hh, confidence in last_boxes:
                        cv2.rectangle(frame, (x, y), (x + ww, y + hh), (241, 155, 92), 2)
                    cv2.rectangle(frame, (0, 0), (frame.shape[1], 48), (248, 250, 255), -1)
                    cv2.putText(frame, f"Anonymous count: {count}", (15, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, .68, (105, 80, 25), 2, cv2.LINE_AA)
                    ok, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 75])
                    if ok:
                        with self.lock:
                            if self.running and session == self.session:
                                self.frame_jpg = buffer.tobytes()
                    time.sleep(playback_delay if source == "video" else .08)
                except Exception as exc:
                    with self.lock:
                        if session == self.session:
                            self.error = f"影像處理錯誤：{exc}"
                    break
        finally:
            cap.release()
            if path is not None:
                path.unlink(missing_ok=True)
            with self.lock:
                if session == self.session and self.camera is cap:
                    self.camera = None
                    if source == "video":
                        self.running = False
                        self.mode = "stopped"
                        self.frame_jpg = None
                        self.message = "影片分析完成，結果已更新至今日統計。" if finished else "影片分析已結束。"
                    elif source == "camera":
                        self.running = False
                        self.mode = "stopped"


monitor = Monitor()
atexit.register(monitor.stop)


@app.get("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    return jsonify(monitor.snapshot())


@app.post("/api/start")
def start():
    data = request.get_json(silent=True) or {}
    mode = data.get("mode", "demo")
    if mode not in ("demo", "camera"):
        return jsonify({"ok": False, "message": "不支援的模式"}), 400
    try:
        index = int(data.get("camera_index", 0))
        if not 0 <= index <= 5:
            raise ValueError
    except (TypeError, ValueError):
        return jsonify({"ok": False, "message": "攝影機編號須介於 0～5"}), 400
    ok, message = monitor.start(mode, index)
    return jsonify({"ok": ok, "message": message}), (200 if ok else 400)


@app.post("/api/upload-video")
def upload_video():
    if "file" not in request.files:
        return jsonify({"ok": False, "message": "請先選擇影片檔案。"}), 400
    uploaded = request.files["file"]
    extension = Path(uploaded.filename or "").suffix.lower()
    if extension not in ALLOWED_VIDEO_EXTENSIONS:
        return jsonify({"ok": False, "message": "支援 MP4、AVI、MOV 或 MKV；建議 MP4（H.264）。"}), 400
    # Keep temporary videos in the user's writable per-user directory.
    temp_dir = DATA_DIR / "temporary_videos"
    temp_dir.mkdir(parents=True, exist_ok=True)
    dest = temp_dir / f"{uuid.uuid4().hex}{extension}"
    try:
        uploaded.save(dest)
        if dest.stat().st_size == 0:
            dest.unlink(missing_ok=True)
            return jsonify({"ok": False, "message": "影片是空的，請選擇其他檔案。"}), 400
        ok, message = monitor.start_video(dest)
        return jsonify({"ok": ok, "message": message}), (200 if ok else 400)
    except OSError:
        dest.unlink(missing_ok=True)
        return jsonify({"ok": False, "message": "無法暫存影片，請確認磁碟剩餘空間。"}), 500


@app.errorhandler(413)
def too_large(_error):
    return jsonify({"ok": False, "message": f"影片檔案太大，請使用小於 {MAX_VIDEO_MB} MB 的測試影片。"}), 413


@app.post("/api/stop")
def stop():
    monitor.stop()
    return jsonify({"ok": True, "message": "監測已停止"})


@app.post("/api/settings")
def settings():
    data = request.get_json(silent=True) or {}
    try:
        threshold = int(data.get("threshold", 4))
        if not 1 <= threshold <= 100:
            raise ValueError
    except (ValueError, TypeError):
        return jsonify({"ok": False, "message": "門檻請輸入 1～100 的整數"}), 400
    with monitor.lock:
        monitor.threshold = threshold
    return jsonify({"ok": True, "threshold": threshold})


@app.get("/api/history")
def history():
    today = datetime.now().date().isoformat()
    with connect() as conn:
        rows = conn.execute("SELECT ts,count,mode FROM samples WHERE ts >= ? ORDER BY ts DESC LIMIT 1000",
                            (today,)).fetchall()
        latest = conn.execute("SELECT ts,count,mode FROM samples ORDER BY ts DESC LIMIT 100").fetchall()
        alerts = conn.execute("SELECT ts,count,message,mode FROM alerts ORDER BY ts DESC LIMIT 8").fetchall()
        peak_row = conn.execute("SELECT count FROM daily_peaks WHERE day = ?", (today,)).fetchone()
    # Six time buckets across the day, or hourly for a full 24-hour chart.
    chart = [{"hour": f"{hour:02d}:00", "people": 0, "samples": 0} for hour in range(24)]
    for r in rows:
        hour = int(r["ts"][11:13])
        chart[hour]["people"] += r["count"]
        chart[hour]["samples"] += 1
    chart = [{"hour": c["hour"], "people": round(c["people"] / c["samples"], 1) if c["samples"] else None}
             for c in chart]
    # These are snapshots, not total passages or unique persons.
    return jsonify({
        "chart": chart,
        "samples_today": len(rows),
        "avg_count_today": round(sum(r["count"] for r in rows) / len(rows), 1) if rows else 0,
        "peak_count_today": max(peak_row["count"] if peak_row else 0,
                                max((r["count"] for r in rows), default=0)),
        "recent": [dict(r) for r in latest[:12]],
        "alerts": [dict(r) for r in alerts],
    })


@app.get("/api/video")
def video():
    def stream():
        while True:
            with monitor.lock:
                if monitor.mode not in ("camera", "video") or not monitor.running:
                    return
                jpg = monitor.frame_jpg
            if jpg:
                yield b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"
            time.sleep(.15)
    return Response(stream(), mimetype="multipart/x-mixed-replace; boundary=frame",
                    headers={"Cache-Control": "no-store"})


if __name__ == "__main__":
    import webbrowser
    threading.Timer(1.0, lambda: webbrowser.open("http://127.0.0.1:5000")).start()
    print("CampusEye AI: http://127.0.0.1:5000")
    app.run(host="127.0.0.1", port=5000, debug=False, threaded=True, use_reloader=False)
