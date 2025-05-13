import requests

try:
    r = requests.get("http://localhost:8080/all", timeout=5)
    print("Success:", r.status_code)
    print(r.json())
except Exception as e:
    print("ERROR:", e)
