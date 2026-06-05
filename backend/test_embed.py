import os
from dotenv import load_dotenv
load_dotenv()
from langchain_google_genai import GoogleGenerativeAIEmbeddings

print("API Key:", os.environ.get("GEMINI_API_KEY")[:10] + "...")

try:
    embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    res = embeddings.embed_query("hello world")
    print("models/text-embedding-004 length:", len(res))
except Exception as e:
    print("Error with models/text-embedding-004:", e)

try:
    embeddings = GoogleGenerativeAIEmbeddings(model="models/embedding-001")
    res = embeddings.embed_query("hello world")
    print("models/embedding-001 length:", len(res))
except Exception as e:
    print("Error with models/embedding-001:", e)
    
try:
    embeddings = GoogleGenerativeAIEmbeddings(model="text-embedding-004")
    res = embeddings.embed_query("hello world")
    print("text-embedding-004 length:", len(res))
except Exception as e:
    print("Error with text-embedding-004:", e)
