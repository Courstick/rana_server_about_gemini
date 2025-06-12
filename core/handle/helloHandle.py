import time
import json
import random
import asyncio
from core.handle.mcpHandle import (
    MCPClient,
    send_mcp_initialize_message,
    send_mcp_tools_list_request,
)
from core.utils.util import remove_punctuation_and_length

TAG = __name__

WAKEUP_CONFIG = {
    "refresh_time": 5,
    "words": ["你好", "你好啊", "嘿，你好", "嗨"],
}

# 用于防止并发调用wakeupWordsResponse的锁
_wakeup_response_lock = asyncio.Lock()


async def handleHelloMessage(conn, msg_json):
    """处理hello消息"""
    audio_params = msg_json.get("audio_params")
    if audio_params:
        format = audio_params.get("format")
        conn.logger.bind(tag=TAG).info(f"客户端音频格式: {format}")
        conn.audio_format = format
        conn.welcome_msg["audio_params"] = audio_params
    features = msg_json.get("features")
    if features:
        conn.logger.bind(tag=TAG).info(f"客户端特性: {features}")
        conn.features = features
        if features.get("mcp"):
            conn.logger.bind(tag=TAG).info("客户端支持MCP")
            conn.mcp_client = MCPClient()
            # 发送初始化
            asyncio.create_task(send_mcp_initialize_message(conn))
            # 发送mcp消息，获取tools列表
            asyncio.create_task(send_mcp_tools_list_request(conn))

    await conn.websocket.send(json.dumps(conn.welcome_msg))


async def checkWakeupWords(conn, text):
    _, filtered_text = remove_punctuation_and_length(text)
    if filtered_text not in conn.config.get("wakeup_words"):
        return False
    asyncio.create_task(wakeupWordsResponse(conn))
    return True


async def wakeupWordsResponse(conn):
    if not conn.tts or not conn.llm or not conn.llm.response_no_stream:
        return

    try:
        # 生成唤醒词回复
        wakeup_word = random.choice(WAKEUP_CONFIG["words"])
        question = (
                "此刻用户正在和你说```"
                + wakeup_word
                + "```。\n请你根据以上用户的内容进行简短回复。要像一个人正常人一样说话，不要像机器人一样说话。\n"
                + "请勿对这条内容本身进行任何解释和回应，请勿返回表情符号，仅返回对用户的内容的回复。"
        )

        result = conn.llm.response_no_stream(conn.config["prompt"], question)
        if not result or len(result) == 0:
            return
    finally:
        # 确保在任何情况下都释放锁
        if _wakeup_response_lock.locked():
            _wakeup_response_lock.release()
