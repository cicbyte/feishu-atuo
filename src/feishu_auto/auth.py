"""
飞书频道 - 权限管理
"""
from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any

from feishu_auto.config import get_config, get_abs_path

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# 默认权限配置（首次运行时写入 ~/.feishu-auto/auth.json）
DEFAULT_AUTH_CONFIG = """{
  "scopes": {
    "tenant": [
      "contact:contact.base:readonly",
      "docx:document:readonly",
      "im:chat:read",
      "im:chat:update",
      "im:message.group_at_msg:readonly",
      "im:message.p2p_msg:readonly",
      "im:message.pins:read",
      "im:message.pins:write_only",
      "im:message.reactions:read",
      "im:message.reactions:write_only",
      "im:message:readonly",
      "im:message:recall",
      "im:message:send_as_bot",
      "im:message:send_multi_users",
      "im:message:send_sys_msg",
      "im:message:update",
      "im:resource",
      "application:application:self_manage",
      "cardkit:card:write",
      "cardkit:card:read"
    ],
    "user": [
      "contact:user.employee_id:readonly",
      "offline_access",
      "base:app:copy",
      "base:field:create",
      "base:field:delete",
      "base:field:read",
      "base:field:update",
      "base:record:create",
      "base:record:delete",
      "base:record:retrieve",
      "base:record:update",
      "base:table:create",
      "base:table:delete",
      "base:table:read",
      "base:table:update",
      "base:view:read",
      "base:view:write_only",
      "base:app:create",
      "base:app:update",
      "base:app:read",
      "board:whiteboard:node:create",
      "board:whiteboard:node:read",
      "calendar:calendar:read",
      "calendar:calendar.event:create",
      "calendar:calendar.event:delete",
      "calendar:calendar.event:read",
      "calendar:calendar.event:reply",
      "calendar:calendar.event:update",
      "calendar:calendar.free_busy:read",
      "contact:contact.base:readonly",
      "contact:user.base:readonly",
      "contact:user:search",
      "docs:document.comment:create",
      "docs:document.comment:read",
      "docs:document.comment:update",
      "docs:document.media:download",
      "docs:document:copy",
      "docx:document:create",
      "docx:document:readonly",
      "docx:document:write_only",
      "drive:drive.metadata:readonly",
      "drive:file:download",
      "drive:file:upload",
      "im:chat.members:read",
      "im:chat:read",
      "im:message",
      "im:message.group_msg:get_as_user",
      "im:message.p2p_msg:get_as_user",
      "im:message:readonly",
      "search:docs:read",
      "search:message",
      "space:document:delete",
      "space:document:move",
      "space:document:retrieve",
      "task:comment:read",
      "task:comment:write",
      "task:task:read",
      "task:task:write",
      "task:task:writeonly",
      "task:tasklist:read",
      "task:tasklist:write",
      "wiki:node:copy",
      "wiki:node:create",
      "wiki:node:move",
      "wiki:node:read",
      "wiki:node:retrieve",
      "wiki:space:read",
      "wiki:space:retrieve",
      "wiki:space:write_only"
    ]
  }
}
"""


def ensure_auth_file() -> str:
    """
    确保 auth.json 文件存在，不存在则创建默认配置

    Returns:
        auth.json 的绝对路径
    """
    auth_file = get_config().auth_file
    auth_path = Path(auth_file)

    # 如果不是绝对路径，转换为绝对路径
    if not auth_path.is_absolute():
        auth_path = Path(get_abs_path(auth_file))

    # 如果文件不存在，写入默认配置
    if not auth_path.exists():
        # 确保目录存在
        auth_path.parent.mkdir(parents=True, exist_ok=True)

        # 写入默认配置
        with open(auth_path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_AUTH_CONFIG)

        logger.info(f"[权限配置] 已创建默认配置文件: {auth_path}")
        logger.info("  - 可根据需要修改此文件来自定义权限")

    return str(auth_path)


