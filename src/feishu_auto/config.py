"""
飞书频道 - 配置管理
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


def get_user_config_dir() -> Path:
    """获取用户配置目录 (~/.feishu-auto)"""
    config_dir = Path.home() / ".feishu-auto"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


# 默认用户配置目录
_USER_CONFIG_DIR = get_user_config_dir()


@dataclass
class Config:
    """飞书配置类"""

    # 调试端口
    debug_port: int = 9222
    # 用户数据目录（存放在用户目录 ~/.feishu-auto 下）
    user_data_dir: str = field(default_factory=lambda: str(_USER_CONFIG_DIR / "user_data"))
    # 权限配置文件路径
    auth_file: str = field(default_factory=lambda: str(_USER_CONFIG_DIR / "auth.json"))
    # 已登录后跳转的页面
    open_platform_url: str = "https://open.feishu.cn/app?lang=zh-CN"
    # 应用 ID 正则表达式
    app_id_pattern: str = r"cli_[a-zA-Z0-9]+"
    # 默认应用名称
    default_app_name: str = "openclaw"
    # 默认版本号
    default_version: str = "0.0.1"
    # 默认版本描述
    default_version_desc: str = "初始版本"
    # 日志级别
    log_level: str = "INFO"


# 全局配置实例
_config: Config | None = None


def get_config() -> Config:
    """获取全局配置实例"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def set_config(config: Config) -> None:
    """设置全局配置实例"""
    global _config
    _config = config


def get_project_root() -> Path:
    """获取项目根目录"""
    return Path(__file__).parent.parent.parent


def get_abs_path(relative_path: str) -> str:
    """获取相对路径的绝对路径"""
    return str(get_project_root() / relative_path)


class ConfigManager:
    """配置管理器（纯内存缓存）"""

    # 类级别的内存缓存
    _memory_cache: dict = {}

    def load(self) -> dict:
        """加载配置（从内存缓存）"""
        return ConfigManager._memory_cache

    def save(self, config: dict) -> None:
        """保存配置（仅保存到内存缓存）"""
        ConfigManager._memory_cache = config

    def get_app_id(self, app_name: str | None = None) -> str:
        """获取应用 ID"""
        app_name = app_name or get_config().default_app_name
        config = self.load()
        app_id = config.get("apps", {}).get(app_name, "")
        if app_id:
            logger.info(f"[配置] 读取应用 ID: {app_name} -> {app_id}")
        return app_id

    def save_app_id(self, app_name: str, app_id: str) -> None:
        """保存应用 ID（仅内存）"""
        config = self.load()
        if "apps" not in config:
            config["apps"] = {}
        config["apps"][app_name] = app_id
        self.save(config)
        logger.info(f"[配置] 已缓存应用 ID: {app_name} -> {app_id}")

    def get_app_secret(self, app_name: str | None = None) -> str:
        """获取 App Secret"""
        app_name = app_name or get_config().default_app_name
        config = self.load()
        return config.get("secrets", {}).get(app_name, "")

    def save_app_secret(self, app_name: str, secret: str) -> None:
        """保存 App Secret（仅内存）"""
        app_name = app_name or get_config().default_app_name
        config = self.load()
        if "secrets" not in config:
            config["secrets"] = {}
        config["secrets"][app_name] = secret
        self.save(config)
        logger.info(f"[配置] 已缓存 App Secret: {app_name}")

    def get_full_config(self, app_name: str | None = None) -> dict:
        """获取应用完整配置（app_id + app_secret）"""
        app_name = app_name or get_config().default_app_name
        config = self.load()
        return {
            "app_id": config.get("apps", {}).get(app_name, ""),
            "app_secret": config.get("secrets", {}).get(app_name, ""),
        }
