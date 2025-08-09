# Quick connectivity test for OpenAI key/base URL.
import os, traceback
from dotenv import load_dotenv
load_dotenv()

print("OPENAI_BASE_URL =", os.getenv("OPENAI_BASE_URL"))
key = os.getenv("OPENAI_API_KEY")
print("OPENAI_API_KEY present:", bool(key), "length:", len(key) if key else 0)
try:
    from openai import OpenAI
    client = OpenAI(api_key=key, base_url=os.getenv("OPENAI_BASE_URL") or None)
    # light call: list models
    models = client.models.list()
    # just show first few ids
    ids = [m.id for m in models.data[:5]]
    print("OK, models:", ids)
except Exception as e:
    print("ERROR:", type(e).__name__, e)
    traceback.print_exc()
