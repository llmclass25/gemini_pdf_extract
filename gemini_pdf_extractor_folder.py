#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
gemini_pdf_extractor_folder.py
使用 Google Gemini 2.5 Pro 模型擷取 PDF 中文內容（單輪分片 + 自動頁碼標註）。
每批獨立呼叫模型，避免多輪對話遺漏或空白問題。
自動在輸出中加入頁碼段落標註。
"""

import os
import sys
import math
import time
import textwrap
from dotenv import load_dotenv
from pypdf import PdfReader
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

# === 1️⃣ 載入 .env 檔案 ===
load_dotenv()

# === 2️⃣ 從環境變數讀取 API 金鑰 ===
api_key = os.getenv("GOOGLE_API_KEY")

if not api_key:
    print("❌ 錯誤：找不到 GOOGLE_API_KEY。請建立 .env 檔案，內容如下：")
    print("GOOGLE_API_KEY=你的金鑰")
    sys.exit(1)

# === 3️⃣ 設定 Gemini API ===
try:
    genai.configure(api_key=api_key)
    print("✅ Google API 金鑰設定成功！")
except Exception as e:
    print(f"❌ 設定 API 金鑰時發生錯誤: {e}")
    sys.exit(1)

# === 4️⃣ 讀取輸入參數 ===
if len(sys.argv) < 2:
    print("\n📘 使用方式：")
    print("python gemini_pdf_extractor_folder.py <PDF目錄路徑> [每批頁數] [每批間隔秒數]\n")
    print("範例：python gemini_pdf_extractor_folder.py ./pdfs 30 10\n")
    sys.exit(0)

PDF_DIR = sys.argv[1]
CHUNK_SIZE = int(sys.argv[2]) if len(sys.argv) > 2 else 30  # 預設每批 30 頁
WAIT_SECONDS = int(sys.argv[3]) if len(sys.argv) > 3 else 10  # 預設每批間隔 10 秒

# === 5️⃣ 檢查輸入目錄 ===
if not os.path.exists(PDF_DIR):
    print(f"❌ 錯誤：找不到目錄「{PDF_DIR}」。")
    sys.exit(1)

pdf_files = [f for f in os.listdir(PDF_DIR) if f.lower().endswith(".pdf")]
if not pdf_files:
    print(f"❌ 目錄 {PDF_DIR} 中沒有 PDF 檔案。")
    sys.exit(1)

print(f"🟢 發現 {len(pdf_files)} 個 PDF 檔案，開始處理...\n")


# === 主處理函式 ===
def process_large_pdf(pdf_path: str, output_file_path: str, chunk_size: int, wait_seconds: int):
    """單輪分片方式擷取 PDF 內容（每批獨立呼叫模型，並自動頁碼標註）"""

    print(f"🔍 正在讀取 PDF: {pdf_path}...")
    try:
        reader = PdfReader(pdf_path)
        total_pages = len(reader.pages)
        print(f"📄 文件總頁數: {total_pages} 頁")
    except Exception as e:
        print(f"❌ 無法讀取 PDF：{e}")
        return

    if total_pages == 0:
        print("❌ 錯誤：此 PDF 沒有頁面。")
        return

    # === 初始化輸出檔 ===
    with open(output_file_path, "w", encoding="utf-8") as f:
        f.write(f"從 PDF 「{os.path.basename(pdf_path)}」 擷取的文字內容\n")
        f.write("=" * 80 + "\n\n")

    # === 上傳檔案至 Gemini ===
    print("☁️ 正在上傳檔案至 Google AI Studio...")
    uploaded_file = genai.upload_file(path=pdf_path, display_name=os.path.basename(pdf_path))
    print(f"✅ 上傳成功！File URI: {uploaded_file.uri}")
    time.sleep(2)  # 等待後端索引完成

    # === 初始化模型 ===
    model = genai.GenerativeModel(
        model_name="gemini-2.5-pro"
    )

    print("\n🚀 === 開始分批擷取 PDF 內容（單輪 + 頁碼標註） ===")
    num_chunks = math.ceil(total_pages / chunk_size)

    for i in range(num_chunks):
        start_page = i * chunk_size + 1
        end_page = min((i + 1) * chunk_size, total_pages)
        progress = (i + 1) / num_chunks * 100

        print(f"\n[批次 {i + 1}/{num_chunks}] 處理頁碼: {start_page}–{end_page}")
        print(f"📊 進度: {progress:.1f}%")

        # === 🧩 請自行貼上完整 prompt ===
        prompt = textwrap.dedent(f"""
        我現在要處理這份 PDF 的 **第 {start_page}–{end_page} 頁**。
        請你嚴格僅處理這個頁碼範圍內的內容，絕對不要跨出或提前引用其他頁的資訊。
        請依照以下提供的《文檔分析與轉錄規範》，進行高保真度的內容擷取與結構化整理。
        輸出需完整保留原始資訊的語意與上下文，並按照**小節分隔**：
        - 每個小節應完整呈現一個主題或概念，文字、表格、公式及圖表文字描述合計約 1000–2000 字，盡量保持邏輯連貫。  
        - 接近上限時自動結束小節並加上標記：
          `（第X章節結束）`  
          X 為小節編號，自動累加。

        請**直接輸出結果，不需多餘回應**，並確保依照原文語言內容撰寫：中文保持中文，英文或其他語言保持原文。

        ---

        ## 文檔分析與轉錄規範

        #### 角色 (Role)
        你是一位專業的文檔分析專家，擅長從包含文字、圖表和複雜排版的 PDF 文件中，進行高保真度的資訊擷取與結構化整理。你的任務是將指定的 PDF 頁面內容，一絲不苟地轉換為一份清晰、完整、且易於閱讀的文字稿。

        #### 任務目標 (Objective)
        精準地處理使用者提供的 PDF 檔案與指定的頁碼範圍，將所有內容（文字、圖表、表格等）轉換為結構化的文字格式。核心目標是**完全保留原始資訊的完整性與上下文關係**。

        ---

        #### 核心指令 (Core Instructions)

        1. **頁碼範圍 (Page Range):**
           - 嚴格僅處理使用者指定的頁碼範圍（例如：`第 1–50 頁`）。完全忽略範圍外的任何內容。

        2. **內容擷取原則 (Extraction Principles):**
           - **主要文本優先:** 以文章的主體內容為核心，依序擷取。
           - **忽略非核心元素:** 除非特別指示，否則應**忽略**頁首、頁尾、頁碼、以及不影響文意理解的邊緣裝飾圖案。
           - **段落定義:** 一個「段落」是指一組語義上連續的句子，通常以縮排或換行分隔。即使在原始文件中因排版而斷行，只要語義連續，就應視為同一段落。
           - **跨頁段落處理:** 若一個段落從第 X 頁結尾開始，並在第 X+1 頁開頭結束，請將其合併為單一段落，並使用其**起始頁碼**進行標記，即 `【第X頁, 段落Y】`。  
             合併後的段落不得省略或刪減任何字詞，確保語意連續。
           - **特殊格式文本:** 程式碼區塊、數學公式或引文等特殊格式，請盡可能保留其原始排版，並使用 Markdown 的程式碼區塊 (```) 或引用 (>) 格式來呈現。  
             所有原始語言（例如英文變數名稱或公式符號）請保持不變，不得翻譯或改寫。

        3. **視覺與表格元素處理 (Visual & Tabular Elements):**
           - **識別與分類:** 當遇到任何非文字內容時，需識別其類型，例如：`圖表` (Chart/Graph)、`示意圖` (Diagram)、`照片` (Photo)、`流程圖` (Flowchart)、`表格` (Table)。
           - **深入描述 (Description & Insight):**
             - 對於**圖表、示意圖、流程圖**，不僅要描述其外觀，更要提煉其**核心洞見**。說明該圖表要傳達的主要訊息、數據趨勢、組件之間的關係或流程的步驟。描述應為**完整、有意義的句子**。
             - 對於**照片或插圖**，描述其內容以及它在上下文中的作用（例如：展示產品外觀、營造特定氛圍等）。
           - **表格轉錄 (Table Transcription):**
             - 將表格內容完整地轉換為 **Markdown 表格格式**。確保所有欄位標題和儲存格資料都被準確無誤地轉錄。
             - 若表格過於複雜無法用 Markdown 呈現，則以條列式清晰描述其結構與內容。  
             所有元素（段落、視覺、表格）請依照它們在原始文件中的出現順序排列輸出，不得重排。

        ---

        #### 輸出格式 (Output Format)

        * **段落 (Paragraph):**
          `【第X頁, 段落Y】`
          [此處為段落的完整文字內容]

        * **視覺元素 (Visual Element):**
          `【第X頁, 視覺元素Y: [類型]】`
          > [此處為對該視覺元素的深入文字描述與洞見分析]

        * **表格 (Table):**
          `【第X頁, 表格Y】`
          [此處為使用 Markdown 格式轉錄的完整表格]

        * **小節結束標記:**
          在每個小節約 1000–2000 字結束時，請加上：
          `（第X章節結束）`  
          X 為小節編號，自動累加。

        * **編號規則 (Numbering Rule):**
          所有元素（段落、視覺元素、表格）的編號 Y 在每一頁都從 1 重新開始計算。

        ---

        #### 輸出格式範例 (Example)
        請僅輸出以下格式的結果，不要加入任何額外解釋、評論或說明文字。
        ````

        【第10頁, 段落1】
        本章節旨在介紹現代電路學的基本原理，並探討能量如何在封閉迴路中進行傳導。我們將從最基礎的元件開始。

        【第10頁, 視覺元素1: 示意圖】

        > 一張電路示意圖，展示一顆電池（標示正負極）透過導線連接一個電阻器，形成一個閉合迴路。圖中用箭頭清晰標示了傳統電流（I）從正極流向負極的方向，同時也暗示了電子流的相反路徑。此圖旨在說明構成基本電路的三個要素：電源、導線與負載。

        【第11頁, 段落1】
        根據德國物理學家格奧爾格·歐姆提出的歐姆定律，電路中的電壓、電流與電阻之間存在線性關係，數學表達式為 V = IR。

        【第11頁, 表格1】

        | 實驗序號 | 電壓 (V) | 電流 (A) | 電阻 (Ω) |
        | :--- | :----- | :----- | :----- |
        | 1    | 5.0    | 0.5    | 10.0   |
        | 2    | 10.0   | 1.0    | 10.0   |
        | 3    | 12.0   | 0.6    | 20.0   |

        【第12頁, 段落1】
        基於上述定律，我們可以進一步分析更複雜的電路結構，例如串聯電路與並聯電路。這兩種連接方式在現實世界的電子設備中有著廣泛的應用。

        （第1章節結束）

        ```
        """)



        # === 呼叫 Gemini ===
        try:
            response = model.generate_content(
                [prompt, uploaded_file],
                safety_settings=None
            )
            # === 檢查回應 ===
            if not hasattr(response, "text") or not response.text.strip():
                print(f"⚠️ 無回應內容或模型未返回文字（第 {i + 1} 批）。")
                continue

            batch_header = f"\n\n===== {os.path.basename(pdf_path)} | 第 {start_page}–{end_page} 頁 =====\n\n"
            batch_footer = "\n" + "=" * 80 + "\n"

            # === 寫入輸出檔案 ===
            with open(output_file_path, "a", encoding="utf-8") as f:
                f.write(batch_header)
                f.write(response.text.strip())
                f.write(batch_footer)
                f.flush()
                os.fsync(f.fileno())

            print(f"✅ 已寫入 {output_file_path} （第 {start_page}–{end_page} 頁）")
            print(f"📦 檔案目前大小：{os.path.getsize(output_file_path)/1024:.1f} KB")

        except Exception as e:
            error_msg = f"❌ 第 {i + 1} 批錯誤（頁碼 {start_page}–{end_page}）：{e}\n"
            print(error_msg)
            with open(output_file_path, "a", encoding="utf-8") as f:
                f.write(error_msg)
                
        # === 間隔等待 ===
        if i < num_chunks - 1:
            print(f"⏳ 等待 {wait_seconds} 秒後進行下一批...")
            time.sleep(wait_seconds)

    print("\n🏁 === 所有頁面處理完畢！ ===")
    time.sleep(2)


# === 執行入口 ===
if __name__ == "__main__":
    for pdf_file in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf_file)
        base_name = os.path.splitext(pdf_file)[0]

        # 輸出檔與原 PDF 同目錄
        txt_output_file = os.path.join(PDF_DIR, f"{base_name}_extracted.txt")

        if os.path.exists(txt_output_file):
            print(f"ℹ️ 已存在 {txt_output_file}，跳過此檔案。")
            continue

        print(f"\n🔹 開始處理 PDF：{pdf_file}")
        process_large_pdf(pdf_path, txt_output_file, CHUNK_SIZE, WAIT_SECONDS)
        print(f"🎉 已完成 PDF：{pdf_file}，輸出至 {txt_output_file}")


