"""
飞书频道 - 事件订阅（WebSocket 长连接）

使用 lark-oapi SDK 实现事件订阅
文档: https://open.feishu.cn/document/client-docs/bot-v3/events/overview
"""
from __future__ import annotations

import logging
import signal
import sys
import threading
import time
from typing import TYPE_CHECKING, Any, Callable

from feishu_auto.config import ConfigManager

if TYPE_CHECKING:
    import lark_oapi as lark

logger = logging.getLogger(__name__)


class FeishuEventClient:
    """飞书事件订阅客户端"""

    def __init__(
        self,
        app_id: str | None = None,
        app_secret: str | None = None,
        app_name: str = "openclaw",
    ) -> None:
        """
        初始化事件客户端

        Args:
            app_id: 应用 ID，默认从配置文件读取
            app_secret: 应用 Secret，默认从配置文件读取
            app_name: 应用名称
        """
        self.app_name = app_name
        self._app_id = app_id
        self._app_secret = app_secret
        self._client: Any = None
        self._event_handler: Any = None
        self._running = False
        self._thread: threading.Thread | None = None

        logger.info(f"[事件订阅] 初始化客户端")
        logger.info(f"  - 应用名称: {app_name}")

    @property
    def app_id(self) -> str:
        """获取 App ID"""
        if self._app_id:
            return self._app_id
        return ConfigManager().get_app_id(self.app_name)

    @property
    def app_secret(self) -> str:
        """获取 App Secret"""
        if self._app_secret:
            return self._app_secret
        return ConfigManager().get_app_secret(self.app_name)

    def on_message_receive(self, data: Any) -> None:
        """
        处理接收消息事件 (v2.0)

        事件类型: im.message.receive_v1
        """
        logger.info(f"[事件] 收到消息")
        logger.info(f"  - 消息 ID: {data.event.message.message_id}")
        logger.info(f"  - 消息类型: {data.event.message.message_type}")
        logger.info(f"  - 发送者: {data.event.sender.sender_id}")

    def on_customized_event(self, data: Any) -> None:
        """处理自定义事件 (v1.0)"""
        import lark_oapi as lark

        logger.info(f"[事件] 收到自定义事件")
        logger.info(f"  - 事件类型: {data.header.event_type}")
        logger.info(f"  - 事件数据: {lark.JSON.marshal(data, indent=4)}")

    def build_event_handler(self) -> Any:
        """构建事件处理器"""
        import lark_oapi as lark

        builder = lark.EventDispatcherHandler.builder("", "")

        # 注册 v2.0 版本消息接收事件
        builder.register_p2_im_message_receive_v1(self.on_message_receive)

        self._event_handler = builder.build()
        return self._event_handler

    def _signal_handler(self, signum: int, frame: Any) -> None:
        """信号处理器"""
        logger.info(f"\n[停止] 收到信号 {signum}，正在停止客户端...")
        self._running = False
        sys.exit(0)

    def start(
        self,
        log_level: Any = None,
        block: bool = True,
        auto_stop: bool = False,
    ) -> None:
        """
        启动长连接客户端

        Args:
            log_level: 日志级别
            block: 是否阻塞主线程
            auto_stop: 连接成功后自动停止（用于配置场景）
        """
        import lark_oapi as lark

        if log_level is None:
            log_level = lark.LogLevel.INFO

        app_id = self.app_id
        app_secret = self.app_secret

        if not app_id or not app_secret:
            logger.error("[错误] 缺少 App ID 或 App Secret")
            logger.error("  - 请先运行 feishu.py 完成应用配置")
            return

        logger.info(f"[启动] 正在连接飞书事件服务...")
        logger.info(f"  - App ID: {app_id[:12]}...")

        # 构建事件处理器
        if not self._event_handler:
            self.build_event_handler()

        # 创建 WebSocket 客户端
        self._client = lark.ws.Client(
            app_id,
            app_secret,
            event_handler=self._event_handler,
            log_level=log_level,
        )

        # 只在主线程中注册信号处理器
        if block and not auto_stop:
            signal.signal(signal.SIGINT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)

        logger.info("=" * 50)
        logger.info("[启动] 长连接客户端已启动")
        logger.info("  - 等待连接成功...")
        if auto_stop:
            logger.info("  - 连接成功后将自动停止（仅用于配置）")
        else:
            logger.info("  - 连接成功后会打印 'connected to wss://xxxxx'")
            logger.info("  - 看到连接成功后，请在飞书开放平台后台保存事件订阅配置")
            if block:
                logger.info("  - 按 Ctrl+C 停止")
        logger.info("=" * 50)

        self._running = True

        # auto_stop 模式：连接成功后自动返回
        if auto_stop:
            connected = threading.Event()

            def run_and_wait() -> None:
                self._client.start()
                time.sleep(5)
                connected.set()

            thread = threading.Thread(target=run_and_wait, daemon=True)
            thread.start()

            logger.info("  - 等待 WebSocket 连接建立（约5秒）...")
            connected.wait(timeout=10)
            logger.info("  - 连接已建立，可以保存配置了")
            return

        if block:
            # 启动客户端（阻塞）
            self._client.start()
        else:
            # 非阻塞模式
            self._thread = threading.Thread(target=self._client.start, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """停止客户端"""
        self._running = False
        logger.info("[停止] 事件订阅客户端已停止")


def create_event_client(app_name: str = "openclaw") -> FeishuEventClient:
    """创建事件客户端"""
    return FeishuEventClient(app_name=app_name)


def start_event_client(
    app_id: str | None = None,
    app_secret: str | None = None,
    block: bool = False,
    auto_stop: bool = False,
) -> FeishuEventClient | None:
    """
    启动事件订阅长连接

    Args:
        app_id: 应用 ID
        app_secret: 应用 Secret
        block: 是否阻塞主线程，默认 False（后台运行）
        auto_stop: 连接成功后自动停止（用于配置场景）
    """
    try:
        import lark_oapi as lark
    except ImportError:
        logger.error("[错误] 未安装 lark-oapi，请运行: pip install lark-oapi")
        return None

    logger.info("")
    logger.info("=" * 50)
    logger.info("[长连接] 启动事件订阅客户端")
    logger.info("=" * 50)

    client = FeishuEventClient(app_id=app_id, app_secret=app_secret)

    if block and not auto_stop:
        client.start(log_level=lark.LogLevel.INFO)
        return client
    else:
        client.start(log_level=lark.LogLevel.INFO, block=False, auto_stop=auto_stop)
        if auto_stop:
            logger.info("[长连接] 客户端已在后台启动（auto_stop 模式）")
            logger.info("  - 连接成功后将自动停止...")
        else:
            logger.info("[长连接] 客户端已在后台启动")
            logger.info("  - 等待连接成功...")
        return client
