import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

try:
    models = list(genai.list_models())
    for m in models:
        print(f"Model: {m.name}")
        print(f"  Supported methods: {m.supported_generation_methods}")
except Exception as e:
    print("Error listing models:", e)
