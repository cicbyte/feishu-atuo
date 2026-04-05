# 飞书开放平台自动化配置工具

飞书开放平台的自动化配置工具，支持应用创建、权限配置、版本管理、事件订阅等功能。

## 功能特性

- 🌐 **浏览器自动化** - 基于 DrissionPage 实现浏览器操作
- 📱 **应用管理** - 自动创建/选择飞书应用
- 🔐 **权限配置** - 自动导入权限配置
- 📦 **版本管理** - 自动创建和发布版本
- 🔌 **事件订阅** - WebSocket 长连接支持

## 安装

```bash
# 使用 pip 安装
pip install feishu-auto

# 或使用 uv 安装
uv pip install feishu-auto
```

### 依赖

- Python >= 3.12
- DrissionPage >= 4.0.0
- lark-oapi >= 1.0.0
- pyperclip >= 1.8.0

## 快速开始

### 命令行使用

```bash
# 使用默认应用名称
feishu-auto

# 指定应用名称
feishu-auto -n myapp

# 指定调试端口
feishu-auto -p 9223

# 设置日志级别
feishu-auto -l DEBUG
```

### Python API 使用

```python
from feishu_auto import FeishuBrowser, create_event_client

# 创建浏览器实例
feishu = FeishuBrowser(app_name="myapp")

# 打开飞书并自动配置
tab = feishu.open_feishu()

# 创建事件订阅客户端
client = create_event_client(app_name="myapp")
client.start(block=False)
```

### 自定义配置

```python
from feishu_auto import FeishuBrowser
from feishu_auto.config import Config, set_config

# 创建自定义配置
config = Config(
    debug_port=9223,
    default_app_name="custom_app",
    default_version="1.0.0",
)

# 设置全局配置
set_config(config)

# 使用自定义配置
feishu = FeishuBrowser(app_name="custom_app")
```

## 项目结构

```
feishu-auto/
├── src/
│   └── feishu_auto/
│       ├── __init__.py      # 包入口
│       ├── __main__.py      # 模块入口
│       ├── cli.py           # 命令行接口
│       ├── config.py        # 配置管理
│       ├── browser.py       # 浏览器基础类
│       ├── auth.py          # 权限管理
│       ├── app.py           # 应用管理
│       ├── version.py       # 版本管理
│       ├── feishu.py        # 主类
│       └── event.py         # 事件订阅
├── tests/                   # 测试目录
├── examples/                # 示例代码
├── pyproject.toml           # 项目配置
└── README.md               # 说明文档
```

## 开发

### 安装开发依赖

```bash
# 克隆项目
git clone https://github.com/yourusername/feishu-auto.git
cd feishu-auto

# 安装开发依赖
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest tests/
```

### 代码检查

```bash
# Ruff 检查
ruff check src/

# 类型检查
mypy src/
```

## 许可证

MIT License
