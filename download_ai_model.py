"""Download and SHA256-verify a YOLOv8n ONNX model. No third-party Python packages."""
from pathlib import Path
from urllib.request import urlopen, Request
import hashlib
import os
import sys

URL = "https://huggingface.co/Shad0ws/yolov8onnx/resolve/main/yolov8n.onnx"
SHA256 = "e97df4e336ab724b22b4513ff39040a08770428e54628abd31b642e7babf75e5"
TARGET = Path(__file__).resolve().parent / "models" / "yolov8n.onnx"


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    if TARGET.is_file() and sha256_file(TARGET) == SHA256:
        print('YOLOv8n 模型已存在，完整性檢查通過。')
        return 0
    tmp = TARGET.with_suffix('.download')
    try:
        print('正在從 Hugging Face 下載 YOLOv8n 模型（約 13 MB）...')
        req = Request(URL, headers={'User-Agent': 'CampusEyeAI-ModelDownload/1.0'})
        with urlopen(req, timeout=90) as r, tmp.open('wb') as fout:
            while True:
                buf = r.read(1024*1024)
                if not buf: break
                fout.write(buf)
                print('.', end='', flush=True)
        print('\n正在驗證模型 SHA-256...')
        if sha256_file(tmp) != SHA256:
            raise ValueError('模型 SHA-256 不符，已拒絕使用下載內容。')
        os.replace(tmp, TARGET)
        print('下載成功！AI 模型可離線使用。')
        return 0
    except Exception as e:
        print('下載失敗：', e)
        print('請確認網路連線。原本的 HOG 偵測仍可繼續使用。')
        return 1
    finally:
        tmp.unlink(missing_ok=True)

if __name__=='__main__':
    sys.exit(main())
