import httpx
payload={"prompt":"sun","min_colors":2,"max_colors":6,"backend":"nano_banana_pro","count":1}
with httpx.Client(timeout=180.0) as c:
    r=c.post('http://step-generate:8001/run', json=payload)
    print('status', r.status_code)
    print(r.text)
