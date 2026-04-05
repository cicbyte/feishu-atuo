"""
飞书频道 - 版本管理
"""
from __future__ import annotations

import json
import logging
import time
from typing import TYPE_CHECKING, Any

from feishu_auto.config import get_config

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class VersionMixin:
    """版本管理混入类"""

    tab: Any
    app_name: str
    app_id: str

    def get_app_id(self, app_name: str | None = None) -> str:
        """获取应用 ID"""
        ...

    def goto_app_page(self, app_id: str | None = None, app_name: str | None = None, page: str = "capability") -> bool:
        """跳转到应用页面"""
        ...

    def check_version_exists_by_api(
        self, app_id: str | None = None, app_name: str | None = None, timeout: float = 10
    ) -> bool:
        """
        通过 API 监听检查是否已存在版本

        Returns:
            True 表示已存在版本，False 表示无版本
        """
        app_id = app_id or self.get_app_id(app_name or self.app_name)

        if not app_id:
            logger.warning("[版本检查] 未找到应用 ID")
            return False

        api_url_pattern = f"app_version/list/{app_id}"
        logger.info(f"[版本检查-API方式] 正在监听接口: .../{api_url_pattern}")

        # 开启网络监听
        self.tab.listen.start(api_url_pattern)

        try:
            # 跳转到版本页面，触发 API 请求
            self.goto_app_page(page="version")

            logger.info(f"  - 等待 API 响应 (超时: {timeout}s)...")

            # 等待捕获请求
            packet = None
            for p in self.tab.listen.steps(timeout=timeout):
                packet = p
                break

            if not packet:
                logger.info("  - 未捕获到 API 响应")
                return False

            # 获取响应内容
            response = packet.response
            if not response:
                logger.info("  - 响应为空")
                return False

            try:
                response_body = response.body
                if response_body is None:
                    logger.info("  - 响应体为空")
                    return False

                # 如果是 bytes 或 str，需要解析 JSON
                if isinstance(response_body, bytes):
                    response_body = json.loads(response_body.decode("utf-8"))
                elif isinstance(response_body, str):
                    response_body = json.loads(response_body)

                data = response_body

                # 打印响应摘要
                response_text = str(data)
                logger.info(
                    f"  - API 响应: {response_text[:200]}..."
                    if len(response_text) > 200
                    else f"  - API 响应: {response_text}"
                )

                # 检查 code
                if data.get("code", -1) != 0:
                    logger.info(
                        f"  - API 返回错误码: {data.get('code')}, msg: {data.get('msg')}"
                    )
                    return False

                # 检查 versions 数组
                versions = data.get("data", {}).get("versions", [])
                if versions:
                    logger.info(f"  - 已存在 {len(versions)} 个版本")
                    for v in versions:
                        logger.info(f"    - 版本: {v.get('appVersion', 'unknown')}")
                    return True
                else:
                    logger.info("  - versions 数组为空，需要创建版本")
                    return False

            except (json.JSONDecodeError, Exception) as e:
                logger.info(f"  - 响应解析失败: {e}")
                return False

        except Exception as e:
            logger.info(f"  - API 监听异常: {e}")
            return False

        finally:
            # 停止监听
            self.tab.listen.stop()

    def click_create_version(self, timeout: float = 5) -> bool:
        """点击创建版本按钮"""
        logger.info(f"[创建版本] 正在查找「创建版本」按钮 (超时: {timeout}s)...")
        xpath = 'x://button[text()="创建版本"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击创建版本")
            return True

        logger.info("  - 未找到按钮")
        return False

    def fill_version_info(
        self,
        version: str | None = None,
        description: str | None = None,
        timeout: float = 5,
    ) -> bool:
        """填写版本信息并保存"""
        config = get_config()
        version = version or config.default_version
        description = description or config.default_version_desc

        logger.info(f"[版本信息] 正在填写版本信息...")
        logger.info(f"  - 版本号: {version}")
        logger.info(f"  - 更新说明: {description}")

        # 填写版本号
        version_xpath = 'x://div[text()="应用版本号"]/ancestor::div[contains(@class,"ud__row")]//input'
        version_input = self.tab.ele(version_xpath, timeout=timeout)
        if not version_input:
            logger.info("  - 未找到版本号输入框")
            return False
        version_input.clear()
        version_input.input(version)
        logger.info("  - 版本号已填写")

        # 填写更新说明
        desc_xpath = 'x://div[text()="更新说明"]/ancestor::div[contains(@class,"ud__row")]//textarea'
        desc_input = self.tab.ele(desc_xpath, timeout=timeout)
        if not desc_input:
            logger.info("  - 未找到更新说明输入框")
            return False
        desc_input.clear()
        desc_input.input(description)
        logger.info("  - 更新说明已填写")

        # 点击保存按钮
        save_btn = self.tab.ele('x://button[text()="保存"]', timeout=timeout)
        if not save_btn:
            logger.info("  - 未找到保存按钮")
            return False
        save_btn.click()
        logger.info("  - 已点击保存")

        return True

    def click_confirm_publish(self, timeout: float = 5) -> bool:
        """点击确认发布按钮"""
        logger.info(f"[确认发布] 正在查找「确认发布」按钮 (超时: {timeout}s)...")
        xpath = 'x://div[@class="ud__confirm__footer__extraAction"]//button[text()="确认发布"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击确认发布")
            return True

        logger.info("  - 未找到按钮")
        return False

    def get_latest_version_by_api(
        self, app_id: str | None = None, app_name: str | None = None, timeout: float = 10
    ) -> str:
        """
        通过 API 获取最新版本号

        Returns:
            最新版本号字符串，如 "1.0.0"，无版本时返回空字符串
        """
        app_id = app_id or self.get_app_id(app_name or self.app_name)

        if not app_id:
            logger.warning("[获取版本] 未找到应用 ID")
            return ""

        api_url_pattern = f"app_version/list/{app_id}"
        logger.info(f"[获取版本] 正在监听接口: .../{api_url_pattern}")

        # 开启网络监听
        self.tab.listen.start(api_url_pattern)

        try:
            # 跳转到版本页面，触发 API 请求
            self.goto_app_page(page="version")

            logger.info(f"  - 等待 API 响应 (超时: {timeout}s)...")

            for packet in self.tab.listen.steps(timeout=timeout):
                if not packet or not packet.response:
                    continue

                try:
                    response_body = packet.response.body
                    if response_body is None:
                        continue

                    if isinstance(response_body, bytes):
                        response_body = json.loads(response_body.decode("utf-8"))
                    elif isinstance(response_body, str):
                        response_body = json.loads(response_body)

                    if response_body.get("code", -1) != 0:
                        continue

                    versions = response_body.get("data", {}).get("versions", [])
                    if versions:
                        latest_version = versions[0].get("appVersion", "")
                        logger.info(f"  - 最新版本: {latest_version}")
                        return latest_version
                    else:
                        logger.info("  - 暂无版本")
                        return ""

                except Exception as e:
                    logger.info(f"  - 解析失败: {e}")
                    continue

        except Exception as e:
            logger.info(f"  - API 监听异常: {e}")

        finally:
            self.tab.listen.stop()

        return ""

    def get_version_count_by_api(
        self, app_id: str | None = None, app_name: str | None = None, timeout: float = 10
    ) -> int:
        """
        通过 API 获取版本数量

        Returns:
            版本数量，无版本时返回 0
        """
        app_id = app_id or self.get_app_id(app_name or self.app_name)

        if not app_id:
            logger.warning("[获取版本数] 未找到应用 ID")
            return 0

        api_url_pattern = f"app_version/list/{app_id}"
        logger.info(f"[获取版本数] 正在监听接口: .../{api_url_pattern}")

        # 开启网络监听
        self.tab.listen.start(api_url_pattern)

        try:
            self.goto_app_page(page="version")

            logger.info(f"  - 等待 API 响应 (超时: {timeout}s)...")

            for packet in self.tab.listen.steps(timeout=timeout):
                if not packet or not packet.response:
                    continue

                try:
                    response_body = packet.response.body
                    if response_body is None:
                        continue

                    if isinstance(response_body, bytes):
                        response_body = json.loads(response_body.decode("utf-8"))
                    elif isinstance(response_body, str):
                        response_body = json.loads(response_body)

                    if response_body.get("code", -1) != 0:
                        continue

                    versions = response_body.get("data", {}).get("versions", [])
                    count = len(versions)
                    logger.info(f"  - 版本数量: {count}")
                    return count

                except Exception as e:
                    logger.info(f"  - 解析失败: {e}")
                    continue

        except Exception as e:
            logger.info(f"  - API 监听异常: {e}")

        finally:
            self.tab.listen.stop()

        return 0

    def calculate_next_version(self, current_version: str) -> str:
        """
        计算下一个版本号
        规则：取最后一位加1，9 → 10
        """
        if not current_version:
            return "1.0.0"

        parts = current_version.split(".")
        if not parts:
            return "1.0.0"

        try:
            last_part = int(parts[-1])
            last_part += 1
            parts[-1] = str(last_part)

            new_version = ".".join(parts)
            logger.info(f"[版本计算] {current_version} → {new_version}")
            return new_version

        except ValueError:
            return "1.0.0"

    def create_new_version(
        self, description: str = "添加权限及更新配置", app_name: str | None = None
    ) -> bool:
        """
        创建新版本（自动计算版本号）

        Returns:
            是否创建成功
        """
        logger.info("[创建新版本] 开始创建...")

        # 获取最新版本号
        latest_version = self.get_latest_version_by_api(app_name=app_name or self.app_name)

        # 计算新版本号
        new_version = self.calculate_next_version(latest_version)

        # 点击创建版本按钮
        time.sleep(2)
        if not self.click_create_version():
            logger.info("  - 未找到创建版本按钮")
            return False

        # 填写版本信息
        time.sleep(2)
        if not self.fill_version_info(version=new_version, description=description):
            logger.info("  - 填写版本信息失败")
            return False

        # 确认发布
        time.sleep(2)
        if not self.click_confirm_publish():
            logger.info("  - 确认发布失败")
            return False

        logger.info(f"[创建新版本] 版本 {new_version} 创建成功")
        return True
