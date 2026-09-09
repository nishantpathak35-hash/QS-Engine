import glob
import json

for f in glob.glob("C:/Users/Admin/.gemini/antigravity-ide/brain/*/.system_generated/logs/transcript.jsonl"):
    with open(f, "r", encoding="utf-8", errors="ignore") as fp:
        for line in fp:
            if '"source":"USER_EXPLICIT"' in line:
                try:
                    data = json.loads(line)
                    txt = data.get("content", "")
                    if any(w in txt.lower() for w in ["repo", "github", "ai", "free"]):
                        print(f"[{f}] User: {txt}\n")
                except Exception:
                    pass
