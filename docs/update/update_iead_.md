# Deferred Retrieval Improvement Ideas

## Context

Current document ingestion stores uploaded files as chunks in Chroma. Each chunk includes metadata
such as `document_id`, `chunk_index`, `task_id`, `source_filename`, and `user_id`.

This is enough for the current Document Management & Vector Storage phase:

- upload original document
- store document metadata in Postgres
- extract text
- split text into chunks
- embed chunks
- store chunks in Chroma
- track ingestion status

The next risk to revisit is answer quality when one useful answer depends on information spread
across multiple chunks.

## Proposal

When implementing the chat/RAG retrieval phase, do not rely on a single best-matching chunk.
Use a small retrieval pipeline:

1. Run semantic search against Chroma with `top_k`, likely 4 to 8.
2. Filter results by `user_id` so users only retrieve their own documents.
3. For each matched chunk, fetch neighboring chunks from the same document:
   - previous chunk: `chunk_index - 1`
   - matched chunk: `chunk_index`
   - next chunk: `chunk_index + 1`
4. Deduplicate chunks by Chroma id.
5. Sort by `document_id` and `chunk_index` before sending context to the LLM.
6. Keep a token budget so the prompt does not become noisy or too expensive.

Suggested first version:

```text
semantic search top_k = 4
neighbor expansion = +/- 1 chunk
max context chunks = 10 to 12
sort = document_id, chunk_index
```

## Why

Chunking protects the system from sending entire documents to the LLM, but it can split related
information across boundaries. Neighbor expansion recovers nearby context without loading the whole
file.

This keeps the design simple:

- Chroma remains the semantic index.
- Postgres remains the metadata and ownership source.
- The LLM receives only selected relevant context.
- No new storage model is needed for the first chat implementation.

## Trade-Offs

Increasing retrieved chunks improves context completeness, but also increases token usage and can
add irrelevant text.

Recommended order of complexity:

1. Start with top-k retrieval plus neighbor expansion.
2. Add reranking only if answer quality is weak.
3. Add section-aware chunking only if documents are large and structured enough to justify it.
4. Avoid HyDE for now; it was intentionally excluded from this phase.

## Validation Later

Use test documents where the answer depends on adjacent chunks:

- fact begins at the end of chunk N and continues in chunk N+1
- question needs two bullet points from separate chunks
- question matches one chunk semantically but needs preceding context

Expected result: retrieval should include the matched chunk and its neighbors, and the final answer
should cite or use the combined context.

## Status

Deferred. Do not implement during the current upload/vector-storage validation pass.
