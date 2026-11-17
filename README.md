# AI Engineer Portfolio — Pedro Pimpão

> **AI Engineer** building LLM applications, retrieval systems and evals. Target domain: **space and geospatial AI**.

This repository is a living portfolio. Each project is a self-contained, runnable demonstration of a core skill in modern AI engineering — built to be understood, tested, and measured, not just to run. Projects are numbered in the order I build them, following my [learning roadmap](./ROADMAP.md).

---

## Projects

| # | Project | What it demonstrates | Status |
|---|---------|----------------------|--------|
| 01 | **[PaAi — Personal Assistant AI](./01-paai-chatbot)** | LLM API integration, persistent token-aware memory, pluggable provider backend, FastAPI service design, evaluation | ✅ Complete |
| 02 | **[Semantic Search Engine](https://github.com/ppimpao/semantic-search-engine)** | Space Domain — dense retrieval over arXiv astro-ph abstracts with an evaluation harness that overturned my own model hypothesis (0.93 vs 0.80 Hit@1) | ✅ Complete |
| 03 | **[Space Document RAG System](./03-space-rag)** | Embeddings, vector search, retrieval pipelines, RAG evaluation (RAGAS) | ⚪ Planned |
| 04 | **[Space Data Research Agent](./04-space-agent)** | LangGraph, tool use, agent state management, human-in-the-loop | ⚪ Planned |
| 05 | **[Multi-Agent Team](./05-multi-agent)** | Multi-agent orchestration, role design, task synthesis | ⚪ Planned |
| 06 | **[Fine-tuned Model](./06-fine-tuned-model)** | LoRA fine-tuning, dataset creation, evaluation, deployment | ⚪ Planned |

**Legend:** ✅ Complete · 🟡 In Progress · ⚪ Planned

---

## Featured: PaAi — Personal Assistant AI

A Telegram chatbot with persistent, token-aware conversation memory and a pluggable LLM backend (Claude by default, Ollama for local runs), built on a decoupled FastAPI service.

- **Text and voice notes.** It answers by text or by voice note. ElevenLabs does speech-to-text and text-to-speech; for long answers, Claude Haiku writes a short spoken summary and the full answer follows as text.
- **Tested.** 93 unit and API tests that need no API key or network.
- **Evaluated against the live models.** Text evals 5/5, voice evals 6/6.
- **Measured.** Latency per step and cost per voice turn (≈3 s for a short answer, ≈21 s for a long one; ≈160 ElevenLabs credits per turn).

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

I build these projects in sequence, following the [roadmap](./ROADMAP.md). Each one is a working system with its own measurements, and each README answers three questions: what problem it solves, which architectural decisions I made and why, and how I measured its quality. If I can't measure it, I don't claim it.

My target domain is **space and geospatial AI** — Earth observation, satellite data, and environmental monitoring — and later projects increasingly point at that field.

---

## License

All projects in this repository are released under the [MIT License](./LICENSE) — feel free to learn from, reuse, and build on this work.
