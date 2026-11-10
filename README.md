# CampusEye AI v1.1.0

CampusEye AI 是一套供研究與教學展示的 **本機匿名人數估計** Windows 原型。使用 Flask + OpenCV，搭配 YOLOv8n ONNX 人體偵測模型，以人數統計呈現空間使用情況。

> **不是人臉辨識或人員追蹤工具。** 偵測數量不等於真實進出人次，也不能單憑影像人數判斷安全、違規或學生行為。實際使用請取得場域許可、告知參與者，並遵守所在地規範。

## 功能

- 本機 Flask 網站及 Windows 圖形啟動器，網址 `http://127.0.0.1:5000`。
- 上傳 MP4、AVI、MOV 或 MKV 測試影片，使用 AI 估算畫面人數及標示辨識框。
- 支援本機 USB 攝影機；沒有攝影機時可使用明確標示的示範模式。
- 儲存匿名統計樣本、當日最高人數及人數門檻提醒（SQLite）。
- 影片上傳大小限制 150 MiB；正常分析完成及程式再次啟動時會嘗試清理暫存影片。若程式異常終止仍應檢查暫存資料夾。
- 桌面版在使用者資料夾下儲存統計資料；原始碼執行時會在專案資料夾產生 `campuseye.sqlite3`。

## 在 Windows 執行原始碼

建議 Python 3.11～3.13，實際套件相容性視作業系統和 Python 版本而定。

```powershell
py -m pip install -r requirements.txt
py app.py
```

開啟 `http://127.0.0.1:5000`。若要使用 GUI 啟動器，執行 `py launcher.py`。

## 啟用 YOLOv8n

在 Windows 執行 `Download_AI_Model.bat`，或執行 `py download_ai_model.py`。

模型來源：`https://huggingface.co/Shad0ws/yolov8onnx/resolve/main/yolov8n.onnx`；下載程式會檢查固定 SHA-256。模型存放於 `models/yolov8n.onnx`。未安裝模型時可能回退使用 OpenCV HOG；請確認網站上的偵測引擎名稱。

**授權提醒：** Ultralytics 表明其 YOLOv8 模型預設受 AGPL-3.0 規範；第三方模型託管頁標示 MIT 並不能單獨證明原始模型可改用 MIT 散布。請於散布模型權重及含有權重的安裝版之前，確認來源、授權與完整對應原始碼要求。詳見 `THIRD_PARTY_NOTICES.md`。

## Windows 安裝程式建置

1. 安裝所需 Python 套件及 PyInstaller：`py -m pip install pyinstaller`。
2. 下載並驗證模型：`Download_AI_Model.bat`。
3. 執行 `build_exe.bat`（Windows），生成 `dist/CampusEye-AI/`。
4. 使用 Inno Setup 開啟 `CampusEyeAI-Setup.iss` 並編譯。建置腳本參照儲存庫根目錄的 `LICENSE`，**此檔案已由 GitHub 儲存庫管理，請確認本機也有完整的 `LICENSE`**。
5. 公開二進位版本前仍需核實模型再散布授權、附帶的第三方函式庫授權文件、完整對應原始碼，以及安裝包是否包含私密檔案；重新建置後以實際生成的 EXE 進行測試與雜湊比對。

## 隱私、準確度與離線使用

- 只提供匿名畫面人數估計，沒有身分辨識、個人資料蒐集或個人追蹤功能。
- 偵測可能漏判或誤判，特別是人物重疊、遮擋、角度與低光源場景。
- Python 人數分析在本機；**Chart.js 與 Google Fonts 仍由外部 CDN 載入**，所以網站圖表與字型在完全離線時不保證完整顯示。
- 上傳的檔案不應包含未經同意的個人影像；不要公開測試影片或本機 SQLite 資料庫。

## 授權

專案在 GitHub 使用 `LICENSE` 提供的 AGPL-3.0 條款；依其授權發布應附上完整對應原始碼與必要著作權及第三方通知。第三方權利仍依各自授權，不因本儲存庫選擇 AGPL-3.0 而自動改變。

`LICENSE` 由 GitHub 倉庫單獨管理，不包含在本 ZIP 中，以免覆蓋您先前建立的授權文件。
