# ADR 0005: Local LLM served by Ollama on the host

- Status: accepted
- Date: 2026-10-16 (recorded 2026-10-19)

## Context

An LLM extracts fields from thousands of postings and later answers RAG questions. It runs locally: a paid API would charge per token for every posting, and the posting texts should stay on the machine. The host runs Windows 11 with Docker Desktop on WSL 2 and has an AMD Radeon RX 5700 XT GPU with 8 GB of VRAM.

## Decision

- **Ollama runs natively on Windows** and uses the GPU through its [Vulkan backend](https://docs.ollama.com/gpu), which is enabled by default.
- **Ollama listens on `127.0.0.1:11434` only.** Containers reach it at [`host.docker.internal:11434`](https://docs.docker.com/desktop/features/networking/networking-how-tos/), which Docker Desktop routes to the host. This was verified from a container on 2026-10-17.
- **The application will use Ollama's [OpenAI-compatible API](https://docs.ollama.com/api/openai-compatibility)**, so moving to vLLM or another server means changing a URL and a model name in configuration.
- **The model is chosen separately**, by an evaluation on our own data, and recorded in its own ADR.

## Alternatives considered

- **Ollama in a container:** Docker Desktop on Windows [passes GPUs to containers only on NVIDIA hardware](https://docs.docker.com/desktop/features/gpu/), so the model would run on the CPU, several times slower.
- **Docker Model Runner:** on Windows (amd64) its [GPU acceleration also requires NVIDIA](https://docs.docker.com/ai/model-runner/) (checked 2026-10-19).
- **Ollama with ROCm:** on Windows, Ollama's ROCm support covers Radeon RX 7000 series cards, not this GPU.
- **A hosted LLM API:** no local setup and stronger models, but a cost per token and posting texts leaving the machine.
- **Ollama listening on all interfaces**, so that scripts in WSL could reach it: this would expose the port to the local network.

## Consequences

- Ollama is installed and updated outside the repository, and Compose does not pin its version (0.40.5 at the time of writing).
- While WSL uses NAT networking, tools run directly in WSL cannot reach Ollama on the Windows loopback. They run in a container, or WSL switches to mirrored networking; to be settled before the extraction stage.
- 8 GB of VRAM fits one model file of up to about 6.5 GB at a time. Speed and quality per model are measured in the evaluation.
