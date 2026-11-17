# 🚀 AI / LLM Engineer Learning Roadmap

> A structured, self-directed path from CS graduate to AI / LLM Engineer.
> This is the public version of my learning plan — it tracks the skills I'm
> building, the resources I'm using, and what I take away at each stage.

## 📊 Progress Overview

| Phase | Focus | Status |
|-------|-------|--------|
| Phase 1 | ML & Deep Learning Foundations | 🟢 Complete |
| Phase 2 | LLM Fundamentals | 🟢 Complete |
| Phase 3 | RAG & Retrieval Systems | 🟡 In Progress |
| Phase 4 | AI Agents | ⚪ Planned |
| Phase 5 | Fine-tuning & Deployment | ⚪ Planned |

**Legend:** ⚪ Planned · 🟡 In Progress · 🟢 Complete

---

## 🎓 Phase 1 — ML & Deep Learning Foundations

**Goal:** Build a solid grounding in machine learning and deep learning fundamentals.

- Kaggle: Python, Pandas, Intro & Intermediate Machine Learning
- Kaggle: Intro to Deep Learning, Computer Vision
- Practical competitions: built and submitted CNNs from scratch and via transfer learning
- 3Blue1Brown — Neural Networks series
- Fast.ai — Practical Deep Learning (selected lessons)
- Andrej Karpathy — Micrograd, "Let's build GPT"
- "The Illustrated Transformer" (Jay Alammar)
- Hugging Face NLP Course (Chapters 1–3)
- Built a simple transformer classifier and used Hugging Face for text classification

**Takeaways:** Comfortable with the ML workflow end-to-end, the fundamentals of neural networks, and the transformer architecture at a conceptual and practical level.

---

## 📚 Phase 2 — LLM Fundamentals

**Goal:** Understand how LLMs work in practice and how to build reliable applications on top of them.

- Kaggle: Natural Language Processing
- Chip Huyen — "Building LLM Applications for Production" + *AI Engineering* (2025)
- Andrej Karpathy — State of GPT, Tokenization
- Prompt engineering guides (OpenAI, promptingguide.ai)
- Anthropic — AI Fluency, Claude 101
- Anthropic — Building with the Claude API *(in progress: agents and workflows section remaining)*
- DeepLearning.AI — ChatGPT Prompt Engineering, Building Systems with ChatGPT

**Practice:**
- Built a CLI chatbot with memory
- Implemented structured outputs and function calling
- **Project 1 — [PaAi](./01-paai-chatbot):** a production-minded Telegram chatbot

**Topics I can now reason about:** why models hallucinate, training-distribution gaps, context-window behavior, and how to measure whether an LLM system actually works.

---

## 🔍 Phase 3 — RAG & Retrieval Systems *(in progress)*

**Goal:** Build retrieval-augmented systems and learn to evaluate retrieval quality.

- Embeddings and semantic search (Sentence Transformers, ChromaDB)
- Chunking strategies, reranking, retrieval pipelines
- DeepLearning.AI — LangChain Chat with Your Data, Building Agentic RAG
- Model Context Protocol (MCP) fundamentals
- Evaluation with RAGAS and the LLM-as-judge pattern
- **Project 2 — [Semantic Search Engine](https://github.com/ppimpao/semantic-search-engine)** ✅ — dense retrieval over arXiv astro-ph abstracts, with an evaluation harness (Hit@1 0.93 vs 0.80)
- **Project 3 — [Space Document RAG System](./03-space-rag)**

---

## 🤖 Phase 4 — AI Agents *(planned)*

**Goal:** Build agentic systems with tool use, state management, and observability.

- ReAct pattern, tools, agent memory
- LangGraph for state machines and control flow
- Observability and tracing (LangSmith)
- Multi-agent orchestration (CrewAI, AutoGen, Deep Agents)
- **Project 4 — [Space Data Research Agent](./04-space-agent)**
- **Project 5 — [Multi-Agent Team](./05-multi-agent)**

---

## 🎯 Phase 5 — Fine-tuning & Deployment *(planned)*

**Goal:** Understand fine-tuning as a design decision and ship a complete application.

- Fine-tuning vs. RAG vs. prompting — when and why
- LoRA / PEFT, custom datasets, evaluation
- MLOps basics: experiment tracking (W&B), containerization (Docker)
- Deployment with FastAPI, monitoring, and logging
- **Project 6 — [Fine-tuned Model](./06-fine-tuned-model)** + a space-adjacent capstone

---

## 📁 Portfolio Projects

| # | Project | Skills | Status |
|---|---------|--------|--------|
| 01 | [PaAi — Personal Assistant AI](./01-paai-chatbot) | LLM APIs, memory, FastAPI, evaluation | ✅ Complete |
| 02 | [Semantic Search Engine](https://github.com/ppimpao/semantic-search-engine) | Dense retrieval, embeddings, retrieval evaluation | ✅ Complete |
| 03 | [Space Document RAG System](./03-space-rag) | Embeddings, vector DBs, retrieval, RAGAS | ⚪ Planned |
| 04 | [Space Data Research Agent](./04-space-agent) | LangGraph, tool use, agents | ⚪ Planned |
| 05 | [Multi-Agent Team](./05-multi-agent) | Orchestration, role design | ⚪ Planned |
| 06 | [Fine-tuned Model](./06-fine-tuned-model) | LoRA, training, evaluation, deployment | ⚪ Planned |

---

## 🧭 Guiding principles

- **Fundamentals before frameworks** — understand the mechanism, then reach for the tool.
- **Measure, don't assume** — every portfolio project includes an evaluation section.
- **System design thinking** — reason about latency, cost, reliability, and tradeoffs, not just features.
- **Domain focus** — point the work at space and geospatial AI, the field I want to work in.
