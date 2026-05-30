# AI Engineer Portfolio — Pedro Pimpão

> Computer Science graduate making a deliberate, documented transition from software developer to **AI / LLM Engineer**, with a focus on **space and geospatial AI**.

This repository is a living portfolio. Each project is a self-contained, runnable demonstration of a core skill in modern AI engineering — built to be understood, tested, and measured, not just to run. Projects are numbered in the order I build them, following my [learning roadmap](./ROADMAP.md).

---

## Projects

| # | Project | What it demonstrates | Status |
|---|---------|----------------------|--------|
| 01 | **[PaAi — Personal Assistant AI](./01-paai-chatbot)** | LLM API integration, persistent token-aware memory, pluggable provider backend, FastAPI service design, evaluation | ✅ Complete |
| 02 | **[Space Document RAG System](./02-space-rag)** | Embeddings, vector search, retrieval pipelines, RAG evaluation (RAGAS) | ⚪ Planned |
| 03 | **[Space Data Research Agent](./03-space-agent)** | LangGraph, tool use, agent state management, human-in-the-loop | ⚪ Planned |
| 04 | **[Multi-Agent Team](./04-multi-agent)** | Multi-agent orchestration, role design, task synthesis | ⚪ Planned |
| 05 | **[Fine-tuned Model](./05-fine-tuned-model)** | LoRA fine-tuning, dataset creation, evaluation, deployment | ⚪ Planned |

**Legend:** ✅ Complete · 🟡 In Progress · ⚪ Planned

---

## Featured: PaAi — Personal Assistant AI

A Telegram chatbot with persistent, token-aware conversation memory and a pluggable LLM backend (Claude by default, Ollama for local runs), built on a decoupled FastAPI service. It includes a unit-tested memory layer and a behavioral evaluation suite that runs against the live model.

→ **[Read the full project README](./01-paai-chatbot)**

---

## Skills demonstrated across this portfolio

- **LLM application engineering** — API integration, prompt design, structured configuration, error handling
- **Memory & state** — token-aware context windows, persistence with SQLite
- **System design** — decoupled services, pluggable provider interfaces, separation of transport and logic
- **Retrieval (RAG)** — embeddings, vector stores, retrieval evaluation *(in progress)*
- **Agents** — tool use, state machines, multi-agent orchestration *(planned)*
- **Evaluation** — behavioral test suites, measuring system quality, not just functionality
- **Engineering practice** — testing, documentation, reproducible environments, version control

---

## About this journey

I'm building these projects in sequence as part of a structured transition into AI engineering, documented openly in the [roadmap](./ROADMAP.md). The emphasis throughout is on **honest, well-measured demonstrations of fundamentals** — each project answers three questions in its README: what problem it solves, what architectural decisions were made and why, and how its quality was measured.

My target domain is **space and geospatial AI** — Earth observation, satellite data, and environmental monitoring — and later projects increasingly point at that field.

---

## License

All projects in this repository are released under the [MIT License](./LICENSE) — feel free to learn from, reuse, and build on this work.
