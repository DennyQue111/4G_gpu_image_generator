from pathlib import Path

from inference_engine import Generation, SIZES, build_command, enhanced_prompt
from model_manager import Components, component_paths


def job():
    return Generation("古风，有山有水", "", "9:16", 3, 100, "居中", Path("out"))


def test_prompt_preserves_description_and_adds_text_space():
    prompt = enhanced_prompt("古风，有山有水", "居中")
    assert "古风，有山有水" in prompt
    assert "empty negative space in the center" in prompt
    assert "no text" in prompt


def test_build_command_uses_4gb_budget_and_sequential_seed(tmp_path):
    components = Components(tmp_path, tmp_path / "sd-cli.exe", tmp_path / "model.gguf")
    command = build_command(components, job(), 2, tmp_path / "raw.png")
    assert command[command.index("-s") + 1] == "102"
    assert command[command.index("--max-vram") + 1] == "3.5"
    assert command[command.index("-W") + 1] == str(SIZES["9:16"][0][0])


def test_component_paths_are_separate_from_exe(tmp_path):
    components = component_paths(tmp_path)
    assert components.root == tmp_path
    assert components.model.parent == tmp_path / "models"
    assert components.cli.parent == tmp_path / "runtime"
