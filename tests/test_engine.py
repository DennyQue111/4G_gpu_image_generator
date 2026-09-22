from pathlib import Path

from background_engine import Settings, make_background, save_batch


def settings(width=320, height=480):
    return Settings(width, height, "流体光带", "深蓝色科技风", "#173b72", 25, "居中", 42)


def test_generate_dimensions_and_mode():
    image = make_background(settings())
    assert image.size == (320, 480)
    assert image.mode == "RGB"


def test_seed_is_reproducible():
    first = make_background(settings())
    second = make_background(settings())
    assert first.tobytes() == second.tobytes()


def test_variants_are_different():
    first = make_background(settings(), 0)
    second = make_background(settings(), 1)
    assert first.tobytes() != second.tobytes()


def test_save_batch(tmp_path: Path):
    paths = save_batch(settings(160, 240), 3, tmp_path, "JPG")
    assert len(paths) == 3
    assert all(path.exists() and path.suffix == ".jpg" for path in paths)
