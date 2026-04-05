"""
飞书自动化工具 - 命令行接口
"""
from __future__ import annotations

import argparse
import logging
import sys
import time

from feishu_auto import __version__
from feishu_auto.feishu import FeishuBrowser


def setup_logging(level: str = "INFO") -> None:
    """配置日志"""
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def main() -> None:
    """命令行入口"""
    parser = argparse.ArgumentParser(
        prog="feishu-auto",
        description="飞书开放平台自动化配置工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  feishu-auto                    使用默认应用名称 (openclaw)
  feishu-auto -n myapp           使用指定应用名称
  feishu-auto --version          显示版本号
        """,
    )

    parser.add_argument(
        "-n",
        "--name",
        type=str,
        default="openclaw",
        help="应用名称 (默认: openclaw)",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=9222,
        help="浏览器调试端口 (默认: 9222)",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        type=str,
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="日志级别 (默认: INFO)",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"feishu-auto {__version__}",
    )

    args = parser.parse_args()

    # 配置日志
    setup_logging(args.log_level)

    logging.info("=" * 50)
    logging.info("飞书开放平台自动化配置工具")
    logging.info("=" * 50)
    logging.info(f"  - 版本: {__version__}")
    logging.info(f"  - 应用名称: {args.name}")
    logging.info(f"  - 调试端口: {args.port}")

    # 创建浏览器实例
    feishu = FeishuBrowser(port=args.port, app_name=args.name)

    # 打开飞书首页（自动完成全部流程）
    tab = feishu.open_feishu()

    logging.info("=" * 50)
    logging.info(f"当前页面: {tab.title}")
    logging.info(f"当前URL: {tab.url}")
    logging.info("=" * 50)
    logging.info("")
    logging.info("[完成] 配置完成！长连接客户端已在后台运行")
    logging.info("  - 浏览器可手动关闭")
    logging.info("  - 按 Ctrl+C 退出程序")
    logging.info("=" * 50)

    # 保持程序运行
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("\n[退出] 程序已停止")


if __name__ == "__main__":
    main()
