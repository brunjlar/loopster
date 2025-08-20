import os
from loopster.config import from_file, merge_config, LoopsterConfig


def test_load_and_merge_config_env_and_cli(tmp_path, monkeypatch):
    # File config
    cfg_file = tmp_path / "config.toml"
    cfg_file.write_text(
        """
provider = "gemini"
tool = "gemini-cli"
log_dir = "logs"
        """.strip()
    )

    file_cfg = from_file(str(cfg_file))

    # Env overrides tool
    monkeypatch.setenv("LOOPSTER_TOOL", "codex-cli")

    # CLI overrides env
    cli_cfg = {"provider": "codex", "log_dir": "/tmp/logs"}

    merged = merge_config(file_cfg, os.environ, cli_cfg)
    assert isinstance(merged, LoopsterConfig)
    assert merged.provider == "codex"  # from CLI
    assert merged.tool == "codex-cli"  # from ENV
    assert merged.log_dir == "/tmp/logs"  # from CLI
