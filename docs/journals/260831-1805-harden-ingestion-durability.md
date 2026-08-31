---
title: "Harden Ingestion Durability"
date: "2026-08-31"
plan: "260831-1310-harden-ingestion-durability"
---

# Harden Ingestion Durability

## Context

The ingestion path used Celery for asynchronous execution and Chroma for vectors, but PostgreSQL did
not fence duplicate deliveries, stale workers, broker publication loss, or partial vector writes.
The plan required durable generation ownership, bounded recovery, and resource ceilings without
changing the public upload endpoint shape.

## What Changed

- PostgreSQL now owns document visibility through `Document.active_generation`, job attempt fencing
  through `IngestionJob.generation`, generation manifests, and a transactional dispatch outbox.
- Chroma writes are generation-qualified and verified before activation. Retrieval resolves active
  generations from PostgreSQL and fails closed on missing or mismatched owner/document/generation
  metadata.
- Celery delivery carries `(task_id, generation)`, claims only matching pending work, and finalizes
  success/failure only while the same generation owns the job lease.
- Recovery rotates stale pending/processing jobs to new generations, outbox publication uses leased
  rows with bounded retries, and stale generation cleanup is exact and capped.
- Ingestion enforces PDF page, extracted-character, and chunk-count ceilings before embedding/vector
  writes.

## Decisions

- Dispatch is explicitly at least once. The safety boundary is PostgreSQL generation fencing, not a
  distributed transaction with Redis or Chroma.
- Existing live generation-less vectors require either reset volumes or the explicit legacy reindex
  command before serving generation-filtered chat.
- Parser hardening remains limited to application ceilings; MIME validation, malware scanning,
  process sandboxing, and tenant quotas stay deferred.

## Verification

Local gates passed: scoped ruff, Django checks for local/test settings, migration drift check, full
pytest, and Compose config. Subagent verification also passed Docker-backed Chroma tests, production
document/RAG tests, rebuilt-stack smoke, and management command smoke. Repo-wide ruff still reports
pre-existing `.agents` and `.claude` lint issues outside this implementation.
