import os
from .graph import build_book_writing_graph
from dotenv import load_dotenv

def main():
    """
    主函数：运行全新的图书撰写工作流。
    """
    # 在程序开始时加载 .env 文件
    load_dotenv()

    # --- 1. 检查API密钥 ---
    if not os.getenv("GEMINI_API_KEY") or not os.getenv("OPENAI_API_BASE"):
        print("[错误] GEMINI_API_KEY 或 OPENAI_API_BASE 未设置。请在 .env 文件中设置这些变量后重试。")
        return

    # --- 2. 加载图书大纲 ---
    try:
        with open("202508042315.md", "r", encoding="utf-8") as f:
            book_outline = f.read()
        print("图书大纲已成功加载。")
    except FileNotFoundError:
        print("[错误] 未找到大纲文件 '202508042315.md'。请确保文件存在于正确的位置。")
        return
    except Exception as e:
        print(f"[错误] 读取大纲文件时发生错误: {e}")
        return

    # --- 3. 构建并获取工作流图 ---
    app = build_book_writing_graph()

    # --- 4. 设置初始状态并运行工作流 ---
    initial_state = {
        "book_outline": book_outline,
        "chapter_outlines": [],
        "completed_chapters": [],
        "final_book": "",
        "current_chapter_index": 0,
    }

    print("\n--- 开始执行图书撰写工作流 ---")
    final_state = None
    for state_update in app.stream(initial_state):
        # state_update 的格式是 {node_name: state_after_node}
        node_name = list(state_update.keys())[0]
        updated_state = list(state_update.values())[0]
        print(f"--- 节点 '{node_name}' 执行完毕 ---")
        # 可以在这里添加更详细的日志，例如当前进度
        if node_name == "run_chapter_workflow":
            print(f"已完成 {len(updated_state.get('completed_chapters', []))} / {len(updated_state.get('chapter_outlines', []))} 个章节。")
        final_state = updated_state

    print("\n--- 工作流执行完毕 ---")

    # --- 5. 保存最终书稿 ---
    if final_state and final_state.get("final_book"):
        try:
            with open("final_book.md", "w", encoding="utf-8") as f:
                f.write(final_state["final_book"])
            print("\n最终书稿已成功保存到 'final_book.md' 文件中。")
        except IOError as e:
            print(f"\n[错误] 保存最终书稿失败: {e}")
    else:
        print("\n[警告] 未生成最终书稿，无法保存。")

if __name__ == "__main__":
    main()