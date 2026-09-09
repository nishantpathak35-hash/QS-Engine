import urllib.request
import json

payload = {
    "messages": [
        {"role": "user", "content": 'Respond in valid JSON only: {"status": "AI_READY", "model": "pollinations"}'}
    ],
    "model": "openai",
    "jsonMode": True
}

req = urllib.request.Request(
    "https://text.pollinations.ai/",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
)

try:
    with urllib.request.urlopen(req, timeout=15) as resp:
        print("Free AI Response:", resp.read().decode("utf-8"))
except Exception as e:
    print("Free AI Error:", e)
