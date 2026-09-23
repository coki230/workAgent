from langchain_openai import ChatOpenAI
from openai.resources import Chat

from app.config import get_settings
from langchain_ollama import ChatOllama

settings = get_settings()


def get_llm_ollama():
    return ChatOllama(
        model=settings.OLLAMA_MODEL,
        base_url=settings.OLLAMA_BASE_URL,
        temperature=0.1
    )

def get_llm_openai():
    llm = ChatOpenAI(
        model=settings.OPENAI_MODEL,
        base_url=settings.OPENAI_BASE_URL,
        api_key="no-key-required",  # llama-server 不需要真实 key，但 LangChain 校验需要填任意非空字符串
        temperature=0.1,
        timeout=1200.0
    )
    return llm



def get_llm():
    return get_llm_ollama()