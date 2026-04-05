"""测试配置模块"""
import pytest

from feishu_auto.config import Config, get_config, set_config


def test_default_config():
    """测试默认配置"""
    config = Config()
    assert config.debug_port == 9222
    assert config.default_app_name == "openclaw"
    assert config.default_version == "0.0.1"


def test_get_config_singleton():
    """测试配置单例"""
    config1 = get_config()
    config2 = get_config()
    assert config1 is config2


def test_set_config():
    """测试设置配置"""
    custom_config = Config(debug_port=9999, default_app_name="test_app")
    set_config(custom_config)
    config = get_config()
    assert config.debug_port == 9999
    assert config.default_app_name == "test_app"
    # 重置为默认配置
    set_config(Config())
