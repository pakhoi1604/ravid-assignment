---
title: "LangChain Dependency Refresh Plan"
created: "2026-08-30"
type: journal
---

# LangChain Dependency Refresh Plan

## Context

Created `plans/260830-1740-langchain-dependency-refresh/` to clean up the Part 1 dependency graph
before implementing Part 2.

## What Happened

- Planned removal of the unused `langchain` umbrella package.
- Selected current stable modular packages only for imports Part 1 actually uses: text splitting,
  Chroma integration, Hugging Face embeddings, and their concrete runtimes.
- Planned alignment of the Chroma Python client and Docker server versions.
- Added baseline, focused regression, full Part 1, Docker build, and fresh-stack live-ingestion
  gates.

## Decisions

- Keep transitive packages such as `langchain-core` out of direct dependencies until project source
  imports them.
- Make only compatibility repairs demonstrated by tests; preserve Part 1 API, metadata, and vector
  ID contracts.
- Validation confirmed current Docker persistence is disposable test data. Reset only the resolved
  project-owned PostgreSQL, media, and Chroma volumes together; preserve the Hugging Face cache and
  unrelated Docker data.
- Block the RAG Part 2 and reusable endpoint smoke-test plans until the refreshed dependency stack
  passes Part 1 regression checks.

## Next

Review and execute `plans/260830-1740-langchain-dependency-refresh/plan.md` before continuing the
blocked plans.
