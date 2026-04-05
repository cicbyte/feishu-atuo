"""
飞书频道 - 浏览器基础类
"""
from __future__ import annotations

import logging
import random
import re
import socket
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from feishu_auto.config import get_config, get_abs_path

if TYPE_CHECKING:
    from DrissionPage import ChromiumPage

logger = logging.getLogger(__name__)


class BrowserBase:
    """浏览器基础类"""

    def __init__(
        self,
        port: int | None = None,
        user_data_path: str | None = None,
    ) -> None:
        """
        初始化浏览器配置

        Args:
            port: 调试端口，默认使用配置中的端口
            user_data_path: 用户数据路径，默认使用配置中的路径
        """
        config = get_config()
        self.port = port or config.debug_port
        self.user_data_path = user_data_path or config.user_data_dir
        self._browser: ChromiumPage | None = None
        self._tab: Any = None

        logger.info(f"[初始化] 浏览器配置")
        logger.info(f"  - 调试端口: {self.port}")
        logger.info(f"  - 用户数据路径: {self._get_abs_user_data_path()}")

    def _get_abs_user_data_path(self) -> str:
        """获取用户数据的绝对路径（自动创建目录）"""
        path = Path(self.user_data_path)
        if not path.is_absolute():
            path = Path(get_abs_path(self.user_data_path))
        # 确保目录存在
        path.mkdir(parents=True, exist_ok=True)
        return str(path)

    def _is_port_in_use(self, port: int) -> bool:
        """检测端口是否已被占用"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("127.0.0.1", port)) == 0

    def _create_options(self) -> Any:
        """创建浏览器配置选项"""
        from DrissionPage import ChromiumOptions

        co = ChromiumOptions()

        # 设置调试端口（调试模式核心配置）
        co.set_local_port(self.port)

        # 设置用户数据持久化路径
        co.set_user_data_path(self._get_abs_user_data_path())

        # 可选：设置页面加载策略
        co.set_load_mode("eager")  # 'normal' | 'eager' | 'none'

        # 可选：设置超时时间（秒）
        co.set_timeouts(base=10, page_load=30, script=30)

        return co

    @property
    def browser(self) -> ChromiumPage:
        """获取浏览器实例（懒加载，自动复用已运行的浏览器）"""
        if self._browser is None:
            from DrissionPage import ChromiumPage

            port_in_use = self._is_port_in_use(self.port)

            if port_in_use:
                logger.info(f"[复用] 端口 {self.port} 已有浏览器运行，直接接管")
                # 直接通过端口连接已运行的浏览器
                self._browser = ChromiumPage(addr_or_opts=self.port)
            else:
                logger.info(f"[启动] 端口 {self.port} 可用，启动新浏览器")
                co = self._create_options()
                self._browser = ChromiumPage(addr_or_opts=co)

        return self._browser

    @property
    def tab(self) -> Any:
        """获取当前标签页"""
        if self._tab is None:
            self._tab = self.browser.latest_tab
        return self._tab

    def close(self) -> None:
        """关闭浏览器（保留用户数据）"""
        if self._browser:
            logger.info("[关闭] 正在关闭浏览器...")
            self._browser.quit()
            self._browser = None
            self._tab = None
            logger.info("  - 浏览器已关闭")

    def goto_url(self, url: str) -> None:
        """跳转到指定 URL"""
        logger.info(f"[跳转] 正在跳转到: {url}")
        self.tab.get(url)
        logger.info(f"  - 跳转完成，当前页面: {self.tab.title}")

    def wait(self, seconds: float = 2) -> None:
        """等待指定秒数"""
        time.sleep(seconds)

    def random_wait(self, min_seconds: float = 1, max_seconds: float = 3) -> None:
        """随机等待"""
        wait_time = random.uniform(min_seconds, max_seconds)
        time.sleep(wait_time)


class PageHelper:
    """页面操作辅助类"""

    def __init__(self, tab: Any) -> None:
        self.tab = tab

    def find_element(self, xpath: str, timeout: float = 3) -> Any:
        """查找元素（XPath 格式，需要以 x: 开头）"""
        return self.tab.ele(xpath, timeout=timeout)

    def click_element(self, xpath: str, timeout: float = 3) -> bool:
        """点击元素"""
        ele = self.find_element(xpath, timeout)
        if ele:
            ele.click()
            return True
        return False

    def input_text(
        self,
        xpath: str,
        text: str,
        timeout: float = 3,
        clear_first: bool = True,
    ) -> bool:
        """输入文本"""
        ele = self.find_element(xpath, timeout)
        if not ele:
            return False
        if clear_first:
            ele.clear()
        ele.input(text)
        return True

    def get_current_url(self) -> str:
        """获取当前 URL"""
        return self.tab.url

    def extract_pattern(self, pattern: str, text: str | None = None) -> str:
        """从文本中提取匹配正则的内容"""
        text = text or self.get_current_url()
        match = re.search(pattern, text)
        if match:
            return match.group()
        return ""

    def select_all(self) -> None:
        """全选（Ctrl+A）"""
        from DrissionPage.common import Keys

        self.tab.actions.type(Keys.CTRL_A)

    def delete(self) -> None:
        """删除（Backspace）"""
        from DrissionPage.common import Keys

        self.tab.actions.type(Keys.BACKSPACE)

    def paste(self) -> None:
        """粘贴（Ctrl+V）"""
        from DrissionPage.common import Keys

        self.tab.actions.key_down(Keys.CTRL)
        self.tab.actions.type("v")
        self.tab.actions.key_up(Keys.CTRL)

    def copy_to_clipboard(self, text: str) -> bool:
        """复制文本到剪贴板"""
        try:
            import pyperclip

            pyperclip.copy("")
            pyperclip.copy(text)
            return True
        except ImportError:
            logger.warning("  - 警告: 未安装 pyperclip")
            return False

    def get_from_clipboard(self) -> str:
        """从剪贴板获取文本"""
        try:
            import pyperclip

            return pyperclip.paste()
        except ImportError:
            logger.warning("  - 警告: 未安装 pyperclip")
            return ""
