---
title: Customer Service Agent
emoji: 🎧
colorFrom: blue
colorTo: green
sdk: docker
app_port: 8501
app_file: app.py
pinned: false
---

# 🎧 Customer Service Agent
> **Live Demo** [Click Here](https://huggingface.co/spaces/khaledxd/customer-service-agent)
> **Built with** LangGraph · GPT-4o · MySQL · Qdrant · LlamaIndex · Streamlit

----

## What is this?

An AI-powered customer service agent that handles real customer requests automatically:

- **Track orders** → "What is the status of order 5?"
- **Check availability** → "Is MacBook Pro available in gray in Riyadh?"
- **Submit returns** → "I want to return order 8, it arrived damaged"
- **File complaints** → "I have a complaint about my laptop screen"
- **Answer FAQ questions** → "What is your return policy?"

Supports **Arabic and English** out of the box.

---

## How it works

```
Customer message
        ↓
   router_node        ← GPT-4o detects intent + extracts data
        ↓
┌──────────────────────────────────────────┐
│ order_status_node  → SQL lookup          │
│ availability_node  → SQL lookup          │
│ return_node        → SQL insert          │
│ complaint_node     → SQL insert          │
│ faq_node           → RAG over docs       │
└──────────────────────────────────────────┘
        ↓
  Professional response to customer
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| Agent framework | LangGraph | Controls intent routing between nodes |
| LLM | GPT-4o | Intent detection, data extraction, responses |
| Database | MySQL + SQLAlchemy | Orders, products, returns, complaints |
| FAQ search | LlamaIndex + Qdrant | RAG over policy documents |
| Embeddings | text-embedding-3-small | Vector search for FAQ |
| UI | Streamlit | Customer chat interface |
| Tool layer | Custom MCP registry | Unified interface for all services |

---

## Project Structure

```
customer-service-agent/
├── app.py                  # Streamlit UI
├── main.py                 # CLI testing mode
├── requirements.txt
├── Dockerfile
├── .env.example
│
├── data/
│   └── faqs/               # Upload FAQ / policy PDFs here
│
└── src/
    ├── graph/
    │   ├── state.py        # Agent session memory
    │   ├── nodes.py        # 6 node functions
    │   └── workflow.py     # LangGraph graph assembly
    │
    ├── db/
    │   ├── sql_client.py   # MySQL + safety guards
    │   └── vector_store.py # Qdrant FAQ search
    │
    └── tools/
        ├── mcp_tools.py    # 8 MCP tools
        └── custom_tools.py # Utility functions
```

---

## Running Locally

### 1. Clone
```bash
git clone https://github.com/YOUR_USERNAME/customer-service-agent.git
cd customer-service-agent
```

### 2. Install
```bash
pip install -r requirements.txt
```

### 3. Configure
```bash
cp .env.example .env
# Fill in your OpenAI key and MySQL credentials
```

### 4. Set up database
Run the SQL file in DBeaver or MySQL Workbench to create tables and insert fake data.

### 5. Start Qdrant
```bash
docker run -p 6333:6333 -v qdrant_storage:/qdrant/storage qdrant/qdrant
```

### 6. Run
```bash
# Streamlit UI.
streamlit run app.py

# Or CLI for quick testing
python main.py
```

---

## Example Questions

**Order tracking:**
- "What is the status of order 3?"
- "Show me my orders" *(requires customer ID)*

**Product availability:**
- "Is MacBook Pro available in Riyadh?"
- "Do you have iPhone 15 Pro in Titanium?"
- "What laptops are available in Jeddah?"

**Returns:**
- "I want to return order 8, it arrived damaged" *(requires customer ID)*

**Complaints:**
- "I have a complaint about order 3, the screen has scratches" *(requires customer ID)*

**FAQ:**
- "What is your return policy?"
- "How long does shipping take?"

**Arabic:**
- "ما هو حالة طلبي رقم 5؟"
- "هل يتوفر MacBook Pro باللون الرمادي في الرياض؟"
- "أريد إرجاع طلبي رقم 8"

---

## Author

Built by Khaled Abdulaziz · [LinkedIn](https://www.linkedin.com/in/khaled-abdulaziz/) · [Hugging Face](https://huggingface.co/khaledxd)
