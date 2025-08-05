# 多Agent报告撰写系统

这是一个基于LangGraph构建的多Agent协作系统，旨在自动化生成包含多个章节的深度研究报告。

系统通过编排不同的AI Agent（如首席架构师、研究分析师、编辑）来分工合作，完成从初稿撰写到最终整合润色的全过程。

## 项目结构

```
.
├── agents.py         # 定义所有核心Agent的逻辑和提示词
├── graph.py          # 使用LangGraph构建Agent协作的工作流
├── main.py           # 项目主入口，负责启动和运行系统
├── requirements.txt  # 项目所需的Python依赖
├── .env              # 存放API密钥等环境变量
└── README.md         # 项目说明文档
```

## 安装与配置

**1. (推荐) 安装 uv**
`uv` 是一个极速的Python包安装和解析器，可以用来替代 `pip` 和 `venv`。如果您的系统中没有安装 `uv`，请通过以下方式安装：
```bash
# macOS / Linux
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**2. 创建虚拟环境并安装依赖**
在项目根目录下运行：
```bash
# 该命令会自动创建一个 .venv 虚拟环境，并安装 requirements.txt 中的所有依赖
uv sync
```
之后，如需手动激活环境，请运行：
```bash
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

**3. 配置API密钥**
本项目支持两种模型调用方式，请根据您的需求配置 `.env` 文件。

**方式一：使用自定义OpenAI兼容模型（推荐）**
如果您想使用自定义的、与OpenAI API格式兼容的模型（例如本地模型、或通过代理访问的Gemini/Claude等），请填写以下变量。**系统将优先使用这些变量。**

```.env
# --- 自定义OpenAI兼容模型配置 ---
GEMINI_URL="https://your-custom-endpoint.com/v1"
GEMINI_API_KEY="your-custom-api-key"
GEMINI_MODEL="your-custom-model-name"
GEMINI_TEMPERATURE=0.3
```

**方式二：使用OpenAI官方模型**
如果未提供完整的自定义模型配置，系统将自动回退使用OpenAI官方API。请确保 `OPENAI_API_KEY` 已设置。

```.env
# --- 备用OpenAI官方配置 ---
OPENAI_API_KEY="sk-..."
```

## 如何运行

完成安装和配置后，直接运行主程序即可启动报告生成工作流。

```bash
python main.py
```

系统将开始执行，您会在终端看到当前使用的模型配置以及每个Agent的工作日志。工作流执行完毕后，最终的报告将自动保存为 `final_report.md` 文件。

## 工作流概览

系统的工作流在 `graph.py` 中定义，目前为一个简化的线性流程：
1.  **首席架构师 (Architect)**: 负责撰写技术性强的第一章。
2.  **研究分析师 (Analyst)**: 负责撰写实践性强的第二章。
3.  **编辑与审校官 (Editor)**: 负责将前两章的初稿整合、润色，生成最终报告。