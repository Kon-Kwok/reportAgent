import time
import httpx
import openai
from typing import TypedDict, List, Callable, Any
from langgraph.graph import StateGraph, END
from .agents import (
    get_writer_agent,
    get_reviewer_agent,
    get_refiner_agent,
    get_humanize_agent,
    humanize_agent_node,
)

# 辅助函数：为 agent 调用添加重试逻辑
def retry_on_read_error(agent_call: Callable, params: dict, max_retries: int = 3) -> Any:
    """
    一个包装函数，用于在发生 httpx.ReadError 或 openai.APIError 时重试 agent 调用。
    """
    attempt = 0
    wait_time = 2  # 初始等待时间为2秒
    while attempt < max_retries:
        try:
            return agent_call(params)
        except (httpx.ReadError, openai.APIError, ValueError) as e:
            attempt += 1
            print(f"--- 警告: 发生 {type(e).__name__}: {e} ---")
            if attempt >= max_retries:
                print(f"--- 错误: 达到最大重试次数 ({max_retries})。任务失败。 ---")
                raise  # 达到最大重试次数后，重新引发异常
            print(f"--- 操作: 在 {wait_time} 秒后重试 (尝试次数 {attempt}/{max_retries}) ---")
            time.sleep(wait_time)
            wait_time *= 2  # 下次等待时间翻倍

# 1. 定义工作流状态
class BookWritingState(TypedDict):
    """
    表示图书撰写过程状态的字典。
    """
    # 输入状态
    book_outline: str  # 完整的图书大纲

    # 内部状态
    chapter_outlines: List[str]  # 按顺序排列的每个章节的大纲列表
    completed_chapters: List[str]  # 已经完成的章节内容列表
    current_chapter_index: int  # 当前正在处理的章节索引

    # 输出状态
    final_book: str  # 最终拼接完成的书稿

class ChapterWritingState(TypedDict):
    """
    用于在章节撰写工作流中传递状态的字典。
    """
    outline: str
    draft: str
    reviews: List[str]
    refined_draft: str
    iteration_count: int
    max_iterations: int

# 2. 定义主工作流节点
def parse_outline_node(state: BookWritingState) -> BookWritingState:
    """
    解析节点：将图书大纲分解为章节大纲。
    """
    print("--- 节点: 解析大纲 ---")
    # 按 "####" 分割字符串，并过滤掉第一个空字符串（如果存在）
    parts = state['book_outline'].split('####')
    # 将 "####" 加回到每个部分的开头，并去除空白
    outlines = [f"####{part}".strip() for part in parts if part.strip()]
    
    return {
        **state,
        "chapter_outlines": outlines,
        "completed_chapters": [],
        "current_chapter_index": 0,
    }

def run_chapter_workflow_node(state: BookWritingState) -> BookWritingState:
    """
    章节撰写节点：为单个章节运行子工作流。
    """
    print(f"--- 节点: 运行章节 {state['current_chapter_index'] + 1} 工作流 ---")
    
    current_index = state['current_chapter_index']
    chapter_outline = state['chapter_outlines'][current_index]
    
    # 构建并运行子工作流
    chapter_writing_workflow = build_chapter_writing_graph()
    # 注意：为子工作流设置合适的 max_iterations
    final_chapter_state = chapter_writing_workflow.invoke({
        "outline": chapter_outline,
        "max_iterations": 2
    })
    
    # 获取最终润色稿或初稿
    completed_chapter = final_chapter_state.get("refined_draft") or final_chapter_state.get("draft", "")
    
    # 更新主工作流状态
    new_completed_chapters = state['completed_chapters'] + [completed_chapter]
    new_index = state['current_chapter_index'] + 1
    
    return {
        **state,
        "completed_chapters": new_completed_chapters,
        "current_chapter_index": new_index,
    }

def compile_book_node(state: BookWritingState) -> BookWritingState:
    """
    汇编节点：将所有完成的章节合并成最终书稿。
    """
    print("--- 节点: 汇编最终书稿 ---")
    
    report = "\n\n".join(state['completed_chapters'])
    return {
        **state,
        "final_book": report
    }

# 3. 定义主工作流条件判断
def should_write_next_chapter(state: BookWritingState) -> str:
    """
    条件判断：检查是否还有章节需要撰写。
    """
    print("--- 条件判断: 是否撰写下一章? ---")
    if state['current_chapter_index'] < len(state['chapter_outlines']):
        print("--- 决策: 是 ---")
        return "run_chapter_workflow"
    else:
        print("--- 决策: 否 ---")
        return "compile_book"

# 4. 定义章节撰写工作流节点
def write_node(state: ChapterWritingState) -> ChapterWritingState:
    """
    撰写节点：根据大纲生成初稿。
    """
    print("--- 节点: 撰写 ---")
    agent = get_writer_agent()
    draft = retry_on_read_error(agent.invoke, {"outline": state['outline']})
    
    # 初始化状态
    return {
        **state,
        "draft": draft,
        "reviews": [],
        "refined_draft": "",
        "iteration_count": 0,
    }

