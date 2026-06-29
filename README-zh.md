<div align=center>

<img src=".doc/images/banner.png"  alt="Banner"/>

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![License](https://img.shields.io/badge/License-GPL%20v3-green)
![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

README 语言版本 [ [English](README.md) | [**简体中文**](README-zh.md) ]
</div>

# **Azure AI Proxy**
<img src=".doc/images/logo.png" width="150px" alt="logo" align="right" style="float: right"/>

_**"一个轻量级代理，将 Azure OpenAI API 格式桥接到任何 LiteLLM 支持的后端。"**_

一个轻量级、模块化的代理，提供与 Azure OpenAI 兼容的 API，并通过 [LiteLLM](https://docs.litellm.ai/docs/) 将请求转换为后端调用 — 使您能够通过统一的 Azure AI 接口使用 **DeepSeek**、**MIMO**、**Anthropic**、**Ollama** 或任何自定义模型。

兼容支持 Azure OpenAI API 格式的工具和 IDE，包括 JetBrains IDE 和 GitHub Copilot。

## 功能特性与优势

- **完全兼容 Azure AI** — 支持 `/openai/deployments`、`/openai/models`、聊天完成、嵌入和传统完成接口。
- **通过 LiteLLM 支持多提供商** — 使用任何 LiteLLM 支持的提供商（`openai/`、`deepseek/`、`anthropic/`、`ollama/` 等），统一配置。
- **模型身份模拟** — 使用 `base_model` 模拟已知的 Azure 模型，修复上下文窗口显示问题。
- **多模型支持** — 在 `config.yaml` 中配置多个后端，并通过 JetBrains 的部署选择器切换。
- **增强的流式传输** — SSE 保活注释、每块超时保护、优雅的客户端断开检测。
- **工具调用清理** — 自动修复工具调用参数中的格式错误 JSON（例如未转义的 Windows 路径）。
- **优雅的错误处理** — 客户端中断时优雅断开连接、Azure 格式的错误响应、完整的 LiteLLM 异常映射。
- **调试模式** — 切换 `general.debug` 记录完整的请求正文以便故障排除。
- **访问控制** — 设置 `general.api-key` 要求所有代理请求都需要 API 密钥。

## 快速开始

### 1. 先决条件

- Python **3.10+**
- Windows、macOS 或 Linux

### 2. 克隆与设置

```shell
git clone https://github.com/CarmJos/azure-ai-proxy
cd azure-ai-proxy
```

然后运行初始化脚本创建 .venv 并安装依赖，

Windows 系统：
```shell
init.bat
```

macOS / Linux 系统：
```shell
chmod +x init.sh
./init.sh
```

> [!CAUTION]  
> 如果初始化脚本失败，请使用文本编辑器打开它并检查命令。该脚本很简单 — 每个步骤都是单个 shell 命令，您也可以手动运行。

### 3. 配置模型

编辑 `config.yaml` 定义您的后端模型：

```yaml
general:
  host: "0.0.0.0"
  port: 4000
  timeout: 120
  debug: false              # 设置为 true 以记录请求正文
  api-key: ""               # 可选 — 设置此值要求所有请求都必须提供 api-key 头
  log-level: "INFO"         # DEBUG / INFO / WARNING / ERROR
  log-file: ""              # 日志文件路径（空 = 仅输出到标准输出）
  max-stream-timeout: 300   # 流式传输块之间的最大超时秒数
  keepalive-interval: 15    # SSE 保活注释之间的秒数

models:
  - model_name: deepseek-v4-pro
    litellm_params:
      model: deepseek/deepseek-v4-pro
      api_base: https://api.deepseek.com
      api_key: sk-YOUR-KEY
      supports_function_calling: true
      supports_reasoning: true
      max_tokens: 384000
      max_input_tokens: 1000000
      max_output_tokens: 384000
      timeout: 180
```

完整的带注释示例及多提供商配置请参见 [`config.example.yaml`](config.example.yaml)。

### 4. 运行

**Windows 系统：**

```shell
run.bat
```

**macOS / Linux 系统：**

```shell
chmod +x run.sh
./run.sh
```

代理将在 `http://localhost:4000` 启动。

### 5. 与 JetBrains IDE 配合使用

> [!NOTE]
> 以下步骤展示如何将此代理连接到 **JetBrains GitHub Copilot**。
> 任何支持 Azure OpenAI API 格式的客户端都可以类似地工作。

1. 打开 **Copilot Chat** 面板。
2. 点击聊天输入区域中的模型选择器下拉菜单。
3. 选择 **Manage Models**。
4. 在 **Azure** 提供商部分下，点击 **+ Add models**。
5. 为每个模型填写表单：

| 字段 | 值 |
|---|---|
| **Model ID** | `config.yaml` 中的精确部署名称（例如 `deepseek-v4-pro`） |
| **Deployment URL** | `http://{host}:{port}/openai/deployments/{model-id}/chat/completions` |
| **API key** | 任何值 — 除非设置了 `general.api-key`，则必须与该密钥匹配 |
| **Model name** | 您喜欢的显示名称 |
| **Tool** | **勾选**（否则不支持"代理"模式） |
| **Vision** | **取消勾选**（除非您的后端支持图像输入） |

> [!TIP]
> **Deployment URL** 必须包含与 **Model ID** 字段相同的模型 ID。
> 将 `{model-id}` 替换为您的实际部署名称，例如：
> `http://localhost:4000/openai/deployments/deepseek-v4-pro/chat/completions`。

添加后，模型将出现在您的 Copilot Chat 模型选择器中。

## 配置参考

### `config.yaml`

#### 常规设置

| 字段 | 类型 | 描述 |
|---|---|---|
| `general.host` | str | 绑定地址（默认：`0.0.0.0`） |
| `general.port` | int | 代理监听端口（默认：`4000`） |
| `general.timeout` | int | 每个请求的超时秒数（默认：`120`） |
| `general.debug` | bool | 当为 `true` 时记录完整的 POST 请求正文 |
| `general.api-key` | str | 可选 — 要求所有请求都必须提供此 `api-key` 头 |
| `general.log-level` | str | 日志级别：`DEBUG` / `INFO` / `WARNING` / `ERROR`（默认：`INFO`） |
| `general.log-file` | str | 日志文件路径（空 = 仅输出到标准输出） |
| `general.max-stream-timeout` | int | 流式传输块之间的最大超时秒数（默认：`300`） |
| `general.keepalive-interval` | int | SSE 保活注释之间的秒数（默认：`15`） |

#### 模型设置

| 字段 | 类型 | 描述 |
|---|---|---|
| `models[].model_name` | str | JetBrains 中显示的部署名称 |
| `models[].litellm_params.model` | str | LiteLLM 模型标识符（例如 `deepseek/deepseek-v4-pro`） |
| `models[].litellm_params.api_base` | str | 后端 API 基础 URL |
| `models[].litellm_params.api_key` | str | API 密钥（或 `os.environ/VAR` 引用环境变量） |
| `models[].litellm_params.base_model` | str | 可选 — 要模拟的 Azure 模型名称 |
| `models[].litellm_params.max_input_tokens` | int | 报告的上下文窗口大小 |
| `models[].litellm_params.timeout` | int | 每个模型的超时覆盖秒数 |

所有 `litellm_params` 字段都支持 LiteLLM 的完整参数集（`temperature`、`supports_vision`、`supports_function_calling`、`supports_reasoning`、`supports_tool_choice`、`extra_headers` 等）。

完整的支持提供商和模型列表请参见 [LiteLLM Providers](https://docs.litellm.ai/docs/providers)。

### CLI 参数

```
python -m proxy.server --config config.yaml --port 4000 --host 0.0.0.0
```

| 标志 | 默认值 | 描述 |
|---|---|---|
| `--config` | `config.yaml` | YAML 配置文件路径 |
| `--port` | 来自配置 | 覆盖监听端口 |
| `--host` | 来自配置 | 覆盖绑定地址 |

## API 端点

| 方法 | 路径 | 描述 |
|---|---|---|
| `GET` | `/openai/deployments` | 列出所有已配置的部署 |
| `GET` | `/openai/deployments/{name}` | 单个部署详情 |
| `GET` | `/openai/deployments/{name}/models` | 部署的模型信息 |
| `POST` | `/openai/deployments/{name}/chat/completions` | 聊天完成（流式和非流式） |
| `POST` | `/openai/deployments/{name}/embeddings` | 嵌入 |
| `POST` | `/openai/deployments/{name}/completions` | 传统文本完成 |
| `GET` | `/openai/models` | Azure 模型目录 |
| `GET` | `/openai/models/{name}` | 单个模型详情（Azure 格式） |
| `GET` | `/v1/models` | OpenAI 兼容的模型列表 |
| `GET` | `/v1/models/{name}` | 单个模型详情（OpenAI 格式） |
| `GET` | `/health` | 健康检查 |
| `GET` | `/logs` | 最近的日志缓冲区（最后 200 行） |

## 项目结构

```
proxy/
├── server.py           # 应用程序工厂和入口点
├── config.py           # 配置加载和管理
├── bridge.py           # LiteLLM 桥接 — 转换请求并规范化响应
├── models.py           # 解析请求的数据模型
├── routes.py           # 路由注册
├── middleware.py        # 认证、日志记录、CORS、错误处理中间件
├── azure_format.py     # Azure 格式响应构建器和 SSE 格式化
├── logging_setup.py    # 日志记录配置
├── utils.py            # 实用工具函数（JSON 清理等）
└── handlers/
    ├── chat.py         # 聊天完成处理器
    ├── embeddings.py   # 嵌入处理器
    ├── completions.py  # 传统完成处理器
    ├── models.py       # 模型列表处理器
    ├── deployments.py  # 部署列表处理器
    └── health.py       # 健康检查和通配符处理器
```

## 支持与捐赠

如果您欣赏此插件，请考虑通过 [GitHub Sponsors](https://github.com/sponsors/CarmJos) 或 [爱发电](https://www.ifdian.net/a/carmjos/plan) 向我捐赠！

**感谢您支持开源项目！**

非常感谢 JetBrains 友好地为我们提供许可证，以进行此项目和其他开源项目。

[![](https://resources.jetbrains.com/storage/products/company/brand/logos/jb_beam.svg)](https://www.jetbrains.com/?from=https://github.com/CarmJos/)

## 开源许可

本项目的源代码基于
[GNU 通用公共许可证，版本 3](https://www.gnu.org/licenses/gpl-3.0.html) 授权。
