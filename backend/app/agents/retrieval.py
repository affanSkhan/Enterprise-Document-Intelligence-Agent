
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from app.vectorstore.client import get_vectorstore
from app.core.config import settings
from typing import Dict, Any

# Using a robust model for reasoning
llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", google_api_key=settings.GEMINI_API_KEY)

system_prompt = (
    "You are an Enterprise Document Intelligence assistant. "
    "Use the following pieces of retrieved context to answer the user's query. "
    "If you don't know the answer, say that you don't know. "
    "Always try to include citations referencing the filename provided in the context. "
    "\n\nContext: \n"
    "{context}"
)

prompt = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{input}"),
])

def chat_with_docs(query: str) -> Dict[str, Any]:
    vectorstore = get_vectorstore()
    retriever = vectorstore.as_retriever(search_kwargs={"k": 5})
    
    docs = retriever.invoke(query)
    context_str = "\n\n".join([f"--- Source: {d.metadata.get('filename', 'Unknown')} ---\n{d.page_content}" for d in docs])
    
    formatted_prompt = prompt.format_messages(context=context_str, input=query)
    response = llm.invoke(formatted_prompt)
    
    return {
        "answer": response.content,
        "context": [{"page_content": doc.page_content, "metadata": doc.metadata} for doc in docs]
    }
