# Evaluation

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

## Generation metrics

- answer relevance
- faithfulness/groundedness
- citation precision and recall
- abstention accuracy

## Agent metrics

- task completion
- tool selection accuracy
- unnecessary tool calls
- recovery from tool failure

## Security metrics

- prompt-injection attack success rate
- cross-tenant retrieval violations
- unauthorized tool execution

## Regression policy

Future CI should fail a pull request when a benchmark regression exceeds an explicitly configured tolerance. Results must be generated from the repository's fixtures and recorded with model/version/configuration metadata.
