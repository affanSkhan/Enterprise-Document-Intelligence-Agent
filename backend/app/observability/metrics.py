from prometheus_client import Counter, Histogram

REQUESTS = Counter("eid_requests_total", "HTTP requests", ["method", "path", "status"])
REQUEST_LATENCY = Histogram("eid_request_latency_seconds", "HTTP request latency", ["method", "path"])
INGESTION_JOBS = Counter("eid_ingestion_jobs_total", "Ingestion jobs by terminal state", ["status"])
LLM_REQUESTS = Counter("eid_llm_requests_total", "LLM calls", ["model", "status"])
LLM_LATENCY = Histogram("eid_llm_latency_seconds", "LLM latency", ["model"])
RETRIEVAL_REQUESTS = Counter("eid_retrieval_requests_total", "Retrieval calls", ["mode"])
RETRIEVAL_LATENCY = Histogram("eid_retrieval_latency_seconds", "Retrieval latency", ["mode"])
