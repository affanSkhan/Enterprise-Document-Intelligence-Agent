from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.core.config import settings
from app.vectorstore.client import get_vectorstore
import json

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.GEMINI_API_KEY)

def compare_documents(doc_id_1: str, doc_id_2: str, query: str) -> str:
    vectorstore = get_vectorstore()
    results_1 = vectorstore.similarity_search(query, k=5, filter={"doc_id": doc_id_1})
    results_2 = vectorstore.similarity_search(query, k=5, filter={"doc_id": doc_id_2})
    
    context_1 = "\n".join([doc.page_content for doc in results_1])
    context_2 = "\n".join([doc.page_content for doc in results_2])
    
    prompt = ChatPromptTemplate.from_template(
        "You are an expert analyst. Compare the following two document contexts regarding: {query}\n\n"
        "--- Document 1 ---\n{context_1}\n\n"
        "--- Document 2 ---\n{context_2}\n\n"
        "Provide a detailed comparison highlighting similarities and differences."
    )
    chain = prompt | llm
    return chain.invoke({"query": query, "context_1": context_1, "context_2": context_2}).content

def generate_report(topic: str) -> str:
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search(topic, k=10)
    context = "\n".join([doc.page_content for doc in results])
    
    prompt = ChatPromptTemplate.from_template(
        "You are a business analyst. Generate a comprehensive executive report on the topic: {topic} "
        "using the following context.\n\nContext:\n{context}\n\n"
        "Structure the report professionally with an Executive Summary, Key Findings, and Conclusion."
    )
    chain = prompt | llm
    return chain.invoke({"topic": topic, "context": context}).content

def extract_bom(doc_id: str):
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search("bill of materials parts list components", k=10, filter={"doc_id": doc_id})
    context = "\n".join([doc.page_content for doc in results])
    
    prompt = ChatPromptTemplate.from_template(
        "You are an engineering assistant. Extract a Bill of Materials (BOM) from the following context. "
        "Return the output as a valid JSON array of objects, where each object has keys: 'part_number', 'description', 'quantity'.\n\n"
        "Context:\n{context}\n\nJSON Output:"
    )
    chain = prompt | llm
    try:
        response = chain.invoke({"context": context}).content
        clean = response.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        return {"error": "Failed to parse BOM", "details": str(e), "raw": response}

def generate_presentation(topic: str):
    vectorstore = get_vectorstore()
    results = vectorstore.similarity_search(topic, k=8)
    context = "\n".join([doc.page_content for doc in results])
    
    prompt = ChatPromptTemplate.from_template(
        "You are a presentation designer. Create a slide deck outline for the topic: {topic} "
        "based on the following context. Return a JSON array where each object represents a slide "
        "with keys: 'title' and 'bullet_points' (an array of strings).\n\n"
        "Context:\n{context}\n\nJSON Output:"
    )
    chain = prompt | llm
    try:
        response = chain.invoke({"topic": topic, "context": context}).content
        clean = response.replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        return {"error": "Failed to generate presentation", "details": str(e)}
