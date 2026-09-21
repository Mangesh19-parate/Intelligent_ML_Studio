# ADR-003: Model Artifact Integrity & HMAC Signing

## Status
**ACCEPTED**

## Context
Model artifacts serialized to disk/object storage (joblib/pickle) present a critical security risk: untrusted deserialization exploits (arbitrary code execution via malicious pickle payloads). In enterprise environments, model tampering or unintended artifact substitution must be prevented before models are deserialized for live inference.

## Decision
We enforce cryptographic artifact signing and validation:
1. **Manifest Generation**: When a model is finalized and saved, a SHA-256 hash of the artifact file and its metadata manifest is computed.
2. **HMAC Signing**: The manifest is signed using HMAC-SHA256 with the server's `ARTIFACT_SIGNING_KEY`.
3. **Pre-Deserialization Verification**: Before loading any model into memory for evaluation or inference, the signature and artifact SHA-256 checksum are verified. If verification fails, deserialization is aborted with a security exception.

## Consequences
- **Positive**: Complete mitigation of artifact tampering, cryptographic non-repudiation, protection against unauthorized pickle injection.
- **Negative**: Requires strict management of `ARTIFACT_SIGNING_KEY` environment secret across API and worker instances.
