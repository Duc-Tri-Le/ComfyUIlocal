# ComfyUI-Flow-Veo3 (Google Flow Veo 3 & MiniMax Director)

Bộ custom node mạnh mẽ dành cho **ComfyUI**, cung cấp quy trình tự động hóa chuẩn điện ảnh Hollywood để phân tích thị giác đa phương thức (Multimodal Vision), viết prompt kịch bản phân cảnh chi tiết cho **Google Flow Veo 3 (Veo 3.1 / Omni Flash)** & **MiniMax Hailuo**, biên tập prompt thông minh và kết nối sinh video.

---

## 📋 Danh sách Node trong bộ công cụ

| Tên Node | Tên hiển thị ComfyUI | Chức năng chính |
|---|---|---|
| `Flow_Veo3_Vision` | **Google Flow Veo 3 Vision** | Nhận diện nhân vật, trang phục, góc máy, ánh sáng từ ảnh/video/audio và xuất `VISION_CONTEXT`. |
| `Flow_Veo3_Promptor` | **Google Flow Veo 3 Promptor** | Bộ não đạo diễn 2 tầng (Stage 1: Director Blueprint -> Stage 2: Storyboard & Dialogue Prompt). |
| `Flow_Veo3_Editor` | **Google Flow Veo 3 Prompt Preview & Edit** | Xem trước và tinh chỉnh prompt (Refine) trực tiếp bằng AI trên từng câu, từng phân cảnh. |
| `Flow_Veo3_Composer` | **Google Flow Veo 3 Prompt Composer** | Trình soạn thảo prompt thủ công hỗ trợ autocomplete menu (`@`, `<`, `[`). |
| `Flow_Veo3_VideoGenerator` | **Google Flow Veo 3 Video Generator** | Gửi prompt sang backend sinh video Veo 3.1 / Omni Flash, xuất file `.mp4` và dãy tensor `IMAGE`. |

---

## 🛠️ Hướng dẫn cài đặt chi tiết (Setup Guide)

### 1. Yêu cầu hệ thống (Prerequisites)
- **Python**: `3.10` trở lên.
- **ComfyUI**: Đã cài đặt và đang hoạt động bình thường.
- **Git**: Đã cài đặt trên máy.

---

### 2. Cài đặt vào ComfyUI

#### Cách A: Dành cho bản cài đặt Git / Virtualenv tiêu chuẩn

1. Mở Terminal / PowerShell và di chuyển vào thư mục `custom_nodes` của ComfyUI:
   ```bash
   cd ComfyUI/custom_nodes
   ```

2. Clone repository này về:
   ```bash
   git clone https://github.com/Duc-Tri-Le/ComfyUI.git ComfyUI-Flow-Veo3
   ```

3. Di chuyển vào thư mục vừa clone và cài đặt thư viện phụ thuộc:
   ```bash
   cd ComfyUI-Flow-Veo3
   pip install -r requirements.txt
   ```

---

#### Cách B: Dành cho bản ComfyUI Portable (Windows)

1. Mở Command Prompt hoặc PowerShell tại thư mục gốc của bản Portable:
   ```powershell
   cd ComfyUI_windows_portable\ComfyUI\custom_nodes
   ```

2. Clone repo về thư mục `custom_nodes`:
   ```powershell
   git clone https://github.com/Duc-Tri-Le/ComfyUI.git ComfyUI-Flow-Veo3
   ```

3. Cài đặt `requirements.txt` bằng môi trường Python nhúng (`python_embeded`):
   ```powershell
   cd ..\..\python_embeded
   .\python.exe -m pip install -r ..\ComfyUI\custom_nodes\ComfyUI-Flow-Veo3\requirements.txt
   ```

---

## ⚙️ Cấu hình API & Mô hình LLM (Configuration)

Bộ node hỗ trợ cả **Cloud API** (Gemini, OpenAI, Claude) và **Local LLM offline** (Ollama, LM Studio, llama.cpp, Qwen-VL).

### Bước 1: Khởi tạo file cấu hình
Hệ thống đi kèm file mẫu [config.example.json](config.example.json). Hãy copy thành `config.json`:

- **Trên Windows (PowerShell):**
  ```powershell
  copy config.example.json config.json
  ```
- **Trên Linux / macOS:**
  ```bash
  cp config.example.json config.json
  ```

### Bước 2: Cài đặt API Key & Provider

Bạn có 2 cách để thiết lập:

#### Cách 1: Thiết lập qua giao diện ComfyUI (Khuyên dùng)
1. Khởi động ComfyUI (`python main.py` hoặc `run_nvidia_gpu.bat`).
2. Nhấn vào biểu tượng **Bánh răng (Settings)** ở góc trên bên phải ComfyUI.
3. Tìm mục **Google Flow Veo 3 / MiniMax Settings**:
   - Bật/tắt các Provider mong muốn.
   - Điền **API Key** và chọn **Model mặc định**.
   - Nhấn **Save** (cấu hình được tự động lưu vào `config.json` ngay lập tức mà không cần khởi động lại ComfyUI).

