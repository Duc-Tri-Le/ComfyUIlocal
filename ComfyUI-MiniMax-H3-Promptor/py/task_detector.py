"""
Google Flow Veo 3 Task Detector
Identifies the video generation mode (T2V, I2V, FL2V, R2V) based on connected media inputs.
"""

# Valid Veo 3 and Flow task types
TASK_TYPES = ["T2V", "I2V", "FL2V", "R2V", "FL2VA", "Ref2VA"]

# Full descriptions for UI
TASK_DESCRIPTIONS = {
    "T2V": "Text-to-Video (T2V)",
    "I2V": "Image-to-Video (I2V)",
    "FL2V": "First-and-Last-Frame (FL2V)",
    "R2V": "Reference-to-Video (R2V / Omni)",
    # Backward compatibility
    "FL2VA": "First-and-Last-Frame (FL2V)",
    "Ref2VA": "Reference-to-Video (R2V / Omni)",
}

# User-facing options (includes Auto)
TASK_TYPE_OPTIONS = ["Auto", "Text-to-Video (T2V)", "Image-to-Video (I2V)", "First-and-Last-Frame (FL2V)", "Reference-to-Video (R2V / Omni)"]


class TaskDetector:
    """Detect the appropriate Google Flow Veo 3 task type from node inputs."""

    @staticmethod
    def detect(
        image_count: int = 0,
        has_video: bool = False,
        has_audio: bool = False,
        user_override: str = "Auto",
    ) -> str:
        """
        Determine the task type based on connected inputs.
        
        Args:
            image_count: Number of images provided (0-9).
            has_video: Whether a video reference is provided.
            has_audio: Whether an audio reference is provided.
            user_override: Explicit user selection from the dropdown.
        """
        # Respect explicit user choice
        if user_override and user_override != "Auto":
            for short_code, desc in TASK_DESCRIPTIONS.items():
                if user_override == desc or user_override == short_code:
                    if short_code in ["FL2VA", "FL2V"]:
                        return "FL2V"
                    if short_code in ["Ref2VA", "R2V"]:
                        return "R2V"
                    return short_code
            if user_override in TASK_TYPES:
                return user_override

        # Auto-detection logic for Google Flow Veo 3
        if image_count >= 3 or (has_video and image_count > 0):
            return "R2V"   # 3+ images = Reference / Omni
        elif image_count == 2:
            return "FL2V"  # Exactly 2 images = First & Last frame
        elif image_count == 1:
            return "I2V"   # 1 image = Start frame
        else:
            return "T2V"   # 0 images = Text only

    @staticmethod
    def get_task_description(task_type: str) -> str:
        """Get a human-readable description for a task type."""
        descriptions = {
            "T2V": "Text-to-Video (no media references)",
            "I2V": "Image-to-Video (single start frame)",
            "FL2V": "First/Last Frame (two boundary images)",
            "FL2VA": "First/Last Frame (two boundary images)",
            "R2V": "Reference-to-Video (Omni multi-reference)",
            "Ref2VA": "Reference-to-Video (Omni multi-reference)",
        }
        return descriptions.get(task_type, f"Google Flow Veo 3 ({task_type})")
