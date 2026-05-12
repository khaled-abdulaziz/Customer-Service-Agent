# ==============================================================
# mcp_tools.py — MCP Tool Registry
# ==============================================================

import os
from typing import Any

from dotenv import load_dotenv
from openai import OpenAI as _OpenAI

from src.db.sql_client import run_query, run_action
from src.db.vector_store import get_query_engine

load_dotenv()

# ==============================================================
# OpenAI client
# ==============================================================

_openai_client = _OpenAI(
    api_key=os.getenv("OPENAI_API_KEY", "")
)

OPENAI_MODEL = os.getenv(
    "OPENAI_MODEL",
    "gpt-4o"
)

# ==============================================================
# Tool: ask_llm
# ==============================================================

def ask_llm(
    system_prompt: str,
    user_message: str,
    temperature: float = 0.1
) -> dict[str, Any]:

    try:

        resp = _openai_client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[
                {
                    "role": "system",
                    "content": system_prompt
                },
                {
                    "role": "user",
                    "content": user_message
                },
            ],
            temperature=temperature,
        )

        content = (
            resp.choices[0]
            .message
            .content
        )

        if not content:

            return {
                "response": "",
                "model": OPENAI_MODEL,
                "success": False,
            }

        return {
            "response": content.strip(),
            "model": OPENAI_MODEL,
            "success": True,
        }

    except Exception as e:

        return {
            "response": f"❌ LLM call failed: {str(e)}",
            "model": OPENAI_MODEL,
            "success": False,
        }

# ==============================================================
# Tool: search_faqs
# ==============================================================

def search_faqs(
    query: str,
    top_k: int = 4
) -> dict[str, Any]:

    try:

        engine = get_query_engine(top_k=top_k)

        response = engine.query(query)

        answer_text = str(response).strip()

        
        try:

            nodes = response.source_nodes

            source_texts = [
                n.node.text.strip()
                for n in nodes
                if getattr(n.node, "text", "").strip()
            ]

        except Exception:

            source_texts = []

        
        bad_answers = {
            "",
            "none",
            "null",
            "empty response",
            "no response",
        }

        if (
            answer_text.lower().strip() in bad_answers
            or len(answer_text.strip()) < 5
        ):

            if source_texts:

                combined = "\n\n".join(
                    source_texts[:2]
                )

                fallback_prompt = f"""
The customer asked:

{query}

Use ONLY this policy information to answer clearly:

{combined}

Answer in the same language as the customer.
"""

                llm_result = ask_llm(
                    "You are a professional customer support agent.",
                    fallback_prompt,
                    temperature=0.1,
                )

                if llm_result["success"]:

                    answer_text = llm_result["response"]

                else:

                    answer_text = combined[:1000]

            else:

                return {
                    "answer": "",
                    "source_texts": [],
                    "success": False,
                }

        return {
            "answer": answer_text,
            "source_texts": source_texts,
            "success": True,
        }

    except Exception as e:

        return {
            "answer": f"❌ FAQ search failed: {str(e)}",
            "source_texts": [],
            "success": False,
        }

# ==============================================================
# Tool: get_order_status
# ==============================================================

def get_order_status(order_id: int) -> dict[str, Any]:

    query = f"""
        SELECT
            o.order_id,
            o.status AS order_status,
            o.order_date,
            o.total_price,
            o.city,
            p.product_name,
            p.brand,
            c.full_name AS customer_name
        FROM orders o
        JOIN products p ON o.product_id = p.product_id
        JOIN customers c ON o.customer_id = c.customer_id
        WHERE o.order_id = {order_id}
        LIMIT 1
    """

    result = run_query(query)

    if isinstance(result, str):

        return {
            "rows": [],
            "success": False,
            "message": result
        }

    if not result:

        return {
            "rows": [],
            "success": False,
            "message": f"No order found with ID {order_id}"
        }

    return {
        "rows": result,
        "success": True,
        "message": "Order found"
    }

# ==============================================================
# Tool: get_product_info
# ==============================================================

