# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is `gemini-webapi`, a reverse-engineered asynchronous Python wrapper for Google Gemini web app. It provides an unofficial API to interact with Gemini using browser cookies for authentication.

## Development Commands

### Install dependencies
```bash
pip install -e .
```

### Install with optional browser cookie support
```bash
pip install -e . browser-cookie3
```

### Run tests
Tests require valid Gemini cookies set as environment variables:
```bash
export SECURE_1PSID="your_cookie_value"
export SECURE_1PSIDTS="your_cookie_value"  # optional
python -m unittest tests/test_client_features.py
```

Run a single test:
```bash
python -m unittest tests.test_client_features.TestGeminiClient.test_successful_request
```

### Run OpenAI-compatible server
```bash
export GEMINI_1PSID="your_cookie_value"
export GEMINI_1PSIDTS="your_cookie_value"  # optional
export GEMINI_PROXY="http://proxy:port"    # optional
export API_KEY="your_api_key"              # optional
python src/openai_server.py
```

### Code style
Uses Black formatter:
```bash
pip install black
black src/
```

## Architecture

### Core Components (`src/gemini_webapi/`)

**client.py** - Main entry points:
- `GeminiClient`: Async httpx client that manages cookies, authentication, and API requests
- `ChatSession`: Maintains conversation state across multiple turns (metadata: cid, rid, rcid)

**components/gem_mixin.py** - Mixin providing gem (system prompt) management:
- CRUD operations for custom gems via batch execute RPC calls

**constants.py** - API configuration:
- `Endpoint`: URLs for Gemini services
- `Model`: Enum with model names and their header strings (x-goog-ext headers)
- `GRPC`: RPC method IDs for batch operations
- `ErrorCode`: Known server error codes

**types/** - Pydantic models:
- `ModelOutput`: Response container with text, images, thoughts, candidates
- `Candidate`: Individual response candidate with rcid
- `Gem`/`GemJar`: System prompt configuration
- `WebImage`/`GeneratedImage`: Image response types
- `RPCData`: Payload structure for batch execute

**utils/** - Helper functions:
- `get_access_token`: Fetches SNlM0e token from Gemini init page
- `rotate_1psidts`: Background cookie refresh
- `upload_file`: File upload to Google's content-push service
- `load_browser_cookies`: Optional browser-cookie3 integration

### Request Flow
1. `GeminiClient.init()` fetches access token (SNlM0e) and starts cookie refresh
2. `generate_content()` POSTs to StreamGenerate endpoint with orjson-serialized payload
3. Response parsing extracts candidates, images, and thoughts from nested JSON structure
4. `ChatSession` tracks metadata for multi-turn conversations

### Key Implementation Details
- Uses httpx with HTTP/1.1 (HTTP/2 disabled to avoid RemoteProtocolError)
- Cookie refresh runs in background asyncio task
- Auto-close feature manages client lifecycle for long-running services
- Response parsing uses `get_nested_value()` helper for safe nested access
- Model selection via header manipulation (`x-goog-ext-525001261-jspb`)

### OpenAI-Compatible Server (`src/openai_server.py`)
FastAPI server that wraps GeminiClient to provide `/v1/chat/completions` and `/v1/models` endpoints compatible with OpenAI API format.
