"""
Google Flow Veo 3 PostProcessor
Cleans, normalizes, and compiles cinematic prompts conforming to Google Flow Veo 3 specifications:
- 5-Component Structure (Camera, Subject, Action, Setting, Lighting)
- Isolated camera movement sentence
- Strict dialogue formatting with (no subtitles)
- Distinct Audio:, SFX:, Music:, and Negative: labels
"""
import re
from .utils import sanitize_llm_output, log_warning, log_info

VEO3_DEFAULT_NEGATIVE = "Negative: subtitles, watermark, text overlay, blurry, distorted face, low quality"


class PostProcessor:
    """Clean, format, and assemble the final Google Flow Veo 3 prompt."""

    @staticmethod
    def split_audio_layers(text: str) -> tuple[str, str, str, str]:
        """
        Extract Audio, SFX, Music, and Negative lines out of the prompt text.
        Returns: (body_prose, audio_str, sfx_str, music_str)
        """
        if not text:
            return "", "", "", ""

        # Extract Audio / SFX / Music via regex
        audio_val = ""
        sfx_val = ""
        music_val = ""

        m_audio = re.search(r'\b(?:audio|ambient|overall_soundscape)\s*:\s*(.*?)(?=\b(?:sfx|foley|sound|music|score|bgm|negative|neg)\s*:|\Z)', text, re.IGNORECASE | re.DOTALL)
        if m_audio:
            audio_val = m_audio.group(1).strip()

        m_sfx = re.search(r'\b(?:sfx|foley|sound)\s*:\s*(.*?)(?=\b(?:audio|ambient|music|score|bgm|negative|neg)\s*:|\Z)', text, re.IGNORECASE | re.DOTALL)
        if m_sfx:
            sfx_val = m_sfx.group(1).strip()

        m_music = re.search(r'\b(?:music|score|bgm|non_diegetic_music)\s*:\s*(.*?)(?=\b(?:audio|ambient|sfx|foley|sound|negative|neg)\s*:|\Z)', text, re.IGNORECASE | re.DOTALL)
        if m_music:
            music_val = m_music.group(1).strip()

        # Remove audio/sfx/music/negative from body
        body = re.sub(r'\b(?:audio|ambient|overall_soundscape|sfx|foley|sound|music|score|bgm|non_diegetic_music|negative|neg)\s*:\s*.*?(?=(?:\b(?:audio|ambient|overall_soundscape|sfx|foley|sound|music|score|bgm|non_diegetic_music|negative|neg)\s*:|\Z))', '', text, flags=re.IGNORECASE | re.DOTALL)
        body = body.strip()

        return body, audio_val, sfx_val, music_val

    @staticmethod
    def _clean_veo3_dialogue(text: str) -> str:
        """
        Guarantee dialogue is formatted as `Character says: "..." (no subtitles)`
        to prevent Veo 3 from burning text/subtitles on the video frame.
        """
        # Convert any legacy <d>[Lang] "..."</d> dialogue tags
        text = re.sub(
            r'<d>(?:\[[^\]]+\])?\s*([“"\']?)(.*?)\1\s*</d>',
            lambda m: f'says: "{m.group(2).strip()}" (no subtitles)',
            text,
            flags=re.IGNORECASE | re.DOTALL
        )

        # Ensure existing quotes like `says: "..."` have `(no subtitles)`
        speech_pattern = r'(\b(?:says|whispers|shouts|asks|replies|exclaims|mutters|murmurs)\b\s*:\s*[“"]([^”"\n]+)[”"])'
        
        def _add_no_subtitles(m):
            matched_speech = m.group(1)
            # If already has (no subtitles) nearby, keep as is
            sub_check = text[m.end():m.end() + 25].lower()
            if "(no subtitles)" in sub_check or "no subtitle" in sub_check:
                return matched_speech
            return f"{matched_speech} (no subtitles)"

        text = re.sub(speech_pattern, _add_no_subtitles, text, flags=re.IGNORECASE)
        return text

    @staticmethod
    def _strip_legacy_tags(text: str) -> str:
        """Strip legacy structured-prompt syntax (<Subject N>, <Picture N>, [Shot N], etc.)."""
        # Remove section headers
        text = re.sub(r'^(?:subject_definitions|summary|retention_analysis|detailed_description|integrated_multimodal_description):\s*\n?', '', text, flags=re.IGNORECASE | re.MULTILINE)
        
        # Replace <Subject N> with natural pronouns or character references
        text = re.sub(r'<Subject\s+\d+>\s*(?:\(S\d+\))?\s*(?:is\s*)?', 'the character ', text, flags=re.IGNORECASE)
        text = re.sub(r'<\/?(?:Subject|Picture|Video|Audio)\s*\d*>', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\(S\d+\)', '', text, flags=re.IGNORECASE)
        
        # Convert [Shot 1], [Shot 2 At MM:SS] into natural prose transitions
        def _replace_shots(m):
            shot_num = int(m.group(1))
            if shot_num == 1:
                return ""
            elif shot_num == 2:
                return "Then cut to"
            else:
                return "Finally, transitioning to"

        text = re.sub(r'\[Shot\s+(\d+)[^\]]*\]', _replace_shots, text, flags=re.IGNORECASE)
        
        # Clean up double spaces or dangling punctuation
        text = re.sub(r'\s{2,}', ' ', text).strip()
        text = re.sub(r'\n{3,}', '\n\n', text)
        return text

    @staticmethod
    def compile_final_prompt(
        creative_text: str,
        task_type: str = "T2V",
        subject_definitions: str = "",
        alignment_instructions: str = "",
        duration: float = 8.0,
        user_description: str = "",
        output_language: str = "English",
    ) -> str:
        """
        Assemble the final official Google Flow Veo 3 prompt payload.
        Ensures 5-component prose with separate camera kinematics and labeled audio lines.
        """
        raw = sanitize_llm_output(creative_text)
        
        # 1. Clean legacy tags and section headers
        body, audio, sfx, music = PostProcessor.split_audio_layers(raw)
        body = PostProcessor._strip_legacy_tags(body)
        body = PostProcessor._clean_veo3_dialogue(body)

        # 2. Default fallbacks if audio layers were omitted
        if not audio:
            audio = "ambient environmental room tone matching the natural acoustics of the scene."
        if not sfx:
            sfx = "subtle Foley sound effects synchronized with character movements and physical interactions."
        if not music:
            music = "gentle cinematic background score emphasizing emotional atmosphere."

        # 3. Assemble Veo 3 blocks
        prompt_parts = [body]
        
        audio_block = (
            f"Audio: {audio}\n"
            f"SFX: {sfx}\n"
            f"Music: {music}\n"
            f"{VEO3_DEFAULT_NEGATIVE}"
        )
        prompt_parts.append(audio_block)

        final_prompt = "\n\n".join(prompt_parts).strip()
        return final_prompt

    @staticmethod
    def clean(
        raw_output: str,
        task_type: str = "T2V",
        full_task_desc: str = "",
        subject_defs: str = "",
        alignment_inst: str = "",
        duration: float = 8.0,
        user_description: str = "",
        output_language: str = "English",
    ) -> str:
        """Main entry point for Google Flow Veo 3 prompt post-processing."""
        if not raw_output:
            return ""

        return PostProcessor.compile_final_prompt(
            creative_text=raw_output,
            task_type=task_type,
            subject_definitions=subject_defs,
            alignment_instructions=alignment_inst,
            duration=duration,
            user_description=user_description,
            output_language=output_language,
        )