def review_node(state: ChapterWritingState) -> ChapterWritingState:
    """
    审校节点：对当前稿件进行审校并提出意见。
    """
    print("--- 节点: 审校 ---")
    agent = get_reviewer_agent()
    # 优先审校润色稿，如果不存在则审校初稿
    current_draft = state.get("refined_draft") or state.get("draft", "")
    review = retry_on_read_error(agent.invoke, {"draft": current_draft})
    
    # 将新的审校意见添加到列表中
    state["reviews"].append(review)
    return state

def refine_node(state: ChapterWritingState) -> ChapterWritingState:
    """
    润色节点：根据审校意见修改稿件。
    """
    print("--- 节点: 润色 ---")
    agent = get_refiner_agent()
    # 获取最新的审校意见
    latest_review = state["reviews"][-1]
    # 获取用于润色的基础稿件
    base_draft = state.get("refined_draft") or state.get("draft", "")
    
    refined_draft = retry_on_read_error(agent.invoke, {
        "draft": base_draft,
        "review": latest_review
    })
    
    # 更新润色稿并增加迭代次数
    state["refined_draft"] = refined_draft
    state["iteration_count"] += 1
    return state

# 5. 定义章节撰写工作流条件判断函数
def should_continue(state: ChapterWritingState) -> str:
    """
    条件判断：决定是继续润色还是结束流程。
    """
    print("--- 条件判断: 是否继续? ---")
    latest_review = state["reviews"][-1]
    iteration_count = state["iteration_count"]
    max_iterations = state["max_iterations"]

    # 检查是否达到最大迭代次数或审校意见表示无需修改
    if "无需修改" in latest_review or iteration_count >= max_iterations:
        print("--- 决策: 结束 ---")
        return "end"
    else:
        print(f"--- 决策: 继续润色 (迭代次数: {iteration_count + 1}) ---")
        return "refine"

# 6. 构建章节撰写工作流图
def build_chapter_writing_graph():
    """
    构建并返回章节撰写子工作流图。
    """
    workflow = StateGraph(ChapterWritingState)

    # 添加节点
    workflow.add_node("write", write_node)
    workflow.add_node("review", review_node)
    workflow.add_node("refine", refine_node)

    # 设置入口点
    workflow.set_entry_point("write")

    # 添加边
    workflow.add_edge("write", "review")
    workflow.add_edge("refine", "review")

    # 添加条件边
    workflow.add_conditional_edges(
        "review",
        should_continue,
        {
            "refine": "refine",
            "end": END,
        },
    )

    # 编译图
    app = workflow.compile()
    print("章节撰写子工作流图已成功构建。")
    return app

def humanizer_node_with_retry(state: BookWritingState) -> BookWritingState:
    """
    带重试逻辑的 Humanizer 节点。
    """
    print("--- 节点: 拟人化 (带重试逻辑) ---")
    report = state.get('final_book', '')
    if not report:
        print("--- 警告: 在 humanizer_node_with_retry 中未找到报告内容，跳过。 ---")
        return {**state, "final_book": ""}

    agent = get_humanize_agent()
    
    # 使用重试包装器调用 agent
    humanized_report = retry_on_read_error(
        agent.invoke,
        {"text_to_humanize": report}
    )
    
    return {**state, "final_book": humanized_report}

# 7. 构建主工作流图
def build_book_writing_graph():
    """
    构建并返回图书撰写主工作流图。
    """
    workflow = StateGraph(BookWritingState)

    # 添加节点
    workflow.add_node("parse_outline", parse_outline_node)
    workflow.add_node("run_chapter_workflow", run_chapter_workflow_node)
    workflow.add_node("compile_book", compile_book_node)
    # workflow.add_node("humanizer", humanize_agent) # 注释或删除这行
    workflow.add_node("humanizer", humanizer_node_with_retry) # 添加这行

    # 设置入口点
    workflow.set_entry_point("parse_outline")

    # 添加边
    workflow.add_edge("compile_book", "humanizer")
    workflow.add_edge("humanizer", END)

    # 添加条件边
    workflow.add_conditional_edges(
        "parse_outline",
        should_write_next_chapter,
        {
            "run_chapter_workflow": "run_chapter_workflow",
            "compile_book": "compile_book",
        },
    )
    workflow.add_conditional_edges(
        "run_chapter_workflow",
        should_write_next_chapter,
        {
            "run_chapter_workflow": "run_chapter_workflow",
            "compile_book": "compile_book",
        },
    )
    
    # 编译图
    app = workflow.compile()
    print("图书撰写主工作流图已成功构建。")
    return app