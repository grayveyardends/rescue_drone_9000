import requests, base64

with open("../photos/one.webp", "rb") as f:
    img_b64 = base64.b64encode(f.read()).decode()

r = requests.post("http://localhost:8080/v1/chat/completions", json={
    "messages": [{
        "role": "user",
        "content": [
            {"type": "image_url", 
             "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
            {"type": "text", 
             "text": "You are a SAR drone. Analyze this frame and produce an OBSERVATION block."}
        ]
    }],
    "max_tokens": 512
})
print(r.json()["choices"][0]["message"]["content"])
