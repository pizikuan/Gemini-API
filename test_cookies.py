import os
import sys
import asyncio
from dotenv import load_dotenv

# Ensure local gemini_webapi is used
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "src")))

from gemini_webapi import GeminiClient

# 加载环境变量
load_dotenv()

async def test_cookies():
    """测试 Cookie 是否有效"""
    secure_1psid = os.getenv("GEMINI_1PSID")
    secure_1psidts = os.getenv("GEMINI_1PSIDTS")
    proxy = os.getenv("GEMINI_PROXY")

    if not secure_1psid:
        print("ERROR: GEMINI_1PSID environment variable not set")
        return

    print("Testing Cookie validity...")
    print(f"1PSID: {secure_1psid[:20]}...")
    print(f"1PSIDTS: {secure_1psidts[:20]}..." if secure_1psidts else "1PSIDTS: Not set")

    try:
        client = GeminiClient(secure_1psid, secure_1psidts or "", proxy=proxy)
        await client.init(timeout=30, verbose=False)
        print("SUCCESS: Cookie validation passed!")

        # Test content generation
        response = await client.generate_content("Hello")
        print(f"Response: {response.text[:100]}...")

        await client.close()

    except Exception as e:
        print(f"ERROR: Cookie validation failed: {e}")
        print("\nTo get new cookies:")
        print("1. Visit https://gemini.google.com")
        print("2. Press F12 to open developer tools")
        print("3. Go to Network tab")
        print("4. Refresh the page")
        print("5. Click any request, check Cookies for __Secure-1PSID and __Secure-1PSIDTS")

if __name__ == "__main__":
    asyncio.run(test_cookies())