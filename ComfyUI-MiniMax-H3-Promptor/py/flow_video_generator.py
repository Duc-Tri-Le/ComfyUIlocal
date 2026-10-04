"""
Google Flow Veo 3 Video Generator (ComfyUI Node)
Connects to Google Flow (via FlowStory backend) to generate videos using Veo 3.1 / Omni Flash.
Outputs decoded video frames (IMAGE tensor) and local MP4 file path.
"""
from __future__ import annotations

import os
import time
import json
import base64
from io import BytesIO
import urllib.request
import urllib.error
import urllib.parse
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

try:
    # pyrefly: ignore [missing-import]
    import numpy as np
    from PIL import Image
    # pyrefly: ignore [missing-import]
    import cv2
    # pyrefly: ignore [missing-import]
    import torch
except ImportError:
    np = None
    Image = None
    cv2 = None
    torch = None

try:
    # pyrefly: ignore [missing-import]
    import folder_paths
except ImportError:
    folder_paths = None

try:
    # pyrefly: ignore [missing-import]
    from comfy_api.latest import io
except ImportError:
    class _DummyIO:
        class ComfyNode: pass
        class NodeOutput:
            def __init__(self, *args, **kwargs): self.args = args
        class Schema:
            def __init__(self, *args, **kwargs): pass
        class _Field:
            @classmethod
            def Input(cls, *args, **kwargs): return None
            @classmethod
            def Output(cls, *args, **kwargs): return None
        Combo = Image = Video = Audio = String = Float = Int = _Field
    io = _DummyIO()

# pyrefly: ignore [missing-import]
from .utils import log_info, log_error, log_warning


ASPECT_RATIO_MAP = {
    "16:9 Landscape": "VIDEO_ASPECT_RATIO_LANDSCAPE",
    "9:16 Portrait": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "1:1 Square": "VIDEO_ASPECT_RATIO_SQUARE",
}

MODEL_PRESETS = [
    "veo_3_1_i2v_s_fast_ultra (High Quality)",
    "veo_3_1_i2v_lite_low_priority (0 Credits)",
    "veo_3_1_i2v_lite (Fast)",
    "veo_3_1_r2v_fast (Reference / Omni)",
    "omni_flash_standard (Omni Flash)",
]


def _tensor_to_png_base64(image_tensor: torch.Tensor) -> str:
    """Convert a ComfyUI IMAGE tensor [B, H, W, C] to PNG base64 string."""
    t = image_tensor
    if len(t.shape) == 4:
        t = t[0]
    # Ensure on CPU and convert to uint8
    arr = (t.detach().cpu().numpy() * 255.0).clip(0, 255).astype(np.uint8)
    pil_img = Image.fromarray(arr)
    
    buf = BytesIO()
    pil_img.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _read_video_frames(video_path: str) -> Tuple[torch.Tensor, float]:
    """Read all frames from an MP4 video into a PyTorch float32 tensor [N, H, W, 3]."""
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")
        
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 24.0
    frames = []
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        frames.append(frame_rgb)
    cap.release()
    
    if not frames:
        raise ValueError(f"Failed to read any video frames from: {video_path}")
        
    frames_np = np.stack(frames).astype(np.float32) / 255.0
    return torch.from_numpy(frames_np), float(fps)


