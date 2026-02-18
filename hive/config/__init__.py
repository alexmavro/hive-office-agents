"""Configuration module for hive."""

from hive.config.loader import load_config, get_config_path
from hive.config.schema import Config

__all__ = ["Config", "load_config", "get_config_path"]
