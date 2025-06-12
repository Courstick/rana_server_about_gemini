import os
import argparse
import yaml
from collections.abc import Mapping
from config.manage_api_client import get_agent_models

# 添加全局配置缓存
_config_cache = None


def get_project_dir():
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"


def read_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config


def load_config():
    """加载配置文件"""
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    default_config_path = get_project_dir() + "config.yaml"
    custom_config_path = get_project_dir() + "data/.config.yaml"

    # 加载默认配置
    default_config = read_config(default_config_path)
    custom_config = read_config(custom_config_path)

    config = merge_configs(default_config, custom_config)
    # 初始化目录
    _config_cache = config
    return config


def get_private_config_from_api(config, device_id, client_id):
    """从Java API获取私有配置"""
    return get_agent_models(device_id, client_id, config["selected_module"])


def merge_configs(default_config, custom_config):
    """
    递归合并配置，custom_config优先级更高

    Args:
        default_config: 默认配置
        custom_config: 自定义配置

    Returns:
        合并后的配置
    """
    if not isinstance(default_config, Mapping) or not isinstance(
            custom_config, Mapping
    ):
        return custom_config

    merged = dict(default_config)

    for key, value in custom_config.items():
        if (
                key in merged
                and isinstance(merged[key], Mapping)
                and isinstance(value, Mapping)
        ):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value

    return merged
