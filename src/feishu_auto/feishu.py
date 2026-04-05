"""
飞书频道 - 主类（组合各功能模块）
"""
from __future__ import annotations

import json
import logging
import sys
import time
from typing import TYPE_CHECKING, Any

from feishu_auto.app import AppMixin
from feishu_auto.auth import AuthMixin
from feishu_auto.browser import BrowserBase
from feishu_auto.config import get_config
from feishu_auto.event import start_event_client
from feishu_auto.version import VersionMixin

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class FeishuBrowser(BrowserBase, AppMixin, AuthMixin, VersionMixin):
    """
    飞书浏览器自动化类

    组合以下功能模块：
    - BrowserBase: 浏览器基础操作
    - AppMixin: 应用管理
    - AuthMixin: 权限管理
    - VersionMixin: 版本管理
    """

    def __init__(
        self,
        port: int | None = None,
        user_data_path: str | None = None,
        app_name: str = "openclaw",
    ) -> None:
        super().__init__(port, user_data_path)
        self.app_name = app_name
        self.app_id = ""
        self.app_secret = ""

    def open_feishu(
        self,
        url: str = "https://www.feishu.cn",
        auto_close_popup: bool = True,
        auto_login: bool = True,
        app_name: str | None = None,
    ) -> Any:
        """
        打开飞书页面

        Args:
            url: 飞书页面地址
            auto_close_popup: 是否自动关闭弹框
            auto_login: 是否自动检查登录状态
            app_name: 应用名称（可选，默认使用 self.app_name）

        Returns:
            tab 对象，如果需要登录则返回 None
        """
        config = get_config()

        logger.info(f"[访问] 正在打开飞书页面: {url}")
        self.tab.get(url)
        logger.info(f"  - 页面标题: {self.tab.title}")

        if auto_close_popup:
            logger.info("[弹框] 检查并关闭首页弹框...")
            self.close_popup()

        if auto_login:
            logger.info("[登录] 检查登录状态...")
            if self.check_and_click_login(app_name=app_name or self.app_name):
                sys.exit(0)

        return self.tab

    def close_popup(self, timeout: float = 3) -> bool:
        """关闭首页弹框"""
        # XPath 定位策略（按优先级尝试）
        xpath_selectors = [
            "x://div[contains(@class, 'popup-close') and contains(@class, 'popup-close-pc')]",
            "x://div[contains(@class, 'popup-close-pc')]",
            "x://div[contains(@class, 'popup-close')]",
        ]

        for i, xpath in enumerate(xpath_selectors):
            try:
                logger.info(f"  - 尝试策略 {i+1}/{len(xpath_selectors)}: {xpath}")
                close_btn = self.tab.ele(xpath, timeout=timeout)
                if close_btn:
                    logger.info("  - 发现弹框关闭按钮，正在点击...")
                    close_btn.click()
                    logger.info("  - 弹框已关闭")
                    return True
                else:
                    logger.info("  - 未找到匹配元素")
            except Exception as e:
                logger.info(f"  - 查找失败: {e}")
                continue

        logger.info("  - 无弹框或弹框已处理")
        return False

    def check_and_click_login(
        self, timeout: float = 3, app_name: str | None = None
    ) -> bool:
        """
        检查是否需要登录

        Returns:
            True 表示未登录，已跳转到登录页面，程序应退出
            False 表示已登录，继续执行
        """
        config = get_config()

        logger.info(f"  - 正在检查登录状态...")
        logger.info(f"  - 当前 URL: {self.tab.url}")

        # 检查 URL 是否已经是登录页面
        if "login" in self.tab.url.lower() or "accounts" in self.tab.url.lower():
            logger.info("")
            logger.info("=" * 50)
            logger.info("[登录] 检测到未登录状态（登录页面）")
            logger.info("=" * 50)
            logger.info("")
            logger.info("[提示] 请在当前登录页面扫码登录")
            logger.info("[提示] 登录成功后，请重新运行程序")
            logger.info("=" * 50)
            return True

        # XPath 定位登录按钮
        login_btn = self.tab.ele('x://a[text()="登录/注册"]', timeout=timeout)

        if login_btn:
            logger.info("")
            logger.info("=" * 50)
            logger.info("[登录] 检测到未登录状态（登录按钮）")
            logger.info("=" * 50)
            login_btn.click()
            logger.info("")
            logger.info("[提示] 已跳转到登录页面，请扫码登录")
            logger.info("[提示] 登录成功后，请重新运行程序")
            logger.info("=" * 50)
            return True

        logger.info("  - 已登录状态，继续执行")
        # 已登录，跳转到开放平台
        logger.info(f"  - 正在跳转到开放平台: {config.open_platform_url}")
        self.tab.get(config.open_platform_url)
        logger.info(f"  - 跳转完成，当前页面: {self.tab.title}")
        time.sleep(2)

        # 再次检查跳转后是否进入登录页面
        if "login" in self.tab.url.lower() or "accounts" in self.tab.url.lower():
            logger.info("")
            logger.info("=" * 50)
            logger.info("[登录] 检测到未登录状态（跳转后登录页面）")
            logger.info("=" * 50)
            logger.info("")
            logger.info("[提示] 请在当前登录页面扫码登录")
            logger.info("[提示] 登录成功后，请重新运行程序")
            logger.info("=" * 50)
            return True

        # 检查应用是否已存在
        is_new_app = False
        result = self.check_and_click_existing_app()

        if result["action"] == "select":
            # 唯一匹配，直接跳转
            self.app_id = result["selected_app_id"]
            logger.info(f"  - 自动选择应用: {self.app_id}")
            self.goto_app_by_id(self.app_id)
            time.sleep(2)

        elif result["action"] == "choose":
            # 多个匹配，让用户选择
            matched_apps = result["apps"]
            need_create_new = False

            logger.info("")
            logger.info("=" * 50)
            logger.info(f"[选择应用] 发现 {len(matched_apps)} 个同名应用「{self.app_name}»")
            logger.info("=" * 50)
            logger.info("请选择操作:")
            for i, app in enumerate(matched_apps):
                logger.info(
                    f"  {i+1}. 使用此应用 (ID: {app.get('appID')}, 版本: {app.get('version', 'N/A')})"
                )
            logger.info(f"  0. 创建新应用（使用新名称）")
            logger.info("=" * 50)

            # 获取用户输入
            while True:
                try:
                    choice = input("请输入选项编号: ").strip()
                    choice_num = int(choice)

                    if choice_num == 0:
                        new_name = (
                            input(f"请输入新应用名称 (默认: {self.app_name}_new): ").strip()
                            or f"{self.app_name}_new"
                        )
                        self.app_name = new_name
                        logger.info(f"  - 将创建新应用: {self.app_name}")
                        need_create_new = True
                        break
                    elif 1 <= choice_num <= len(matched_apps):
                        selected = matched_apps[choice_num - 1]
                        self.app_id = selected.get("appID", "")
                        logger.info(f"  - 已选择应用: {self.app_id}")
                        self.goto_app_by_id(self.app_id)
                        time.sleep(2)
                        break
                    else:
                        logger.info(f"  - 无效选项，请输入 0-{len(matched_apps)}")
                except ValueError:
                    logger.info("  - 请输入数字")

            if need_create_new:
                time.sleep(2)
                if self.click_create_app():
                    time.sleep(2)
                    success, self.app_id = self.create_app_with_listen(app_name=self.app_name)
                    if success:
                        is_new_app = True
                        time.sleep(2)

        else:
            # 未找到，创建新应用
            time.sleep(2)
            if self.click_create_app():
                time.sleep(2)
                success, self.app_id = self.create_app_with_listen(app_name=self.app_name)
                if success:
                    is_new_app = True
                    time.sleep(2)

        # 获取 App Secret
        self.app_secret = ""
        if self.app_id:
            logger.info("")
            logger.info("[App Secret] 正在获取...")
            self.app_secret = self.get_app_secret()
            if not self.app_secret:
                logger.info("  - 获取失败，重试一次...")
                self.app_secret = self.get_app_secret()

        # 新创建的应用，启动长连接
        if is_new_app and self.app_id and self.app_secret:
            logger.info("")
            logger.info("[长连接] 新应用，启动长连接客户端...")
            start_event_client(app_id=self.app_id, app_secret=self.app_secret, block=False, auto_stop=True)
            time.sleep(6)

        # 跳转到 capability 页面
        self.goto_app_page(page="capability")
        time.sleep(2)

        # 添加机器人
        self.add_bot()
        time.sleep(2)

        # 通过 API 监听检查权限差异
        need_import, missing = self.check_permissions_diff_by_api()

        if not need_import:
            logger.info("[权限检查] 权限已完整，无需导入")
            time.sleep(2)
        else:
            logger.info(f"[权限导入] 缺少 {len(missing)} 个权限，开始导入...")

            if not self.click_batch_import_export():
                logger.info("  - 未找到批量导入/导出权限按钮")
                return False

            time.sleep(1)

            # 切换到导入标签
            logger.info("  - 切换到导入标签...")
            import_xpath = 'x://div[text()="导入"]'
            import_tab = self.tab.ele(import_xpath, timeout=3)
            if import_tab:
                import_tab.click()
                time.sleep(2)

            # 输入权限内容
            self.input_auth_content()
            time.sleep(2)

            # 格式化 JSON
            self.click_format_json()
            time.sleep(2)

            # 点击下一步
            self.click_next_step()
            time.sleep(2)

            # 申请开通
            self.click_apply_permission()
            time.sleep(2)

            # 确认
            self.click_confirm_drawer()
            time.sleep(2)

            # 检查是否已有版本
            if not self.check_version_exists_by_api():
                time.sleep(2)
                self.click_create_version()
                time.sleep(2)
                self.fill_version_info()
                time.sleep(2)
                self.click_confirm_publish()
                time.sleep(2)

        logger.info("[完成] 飞书应用基础配置完成！")

        # 追踪是否有更新操作
        has_updates = False

        # 通过 API 检查事件配置状态
        logger.info("")
        logger.info("[事件订阅] 检查事件配置状态...")
        time.sleep(2)
        event_status = self.check_events_configured_by_api()

        # 先判断是否需要更新订阅方式
        if event_status["need_update_mode"]:
            has_updates = True
            logger.info("[订阅方式] 需要更新为长连接模式...")

            if not is_new_app:
                logger.info("")
                logger.info("[长连接] 启动事件订阅客户端...")
                start_event_client(app_id=self.app_id, app_secret=self.app_secret, block=False, auto_stop=True)
                time.sleep(6)

            # 刷新页面
            logger.info("[页面] 刷新页面...")
            self.tab.refresh()
            time.sleep(3)

            # 重新跳转到事件订阅页面
            self.goto_app_page(page="event")
            time.sleep(2)

            time.sleep(2)
            self.click_subscribe_mode_button()
            time.sleep(1)
            self.select_long_connection_mode()
            time.sleep(1)
            self.click_save_event_config()
        else:
            logger.info("[订阅方式] 已是长连接模式，无需更新")

        # 判断是否需要添加事件
        if event_status["need_add_events"]:
            has_updates = True
            logger.info(
                f"[事件配置] 缺少 {len(event_status['missing_events'])} 个事件，开始添加..."
            )

            time.sleep(2)
            self.click_add_event()
            time.sleep(1)
            self.search_event("消息")
            time.sleep(1)
            self.select_default_events()
            time.sleep(1)
            self.click_confirm_add_event()

        # 回调配置流程
        logger.info("")
        logger.info("[回调配置] 开始配置回调...")

        time.sleep(2)
        self.start_callback_api_listen()
        time.sleep(1)
        self.click_callback_config_tab()

        callback_status = self.check_callback_configured_by_api()

        self.stop_callback_api_listen()

        if callback_status["need_update_mode"]:
            has_updates = True
            logger.info("[回调配置] 需要更新订阅方式为长连接...")

            time.sleep(2)
            self.click_callback_subscribe_mode_button()
            time.sleep(1)
            self.select_callback_long_connection_mode()
            time.sleep(1)
            self.click_callback_save_button()
        else:
            logger.info("[回调配置] 已是长连接模式，无需更新订阅方式")

        if callback_status["need_add_callback"]:
            has_updates = True
            logger.info("[回调配置] 需要添加回调...")

            time.sleep(2)
            self.click_add_callback_button()
            time.sleep(1)
            self.select_card_action_trigger_checkbox()
            time.sleep(1)
            self.click_confirm_add_callback_button()
        else:
            logger.info("[回调配置] 回调已配置，无需添加")

        # 版本发布
        logger.info("")
        if has_updates:
            logger.info("[版本管理] 检测到更新操作，开始创建新版本...")

            version_count = self.get_version_count_by_api()
            logger.info(f"[版本管理] 当前版本数: {version_count}")

            if version_count < 2:
                time.sleep(2)
                self.create_new_version(description="添加权限及更新配置")
            else:
                logger.info("[版本管理] 已存在2个版本，不发布新版本")
        else:
            logger.info("[版本管理] 无更新操作，不发布新版本")

        logger.info("[完成] 飞书应用配置完成！")
        return False

    # ==================== 事件订阅相关方法 ====================

    def goto_event_page(self, app_id: str | None = None, app_name: str | None = None) -> bool:
        """跳转到事件订阅页面"""
        app_name = app_name or self.app_name
        app_id = app_id or self.get_app_id(app_name)

        if not app_id:
            logger.warning("[事件订阅] 未找到应用 ID，无法跳转")
            return False

        url = f"https://open.feishu.cn/app/{app_id}/event"
        logger.info(f"[事件订阅] 正在跳转到: {url}")
        self.tab.get(url)
        logger.info(f"  - 跳转完成，当前页面: {self.tab.title}")
        return True

    def check_events_configured_by_api(self, timeout: float = 10) -> dict:
        """通过 API 监听检查事件配置状态"""
        app_id = self.get_app_id()

        result: dict = {
            "need_add_events": True,
            "missing_events": [],
            "need_update_mode": True,
            "event_mode": 1,
        }

        if not app_id:
            logger.warning("[事件检查] 未找到应用 ID")
            result["missing_events"] = [
                "im.message.receive_v1",
                "im.message.message_read_v1",
                "im.message.reaction.deleted_v1",
            ]
            return result

        required_events = [
            "im.message.receive_v1",
            "im.message.message_read_v1",
            "im.message.reaction.deleted_v1",
        ]

        api_pattern = f"developers/v1/event/{app_id}"

        logger.info(f"[事件检查] 正在监听 API: {api_pattern}")
        logger.info(f"  - 需要检查的事件: {required_events}")

        self.tab.listen.start(api_pattern)
        self.goto_event_page()

        logger.info(f"  - 等待 API 响应 (超时: {timeout}s)...")

        try:
            for packet in self.tab.listen.steps(timeout=timeout):
                try:
                    response = packet.response
                    if not response:
                        continue

                    body = response.body
                    if not body:
                        continue

                    if isinstance(body, str):
                        data = json.loads(body)
                    else:
                        data = body

                    logger.info(f"  - 收到 API 响应")

                    configured_events: set[str] = set()
                    event_mode = 1

                    if isinstance(data, dict):
                        event_mode = data.get("data", {}).get("eventMode", 1)
                        result["event_mode"] = event_mode
                        logger.info(
                            f"  - eventMode: {event_mode} ({'长连接' if event_mode == 4 else '未配置' if event_mode == 1 else '其他模式'})"
                        )

                        events_list = data.get("data", {}).get("events", [])
                        if events_list and isinstance(events_list, list):
                            for event in events_list:
                                if isinstance(event, str):
                                    configured_events.add(event)

                    logger.info(f"  - 已配置的事件: {configured_events}")

                    missing_events = [e for e in required_events if e not in configured_events]
                    result["missing_events"] = missing_events
                    result["need_add_events"] = len(missing_events) > 0
                    result["need_update_mode"] = event_mode != 4

                    logger.info(f"  - 需要添加事件: {result['need_add_events']}")
                    logger.info(f"  - 需要更新订阅方式: {result['need_update_mode']}")

                    return result

                except Exception as e:
                    logger.info(f"  - 解析响应失败: {e}")
                    continue

        except Exception as e:
            logger.info(f"  - 监听超时或失败: {e}")

        finally:
            self.tab.listen.stop()

        logger.info("  - 未收到 API 响应，默认需要添加事件")
        result["missing_events"] = required_events
        return result

    def click_subscribe_mode_button(self, timeout: float = 5) -> bool:
        """点击订阅方式按钮"""
        logger.info(f"[订阅方式] 正在查找订阅方式按钮 (超时: {timeout}s)...")
        xpath = 'x://span[contains(text(),"订阅方式")]/following-sibling::button'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击订阅方式按钮")
            return True

        logger.info("  - 未找到按钮")
        return False

    def select_long_connection_mode(self, timeout: float = 5) -> bool:
        """选中长连接模式 radio 选项"""
        logger.info(f"[长连接模式] 正在查找长连接选项 (超时: {timeout}s)...")
        xpath = 'x://b[text()="长连接"]/ancestor::label//input'
        radio = self.tab.ele(xpath, timeout=timeout)

        if radio:
            logger.info("  - 发现长连接选项，正在选中...")
            radio.click()
            logger.info("  - 已选中长连接模式")
            return True

        logger.info("  - 未找到长连接选项")
        return False

    def click_save_event_config(self, timeout: float = 5) -> bool:
        """点击保存事件配置按钮"""
        logger.info(f"[保存配置] 正在查找保存按钮 (超时: {timeout}s)...")
        xpath = 'x://div[@class="ud__space__item"]/button[text()="保存"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现保存按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击保存按钮")
            return True

        logger.info("  - 未找到保存按钮")
        return False

    def click_add_event(self, timeout: float = 5) -> bool:
        """点击添加事件按钮"""
        logger.info(f"[添加事件] 正在查找添加事件按钮 (超时: {timeout}s)...")
        xpath = 'x://button[text()="添加事件"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现添加事件按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击添加事件按钮")
            return True

        logger.info("  - 未找到添加事件按钮")
        return False

    def search_event(self, event_name: str, timeout: float = 5) -> bool:
        """在搜索框中搜索事件"""
        logger.info(f"[搜索事件] 正在搜索: {event_name}...")
        xpath = 'x://input[@placeholder="搜索"]'
        search_input = self.tab.ele(xpath, timeout=timeout)

        if not search_input:
            logger.info("  - 未找到搜索框")
            return False

        search_input.clear()
        search_input.input(event_name)
        logger.info(f"  - 已输入: {event_name}")
        return True

    def select_event_checkbox(self, event_name: str, timeout: float = 3) -> bool:
        """选中指定事件的 checkbox"""
        logger.info(f"[选中事件] 正在选中: {event_name}...")
        xpath = f'x://span[text()="{event_name}"]/ancestor::div[@class="ud__space__item"]//input'
        checkbox = self.tab.ele(xpath, timeout=timeout)

        if checkbox:
            logger.info("  - 发现 checkbox，正在点击...")
            checkbox.click()
            logger.info(f"  - 已选中: {event_name}")
            return True
        logger.info(f"  - 未找到: {event_name}")
        return False

    def select_default_events(self) -> bool:
        """选中默认的三个事件"""
        events = [
            "im.message.receive_v1",
            "im.message.message_read_v1",
            "im.message.reaction.deleted_v1",
        ]

        logger.info("[选中事件] 正在选中默认事件...")
        success_count = 0

        for event_name in events:
            time.sleep(0.5)
            if self.select_event_checkbox(event_name):
                success_count += 1

        logger.info(f"[选中事件] 已选中 {success_count}/{len(events)} 个事件")
        return success_count == len(events)

    def click_confirm_add_event(self, timeout: float = 5) -> bool:
        """点击添加事件弹框中的"添加"按钮"""
        logger.info(f"[确认添加] 正在查找添加按钮 (超时: {timeout}s)...")
        xpath = 'x://button[text()="添加"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现添加按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击添加按钮")
            return True

        logger.info("  - 未找到添加按钮")
        return False

    # ==================== 回调配置相关方法 ====================

    def click_callback_config_tab(self, timeout: float = 5) -> bool:
        """点击"回调配置" tab"""
        logger.info(f"[回调配置] 正在查找回调配置 tab (超时: {timeout}s)...")
        xpath = 'x://div[text()="回调配置"][contains(@class,"ud__tabs")]'
        tab_element = self.tab.ele(xpath, timeout=timeout)

        if tab_element:
            logger.info("  - 发现回调配置 tab，正在点击...")
            tab_element.click()
            logger.info("  - 已点击回调配置 tab")
            return True

        logger.info("  - 未找到回调配置 tab")
        return False

    def check_callback_configured_by_api(self, timeout: float = 10) -> dict:
        """通过 API 监听检查回调配置状态"""
        app_id = self.get_app_id()

        result: dict = {
            "need_update_mode": True,
            "need_add_callback": True,
            "callback_mode": 1,
            "callbacks": [],
        }

        if not app_id:
            logger.warning("[回调检查] 未找到应用 ID")
            return result

        required_callbacks = ["card.action.trigger"]

        logger.info(f"[回调检查] 等待 API 响应 (超时: {timeout}s)...")
        logger.info(f"  - 需要检查的回调: {required_callbacks}")

        try:
            for packet in self.tab.listen.steps(timeout=timeout):
                try:
                    response = packet.response
                    if not response:
                        continue

                    body = response.body
                    if not body:
                        continue

                    if isinstance(body, str):
                        data = json.loads(body)
                    else:
                        data = body

                    logger.info(f"  - 收到 API 响应")

                    callback_mode = 1
                    callbacks: list[str] = []

                    if isinstance(data, dict):
                        callback_mode = data.get("data", {}).get("callbackMode", 1)
                        result["callback_mode"] = callback_mode
                        logger.info(
                            f"  - callbackMode: {callback_mode} ({'长连接' if callback_mode == 4 else '未配置' if callback_mode == 1 else '其他模式'})"
                        )

                        callbacks = data.get("data", {}).get("callbacks", [])
                        result["callbacks"] = callbacks
                        logger.info(f"  - 已配置的回调: {callbacks}")

                    result["need_update_mode"] = callback_mode != 4
                    missing_callbacks = [c for c in required_callbacks if c not in callbacks]
                    result["need_add_callback"] = len(missing_callbacks) > 0

                    logger.info(f"  - 需要更新订阅方式: {result['need_update_mode']}")
                    logger.info(f"  - 需要添加回调: {result['need_add_callback']}")

                    return result

                except Exception as e:
                    logger.info(f"  - 解析响应失败: {e}")
                    continue

        except Exception as e:
            logger.info(f"  - 监听超时或失败: {e}")

        logger.info("  - 未收到 API 响应，默认需要配置")
        return result

    def start_callback_api_listen(self) -> None:
        """启动回调 API 监听"""
        app_id = self.get_app_id()
        if not app_id:
            logger.warning("[回调监听] 未找到应用 ID")
            return

        api_pattern = f"developers/v1/callback/{app_id}"
        logger.info(f"[回调监听] 启动监听: {api_pattern}")
        self.tab.listen.start(api_pattern)

    def stop_callback_api_listen(self) -> None:
        """停止回调 API 监听"""
        logger.info("[回调监听] 停止监听")
        self.tab.listen.stop()

    def click_add_callback_button(self, timeout: float = 10) -> bool:
        """点击"添加回调"按钮"""
        logger.info(f"[回调配置] 正在查找添加回调按钮 (超时: {timeout}s)...")
        xpath = 'x://button[text()="添加回调"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现添加回调按钮，正在点击...")
            btn.click(by_js=True)
            logger.info("  - 已点击添加回调按钮")
            return True

        logger.info("  - 未找到添加回调按钮（可能已配置）")
        return False

    def select_card_action_trigger_checkbox(self, timeout: float = 3) -> bool:
        """选中 card.action.trigger 事件的 checkbox"""
        logger.info(f"[回调配置] 正在选中 card.action.trigger...")
        xpath = 'x://span[text()="card.action.trigger"]/ancestor::div[@class="ud__space__item"]//input'
        checkbox = self.tab.ele(xpath, timeout=timeout)

        if checkbox:
            logger.info("  - 发现 checkbox，正在点击...")
            checkbox.click()
            logger.info("  - 已选中 card.action.trigger")
            return True

        logger.info("  - 未找到 card.action.trigger checkbox")
        return False

    def click_confirm_add_callback_button(self, timeout: float = 5) -> bool:
        """点击回调弹框中的"添加"按钮"""
        logger.info(f"[回调配置] 正在查找确认添加按钮 (超时: {timeout}s)...")
        xpath = 'x://div[@class="ud__modal__footer__btns"]/button[text()="添加"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现添加按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击添加按钮")
            return True

        logger.info("  - 未找到添加按钮")
        return False

    def click_callback_subscribe_mode_button(self, timeout: float = 5) -> bool:
        """点击回调配置中的订阅方式按钮"""
        logger.info(f"[回调配置-订阅方式] 正在查找订阅方式按钮 (超时: {timeout}s)...")
        xpath = 'x://span[contains(text(),"订阅方式")]/following-sibling::button'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现订阅方式按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击订阅方式按钮")
            return True

        logger.info("  - 未找到订阅方式按钮")
        return False

    def select_callback_long_connection_mode(self, timeout: float = 5) -> bool:
        """选中回调配置中的长连接模式 radio 选项"""
        logger.info(f"[回调配置-长连接模式] 正在查找长连接选项 (超时: {timeout}s)...")
        xpath = 'x://b[text()="长连接"]/ancestor::label//input'
        radio = self.tab.ele(xpath, timeout=timeout)

        if radio:
            logger.info("  - 发现长连接选项，正在选中...")
            radio.click()
            logger.info("  - 已选中长连接模式")
            return True

        logger.info("  - 未找到长连接选项")
        return False

    def click_callback_save_button(self, timeout: float = 5) -> bool:
        """点击回调配置中的保存按钮"""
        logger.info(f"[回调配置-保存] 正在查找保存按钮 (超时: {timeout}s)...")
        xpath = 'x://button[text()="保存"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现保存按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击保存按钮")
            return True

        logger.info("  - 未找到保存按钮")
        return False


def get_feishu_browser(app_name: str = "openclaw") -> FeishuBrowser:
    """获取飞书浏览器实例"""
    return FeishuBrowser(app_name=app_name)
