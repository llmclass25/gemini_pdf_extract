# Gemini PDF Extractor

這個專案提供兩個 Python 腳本，用於使用 **Google Gemini 2.5 Pro** 模型高保真度擷取 PDF 文件內容，並將文字、表格及圖表等結構化輸出。支援單檔處理與整個資料夾批次處理。

---

## 目錄

* [功能說明](#功能說明)
* [安裝與環境設定](#安裝與環境設定)
* [使用方式](#使用方式)

  * [單一 PDF 擷取](#單一-pdf-擷取)
  * [資料夾批次處理](#資料夾批次處理)
* [程式細節](#程式細節)
* [輸出格式](#輸出格式)

---

## 功能說明

### gemini_pdf_extractor.py

* 擷取單一 PDF 文件內容。
* 將文字、表格及視覺元素（圖表、照片、流程圖等）依規範整理。
* 支援分批頁數處理與每輪等待時間控制。
* 使用 **Google Gemini 2.5 Pro** 模型高保真度擷取中文及多語言內容。

### gemini_pdf_extractor_folder.py

* 批次處理資料夾內所有 PDF 文件。
* 自動生成每個 PDF 的文字輸出檔。
* 同樣支援分批頁數與等待時間設定。
* 已處理的檔案會自動跳過，避免重複處理。
* 可同時指定單一 PDF 或整個資料夾。

---

## 安裝與環境設定

1. **建立虛擬環境（建議）**

```bash
python -m venv venv
source venv/bin/activate  # macOS/Linux
venv\Scripts\activate     # Windows
```

2. **安裝依賴套件**

```bash
pip install -r requirements.txt
```

`requirements.txt` 範例：

```
pypdf
python-dotenv
google-generativeai
```

3. **設定 .env**
   在專案根目錄建立 `.env`，內容：

```
GOOGLE_API_KEY=你的金鑰
```

> 此 API 金鑰用於存取 Google Gemini 2.5 Pro 模型。

---

## 使用方式

### 單一 PDF 擷取

```bash
python gemini_pdf_extractor.py <PDF檔案路徑> [每輪處理頁數] [每輪間隔秒數]
```

**範例：**

```bash
python gemini_pdf_extractor.py pdfs/report01.pdf 30 10

or

python gemini_pdf_extractor.py pdfs/report01.pdf 30 10 > log.txt 2>&1
```

* 預設每輪處理 30 頁。
* 預設每輪間隔 10 秒。
* 輸出檔案會以 `<PDF檔名>_extracted.txt` 儲存，與 PDF 同目錄。

---

### 資料夾批次處理

```bash
python gemini_pdf_extractor_folder.py <PDF目錄路徑或單一PDF路徑> [每輪處理頁數] [每輪間隔秒數]
```

**範例：**

```bash
python gemini_pdf_extractor_folder.py ./pdfs 30 10

or

python gemini_pdf_extractor_folder.py ./pdfs/report01.pdf 30 10 > log.txt 2>&1
```

* 會自動掃描資料夾內所有 PDF，或可指定單一 PDF。
* 已存在的 `_extracted.txt` 檔案會跳過處理。
* 每個 PDF 都會輸出對應的文字檔。
* 支援自訂每輪處理頁數與等待秒數，避免請求過大。

---

## 程式細節

* **API 設定與安全性**

  * 使用 `google.generativeai` 連線 Gemini 模型。
  * 程式預設 `safety_settings=None`，即 **不啟用安全過濾**。
  * 若希望套用安全內容過濾，可自訂 `safety_settings` 參數。

  **範例修改方法：**

  ```python
  # 原始寫法（預設無安全審核）
  model = genai.GenerativeModel(
      model_name="gemini-2.5-pro",
      safety_settings=None
  )

  # 若希望啟用安全限制
  model = genai.GenerativeModel(
      model_name="gemini-2.5-pro",
      safety_settings=safety_settings  
  )
  ```

* **分批處理**

  * 避免一次處理整份 PDF 導致請求過大。
  * 使用者可自訂每輪頁數與等待秒數（預設 30 頁、10 秒）。

* **多輪對話處理**

  * 每批獨立呼叫模型，保持小節及段落編號連續。
  * 支援跨頁段落合併與頁碼標註。

* **段落與元素編號規則**

  * 每頁段落、表格、視覺元素編號從 1 開始。
  * 每個小節約 1000–2000 字後自動加上 `(第X章節結束)`。

---

## 輸出格式

### 範例

```
【第10頁, 段落1】
本章節旨在介紹現代電路學的基本原理，並探討能量如何在封閉迴路中進行傳導。

【第10頁, 視覺元素1: 示意圖】
> 一張電路示意圖，展示一顆電池透過導線連接一個電阻器，形成閉合迴路。

【第11頁, 表格1】
| 實驗序號 | 電壓 (V) | 電流 (A) | 電阻 (Ω) |
| :--- | :----- | :----- | :----- |
| 1    | 5.0    | 0.5    | 10.0   |

（第1章節結束）
```

* **段落**：`【第X頁, 段落Y】`
* **視覺元素**：`【第X頁, 視覺元素Y: [類型]】` + 描述
* **表格**：`【第X頁, 表格Y】` + Markdown 表格
* **章節結束**：`（第X章節結束）`

---

## 注意事項

* PDF 檔案需可被 `pypdf` 讀取。
* 若 PDF 包含圖片或手寫內容，Gemini 模型會嘗試文字描述，但效果依模型理解能力而定。
* API 調用次數受金鑰限制，建議分批處理大型 PDF。
* 請確保 `.env` 中金鑰正確，否則程式會停止執行。



