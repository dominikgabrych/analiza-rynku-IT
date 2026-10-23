# ADR 0005: Local LLM served by Ollama on the host

- Status: accepted
- Date: 2026-10-16 (recorded 2026-10-19)

## Context

An LLM extracts fields from thousands of postings and later answers questions about them. It runs locally, because a paid API would charge per token for every posting and the posting texts should stay on the machine. The host runs Windows 11 with Docker Desktop and an AMD GPU with 8 GB of VRAM.

## Decision

- **Ollama runs natively on Windows**, uses the GPU through Vulkan and listens on `127.0.0.1` only. Containers reach it at `host.docker.internal`.
- **The application talks to Ollama's OpenAI-compatible API**, so switching to vLLM or another server is a change of URL and model name.
- **The model is chosen separately**, by an evaluation on our own data.

## Alternatives considered

- **Ollama in a container:** Docker Desktop on Windows [passes only NVIDIA GPUs to containers](https://docs.docker.com/desktop/features/gpu/), so the model would run on the CPU, several times slower.
- **Docker Model Runner or ROCm:** both lack GPU support for this card on Windows.
- **A hosted LLM API:** stronger models without setup, but a cost per token and posting texts leaving the machine.

## Consequences

- Ollama is installed and updated outside the repository.
- Tools run directly in WSL cannot reach Ollama while WSL uses NAT networking; they run in a container or WSL switches to mirrored networking.
- 8 GB of VRAM limits a model file to about 6.5 GB.
