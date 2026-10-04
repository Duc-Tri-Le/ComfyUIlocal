# ComfyUIlocal

Workspace thiết lập ComfyUI chạy cục bộ trên Windows với card NVIDIA (hỗ trợ GTX 1650 4GB VRAM).

## Bao gồm
- **ComfyUI**: Core engine ComfyUI.
- **ComfyUI-MiniMax-H3-Promptor**: Custom node hỗ trợ tạo prompt và xử lý vision qua LLM.
- **run_gpu.bat**: File batch khởi chạy nhanh với tối ưu `--lowvram`.

## Hướng dẫn khởi chạy
1. Chạy file `run_gpu.bat` hoặc gõ:
   ```cmd
   cd ComfyUI
   python main.py --windows-standalone-build --lowvram
   ```
2. Truy cập web UI tại: `http://127.0.0.1:8188`