def get_product_info(
    product_name: str = None,
    color: str = None,
    city: str = None,
    product_id: int = None,
) -> dict[str, Any]:

    conditions = []

    if product_id:
        conditions.append(f"product_id = {product_id}")

    if product_name:
        safe_name = product_name.replace("'", "''")
        conditions.append(
            f"product_name LIKE '%{safe_name}%'"
        )

    if color:
        safe_color = color.replace("'", "''")
        conditions.append(
            f"color LIKE '%{safe_color}%'"
        )

    if city:
        safe_city = city.replace("'", "''")
        conditions.append(
            f"city_available LIKE '%{safe_city}%'"
        )

    where = (
        f"WHERE {' AND '.join(conditions)}"
        if conditions else ""
    )

    query = f"""
        SELECT
            product_id,
            product_name,
            brand,
            category,
            color,
            price,
            stock_quantity,
            city_available,
            status
        FROM products
        {where}
        LIMIT 10
    """

    result = run_query(query)

    if isinstance(result, str):

        return {
            "rows": [],
            "success": False,
            "message": result
        }

    if not result:

        return {
            "rows": [],
            "success": False,
            "message": "No products found"
        }

    return {
        "rows": result,
        "success": True,
        "message": f"Found {len(result)} products"
    }

# ==============================================================
# Tool: create_return
# ==============================================================

def create_return(
    order_id: int,
    customer_id: int,
    reason: str
) -> dict[str, Any]:

    safe_reason = reason.replace("'", "''")

    query = (
        "INSERT INTO return_requests "
        "(order_id, customer_id, reason, status) "
        "VALUES (:order_id, :customer_id, :reason, 'pending')"
    )

    result = run_action(
        query,
        {
            "order_id": order_id,
            "customer_id": customer_id,
            "reason": safe_reason,
        }
    )

    return result

# ==============================================================
# Tool: create_complaint
# ==============================================================

def create_complaint(
    customer_id: int,
    complaint_text: str,
    order_id: int = None,
    product_id: int = None,
) -> dict[str, Any]:

    query = (
        "INSERT INTO complaints "
        "(customer_id, order_id, product_id, complaint_text, status) "
        "VALUES "
        "(:customer_id, :order_id, :product_id, :complaint_text, 'open')"
    )

    result = run_action(
        query,
        {
            "customer_id": customer_id,
            "order_id": order_id,
            "product_id": product_id,
            "complaint_text": complaint_text,
        }
    )

    return result

# ==============================================================
# Tool: get_customer_orders
# ==============================================================

def get_customer_orders(customer_id: int) -> dict[str, Any]:

    query = f"""
        SELECT
            o.order_id,
            o.status AS order_status,
            o.order_date,
            o.total_price,
            o.city,
            p.product_name,
            p.brand
        FROM orders o
        JOIN products p
            ON o.product_id = p.product_id
        WHERE o.customer_id = {customer_id}
        ORDER BY o.order_date DESC
        LIMIT 20
    """

    result = run_query(query)

    if isinstance(result, str):

        return {
            "rows": [],
            "success": False,
            "message": result
        }

    if not result:

        return {
            "rows": [],
            "success": False,
            "message": "No orders found"
        }

    return {
        "rows": result,
        "success": True,
        "message": f"Found {len(result)} orders"
    }

# ==============================================================
# Tool: get_schema_info
# ==============================================================

def get_schema_info() -> dict[str, Any]:

    return {
        "schema": "Customer service database schema loaded.",
        "success": True,
    }

# ==============================================================
# Tool Registry
# ==============================================================

TOOL_REGISTRY: dict[str, callable] = {
    "ask_llm": ask_llm,
    "search_faqs": search_faqs,
    "get_order_status": get_order_status,
    "get_product_info": get_product_info,
    "create_return": create_return,
    "create_complaint": create_complaint,
    "get_customer_orders": get_customer_orders,
    "get_schema_info": get_schema_info,
}

# ==============================================================
# Unified Tool Caller
# ==============================================================

def call_tool(name: str, **kwargs) -> dict[str, Any]:

    if name not in TOOL_REGISTRY:

        available = list(
            TOOL_REGISTRY.keys()
        )

        raise ValueError(
            f"Unknown tool '{name}'. Available: {available}"
        )

    print(f"🔧 MCP tool called: {name}")

    return TOOL_REGISTRY[name](**kwargs)