# Mythos standalone offline intelligence

## Vision
Mythos is a **100% owner-controlled**, standalone local agent for coding, generative, creative, and ML/LLM work. After one optional offline-capable brain install, it must not need any remote server (xAI, cloud APIs, or public registries) to use its capabilities.

## Must
1. Inference stays on this machine: loopback Ollama and/or in-process GGUF; never `api.x.ai` or other remote LLM hosts.
2. `health` reports offline readiness: local provider, `bills_xai=false`, whether a GGUF brain exists on disk, whether a local runner is up, and `network_mode` (`airgap` | `local`).
3. Airgap mode refuses non-loopback LLM bases and remote model pulls; setup may still use Hugging Face git only when airgap is off and the brain is missing.
4. When a GGUF is on disk and `llama_cpp` (llama-cpp-python) is importable, Mythos can chat without the Ollama daemon.
5. An offline `educate` path records/teaches local improvements without calling remote services.
6. Identity text states owned standalone offline stance: coding + generative + creative + local LLM/ML, NO CHARGES.

## Must not
- Claim literal AGI or cloud Grok parity.
- Require XAI_API_KEY or any paid API.
- Download models while `MYTHOS_AIRGAP=1` / airgap mode.
- Break existing `chat` / `create` / `run` / `health` / provider refuse-xAI tests.

## Honest limit
Training a new foundation model from scratch is out of scope. "Neural network / LLM / ML" here means local inference + local tooling over open weights the owner keeps on disk.
