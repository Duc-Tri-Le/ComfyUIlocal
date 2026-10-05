"""
Google Flow Veo 3 Prompt Editor & Refine
Read, preview, inline edit, and AI-refine Google Flow Veo 3 prompts.
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
        String = _Field
    io = _DummyIO()


class Flow_Veo3_Editor(io.ComfyNode):
    """
    Google Flow Veo 3 Prompt Preview & Edit.
    Displays the generated prompt with syntax highlighting, allows inline editing,
    one-click AI refinement of individual camera kinematics or audio sections, and lock switch protection.
    """
    OUTPUT_NODE = True
    FUNCTION = "execute"
    CATEGORY = "🧪AILab/🎬 Google Flow Veo 3"

    @classmethod
    def define_schema(cls):
        return io.Schema(
            node_id="Flow_Veo3_Editor",
            display_name="Google Flow Veo 3 Prompt Preview & Edit",
            category="🧪AILab/🎬 Google Flow Veo 3",
            is_output_node=True,
            inputs=[
                io.String.Input(
                    "prompt",
                    multiline=True,
                    force_input=True,
                    default="",
                    optional=True,
                    tooltip="Connect PROMPT output from Google Flow Veo 3 Promptor here.",
                ),
                io.String.Input(
                    "_stored_prompt",
                    multiline=True,
                    default="",
                    tooltip="Internal storage — do not connect.",
                ),
            ],
            outputs=[
                io.String.Output(
                    "prompt",
                    display_name="PROMPT",
                    tooltip="The refined Google Flow Veo 3 prompt text ready for downstream video generator nodes.",
                ),
            ],
        )

    @classmethod
    def IS_CHANGED(cls, prompt: str = "", _stored_prompt: str = "", **kwargs):
        return float("nan")

    @classmethod
    def execute(cls, prompt: str = "", _stored_prompt: str = "", **kwargs) -> dict:
        incoming = str(prompt).strip() if prompt and str(prompt).strip() else ""
        stored = str(_stored_prompt).strip() if _stored_prompt else ""
        value = incoming if incoming else stored

        return {
            "ui": {
                "prompt": [value],
                "text": [value],
            },
            "result": (value,)
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("prompt",)
    OUTPUT_TOOLTIPS = ("The refined Google Flow Veo 3 prompt text ready for downstream video generator nodes.",)


# Aliases for compatibility
H3_PromptEditor = Flow_Veo3_Editor

NODE_CLASS_MAPPINGS = {
    "Flow_Veo3_Editor": Flow_Veo3_Editor,
    "H3_PromptEditor": Flow_Veo3_Editor,  # Legacy alias
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "Flow_Veo3_Editor": "Google Flow Veo 3 Prompt Preview & Edit",
    "H3_PromptEditor": "Google Flow Veo 3 Prompt Preview & Edit (Legacy Alias)",
}
