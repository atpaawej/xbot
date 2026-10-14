"""Configuration package for xbot."""

from xbot.config.settings import (
    Config,
    get_config,
    get_config_file_paths,
    load_env_files,
    load_json_file,
    normalize_setting_key,
    save_json_file,
    set_config,
    strip_json_comments,
    update_setting,
)

__all__ = [
    "Config",
    "get_config",
    "get_config_file_paths",
    "load_env_files",
    "load_json_file",
    "normalize_setting_key",
    "save_json_file",
    "set_config",
    "strip_json_comments",
    "update_setting",
]