#### Cách 2: Chỉnh sửa trực tiếp file `config.json`
Mở [config.json](config.json) bằng trình soạn thảo và điền API key của bạn:

```json
{
  "providers": {
    "prov_1720000003": {
      "name": "gemini",
      "type": "gemini",
      "api_base": "https://generativelanguage.googleapis.com/v1beta",
      "api_key": "YOUR_GEMINI_API_KEY_HERE",
      "model": "gemini-2.5-flash",
      "enabled": true
    },
    "prov_1720000001": {
      "name": "openai",
      "type": "openai",
      "api_base": "https://api.openai.com/v1",
      "api_key": "YOUR_OPENAI_API_KEY_HERE",
      "model": "gpt-4o",
      "enabled": false
    },
    "prov_1720000002": {
      "name": "anthropic",
      "type": "anthropic",
      "api_base": "https://api.anthropic.com/v1",
      "api_key": "YOUR_CLAUDE_API_KEY_HERE",
      "model": "claude-3-5-sonnet-latest",
      "enabled": false
    },
    "prov_1720000004": {
      "name": "ollama",
      "type": "ollama",
      "api_base": "http://localhost:11434",
      "model": "llama3.2-vision",
      "enabled": true,
      "unload_after_run": true
    },
    "prov_1720000006": {
      "name": "lmstudio",
      "type": "openai",
      "api_base": "http://localhost:1234/v1",
      "api_key": "sk-dummy",
      "model": "local-model",
      "enabled": false,
      "unload_after_run": true
    }
  }
}
```

> [!TIP]
> **Khuyên dùng Google Gemini (`gemini-2.5-flash`):**
> Có gói miễn phí tốc độ rất cao, khả năng đọc và hiểu hình ảnh/video phân tích nhân vật chuẩn xác. Bạn có thể lấy API Key miễn phí tại [Google AI Studio](https://aistudio.google.com/).

---

## 🚀 Hướng dẫn sử dụng nhanh (Quick Start Workflows)

### 1. Quy trình Text-to-Video (T2V) — Thuần văn bản
1. Thêm node **Google Flow Veo 3 Promptor**.
2. Đặt `task_type`: `Auto` hoặc `T2V`.
3. Nhập ý tưởng cốt truyện vào ô `description` (Ví dụ: *"A cyberpunk samurai walks through neon rain in Neo Tokyo"*).
4. Nối đầu ra `PROMPT` của node Promptor vào node **Google Flow Veo 3 Video Generator** (hoặc node Sampler video bạn đang dùng).

### 2. Quy trình Image/Reference-to-Video (I2V / R2V) — Giữ nhất quán nhân vật
1. Thêm node **Load Image** để nạp ảnh nhân vật hoặc bối cảnh.
2. Nối `IMAGE` vào cổng `ref_images` của node **Google Flow Veo 3 Vision**.
3. Nối đầu ra `VISION_CONTEXT` từ node Vision sang cổng `vision_context` của node **Google Flow Veo 3 Promptor**.
4. Node Promptor sẽ tự động nhận diện chế độ `I2V` hoặc `R2V`, trích xuất thông số nhân vật và lồng ghép vào kịch bản phim.
5. (Tùy chọn) Nối `PROMPT` sang node **Google Flow Veo 3 Prompt Preview & Edit** để xem trước và dùng AI sửa nhanh từng câu chữ trước khi render.

---

## 💡 Tùy biến nâng cao (Advanced Customization)

- **Chiến lược phân tích thị giác:** Chỉnh sửa file [vision_prompts.json](vision_prompts.json) để thêm các prompt phân tích thị giác chuyên sâu riêng cho bạn.
- **Mẫu kịch bản điện ảnh:** Thư mục [templates/](templates/) chứa các cấu trúc prompt định hướng cho từng chế độ (`t2v.txt`, `i2v.txt`, `r2v.txt`, `fl2v.txt`).
- **Tự động giải phóng VRAM:** Các mô hình Local LLM (Ollama, LM Studio) được cấu hình `unload_after_run: true` sẽ tự động giải phóng VRAM ngay sau khi phân tích xong để nhường bộ nhớ GPU cho mô hình sinh video.

---

## ❓ Xử lý sự cố thường gặp (Troubleshooting)

1. **Lỗi `ModuleNotFoundError` khi khởi động ComfyUI:**
   - Chạy lệnh: `pip install -r requirements.txt` trong môi trường Python mà ComfyUI đang sử dụng.
2. **Không thấy node xuất hiện trên menu ComfyUI:**
   - Kiểm tra log terminal khi khởi động ComfyUI, đảm bảo có thông báo:
     `[ComfyUI-Flow-Veo3] v2.0.0 | 10 nodes Loaded`.
   - Đảm bảo thư mục đặt đúng vị trí: `ComfyUI/custom_nodes/ComfyUI-Flow-Veo3`.
3. **Lỗi kết nối Local LLM (Ollama / LM Studio):**
   - Đảm bảo service Ollama (`ollama serve`) hoặc LM Studio Local Server đã được bật trước khi nhấn Queue Prompt.

---

## 📜 Giấy phép (License)
Phát triển và phân phối theo giấy phép mã nguồn mở GPL-3.0.
