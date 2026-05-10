from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from transformers import AutoModelForCausalLM, AutoTokenizer, TextIteratorStreamer
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
import torch
import logging
from threading import Thread
from typing import Optional
from pydantic import BaseModel
import time
import json
from datetime import datetime
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI 助手 API",
    description="高性能 AI 助手 API 服务",
    version="1.0.0"
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(GZipMiddleware, minimum_size=1000)

# 模型配置
model_path = "/root/autodl-tmp/Models/deepseek-r1-7b-merged"
device = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {device}")
logger.info(f"Model path: {model_path}")

# 加载模型
try:
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        trust_remote_code=True,
        torch_dtype=torch.float16
    ).to(device)
    model.eval()
    logger.info("Model loaded successfully!")
except Exception as e:
    logger.error(f"Error loading model: {str(e)}")
    raise

# 请求限流配置
REQUEST_LIMIT = 100  # 每分钟最大请求数
request_times = []

class ChatRequest(BaseModel):
    prompt: str
    max_length: Optional[int] = 200
    temperature: Optional[float] = 0.7
    top_p: Optional[float] = 0.9

class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str] = None
    timestamp: str

def check_rate_limit():
    """检查请求频率限制"""
    current_time = time.time()
    # 清理过期的请求记录
    request_times[:] = [t for t in request_times if current_time - t < 60]
    
    if len(request_times) >= REQUEST_LIMIT:
        return False
    
    request_times.append(current_time)
    return True

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """添加请求处理时间头"""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局异常处理"""
    logger.error(f"Global error: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc),
            timestamp=datetime.now().isoformat()
        ).dict()
    )

@app.get("/health")
async def health_check():
    """健康检查端点"""
    return {
        "status": "healthy",
        "model_loaded": model is not None,
        "timestamp": datetime.now().isoformat()
    }

@app.post("/generate")
async def generate_text(request: ChatRequest, background_tasks: BackgroundTasks):
    """生成文本"""
    # 检查请求频率限制
    if not check_rate_limit():
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later."
        )

    try:
        logger.info(f"Processing request with prompt: {request.prompt[:50]}...")
        
        # 创建流式生成器
        streamer = TextIteratorStreamer(
            tokenizer, 
            skip_prompt=True,
            timeout=60,
            skip_special_tokens=True
        )

        # 设置生成参数
        generation_kwargs = dict(
            **tokenizer(request.prompt, return_tensors="pt").to(device),
            max_new_tokens=request.max_length,
            streamer=streamer,
            pad_token_id=tokenizer.eos_token_id,
            do_sample=True,
            top_p=request.top_p,
            temperature=request.temperature
        )

        # 在后台线程中运行生成
        thread = Thread(target=model.generate, kwargs=generation_kwargs)
        thread.start()

        def event_stream():
            try:
                collected_text = ""
                for token in streamer:
                    if token:  # 只处理非空token
                        collected_text += token
                        yield f"data: {token}\n\n"
                yield "data: [DONE]\n\n"
                logger.info(f"Generated response: {collected_text[:100]}...")
            except Exception as e:
                logger.error(f"Error in event stream: {str(e)}")
                yield f"data: Error: {str(e)}\n\n"
                yield "data: [DONE]\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
                "Content-Type": "text/event-stream; charset=utf-8"
            }
        )

    except Exception as e:
        logger.error(f"Error during text generation: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Text generation failed: {str(e)}"
        )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        workers=1,
        log_level="info"
    )
