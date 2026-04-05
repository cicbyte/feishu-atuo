"""
飞书开放平台自动化配置工具

提供飞书开放平台的自动化配置功能，包括：
- 浏览器自动化操作
- 应用管理
- 权限配置
- 版本管理
- 事件订阅
"""

from feishu_auto.config import Config, get_config
from feishu_auto.browser import BrowserBase, PageHelper
from feishu_auto.feishu import FeishuBrowser
from feishu_auto.event import FeishuEventClient, create_event_client

__version__ = "0.1.0"
__all__ = [
    # Config
    "Config",
    "get_config",
    # Browser
    "BrowserBase",
    "PageHelper",
    # Main
    "FeishuBrowser",
    # Event
    "FeishuEventClient",
    "create_event_client",
]
