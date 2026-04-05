"""
Minimal model lister - writes output to models_out.txt
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()
from google import genai
from google.genai import types

api_key = os.getenv("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key)

lines = []
for m in client.models.list():
    lines.append(f"{m.name}")

with open("models_out.txt", "w") as f:
    f.write("\n".join(lines))
print("Done - see models_out.txt")
