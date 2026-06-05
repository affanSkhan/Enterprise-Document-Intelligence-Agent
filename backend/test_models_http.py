import os
import requests
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY")

url = f"https://generativelanguage.googleapis.com/v1beta/models?key={api_key}"
response = requests.get(url)

if response.status_code == 200:
    data = response.json()
    for model in data.get("models", []):
        print(f"Model: {model.get('name')}")
        print(f"  Methods: {model.get('supportedGenerationMethods')}")
else:
    print(f"Error {response.status_code}: {response.text}")
