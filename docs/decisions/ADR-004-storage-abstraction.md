# ADR-004: Storage Service Abstraction

## Status
**ACCEPTED**

## Context
Intelligent ML Studio must support diverse deployment topologies: local development (standalone filesystem directory), single-node Docker containers, and multi-node cloud environments (S3, Cloudflare R2, MinIO). Direct file operations throughout the codebase create environment lock-in.

## Decision
We introduce an abstract `StorageService` interface:
1. **Core Interface (`infrastructure/storage/base.py`)**: Defines `save_file`, `load_file`, `delete_file`, `exists`, and `get_stream`.
2. **Local Implementation (`infrastructure/storage/local.py`)**: Production-ready local disk storage with directory containment guards against path traversal (`..` attacks).
3. **Object Store Interface (`infrastructure/storage/object_store.py`)**: S3-compatible adapter interface for cloud object storage.

## Consequences
- **Positive**: Clean separation of persistence mechanism from business logic; path traversal protection centralized in storage implementation; seamless migration between local volume and S3.
- **Negative**: File streaming requires standardized wrapper abstractions across local and cloud backends.
