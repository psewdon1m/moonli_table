from pathlib import Path

from app.services.vectorizer import build_vector_assets


def test_build_vector_assets_creates_master_and_layers(tmp_path: Path) -> None:
    pack_dir = tmp_path / "pack_demo"
    pack_dir.mkdir(parents=True, exist_ok=True)
    palette = ["#FF0000", "#00FF00", "#0000FF"]

    vector_assets = build_vector_assets(
        pack_dir=pack_dir,
        candidate_id="cand_123",
        palette=palette,
    )

    master_svg = pack_dir / vector_assets["master_svg"]
    assert master_svg.exists()
    assert "<svg" in master_svg.read_text(encoding="utf-8")
    assert len(vector_assets["color_layers"]) == len(palette)
    for entry in vector_assets["color_layers"]:
        layer_path = pack_dir / entry["path"]
        assert layer_path.exists()
        content = layer_path.read_text(encoding="utf-8")
        assert "<path" in content
        assert entry["color"] in content