class AuthMixin:
    """权限管理混入类"""

    tab: Any
    app_name: str

    def _get_abs_auth_path(self) -> str:
        """获取权限配置文件的绝对路径（自动创建默认配置）"""
        return ensure_auth_file()

    def _read_auth_file(self) -> dict:
        """读取权限配置文件"""
        auth_path = Path(self._get_abs_auth_path())
        if auth_path.exists():
            with open(auth_path, "r", encoding="utf-8") as f:
                return json.load(f)
        logger.warning(f"[权限导入] 权限配置文件不存在: {auth_path}")
        return {}

    def _get_target_permissions(self) -> set[str]:
        """从 auth.json 获取目标权限集合"""
        auth_data = self._read_auth_file()
        if not auth_data:
            return set()

        permissions: set[str] = set()
        scopes = auth_data.get("scopes", {})
        # 合并 tenant 和 user 权限
        permissions.update(scopes.get("tenant", []))
        permissions.update(scopes.get("user", []))
        return permissions

    def click_batch_import_export(self, timeout: float = 5) -> bool:
        """点击批量导入/导出权限按钮"""
        logger.info(f"[权限导入] 正在查找「批量导入/导出权限」按钮 (超时: {timeout}s)...")
        xpath = 'x://button[text()="批量导入/导出权限"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击批量导入/导出权限")
            return True

        logger.info("  - 未找到按钮")
        return False

    def _extract_app_id(self, url: str | None = None) -> str:
        """从当前 URL 或指定 URL 中提取应用 ID"""
        current_url = url or self.tab.url
        pattern = get_config().app_id_pattern
        match = __import__("re").search(pattern, current_url)
        if match:
            return match.group()
        return ""

    def check_permissions_diff_by_api(self, timeout: float = 10) -> tuple[bool, list[str]]:
        """
        通过 API 监听检查权限差异

        监听接口: https://open.feishu.cn/developers/v1/scope/applied/{app_id}

        Returns:
            (need_import, missing_permissions)
            - need_import: True 表示有权限缺失需要导入
            - missing_permissions: 缺失的权限名称列表
        """
        # 从当前 URL 提取 app_id
        app_id = self._extract_app_id()
        if not app_id:
            logger.warning("[权限检查] 未找到应用 ID")
            return False, []

        api_url_pattern = f"scope/applied/{app_id}"
        logger.info(f"[权限检查] 正在监听接口: .../{api_url_pattern}")

        # 获取目标权限
        target_permissions = self._get_target_permissions()
        if not target_permissions:
            logger.info("  - 目标权限为空，无需导入")
            return False, []

        logger.info(f"  - 目标权限数量: {len(target_permissions)}")

        # 开启网络监听
        self.tab.listen.start(api_url_pattern)

        try:
            # 跳转到权限页面，触发 API 请求
            self.goto_app_page(page="auth")  # type: ignore

            logger.info(f"  - 等待 API 响应 (超时: {timeout}s)...")

            # 等待捕获请求
            packet = None
            for p in self.tab.listen.steps(timeout=timeout):
                packet = p
                break

            if not packet:
                logger.info("  - 未捕获到 API 响应")
                return False, []

            # 获取响应内容
            response = packet.response
            if not response:
                logger.info("  - 响应为空")
                return False, []

            try:
                # 获取响应体
                response_body = response.body
                if response_body is None:
                    logger.info("  - 响应体为空")
                    return False, []

                # 如果是 bytes 或 str，需要解析 JSON
                if isinstance(response_body, bytes):
                    response_body = json.loads(response_body.decode("utf-8"))
                elif isinstance(response_body, str):
                    response_body = json.loads(response_body)

                data = response_body

                # 检查 code
                if data.get("code", -1) != 0:
                    logger.info(
                        f"  - API 返回错误码: {data.get('code')}, msg: {data.get('msg')}"
                    )
                    return False, []

                # 从 scopes 中提取已开通的权限
                scopes = data.get("data", {}).get("scopes", [])
                applied_permissions: set[str] = set()

                for scope in scopes:
                    name = scope.get("name")
                    if name:
                        applied_permissions.add(name)

                logger.info(f"  - 已开通权限数量: {len(applied_permissions)}")

                # 比对差异
                missing = target_permissions - applied_permissions
                if missing:
                    logger.info(f"  - 缺少权限 ({len(missing)} 个): {sorted(missing)}")
                    return True, sorted(missing)
                else:
                    logger.info("  - 权限完整，无需导入")
                    return False, []

            except (json.JSONDecodeError, Exception) as e:
                logger.info(f"  - 响应解析失败: {e}")
                return False, []

        except Exception as e:
            logger.info(f"  - API 监听异常: {e}")
            return False, []

        finally:
            # 停止监听
            self.tab.listen.stop()

    def _read_auth_file_raw(self) -> str:
        """读取权限配置文件原始内容"""
        auth_path = Path(self._get_abs_auth_path())
        if auth_path.exists():
            with open(auth_path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def input_auth_content(
        self, auth_content: str | None = None, timeout: float = 5
    ) -> bool:
        """在权限编辑器中输入内容"""
        from DrissionPage.common import Keys

        try:
            import pyperclip

            HAS_PYPERCLIP = True
        except ImportError:
            HAS_PYPERCLIP = False

        # 读取权限内容
        if auth_content is None:
            auth_content = self._read_auth_file_raw()
            if not auth_content:
                return False

        logger.info(f"  - 读取到的权限内容 ({len(auth_content)} 字符)")

        logger.info(f"[权限导入] 正在查找代码编辑器 (超时: {timeout}s)...")

        # 定位 Monaco 编辑器
        xpath = 'x://div[@class="ud__tabs__content"]//div[@class="ud__tabs__pane"]//div[contains(@class,"monaco-editor")][@role="code"]'
        editor = self.tab.ele(xpath, timeout=timeout)

        if not editor:
            logger.info("  - 未找到代码编辑器")
            return False

        logger.info("  - 发现代码编辑器，正在输入内容...")

        # 点击编辑器获取焦点
        editor.click()
        time.sleep(0.2)

        # 先清空内容：全选 + 退格
        logger.info("  - 正在清空编辑器内容...")
        self.tab.actions.type(Keys.CTRL_A)
        time.sleep(0.3)
        self.tab.actions.type(Keys.BACKSPACE)
        time.sleep(0.5)
        # 再次全选删除，确保清空
        self.tab.actions.type(Keys.CTRL_A)
        time.sleep(0.2)
        self.tab.actions.type(Keys.BACKSPACE)
        time.sleep(0.5)

        # 使用剪贴板粘贴内容
        logger.info("  - 正在输入权限内容...")
        if HAS_PYPERCLIP:
            pyperclip.copy("")
            time.sleep(0.1)
            pyperclip.copy(auth_content)
            time.sleep(0.3)
            self.tab.actions.key_down(Keys.CTRL)
            time.sleep(0.1)
            self.tab.actions.type("v")
            time.sleep(0.1)
            self.tab.actions.key_up(Keys.CTRL)
            logger.info("  - 已通过剪贴板粘贴内容")
        else:
            logger.warning("  - 警告: 未安装 pyperclip，使用直接输入")
            self.tab.actions.input(auth_content)

        logger.info("  - 权限内容已输入")
        return True

    def click_format_json(self, timeout: float = 5) -> bool:
        """点击格式化 JSON 按钮"""
        logger.info(f"[格式化] 正在查找「格式化 JSON」按钮 (超时: {timeout}s)...")
        xpath = 'x://button[text()="格式化 JSON"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击格式化 JSON")
            return True

        logger.info("  - 未找到按钮")
        return False

    def click_next_step(self, timeout: float = 5) -> bool:
        """点击下一步，确认新增权限按钮"""
        logger.info(
            f"[下一步] 正在查找「下一步，确认新增权限」按钮 (超时: {timeout}s)..."
        )
        xpath = 'x://button[text()="下一步，确认新增权限"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击下一步，确认新增权限")
            return True

        logger.info("  - 未找到按钮")
        return False

    def click_apply_permission(self, timeout: float = 5) -> bool:
        """点击申请开通按钮"""
        logger.info(f"[申请开通] 正在查找「申请开通」按钮 (超时: {timeout}s)...")
        xpath = 'x://button[text()="申请开通"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击申请开通")
            return True

        logger.info("  - 未找到按钮")
        return False

    def click_confirm_drawer(self, timeout: float = 5) -> bool:
        """点击抽屉确定按钮"""
        logger.info(f"[确定] 正在查找抽屉确认按钮 (超时: {timeout}s)...")
        xpath = 'x://div[@class="ud__drawer__footer"]//button[text()="确认"]'
        btn = self.tab.ele(xpath, timeout=timeout)

        if btn:
            logger.info("  - 发现按钮，正在点击...")
            btn.click()
            logger.info("  - 已点击确定")
            return True

        logger.info("  - 未找到按钮")
        return False
