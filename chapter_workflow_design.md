# 章节撰写子工作流设计方案

## 1. 概述

本文档旨在为自动化图书撰写框架设计一个核心的“章节撰写”子工作流。该工作流的目标是接收一个章节大纲，通过一个“撰写 -> 审校 -> 润色”的迭代循环，自动化地生成高质量的章节内容。

## 2. 工作流状态 (State)

为了在工作流的各个节点之间传递和管理数据，我们定义一个统一的状态对象 `ChapterWritingState`。它是一个 Python `TypedDict`，包含了处理单个章节所需的所有核心数据。

### 2.1. `ChapterWritingState` 定义

```python
from typing import TypedDict, List

class ChapterWritingState(TypedDict):
    """
    用于在章节撰写工作流中传递状态的字典。
    """
    outline: str               # 章节大纲
    draft: str                 # 初稿内容
    reviews: List[str]         # 历次审校意见列表
    refined_draft: str         # 润色后的稿件
    iteration_count: int       # 当前的迭代次数
    max_iterations: int        # 允许的最大迭代次数
```

### 2.2. 字段说明

*   `outline`: 输入的章节大纲，是内容创作的起点和依据。
*   `draft`: 由 `write_node` 生成的初稿。
*   `reviews`: 一个字符串列表，用于存储每一次 `review_node` 产生的审校意见，方便追溯和决策。
*   `refined_draft`: 由 `refine_node` 根据审校意见修改后生成的稿件。在后续的迭代中，此稿件将作为 `review_node` 的输入。
*   `iteration_count`: 记录当前的迭代轮次，用于控制循环次数，防止无限循环。
*   `max_iterations`: 预设的最大迭代次数，作为循环的终止条件之一。

## 3. 工作流节点 (Nodes)

工作流由三个核心的功能节点组成，每个节点负责一项独立的任务。

### 3.1. 撰写节点 (`write_node`)

*   **功能**: 根据输入的章节大纲 (`outline`)，调用大语言模型生成章节的初稿 (`draft`)。
*   **输入**: `outline`
*   **输出**: `draft`

### 3.2. 审校节点 (`review_node`)

*   **功能**: 对当前的稿件（初稿 `draft` 或润色稿 `refined_draft`）进行评估和审校，提出具体的、可操作的修改意见 (`review`)。审校标准可以基于一致性、清晰度、事实准确性等维度。
*   **输入**: `draft` 或 `refined_draft`
*   **输出**: `review` (审校意见)

### 3.3. 润色节点 (`refine_node`)

*   **功能**: 根据 `review_node` 提供的审校意见，对稿件进行修改和润色，生成新版本的稿件 (`refined_draft`)。
*   **输入**: `draft` (或 `refined_draft`), `review`
*   **输出**: `refined_draft`

## 4. 工作流流程 (Flow)

工作流从 `write_node` 开始，然后进入一个由“审校”和“润色”组成的条件循环。

1.  **开始**: 工作流以 `write_node` 作为入口，生成初稿。
2.  **审校**: `review_node` 对稿件进行审校。
3.  **条件判断**: 在 `review_node` 之后，系统会进行一次条件判断：
    *   **条件**: 审校意见是否表明“无需修改”？或者，当前迭代次数 (`iteration_count`) 是否已达到最大值 (`max_iterations`)？
    *   **如果为真 (True)**: 工作流结束，最终的稿件 (`refined_draft` 或 `draft`) 被视为合格产出。
    *   **如果为假 (False)**: 工作流进入 `refine_node`。
4.  **润色与循环**: `refine_node` 根据审校意见进行润色，然后将润色稿再次送回 `review_node` 进行新一轮的审校，形成一个闭环。

### 流程图

以下是使用 Mermaid.js 绘制的工作流流程图：

```mermaid
graph TD
    A[Start] --> B(write_node);
    B --> C{review_node};
    C --> D{is_quality_ok_or_max_iterations};
    D -- No --> E(refine_node);
    E --> C;
    D -- Yes --> F[End];