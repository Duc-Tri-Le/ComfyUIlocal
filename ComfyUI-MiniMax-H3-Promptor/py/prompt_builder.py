"""
Google Flow Veo 3 Prompt Builder
Builds system prompts and user messages adhering to the Google Flow Veo 3 prompt formula:
[Camera/Shot] + [Subject] + [Action] + [Setting] + [Style & Audio]
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from .utils import log_info, log_error, log_debug

# Templates directory
_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


class PromptBuilder:
    """Build system prompts and user messages for Google Flow Veo 3 prompt generation."""

    def __init__(self, templates_dir: str | Path | None = None):
        self.templates_dir = Path(templates_dir) if templates_dir else _TEMPLATES_DIR

    def build_system_prompt(
        self,
        task_type: str,
        template_override: str | None = None,
        duration: float = 8.0,
        output_language: str = "English",
    ) -> str:
        """Assemble the complete system prompt from template files."""
        parts = []

        if output_language.lower() in ("chinese", "zh"):
            parts.append("CRITICAL: You MUST write the ENTIRE OUTPUT PROMPT in Simplified Chinese (简体中文).")
        elif output_language.lower() in ("vietnamese", "vi"):
            parts.append("CRITICAL: Write the scene description in English for Google Veo 3's visual comprehension, but dialogue can be in Vietnamese if specified.")
        else:
            parts.append("CRITICAL: You MUST write the ENTIRE OUTPUT PROMPT in fluent, cinematic English.")

        base = self._load_template("system_base.txt")
        if base:
            duration_str = f"Target Video Duration: {duration:.1f} seconds. Direct the action and kinetic momentum to fit naturally within this {duration:.1f}s window."
            parts.append(f"{base}\n\n{duration_str}")
        else:
            parts.append(self._fallback_base())

        # Map task type to template file
        clean_task = task_type.lower()
        if clean_task in ("fl2va", "fl2v"):
            tmpl_name = "fl2v.txt"
        elif clean_task in ("ref2va", "r2v"):
            tmpl_name = "r2v.txt"
        else:
            tmpl_name = f"{clean_task}.txt"

        if template_override and template_override != "default":
            task_template = self._load_template(template_override) or self._load_template(tmpl_name)
        else:
            task_template = self._load_template(tmpl_name)

        if task_template:
            parts.append(task_template)

        return "\n\n".join(parts)

    def generate_alignment_instruction(self, task_type: str, duration: float, image_count: int) -> str:
        """Generate subtle opening alignment guidance for image-conditioned tasks."""
        if task_type in ["I2V", "i2v"] and image_count >= 1:
            return "Opening directly matching the starting reference frame's composition, pose, and lighting."
        if task_type in ["FL2V", "FL2VA", "fl2v"] and image_count >= 2:
            return f"Beginning with the first reference frame and smoothly transitioning across {duration:.1f}s to conclude on the final frame."
        return ""

    @staticmethod
    def _detect_subject_noun(desc: str) -> str:
        """Accurately identify the natural noun/entity category using strict word boundaries."""
        low = desc.lower()

        # Vehicles & Props
        vehicle_patterns = [
            (r'\b(sports\s*car|supercar|race\s*car)\b', "sports car"),
            (r'\b(taxi|cab)\b', "taxi"),
            (r'\b(car|automobile|vehicle|sedan|coupe|suv|truck|van)\b', "vehicle"),
            (r'\b(motorcycle|motorbike|bike|bicycle|scooter)\b', "motorcycle"),
            (r'\b(airplane|plane|jet|aircraft|spaceship|shuttle)\b', "aircraft"),
            (r'\b(boat|ship|yacht|vessel)\b', "vessel"),
            (r'\b(robot|mech|cyborg|drone)\b', "robot"),
            (r'\b(armor|suit\s+of\s+armor)\b', "armor"),
        ]
        for pat, noun in vehicle_patterns:
            if re.search(pat, low):
                return noun

        # Animals / Creatures
        animal_patterns = [
            (r'\b(black\s+panther)\b', "black panther"),
            (r'\b(panther|leopard|jaguar|cheetah)\b', "panther"),
            (r'\b(tabby\s+cat)\b', "tabby cat"),
            (r'\bcat\b(?!\s*[-_]?\s*(?:ear|tail|eye|print|suit|hat|mask))', "cat"),
            (r'\btiger\b(?!\s*[-_]?\s*(?:stripe|print|pattern))', "tiger"),
            (r'\blion\b(?!\s*[-_]?\s*(?:print|pattern))', "lion"),
            (r'\b(dog|puppy|hound|wolf|fox|bear|dragon|horse|stallion|eagle|hawk|bird|rabbit|deer|creature|beast)\b', None),
        ]
        for pat, noun in animal_patterns:
            m = re.search(pat, low)
            if m:
                return noun if noun else m.group(1)

        # Humanoid / Person
        person_patterns = [
            (r'\b(woman|girl|female|lady|she|her)\b', "young woman"),
            (r'\b(boy|guy|young\s+man)\b', "young man"),
            (r'\b(man|male|gentleman|he|his)\b', "man"),
            (r'\b(warrior|knight|soldier|fighter|ninja|samurai)\b', "warrior"),
        ]
        for pat, noun in person_patterns:
            m = re.search(pat, low)
            if m:
                return noun

        return "subject"

    def generate_subject_definitions(
        self,
        image_count: int,
        has_video: bool = False,
        has_audio: bool = False,
        parsed_vision_dict: Optional[Dict[str, Any]] = None,
    ) -> tuple[str, list[str]]:
        """
        Extract clean subject descriptions from vision analysis
        to weave naturally into the Veo 3 prompt prose.
        """
        lines = []
        valid_tags = []

        if parsed_vision_dict and isinstance(parsed_vision_dict, dict):
            for i in range(image_count):
                key = f"<Picture {i+1}>"
                desc = parsed_vision_dict.get(key, "").strip()
                if desc and "failed to analyze" not in desc.lower():
                    valid_tags.append(key)
                    noun = self._detect_subject_noun(desc)
                    cleaned = re.sub(r'^(?:the\s+)?(?:main\s+)?(?:subject|character|image|picture)\s+(?:is|has|shows|depicts)\s+', '', desc, flags=re.IGNORECASE).strip()
                    lines.append(f"Reference {i+1} ({noun}): {cleaned}")

            if has_video:
                desc = parsed_vision_dict.get("<Video 1>", "").strip()
                if desc and "failed to analyze" not in desc.lower():
                    lines.append(f"Reference Video: {desc}")
                    valid_tags.append("<Video 1>")

            return "\n".join(lines), valid_tags
        else:
            return "", []

    def build_blueprint_system_prompt(self, output_language: str = "English") -> str:
        """System prompt for Stage 1: Google Flow Veo 3 Director Blueprint synthesis."""
        return """You are a master Hollywood Director, Cinematographer, and Screenwriter for Google Flow Veo 3.
