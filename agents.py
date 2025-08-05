import os
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from prompts import (
    WRITER_TEMPLATE,
    REVIEWER_TEMPLATE,
    REFINER_TEMPLATE
)

def create_llm_chain(template: str, default_temperature: float = 0.7):
    """
    创建一个基于LLM的处理链。
    该函数会优先使用.env文件中配置的自定义Gemini模型，
    如果未配置，则回退到使用标准的OpenAI模型。

    Args:
        template: 用于LLM的提示词模板。
        default_temperature: 模型的默认温度参数。

    Returns:
        一个可执行的LangChain处理链。
    """
    # --- 模型配置 ---
    # 优先从环境变量读取自定义模型配置
    base_url = os.getenv("OPENAI_API_BASE")
    api_key = os.getenv("GEMINI_API_KEY")
    # 兼容旧版环境变量，如果GEMINI_MODEL不存在，则使用默认值
    model_name = os.getenv("GEMINI_MODEL", "gemini-pro")
    temperature_str = os.getenv("GEMINI_TEMPERATURE")

    # 检查关键配置是否存在
    if base_url and api_key:
        print(f"--- 使用Gemini模型: {model_name} ---")
        try:
            # 如果温度未设置或为空，则使用默认值
            temperature = float(temperature_str) if temperature_str else default_temperature
        except (ValueError, TypeError):
            print(f"[警告] 无法解析GEMINI_TEMPERATURE，将使用默认值: {default_temperature}")
            temperature = default_temperature
        
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            openai_api_base=base_url,
            openai_api_key=api_key,
            # LangChain的某些版本需要明确指定streaming，以确保兼容性
            streaming=True,
        )
    else:
        # 如果关键配置不完整，则无法继续
        raise ValueError("[错误] 缺少必要的环境变量。请确保在.env文件中正确设置了 OPENAI_API_BASE 和 GEMINI_API_KEY。")

    # --- 链构建 ---
    prompt = ChatPromptTemplate.from_template(template)
    chain = prompt | llm | StrOutputParser()
    return chain

def get_writer_agent():
    """获取章节撰写Agent"""
    return create_llm_chain(WRITER_TEMPLATE)

def get_reviewer_agent():
    """获取章节审校Agent"""
    return create_llm_chain(REVIEWER_TEMPLATE)

def get_refiner_agent():
    """获取章节润色Agent"""
    return create_llm_chain(REFINER_TEMPLATE)