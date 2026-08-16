# Evaluation

The evaluation layer is deliberately separated from the runtime so benchmark results can be reproduced without coupling tests to an HTTP server.

## Benchmark schema

Each question should define:

```json
{
  "question": "What changed in the payment terms?",
  "answer": "...",
  "evidence": [{"document": "contract_v2.pdf", "page": 14}],
  "difficulty": "medium"
}
```

## Retrieval metrics

- Recall@1 / Recall@5 / Recall@10
- MRR
- nDCG
- latency P50/P95

The existing retrieval runner consumes ranked chunk IDs and computes Recall@K, MRR and nDCG from fixtures. citeturn382file0

## Generation metrics

- answer relevance
- faithfulness/groundedness
- citation precision and recall
- abstention accuracy

The repository now includes a deterministic citation precision metric and a conservative groundedness smoke metric. These are evaluation primitives, not claims of benchmark performance.

## Security metrics

- prompt-injection attack success rate
- cross-tenant retrieval violations
- unauthorized tool execution

A small baseline prompt-injection fixture is included in `backend/evaluation/security_cases.json`, and `evaluate_security()` reports accuracy, precision, recall and F1.

## Observability

The runtime exposes Prometheus metrics at `/metrics`, including HTTP request count/latency, retrieval count/latency and LLM count/latency. These metrics describe runtime behavior; they are not benchmark results.

## Regression policy

CI should fail a pull request when a benchmark regression exceeds an explicitly configured tolerance. Results must be generated from repository fixtures and recorded with model/version/configuration metadata. Never publish invented benchmark numbers.
