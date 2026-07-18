import requests, json, time
from pathlib import Path

class LLMBridge:
    def __init__(self, host="http://localhost:8080"):
        self.host = host
        self.action_dir = Path("action")
        self.action_dir.mkdir(exist_ok=True)

    def analyze_frame(self, base64_img: str, context: str = "") -> str:
        payload = {
            "messages": [{
                "role": "system",
                "content": "You are a SAR drone. Respond using [[personX]], <<action_start>>, <<say>>, <<do>>, OBSERVATION:, PRIORITY: structure. Include Malayalam translation in <<say>> blocks."
            }, {
                "role": "user", 
                "content": [
                    {"type": "image_url", 
                     "image_url": {"url": f"data:image/jpeg;base64,{base64_img}"}},
                    {"type": "text", 
                     "text": f"Analyze this drone frame. {context}"}
                ]
            }],
            "temperature": 0.3,
            "max_tokens": 1024
        }
        r = requests.post(f"{self.host}/v1/chat/completions", 
                         json=payload, timeout=60)
        response = r.json()["choices"][0]["message"]["content"]
        self._write_actions(response)
        return response

    def _write_actions(self, response: str):
        """Parse and write actions to /action folder"""
        import re
        actions = re.findall(r'<<action_start>>(.*?)<<end>>', 
                            response, re.DOTALL)
        timestamp = int(time.time())
        action_file = self.action_dir / f"action_{timestamp}.json"
        action_file.write_text(json.dumps({
            "timestamp": timestamp,
            "actions": [a.strip() for a in actions],
            "full_response": response
        }))