Your task is to analyze the user's vision and reference media to produce a high-impact 'Director Blueprint'.

OUTPUT STRUCTURE:
1. [Visual Aesthetic & Lighting]: Lighting setup (volumetric, golden hour, rim light), color palette, and atmosphere.
2. [Cinematography & Camera Choreography]: Lens selection (e.g. 35mm, anamorphic, shallow depth of field) and camera motion (dolly, tracking, pan, crane) formulated as an independent sentence.
3. [Subject & Kinetic Action Arc]: Character actions, expressions, and physical momentum over the 8s clip.
4. [Dialogue & Native Audio Design]: Spoken dialogue with (no subtitles), plus ambient room tone, physical Foley SFX, and musical score.
"""

    def build_blueprint_user_message(
        self,
        description: str,
        duration: float,
        task_type: str,
        vision_context: str = "",
        output_language: str = "English",
        image_count: int = 0,
        has_video: bool = False,
        parsed_vision_dict: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Construct user message for Stage 1: Blueprint Synthesis."""
        msg = f"Task: Construct the Director's Blueprint for a {duration:.1f}s Google Flow Veo 3 ({task_type}) video.\n\n"
        if vision_context:
            msg += f"--- REFERENCE MEDIA ANALYSIS ---\n{vision_context}\n--------------------------------\n\n"
        msg += f"USER'S SCENE DIRECTION & STORY:\n{description}\n\n"
        msg += f"CONSTRAINTS:\n- Duration is {duration:.1f} seconds.\n- Camera movement must be isolated as its own sentence.\n- Dialogue must include (no subtitles).\n"
        return msg

    def build_storyboard_user_message(
        self,
        blueprint: str,
        description: str,
        duration: float,
        task_type: str,
        output_language: str = "English",
        available_tags: Optional[List[str]] = None,
    ) -> str:
        """Construct user message for Stage 2: Prompt Generation using the Stage 1 Blueprint."""
        msg = f"--- APPROVED DIRECTOR BLUEPRINT ---\n{blueprint}\n-----------------------------------\n\n"
        msg += f"USER'S CREATIVE MANDATE:\n{description}\n\n"
        msg += f"DIRECTING TASK: Synthesize the approved Blueprint into the final, masterclass Google Flow Veo 3 prompt.\n"
        msg += "CRITICAL RULES:\n"
        msg += "1. Write 100-150 words of flowing, cinematic prose following: [Camera/Shot] + [Subject] + [Action] + [Setting] + [Style & Lighting].\n"
        msg += "2. Camera movement MUST be written as its own separate sentence (e.g. 'The camera slowly dollies in at eye level.').\n"
        msg += "3. Any dialogue must be formatted strictly as: Character says: \"...\" (no subtitles)\n"
        msg += "4. Do NOT output shot bracket numbers like [Shot 1] or section headers like 'detailed_description:'. Use natural prose transitions like 'Then cut to' if multi-shot.\n"
        msg += "5. Conclude strictly with the four labeled lines:\n"
        msg += "   Audio: [ambient soundscape]\n"
        msg += "   SFX: [Foley sounds]\n"
        msg += "   Music: [musical score]\n"
        msg += "   Negative: subtitles, watermark, text overlay, blurry, distorted face, low quality\n"
        return msg

    def build_vision_system_prompt(self, output_language: str = "English") -> str:
        """Assemble the system prompt for the vision analyzer."""
        return (
            "You are an expert film director and visual analyst for Google Flow Veo 3.\n"
            "Analyze the provided visual media (subjects, clothing, lighting, camera angle, and environment) "
            "so the details can be faithfully incorporated into cinematic video prompts.\n"
            "Output ONLY a valid JSON dictionary mapping the media keys (e.g. '<Picture 1>') to concise, vivid visual descriptions."
        )

    def build_vibe_system_prompt(self) -> str:
        """Assemble the system prompt for the Global Vibe synthesis step."""
        return (
            "You are an expert cinematic visual analyst. "
            "Synthesize the overall visual atmosphere, lighting scheme, and aesthetic style across the provided media."
        )

    @staticmethod
    def parse_overrides(custom_prompt_override: str) -> dict:
        overrides = {}
        for line in custom_prompt_override.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                overrides[k.strip()] = v.strip()
        return overrides

    def build_vision_request(self, output_language: str, target_key: str, active_prompt: str, pos: int = 0, is_video: bool = False, num_frames: int = 1) -> str:
        if is_video:
            return f"{target_key}: Analyze this video sequence for camera motion, subject dynamics, and lighting -> {active_prompt}"
        return f"{target_key}: Analyze this image for subject identity, clothing, lighting, and setting -> {active_prompt}"

    def build_vibe_request(self, output_language: str, final_dict: dict, vibe_prompt_en: str) -> str:
        context_str = json.dumps(final_dict, ensure_ascii=False)
        return f"Based on the following media analyses:\n{context_str}\n\nProvide the overall aesthetic and lighting vibe: {vibe_prompt_en}"

    def get_available_templates(self) -> list[str]:
        templates = ["default"]
        if not self.templates_dir.exists():
            return templates
        for f in sorted(self.templates_dir.glob("*.txt")):
            if f.stem != "system_base":
                templates.append(f.name)
        return templates

    def _load_template(self, filename: str) -> str | None:
        path = self.templates_dir / filename
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except IOError:
            return None

    @staticmethod
    def _fallback_base() -> str:
        return "You are a professional Google Flow Veo 3 prompt writer."
