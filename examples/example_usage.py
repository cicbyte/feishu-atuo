#!/usr/bin/env python3
"""
飞书自动化工具使用示例

演示如何使用 feishu-auto 库进行飞书开放平台的自动化配置
"""
from feishu_auto import FeishuBrowser, get_config
from feishu_auto.config import Config, set_config


def example_basic_usage():
    """基本使用示例"""
    # 创建飞书浏览器实例
    feishu = FeishuBrowser(
        port=9222,
        app_name="myapp"
    )

    # 打开飞书并自动配置
    tab = feishu.open_feishu()

    print(f"当前页面: {tab.title}")
    print(f"当前URL: {tab.url}")


def example_custom_config():
    """自定义配置示例"""
    # 创建自定义配置
    config = Config(
        debug_port=9223,
        default_app_name="custom_app",
        default_version="1.0.0",
        default_version_desc="自定义版本",
    )

    # 设置全局配置
    set_config(config)

    # 创建浏览器实例（将使用自定义配置）
    feishu = FeishuBrowser(app_name="custom_app")
    feishu.open_feishu()


def example_event_client():
    """事件订阅客户端示例"""
    from feishu_auto import create_event_client

    # 创建事件客户端
    client = create_event_client(app_name="myapp")

    # 启动长连接（阻塞模式）
    # client.start(block=True)

    # 或者后台运行
    client.start(block=False)

    print("事件订阅客户端已在后台启动")


if __name__ == "__main__":
    print("=" * 50)
    print("飞书自动化工具使用示例")
    print("=" * 50)

    # 选择要运行的示例
    print("\n请选择示例:")
    print("1. 基本使用")
    print("2. 自定义配置")
    print("3. 事件订阅客户端")

    choice = input("请输入选项 (1-3): ").strip()

    if choice == "1":
        example_basic_usage()
    elif choice == "2":
        example_custom_config()
    elif choice == "3":
        example_event_client()
    else:
        print("无效选项")
