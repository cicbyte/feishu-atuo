"""
飞书频道 - 应用管理
"""
from __future__ import annotations

import json
import logging
import re
import time
from typing import TYPE_CHECKING, Any

from feishu_auto.config import get_config

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class AppMixin:
    """应用管理混入类"""

    tab: Any
    app_name: str
    app_id: str
    app_secret: str

    def _extract_app_id(self, url: str | None = None) -> str:
        """从当前 URL 或指定 URL 中提取应用 ID"""
        current_url = url or self.tab.url
        pattern = get_config().app_id_pattern
        match = re.search(pattern, current_url)
        if match:
            return match.group()
        return ""

    def get_app_id(self, app_name: str | None = None) -> str:
        """获取应用 ID（优先使用实例变量，再从 URL 提取）"""
        # 优先使用实例变量
        if hasattr(self, "app_id") and self.app_id:
            return self.app_id

        # 从当前 URL 提取
        app_id = self._extract_app_id()
        if app_id:
            return app_id

        return ""

    def goto_app_page(
        self, app_id: str | None = None, app_name: str | None = None, page: str = "capability"
    ) -> bool:
        """跳转到应用页面"""
        app_name = app_name or self.app_name
        app_id = app_id or self.get_app_id(app_name)

        if not app_id:
            logger.warning("[跳转] 未找到应用 ID，无法跳转")
            return False

        url = f"https://open.feishu.cn/app/{app_id}/{page}"
        logger.info(f"[跳转] 正在跳转到: {url}")
        self.tab.get(url)
        logger.info(f"  - 跳转完成，当前页面: {self.tab.title}")
        return True

    def click_create_app(self, timeout: float = 5) -> bool:
        """点击创建企业自建应用按钮"""
        logger.info(f"[创建应用] 正在查找「创建企业自建应用」按钮 (超时: {timeout}s)...")
        create_btn = self.tab.ele('x://button[text()="创建企业自建应用"]', timeout=timeout)
        if create_btn:
            logger.info("  - 发现按钮，正在点击...")
            create_btn.click()
            time.sleep(2)
            logger.info("  - 已点击创建企业自建应用")
            return True

        logger.info("  - 未找到创建按钮")
        return False

    def get_app_list_by_api(self, timeout: float = 10) -> list[dict]:
        """
        通过 API 监听获取应用列表

        Returns:
            应用列表，每个元素包含 appID, name, desc 等信息
        """
        api_url_pattern = "app/list"
        logger.info(f"[应用列表] 正在监听接口: .../{api_url_pattern}")

        # 开启网络监听
        self.tab.listen.start(api_url_pattern)

        try:
            # 刷新页面触发 API 请求
            logger.info("  - 刷新页面触发 API 请求...")
            self.tab.refresh()

            logger.info(f"  - 等待 API 响应 (超时: {timeout}s)...")

            # 等待捕获请求
            apps: list[dict] = []
            for p in self.tab.listen.steps(timeout=timeout):
                logger.info(f"  - 捕获请求: {p.url}")

                res = p.response
                if not res:
                    logger.info("    - 无响应，跳过")
                    continue

                try:
                    body = res.body
                    if body is None:
                        logger.info("    - 响应体为空，跳过")
                        continue

                    # 解析 JSON
                    if isinstance(body, bytes):
                        body = json.loads(body.decode("utf-8"))
                    elif isinstance(body, str):
                        body = json.loads(body)

                    # 打印响应摘要
                    code = body.get("code", -1)
                    found_apps = body.get("data", {}).get("apps", None)
                    logger.info(
                        f"    - code: {code}, apps: {len(found_apps) if found_apps else 'None'}"
                    )

                    # 如果找到 apps 且 code 为 0，使用这个响应
                    if code == 0 and found_apps:
                        apps = found_apps
                        logger.info("    - 找到有效响应!")
                        break

                except Exception as e:
                    logger.info(f"    - 解析失败: {e}")
                    continue

            logger.info(f"  - 获取到 {len(apps)} 个应用")
            return apps

        except Exception as e:
            logger.info(f"  - API 监听异常: {e}")
            return []

        finally:
            # 停止监听
            self.tab.listen.stop()

    def find_apps_by_name(self, app_name: str, apps: list[dict]) -> list[dict]:
        """从应用列表中查找匹配名称的应用"""
        matched = []
        for app in apps:
            if app.get("name") == app_name:
                matched.append(app)
        return matched

    def check_and_click_existing_app(
        self, app_name: str | None = None, timeout: float = 10
    ) -> dict:
        """
        检查应用是否已存在（通过 API 监听方式）

        Returns:
            {
                'found': bool,
                'apps': list,
                'action': str,  # 'select', 'choose', 'create'
                'selected_app_id': str,
            }
        """
        app_name = app_name or self.app_name

        logger.info(f"[检查应用] 正在查找应用「{app_name}」...")

        # 通过 API 获取应用列表
        apps = self.get_app_list_by_api(timeout=timeout)

        if not apps:
            logger.info(f"  - 应用列表为空，将创建新应用")
            return {
                "found": False,
                "apps": [],
                "action": "create",
                "selected_app_id": "",
            }

        # 查找匹配名称的应用
        matched_apps = self.find_apps_by_name(app_name, apps)

        if len(matched_apps) == 0:
            logger.info(f"  - 未找到应用「{app_name}」，将创建新应用")
            return {
                "found": False,
                "apps": [],
                "action": "create",
                "selected_app_id": "",
            }

        elif len(matched_apps) == 1:
            app = matched_apps[0]
            app_id = app.get("appID", "")
            logger.info(f"  - 找到唯一匹配的应用: {app_name} (ID: {app_id})")
            return {
                "found": True,
                "apps": matched_apps,
                "action": "select",
                "selected_app_id": app_id,
            }

        else:
            logger.info(f"  - 找到 {len(matched_apps)} 个同名应用「{app_name}»:")
            for i, app in enumerate(matched_apps):
                logger.info(
                    f"    [{i+1}] ID: {app.get('appID')}, 版本: {app.get('version', 'N/A')}"
                )
            return {
                "found": True,
                "apps": matched_apps,
                "action": "choose",
                "selected_app_id": "",
            }

    def create_app_with_listen(
        self, app_name: str | None = None, app_desc: str | None = None, timeout: float = 15
    ) -> tuple[bool, str]:
        """
        创建应用并监听 app/create 接口获取 app_id

        Returns:
            (success, app_id)
        """
        app_name = app_name or self.app_name
        app_desc = app_desc or app_name

        api_url_pattern = "app/create"
        logger.info(f"[创建应用] 正在创建应用「{app_name}»...")
        logger.info(f"  - 监听接口: .../{api_url_pattern}")

        # 开启网络监听
        self.tab.listen.start(api_url_pattern)

        try:
            logger.info(f"  - 填写应用信息...")
            logger.info(f"    - 应用名称: {app_name}")
            logger.info(f"    - 应用描述: {app_desc}")

            # 填写应用名称
            name_input = self.tab.ele("x://form/div[1]//input", timeout=5)
            if not name_input:
                logger.info("  - 未找到应用名称输入框")
                return False, ""
            name_input.clear()
            name_input.input(app_name)

            # 填写应用描述
            desc_input = self.tab.ele("x://form/div[2]//textarea", timeout=5)
            if not desc_input:
                logger.info("  - 未找到应用描述输入框")
                return False, ""
            desc_input.clear()
            desc_input.input(app_desc)

            logger.info("  - 点击创建按钮...")

            # 点击创建按钮
            create_btn = self.tab.ele('x://button[text()="创建"]', timeout=5)
            if not create_btn:
                logger.info("  - 未找到创建按钮")
                return False, ""
            create_btn.click()

            # 等待 API 响应
            logger.info(f"  - 等待创建接口响应 (超时: {timeout}s)...")

            packet = None
            for p in self.tab.listen.steps(timeout=timeout):
                packet = p
                break

            if not packet:
                logger.info("  - 未捕获到创建接口响应")
                return False, ""

            # 获取响应内容
            response = packet.response
            if not response:
                logger.info("  - 响应为空")
                return False, ""

            try:
                response_body = response.body
                if response_body is None:
                    logger.info("  - 响应体为空")
                    return False, ""

                # 解析 JSON
                if isinstance(response_body, bytes):
                    response_body = json.loads(response_body.decode("utf-8"))
                elif isinstance(response_body, str):
                    response_body = json.loads(response_body)

                data = response_body

                # 检查 code
                if data.get("code", -1) != 0:
                    logger.info(
                        f"  - 创建失败，错误码: {data.get('code')}, msg: {data.get('msg')}"
                    )
                    return False, ""

                # 获取 ClientID
                app_id = data.get("data", {}).get("ClientID", "")
                if app_id:
                    logger.info(f"  - 创建成功，应用 ID: {app_id}")
                    return True, app_id
                else:
                    logger.info("  - 响应中未找到 ClientID")
                    return False, ""

            except (json.JSONDecodeError, Exception) as e:
                logger.info(f"  - 响应解析失败: {e}")
                return False, ""

        except Exception as e:
            logger.info(f"  - 创建应用异常: {e}")
            return False, ""

        finally:
            # 停止监听
            self.tab.listen.stop()

    def goto_app_by_id(self, app_id: str, page: str = "capability") -> bool:
        """根据 app_id 直接跳转到应用页面"""
        if not app_id:
            logger.warning("[跳转] 应用 ID 为空")
            return False

        url = f"https://open.feishu.cn/app/{app_id}/{page}"
        logger.info(f"[跳转] 正在跳转到: {url}")
        self.tab.get(url)
        logger.info(f"  - 跳转完成，当前页面: {self.tab.title}")
        return True

    def add_bot(self, timeout: float = 5) -> bool:
        """点击添加机器人按钮"""
        logger.info(f"[机器人] 正在查找机器人按钮 (超时: {timeout}s)...")

        # 先查找添加按钮
        add_xpath = 'x://div[text()="机器人"]/ancestor::div[contains(@class,"ud__card")]//button[text()="添加"]'
        add_btn = self.tab.ele(add_xpath, timeout=timeout)

        if add_btn:
            logger.info("  - 发现添加按钮，正在点击...")
            add_btn.click()
            logger.info("  - 已点击添加机器人")
            return True

        logger.info("  - 未找到添加按钮，检查是否已配置...")
        config_xpath = 'x://div[text()="机器人"]/ancestor::div[contains(@class,"ud__card")]//button[text()="配置"]'
        config_btn = self.tab.ele(config_xpath, timeout=2)

        if config_btn:
            logger.info("  - 发现配置按钮，机器人已配置，跳过")
            return True

        logger.info("  - 未找到添加/配置按钮")
        return False

    def get_app_secret(self, timeout: float = 5, save_to_config: bool = True) -> str:
        """获取 App Secret"""
        try:
            import pyperclip

            HAS_PYPERCLIP = True
        except ImportError:
            HAS_PYPERCLIP = False

        # 跳转到 baseinfo 页面
        self.goto_app_page(page="baseinfo")

        logger.info(f"[App Secret] 正在获取...")
        xpath = 'x://span[text()="App Secret"]/ancestor::div[contains(@class,"ud__row")]//span[contains(@class,"secret-code__btn")][1]'
        copy_btn = self.tab.ele(xpath, timeout=timeout)

        if not copy_btn:
            logger.info("  - 未找到复制按钮")
            return ""

        logger.info("  - 发现复制按钮，正在点击...")
        copy_btn.click()
        time.sleep(0.5)

        # 从剪贴板获取 App Secret
        if HAS_PYPERCLIP:
            app_secret = pyperclip.paste()
            logger.info(
                f"  - 已获取 App Secret: {app_secret[:8]}..."
                if len(app_secret) > 8
                else f"  - 已获取 App Secret: {app_secret}"
            )

            # 保存到实例变量
            if app_secret:
                self.app_secret = app_secret

            return app_secret
        else:
            logger.warning("  - 警告: 未安装 pyperclip，无法获取剪贴板内容")
            return ""
