"""
Google Flow Veo 3 Promptor
AI Director & Cinematographer node generating structured cinematic prompts for Google Flow Veo 3.
"""

import re
try:
    from comfy_api.latest import io
except ImportError:
    class _DummyIO:
        class ComfyNode: pass
        class NodeOutput:
            def __init__(self, *args, **kwargs):
                self.args = args
        class Schema:
            def __init__(self, *args, **kwargs): pass
        class _Field:
            @classmethod
            def Input(cls, *args, **kwargs): return None
            @classmethod
            def Output(cls, *args, **kwargs): return None
        Combo = Image = Video = Audio = String = Float = Int = _Field
    io = _DummyIO()

from .config_manager import get_config_manager
from .task_detector import TASK_TYPE_OPTIONS, TaskDetector
from .prompt_builder import PromptBuilder
from .post_processor import PostProcessor
from .pipeline_engine import execute_director_pipeline
from .utils import log_info, log_error


class Flow_Veo3_Promptor(io.ComfyNode):
    """
    Google Flow Veo 3 Cinematic Promptor.
    Synthesizes natural prose film director prompts conforming to the 5-component Veo 3 structure:
    [Camera/Shot] + [Subject] + [Action] + [Setting] + [Style & Audio]
    """
    CATEGORY = "🧪AILab/🎬 Google Flow Veo 3"
    FUNCTION = "execute"

    @classmethod
    def define_schema(cls):
        try:
            _config = get_config_manager().load()
            active_providers = []
            default_uuid = _config.get("defaults", {}).get("promptor_provider", "")
            default_choice = ""
            
            for k, v in _config.get("providers", {}).items():
                if v.get("enabled", True) is not False:
                    model_name = v.get("model", "").strip()
                    raw_name = v.get("name", k)
                    clean_raw = re.sub(r"\s*\([^)]*\)\s*$", "", raw_name).strip()
                    if model_name:
                        name = f"{clean_raw} ({model_name})"
                    else:
                        name = clean_raw
                    active_providers.append(name)
                    if k == default_uuid:
                        default_choice = name
            
            active_providers.sort()
            
            if not default_choice and active_providers:
                default_choice = active_providers[0]
                
            if not active_providers:
                active_providers = ["No Provider Configured"]
                default_choice = active_providers[0]
                
        except Exception:
            active_providers = ["Error Loading Providers"]
            default_choice = active_providers[0]

        return io.Schema(
            node_id="Flow_Veo3_Promptor",
            display_name="Google Flow Veo 3 Promptor",
            category="🧪AILab/🎬 Google Flow Veo 3",
            inputs=[
                io.Combo.Input("task_type", options=TASK_TYPE_OPTIONS, default=TASK_TYPE_OPTIONS[0], tooltip="Generation mode for Google Flow Veo 3 (T2V, I2V, First-Last Frame, Reference Omni) or Auto detection."),
                io.String.Input("scene_direction", multiline=True, default="", tooltip="Director's scene story, character action, and camera vision. Leave empty for AI creative interpretation."),
                io.Float.Input("duration", default=8.0, min=4.0, max=10.0, step=0.5, tooltip="Target video duration in seconds (Google Veo 3 standard is 8.0s)."),
                io.String.Input("vision_context", multiline=True, force_input=True, default="", optional=True, tooltip="Connect vision_context JSON output from Google Flow Veo 3 Vision node here."),
                io.Combo.Input("reference_images", options=["Auto", "1", "2", "3", "4", "5", "6", "7", "8", "9"], default="Auto", optional=True, tooltip="Number of reference images."),
                io.Combo.Input("reference_videos", options=["Auto", "1", "2", "3"], default="Auto", optional=True, tooltip="Number of reference videos."),
                io.Combo.Input("reference_audios", options=["Auto", "1", "2", "3"], default="Auto", optional=True, tooltip="Number of reference audio tracks."),
                io.Combo.Input("output_language", options=["English", "Vietnamese", "Chinese"], default="English", optional=True, tooltip="Prompt language (English recommended for optimal Veo 3 model comprehension)."),
                io.Combo.Input("provider", options=active_providers, default=default_choice, optional=True, tooltip="LLM provider used for Director reasoning and prompt synthesis."),
                io.Float.Input("temperature", default=0.7, min=0.0, max=1.0, step=0.05, optional=True, tooltip="Sampling temperature for LLM text generation."),
                io.Int.Input("max_tokens", default=4096, min=256, max=8192, step=256, optional=True, tooltip="Maximum token limit for LLM generation response."),
            ],
            outputs=[
                io.String.Output("prompt", display_name="PROMPT", tooltip="Formatted Google Flow Veo 3 prompt ready to connect to Video Generator or Preview & Edit node."),
                io.Float.Output("duration", display_name="DURATION", tooltip="Target video duration in seconds (default 8.0s)."),
                io.Int.Output("length", display_name="LENGTH", tooltip="Frame count at 24 fps (e.g. 192 frames for 8.0s)."),
            ],
        )

    @classmethod
    def execute(
        cls,
        task_type: str,
        duration: float = 8.0,
        scene_direction: str = "",
        description: str = "",
        vision_context: str = "",
        reference_images: str = "Auto",
        reference_videos: str = "Auto",
        reference_audios: str = "Auto",
        output_language: str = "English",
        provider: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
        **kwargs
    ) -> io.NodeOutput:
        user_prompt = scene_direction if scene_direction != "" else description
        if not user_prompt:
            user_prompt = kwargs.get("scene_direction", "") or kwargs.get("description", "")
            
        cleaned_prompt, dur, frames = cls.generate_prompt(
            task_type=task_type,
            description=user_prompt,
            duration=duration,
            vision_context=vision_context,
            reference_images=reference_images,
            reference_videos=reference_videos,
            reference_audios=reference_audios,
            output_language=output_language,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return io.NodeOutput(cleaned_prompt, float(dur), int(frames))

    RETURN_TYPES = ("STRING", "FLOAT", "INT")
    RETURN_NAMES = ("prompt", "duration", "length")
    OUTPUT_TOOLTIPS = (
        "Formatted Google Flow Veo 3 prompt ready to connect to Video Generator or Preview & Edit node.",
        "Target video duration in seconds (default 8.0s).",
        "Frame count at 24 fps (e.g. 192 frames for 8.0s)."
    )

    @classmethod
    def generate_prompt(
        cls,
        task_type: str,
        description: str,
        duration: float = 8.0,
        vision_context: str = "",
        reference_images: str = "Auto",
        reference_videos: str = "Auto",
        reference_audios: str = "Auto",
        output_language: str = "English",
        provider: str = "",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ):
        """Generate a Google Flow Veo 3 prompt using the two-stage director pipeline."""
        result = execute_director_pipeline(
            task_type=task_type,
            description=description,
            duration=duration,
            vision_context=vision_context,
            reference_images=reference_images,
            reference_videos=reference_videos,
            reference_audios=reference_audios,
            output_language=output_language,
            provider=provider,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (result["final_prompt"], float(result["duration"]), int(result["length"]))


# Aliases for compatibility
H3_Promptor = Flow_Veo3_Promptor

NODE_CLASS_MAPPINGS = {
    "Flow_Veo3_Promptor": Flow_Veo3_Promptor,
    "H3_Promptor": Flow_Veo3_Promptor,  # Legacy alias
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Flow_Veo3_Promptor": "Google Flow Veo 3 Promptor",
    "H3_Promptor": "Google Flow Veo 3 Promptor (Legacy H3 Alias)",
}
