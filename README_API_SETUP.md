# Roo Code API 配置指南

## 概述
本项目提供了一个兼容 OpenAI API 的 Gemini 接口，支持通过 API key 进行认证。

## 配置步骤

### 1. 环境变量设置
确保 `.env` 文件包含以下配置：

```env
GEMINI_1PSID=你的_1PSID_Cookie值
GEMINI_1PSIDTS=你的_1PSIDTS_Cookie值
GEMINI_PROXY=socks5://127.0.0.1:1090
API_KEY=ricky
```

### 2. 启动服务
```bash
cd src
python openai_server.py
```

服务将在 `http://localhost:8000` 启动。

### 3. 在 Roo Code 中配置

在 Roo Code 的设置中添加新的 API 提供商：

#### 基本配置
- **Provider Name**: Gemini API
- **API Base URL**: `http://localhost:8000/v1`
- **API Key**: `ricky`

#### 模型配置
- **Model ID**: `gemini-3.0-pro`
- **Model Name**: Gemini 3.0 Pro

#### 可用的模型
- `gemini-3.0-pro` - Gemini 3.0 Pro
- `gemini-2.5-pro` - Gemini 2.5 Pro
- `gemini-2.5-flash` - Gemini 2.5 Flash

## API 使用示例

### cURL 测试
```bash
curl -X POST "http://localhost:8000/v1/chat/completions" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ricky" \
  -d '{
    "model": "gemini-3.0-pro",
    "messages": [
      {"role": "user", "content": "你好，请介绍一下你自己"}
    ]
  }'
```

### Python 调用
```python
import openai

client = openai.OpenAI(
    api_key="ricky",
    base_url="http://localhost:8000/v1"
)

response = client.chat.completions.create(
    model="gemini-3.0-pro",
    messages=[{"role": "user", "content": "你好"}]
)

print(response.choices[0].message.content)
```

## 故障排除

### 1. Cookie 过期
如果遇到认证错误，请重新获取 Gemini 的 Cookie 值并更新 `.env` 文件。

### 2. 代理问题
确保代理服务运行在 `socks5://127.0.0.1:1090`。

### 3. API Key 错误
确保 Roo Code 中的 API Key 设置为 `ricky`（或 `.env` 中配置的值）。

### 4. 服务未启动
检查服务是否在 `http://localhost:8000` 运行：
```bash
curl http://localhost:8000/docs