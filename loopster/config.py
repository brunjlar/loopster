from __future__ import annotations

import os
import pathlib
import sys
from dataclasses import dataclass
from typing import Any, Dict, Optional


try:  # Python 3.11+
    import tomllib  # type: ignore[attr-defined]
except Exception:  # pragma: no cover
    tomllib = None  # type: ignore


@dataclass
class LoopsterConfig:
    provider: Optional[str] = None
    tool: Optional[str] = None
    tool_config_path: Optional[str] = None
    capture_method: str = "auto"  # auto|pty|script
    log_dir: Optional[str] = None


def load_toml(path: str | os.PathLike[str]) -> Dict[str, Any]:
    if tomllib is None:
        raise RuntimeError("TOML support requires Python 3.11+")
    data = pathlib.Path(path).read_bytes()
    return tomllib.loads(data.decode("utf-8"))


def from_file(path: str | None) -> Dict[str, Any]:
    if not path:
        return {}
    p = pathlib.Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    if p.suffix.lower() in {".toml"}:
        return load_toml(p)
    raise ValueError(f"Unsupported config format: {p.suffix}")


def merge_config(
    file_cfg: Dict[str, Any],
    env: Dict[str, str],
    cli: Dict[str, Any],
) -> LoopsterConfig:
    # Flatten keys we care about for initial pass
    def get_env(name: str) -> Optional[str]:
        return env.get(name)

    provider = cli.get("provider") or get_env("LOOPSTER_PROVIDER") or file_cfg.get("provider")
    tool = cli.get("tool") or get_env("LOOPSTER_TOOL") or file_cfg.get("tool")
    tool_config_path = (
        cli.get("tool_config_path")
        or get_env("LOOPSTER_TOOL_CONFIG_PATH")
        or file_cfg.get("tool_config_path")
    )
    capture_method = (
        cli.get("capture_method")
        or get_env("LOOPSTER_CAPTURE_METHOD")
        or file_cfg.get("capture", {}).get("method")
        or "auto"
    )
    log_dir = cli.get("log_dir") or get_env("LOOPSTER_LOG_DIR") or file_cfg.get("log_dir")

    return LoopsterConfig(
        provider=provider,
        tool=tool,
        tool_config_path=tool_config_path,
        capture_method=capture_method,
        log_dir=log_dir,
    )

