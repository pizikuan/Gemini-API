import os
import sys
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import uvicorn
from dotenv import load_dotenv
import json

# Ensure local gemini_webapi is used
sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "."))
)

from gemini_webapi import GeminiClient  # noqa: E402

# Load environment variables from .env file
load_dotenv()


def verify_api_key(request: Request):
    """验证 API key"""
    expected_key = os.getenv("API_KEY")
    if not expected_key:
        return True  # 如果未设置 API key，则跳过验证

    # 检查请求头中的 API key
    auth_header = request.headers.get("authorization", "")
    api_key_header = request.headers.get("api-key", "")

    # 支持多种格式：Bearer token, 直接 api-key
    if auth_header.startswith("Bearer "):
        provided_key = auth_header[7:]  # 移除 "Bearer " 前缀
    else:
        provided_key = api_key_header

    if provided_key != expected_key:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "gemini-3.0-pro"
    messages: list[dict]
    max_tokens: int | None = None
    temperature: float | None = None
    stream: bool = False  # For simplicity, not implementing streaming


class ChatCompletionChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class UsageInfo(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatCompletionResponse(BaseModel):
    id: str = "chatcmpl-gemini"
    object: str = "chat.completion"
    created: int = 0
    model: str
    choices: list[ChatCompletionChoice]
    usage: UsageInfo = UsageInfo()


class ModelInfo(BaseModel):
    id: str
    object: str = "model"
    created: int = 0
    owned_by: str = "google"


class ModelsResponse(BaseModel):
    object: str = "list"
    data: list[ModelInfo]


# Global client
client: GeminiClient | None = None


async def init_gemini_client():
    global client
    # Get cookies from environment variables
    secure_1psid = os.getenv("GEMINI_1PSID")
    secure_1psidts = os.getenv("GEMINI_1PSIDTS")
    proxy = os.getenv("GEMINI_PROXY")

    if not secure_1psid:
        raise ValueError(
            "GEMINI_1PSID environment variable is required"
        )

    client = GeminiClient(secure_1psid, secure_1psidts or "", proxy=proxy)
    await client.init(
        timeout=30,
        auto_close=False,
        close_delay=300,
        auto_refresh=True
    )


app = FastAPI(title="Gemini OpenAI Compatible API")


@app.on_event("startup")
async def startup_event():
    await init_gemini_client()


@app.get("/v1/models")
async def list_models(http_request: Request):
    # 验证 API key
    verify_api_key(http_request)

    models = [
        ModelInfo(id="gemini-3.0-pro"),
        ModelInfo(id="gemini-2.5-pro"),
        ModelInfo(id="gemini-2.5-flash"),
        ModelInfo(id="gpt-4"),
        ModelInfo(id="gpt-4-turbo"),
        ModelInfo(id="gpt-3.5-turbo"),
        ModelInfo(id="gpt-3.5-turbo-16k"),
    ]
    return ModelsResponse(data=models)


@app.post("/v1/chat/completions")
async def create_chat_completion(request_data: ChatCompletionRequest, http_request: Request):
    # 验证 API key
    verify_api_key(http_request)

    if not client:
        raise HTTPException(
            status_code=500,
            detail="Gemini client not initialized"
        )

    # For simplicity, concatenate all user messages as prompt
    def extract_content(msg):
        content = msg.get("content", "")
        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            # Handle multimodal content, extract text parts
            texts = []
            for part in content:
                if isinstance(part, str):
                    texts.append(part)
                elif isinstance(part, dict) and "text" in part:
                    texts.append(part["text"])
            return " ".join(texts)
        else:
            return str(content)

    prompt = "\n".join([extract_content(msg) for msg in request_data.messages])

    # Handle streaming
    if request_data.stream:
        # Map model names, default to gemini-3.0-pro if not recognized
        model_map = {
            "gemini-3.0-pro": "gemini-3.0-pro",
            "gemini-2.5-pro": "gemini-2.5-pro",
            "gemini-2.5-flash": "gemini-2.5-flash",
            "gpt-4": "gemini-3.0-pro",
            "gpt-4-turbo": "gemini-3.0-pro",
            "gpt-3.5-turbo": "gemini-2.5-flash",
            "gpt-3.5-turbo-16k": "gemini-2.5-pro",
        }
        gemini_model = model_map.get(request_data.model, "gemini-3.0-pro")

        async def generate_stream():
            chunk_id = f"chatcmpl-{int(time.time())}"
            created = int(time.time())
            try:
                response = await client.generate_content(
                    prompt, model=gemini_model
                )
                content = response.text

                # First chunk with role
                chunk1 = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request_data.model,
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk1)}\n\n"

                # Content chunk
                chunk2 = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request_data.model,
                    "choices": [{"index": 0, "delta": {"content": content}, "finish_reason": None}]
                }
                yield f"data: {json.dumps(chunk2)}\n\n"

                # Final chunk with finish_reason
                chunk3 = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request_data.model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(chunk3)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                error_chunk = {
                    "id": chunk_id,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": request_data.model,
                    "choices": [{"index": 0, "delta": {"content": f"Error: {str(e)}"}, "finish_reason": "stop"}]
                }
                yield f"data: {json.dumps(error_chunk)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            generate_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )

    try:
        # Map model names, default to gemini-3.0-pro if not recognized
        model_map = {
            "gemini-3.0-pro": "gemini-3.0-pro",
            "gemini-2.5-pro": "gemini-2.5-pro",
            "gemini-2.5-flash": "gemini-2.5-flash",
            "gpt-4": "gemini-3.0-pro",
            "gpt-4-turbo": "gemini-3.0-pro",
            "gpt-3.5-turbo": "gemini-2.5-flash",
            "gpt-3.5-turbo-16k": "gemini-2.5-pro",
        }
        gemini_model = model_map.get(request_data.model, "gemini-3.0-pro")

        response = await client.generate_content(
            prompt, model=gemini_model
        )

        return ChatCompletionResponse(
            id=f"chatcmpl-{int(time.time())}",
            created=int(time.time()),
            model=request_data.model,
            choices=[
                ChatCompletionChoice(
                    message=ChatMessage(
                        role="assistant",
                        content=response.text
                    )
                )
            ]
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Gemini API error: {str(e)}"
        )


if __name__ == "__main__":
    print("Starting Gemini OpenAI Compatible Server...")
    print(
        "Set GEMINI_1PSID and optionally GEMINI_1PSIDTS, GEMINI_PROXY, API_KEY, PORT "
        "environment variables."
    )
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)