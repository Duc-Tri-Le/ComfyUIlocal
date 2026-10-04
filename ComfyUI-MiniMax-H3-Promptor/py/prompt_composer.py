"""
Google Flow Veo 3 Prompt Composer
Manually compose, scaffold, and tag Google Flow Veo 3 prompts.
"""

try:
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
        String = Combo = _Field
    io = _DummyIO()

MODES = [
    "T2V (Text to Video)",
    "I2V (Image to Video)",
    "FL2V (First & Last Frame)",
    "R2V (Reference Omni)",
    "Custom / Blank",
]


class Flow_Veo3_Composer(io.ComfyNode):
    """
    Google Flow Veo 3 Manual Prompt Composer.
    Designed for rapid prompt engineering with Veo 3 mode scaffolds,
    cinematic syntax highlighting, and floating autocomplete menus.
    """
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "🧪AILab/🎬 Google Flow Veo 3"

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Flow_Veo3_Composer",
            display_name="Google Flow Veo 3 Prompt Composer",
            category="🧪AILab/🎬 Google Flow Veo 3",
            is_output_node=True,
            inputs=[
                io.Combo.Input(
                    "mode",
                    options=MODES,
                    default=MODES[0],
                    tooltip="Select the video generation mode to load standard Google Flow Veo 3 templates.",
                ),
                io.String.Input(
                    "_composer_prompt",
                    multiline=True,
                    default="",
                    tooltip="Internal storage of composed prompt — do not connect.",
                ),
            ],
            outputs=[
                io.String.Output(
                    "prompt",
                    display_name="PROMPT",
                    tooltip="The composed Google Flow Veo 3 prompt text ready for downstream video generation.",
                ),
            ],
        )

    @classmethod
    def IS_CHANGED(cls, mode: str = MODES[0], _composer_prompt: str = "", **kwargs):
        return float("nan")

    @classmethod
    def execute(cls, mode: str = MODES[0], _composer_prompt: str = "", **kwargs) -> dict:
        val = str(_composer_prompt).strip() if _composer_prompt else ""
        return {
            "ui": {
                "prompt": [val],
                "text": [val],
            },
            "result": (val,),
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    OUTPUT_TOOLTIPS = (
        "The composed Google Flow Veo 3 prompt text ready for downstream video generation.",
    )


# Aliases for compatibility
H3_PromptComposer = Flow_Veo3_Composer

NODE_CLASS_MAPPINGS = {
    "Flow_Veo3_Composer": Flow_Veo3_Composer,
    "H3_PromptComposer": Flow_Veo3_Composer,  # Legacy alias
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Flow_Veo3_Composer": "Google Flow Veo 3 Prompt Composer",
    "H3_PromptComposer": "Google Flow Veo 3 Prompt Composer (Legacy Alias)",
}