def _http_request(url: str, method: str = "GET", data: Optional[dict] = None, timeout: int = 60) -> dict:
    """Perform synchronous HTTP JSON request."""
    headers = {"Content-Type": "application/json"}
    body_bytes = json.dumps(data).encode("utf-8") if data is not None else None
    
    req = urllib.request.Request(url, data=body_bytes, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            content = resp.read().decode("utf-8")
            return json.loads(content)
    except urllib.error.HTTPError as e:
        err_msg = e.read().decode("utf-8", errors="replace")
        try:
            return {"error": json.loads(err_msg), "http_status": e.code}
        except Exception:
            return {"error": err_msg, "http_status": e.code}
    except Exception as e:
        return {"error": str(e), "http_status": 0}


def _download_file(url: str, output_path: str, timeout: int = 120):
    """Download binary file from URL to disk."""
    req = urllib.request.Request(url, headers={"User-Agent": "ComfyUI-Flow-Veo3"})
    with urllib.request.urlopen(req, timeout=timeout) as resp, open(output_path, "wb") as f:
        while True:
            chunk = resp.read(1024 * 64)
            if not chunk:
                break
            f.write(chunk)


class Flow_Veo3_VideoGenerator(io.ComfyNode):
    """
    Google Flow Veo 3 Video Generator.
    Connects to the FlowStory backend bridge to generate video using Google Flow Veo 3.1 / Omni Flash.
    Polls job status, downloads video, and outputs both decoded IMAGE frame tensors and local MP4 path.
    """
    CATEGORY = "🧪AILab/🎬 Google Flow Veo 3"
    FUNCTION = "execute"
    OUTPUT_NODE = True

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Flow_Veo3_VideoGenerator",
            display_name="Google Flow Veo 3 Video Generator",
            category="🧪AILab/🎬 Google Flow Veo 3",
            inputs=[
                io.String.Input(
                    "prompt",
                    multiline=True,
                    force_input=True,
                    tooltip="Cinematic prompt for Google Flow Veo 3 (connect from Google Flow Veo 3 Promptor or Editor).",
                ),
                io.Image.Input(
                    "image",
                    optional=True,
                    tooltip="Initial frame for Image-to-Video (I2V) or character reference for R2V.",
                ),
                io.Image.Input(
                    "end_image",
                    optional=True,
                    tooltip="Optional final frame for First-and-Last Frame (FL2V) chaining.",
                ),
                io.Combo.Input(
                    "aspect_ratio",
                    options=list(ASPECT_RATIO_MAP.keys()),
                    default="16:9 Landscape",
                    tooltip="Video aspect ratio (16:9 landscape or 9:16 portrait).",
                ),
                io.Int.Input(
                    "duration_s",
                    default=8,
                    min=4,
                    max=10,
                    step=1,
                    tooltip="Video duration in seconds (Google Veo default is 8s; Omni Flash supports 4, 6, 8, 10s).",
                ),
                io.Combo.Input(
                    "model_family",
                    options=["veo", "omni_flash"],
                    default="veo",
                    tooltip="Underlying video generation model family on Google Flow.",
                ),
                io.Combo.Input(
                    "model_preset",
                    options=MODEL_PRESETS,
                    default=MODEL_PRESETS[0],
                    tooltip="Execution quality tier / model configuration.",
                ),
                io.Combo.Input(
                    "resolution",
                    options=["720p", "360p"],
                    default="720p",
                    tooltip="Output resolution (720p standard HD).",
                ),
                io.String.Input(
                    "flow_api_url",
                    default="http://127.0.0.1:8100",
                    tooltip="Base URL of the running FlowStory / Google Flow backend service.",
                ),
                io.Int.Input(
                    "poll_interval_s",
                    default=5,
                    min=2,
                    max=30,
                    step=1,
                    optional=True,
                    tooltip="Seconds between status checks during video generation.",
                ),
                io.Int.Input(
                    "timeout_s",
                    default=420,
                    min=60,
                    max=900,
                    step=30,
                    optional=True,
                    tooltip="Maximum seconds to wait for Google Flow to complete generation.",
                ),
            ],
            outputs=[
                io.Image.Output(
                    "frames",
                    display_name="FRAMES",
                    tooltip="Decoded video frames as ComfyUI IMAGE tensor [N, H, W, 3] (24fps).",
                ),
                io.String.Output(
                    "video_path",
                    display_name="VIDEO_PATH",
                    tooltip="Local file path to the saved .mp4 video on disk.",
                ),
                io.String.Output(
                    "video_url",
                    display_name="VIDEO_URL",
                    tooltip="Remote Google Flow CDN URL of the generated video.",
                ),
            ],
        )

    @classmethod
    def execute(
        cls,
        prompt: str,
        image: Optional[torch.Tensor] = None,
        end_image: Optional[torch.Tensor] = None,
        aspect_ratio: str = "16:9 Landscape",
        duration_s: int = 8,
        model_family: str = "veo",
        model_preset: str = MODEL_PRESETS[0],
        resolution: str = "720p",
        flow_api_url: str = "http://127.0.0.1:8100",
        poll_interval_s: int = 5,
        timeout_s: int = 420,
        **kwargs,
    ) -> io.NodeOutput:
        api_base = flow_api_url.rstrip("/")
        
        # 1. Verify FlowStory backend connectivity
        log_info(f"Checking Google Flow connection at {api_base}/flow/status ...")
        status_res = _http_request(f"{api_base}/flow/status", method="GET", timeout=10)
        
        if "error" in status_res:
            err = (
                f"Failed to connect to FlowStory backend at {api_base}.\n"
                f"Please ensure FlowStory is running (`python -m agent.main` from d:\\code\\FlowStory) "
                f"and that Chrome extension is connected.\nError: {status_res['error']}"
            )
            log_error(err)
            raise ConnectionError(err)
            
        if not status_res.get("connected"):
            log_warning("FlowStory server is reachable, but Chrome extension is not connected yet.")

        # 2. Upload initial and optional end frame images
        start_media_id = None
        end_media_id = None

        if image is not None:
            log_info("Encoding and uploading starting frame to Google Flow...")
            b64_start = _tensor_to_png_base64(image)
            upload_res = _http_request(
                f"{api_base}/flow/upload-image",
                method="POST",
                data={"image_base64": b64_start, "mime_type": "image/png", "file_name": "start_frame.png"},
                timeout=60,
            )
            if "error" in upload_res or not upload_res.get("media_id"):
                raise RuntimeError(f"Failed to upload start image to Google Flow: {upload_res.get('error', upload_res)}")
            start_media_id = upload_res["media_id"]
            log_info(f"Start frame uploaded: media_id={start_media_id}")

        if end_image is not None:
            log_info("Encoding and uploading ending frame to Google Flow...")
            b64_end = _tensor_to_png_base64(end_image)
            upload_end_res = _http_request(
                f"{api_base}/flow/upload-image",
                method="POST",
                data={"image_base64": b64_end, "mime_type": "image/png", "file_name": "end_frame.png"},
                timeout=60,
            )
            if "error" in upload_end_res or not upload_end_res.get("media_id"):
                raise RuntimeError(f"Failed to upload end image to Google Flow: {upload_end_res.get('error', upload_end_res)}")
            end_media_id = upload_end_res["media_id"]
            log_info(f"End frame uploaded: media_id={end_media_id}")

        # 3. Determine aspect ratio and paygate tier
        mapped_aspect = ASPECT_RATIO_MAP.get(aspect_ratio, "VIDEO_ASPECT_RATIO_LANDSCAPE")
        paygate_tier = "PAYGATE_TIER_TWO" if "ultra" in model_preset.lower() else "PAYGATE_TIER_ONE"

        # 4. Submit generation request
        operations = []
        workflows = []
        
        log_info(f"Submitting Veo 3 generation request (family={model_family}, aspect={mapped_aspect}, duration={duration_s}s)...")
        
        if start_media_id is not None:
            # Image-to-Video or First-Last Frame chaining
            gen_payload = {
                "start_image_media_id": start_media_id,
                "prompt": prompt,
                "aspect_ratio": mapped_aspect,
                "duration_s": duration_s,
                "resolution": resolution,
                "user_paygate_tier": paygate_tier,
                "model_family": model_family,
                "scene_id": f"comfy_{int(time.time())}",
            }
            if end_media_id:
                gen_payload["end_image_media_id"] = end_media_id

            submit_res = _http_request(f"{api_base}/flow/generate-video", method="POST", data=gen_payload, timeout=60)
        else:
            # Text-to-Video
            if model_family == "omni_flash":
                gen_payload = {
                    "prompt": prompt,
                    "aspect_ratio": mapped_aspect,
                    "duration_s": duration_s,
                    "resolution": resolution,
                    "user_paygate_tier": paygate_tier,
                }
                submit_res = _http_request(f"{api_base}/flow/generate-video-omni-text", method="POST", data=gen_payload, timeout=60)
            else:
                # Veo text-to-video fallback via reference or omni text endpoint
                gen_payload = {
                    "prompt": prompt,
                    "aspect_ratio": mapped_aspect,
                    "duration_s": duration_s,
                    "resolution": resolution,
                    "user_paygate_tier": paygate_tier,
                }
                submit_res = _http_request(f"{api_base}/flow/generate-video-omni-text", method="POST", data=gen_payload, timeout=60)

        if "error" in submit_res:
            raise RuntimeError(f"Google Flow video submission rejected: {submit_res.get('error', submit_res)}")

        # Extract operation handles or workflow descriptors
        if "operations" in submit_res:
            operations = submit_res["operations"]
        elif "flowkitPolling" in submit_res and "workflows" in submit_res["flowkitPolling"]:
            workflows = submit_res["flowkitPolling"]["workflows"]
        elif "workflows" in submit_res:
            workflows = submit_res["workflows"]

        if not operations and not workflows:
            raise RuntimeError(f"Unexpected response from Google Flow: no operations or workflows found. Details: {submit_res}")

        log_info(f"Video generation task accepted! Polling for completion (timeout={timeout_s}s)...")

        # 5. Polling Loop
        start_time = time.time()
        video_url = None
        
        while time.time() - start_time < timeout_s:
            time.sleep(poll_interval_s)
            elapsed = int(time.time() - start_time)
            
            if workflows:
                check_payload = {"workflows": workflows}
                status_check = _http_request(f"{api_base}/flow/check-status", method="POST", data=check_payload, timeout=30)
                if status_check.get("done") or status_check.get("status") == "COMPLETED":
                    for wf in status_check.get("workflows", []):
                        if wf.get("done") and wf.get("media", {}).get("url"):
                            video_url = wf["media"]["url"]
                            break
                    if video_url:
                        break
            else:
                check_payload = {"operations": operations}
                status_check = _http_request(f"{api_base}/flow/check-status", method="POST", data=check_payload, timeout=30)
                ops_data = status_check.get("operations") or status_check.get("data", {}).get("operations", [])
                
                for op in ops_data:
                    op_status = op.get("status", "")
                    if op_status == "MEDIA_GENERATION_STATUS_SUCCESSFUL":
                        video_url = op.get("operation", {}).get("metadata", {}).get("video", {}).get("fifeUrl")
                        if video_url:
                            break
                    elif "FAILED" in op_status:
                        raise RuntimeError(f"Google Flow generation failed: {op.get('error', op)}")
                if video_url:
                    break

            log_info(f"Waiting for Veo 3 video generation... ({elapsed}s / {timeout_s}s)")

        if not video_url:
            raise TimeoutError(f"Google Flow video generation timed out after {timeout_s} seconds.")

        log_info(f"Video generation successful! Video URL: {video_url}")

        # 6. Download video to ComfyUI output directory
        out_dir = folder_paths.get_output_directory() if folder_paths else os.path.join(os.getcwd(), "output")
        os.makedirs(out_dir, exist_ok=True)
        
        timestamp_str = time.strftime("%Y%m%d_%H%M%S")
        local_filename = f"Flow_Veo3_{timestamp_str}.mp4"
        local_path = os.path.join(out_dir, local_filename)

        log_info(f"Downloading generated video to {local_path} ...")
        # Try direct download first, fallback to FlowStory download proxy if needed
        try:
            _download_file(video_url, local_path, timeout=90)
        except Exception as dl_err:
            log_warning(f"Direct download failed ({dl_err}), trying FlowStory download proxy...")
            proxy_url = f"{api_base}/proxy/download?url={urllib.parse.quote(video_url)}&filename={local_filename}"
            _download_file(proxy_url, local_path, timeout=90)

        # 7. Decode video frames into ComfyUI IMAGE tensor
        log_info(f"Decoding video frames from {local_path} into ComfyUI IMAGE tensor...")
        frames_tensor, fps = _read_video_frames(local_path)
        log_info(f"Decoded {frames_tensor.shape[0]} frames ({frames_tensor.shape[2]}x{frames_tensor.shape[1]} @ {fps} fps).")

        return io.NodeOutput(frames_tensor, local_path, video_url)

    RETURN_TYPES = ("IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("frames", "video_path", "video_url")
    OUTPUT_TOOLTIPS = (
        "Decoded video frames as ComfyUI IMAGE tensor [N, H, W, 3] (24fps).",
        "Local file path to the saved .mp4 video on disk.",
        "Remote Google Flow CDN URL of the generated video.",
    )


NODE_CLASS_MAPPINGS = {
    "Flow_Veo3_VideoGenerator": Flow_Veo3_VideoGenerator,
    "Flow_Veo_Sampler": Flow_Veo3_VideoGenerator,  # Convenience alias
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Flow_Veo3_VideoGenerator": "Google Flow Veo 3 Video Generator",
    "Flow_Veo_Sampler": "Google Flow Veo 3 Video Generator",
}
