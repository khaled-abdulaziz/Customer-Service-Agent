# ==============================================================
# nodes.py — LangGraph Node Functions
# ==============================================================

import json
from .state import AgentState
from src.tools.mcp_tools import (
    ask_llm,
    search_faqs,
    get_order_status,
    get_product_info,
    create_return,
    create_complaint,
    get_customer_orders,
    get_schema_info,
)
from src.tools.custom_tools import (
    format_order_table,
    format_product_table,
    detect_language,
    extract_number_from_text,
    truncate_text,
)


# ==============================================================
# Node 1: Router
# ==============================================================

def router_node(state: AgentState) -> AgentState:
    """
    Reads the customer message and decides:
      1. language      → detect and lock in for the whole conversation
      2. intent        → what does the customer want?
      3. extracted_data → what structured data is in the message?

    LANGUAGE DETECTION STRATEGY:
      - Only update the language if the message contains real letters
      - A message like "3" or "yes" has no language → keep existing
      - Once set, language never changes mid-conversation
      - This fixes the bug where replying with just "3" switched to Arabic

    MULTI-TURN SUPPORT:
      If pending_action is set, the router checks if the new message
      is a continuation and merges the new info without calling the LLM.

    Intent options:
        "order_status"  → customer wants to track an order
        "availability"  → customer wants to check if product is in stock
        "return"        → customer wants to return something
        "complaint"     → customer wants to file a complaint
        "faq"           → general question about policy/product
        "unknown"       → can't determine — fallback to faq
    """
    message        = state["message"]
    pending_action = state.get("pending_action")
    conv_context   = state.get("conversation_context") or {}

    # ------------------------------------------------------------------
    # LANGUAGE
    # ------------------------------------------------------------------
    current_language = state.get("language", "")
    has_real_words   = any(c.isalpha() for c in message)

    if has_real_words:
        
        detected_language = detect_language(message)
        state["language"]  = detected_language
    elif not current_language:
        
        state["language"] = "en"
    

    lang = state["language"]   

    # ------------------------------------------------------------------
    # MULTI-TURN: if we are mid-conversation, merge new info into context
    # ------------------------------------------------------------------
    if pending_action:
        number_in_msg = extract_number_from_text(message)
        waiting_for   = conv_context.get("step", "")

        if waiting_for == "waiting_for_order_id" and number_in_msg:
           
            conv_context["order_id"] = number_in_msg
            conv_context["step"]     = "ready"
            state["intent"]               = pending_action
            state["extracted_data"]       = dict(conv_context)
            state["conversation_context"] = conv_context
            state["pending_action"]       = None
            return state

        elif waiting_for == "waiting_for_reason":
            
            conv_context["reason"] = message.strip()
            conv_context["step"]   = "ready"
            state["intent"]               = pending_action
            state["extracted_data"]       = dict(conv_context)
            state["conversation_context"] = conv_context
            state["pending_action"]       = None
            return state

        elif waiting_for == "waiting_for_product_name":
            
            conv_context["product_name"] = message.strip()
            conv_context["step"]         = "ready"
            state["intent"]               = pending_action
            state["extracted_data"]       = dict(conv_context)
            state["conversation_context"] = conv_context
            state["pending_action"]       = None
            return state

        elif waiting_for == "waiting_for_complaint_text":
            
            conv_context["complaint_text"] = message.strip()
            conv_context["step"]           = "ready"
            state["intent"]               = pending_action
            state["extracted_data"]       = dict(conv_context)
            state["conversation_context"] = conv_context
            state["pending_action"]       = None
            return state

    # ------------------------------------------------------------------
    # FRESH TURN: call GPT-4o to detect intent + extract data
    # ------------------------------------------------------------------
    system_prompt = """You are an intent detection system for a customer service chatbot.

Analyze the customer message and return a JSON object with exactly these two keys:

1. "intent" — one of these exact values:
   - "order_status"  → customer wants to track or check an order (even vaguely)
   - "availability"  → customer wants to know if a product is in stock
   - "return"        → customer wants to return a product
   - "complaint"     → customer wants to file a complaint
   - "faq"           → general question about policy, shipping, warranty, or product info
   - "unknown"       → cannot determine

2. "extracted_data" — a dict of any structured data found in the message:
   - order_id      (int)   : if a number that looks like an order ID is mentioned
   - product_name  (str)   : if a product name or brand is mentioned
   - product_id    (int)   : if a product ID number is mentioned
   - color         (str)   : if a color is mentioned
   - city          (str)   : if a city is mentioned
   - reason        (str)   : if a return reason is mentioned
   - complaint_text (str)  : if complaint details are mentioned
   - customer_id   (int)   : if a customer ID is mentioned

Rules:
- Return ONLY valid JSON — no explanation, no markdown, no backticks
- Works for Arabic and English messages
- If data is not mentioned, do not include the key"""

    result = ask_llm(system_prompt, message)

    if not result["success"]:
        state["intent"]               = "faq"
        state["extracted_data"]       = {}
        state["llm_used"]             = "error"
        state["pending_action"]       = None
        state["conversation_context"] = {}
        return state

    try:
        parsed         = json.loads(result["response"])
        intent         = parsed.get("intent", "unknown")
        extracted_data = parsed.get("extracted_data", {})
    except json.JSONDecodeError:
        intent         = "faq"
        extracted_data = {}

    valid_intents = {"order_status", "availability", "return",
                     "complaint", "faq", "unknown"}
    if intent not in valid_intents:
        intent = "faq"

    state["intent"]               = intent
    state["extracted_data"]       = extracted_data
    state["llm_used"]             = result["model"]
    state["pending_action"]       = None
    state["conversation_context"] = {}

    print(f"🧭 Router → intent='{intent}' | lang='{lang}' | data={extracted_data}")
    return state


# ==============================================================
# Node 2: Order Status
# ==============================================================

def order_status_node(state: AgentState) -> AgentState:
    """
    Looks up an order by ID and returns its current status.

    LANGUAGE: reads state["language"] — never calls detect_language()
    This ensures the response language matches the conversation language
    even when the customer's last message was just a number.

    Flow:
        Extract order_id → if missing ask for it (in correct language)
        → call get_order_status()
        → format with GPT-4o in the correct language
    """
    message        = state["message"]
    extracted_data = state.get("extracted_data", {})
    lang           = state.get("language", "en")   # read from state — not detected here

    order_id = extracted_data.get("order_id")
    if not order_id:
        order_id = extract_number_from_text(message)

    if not order_id:
        
        if lang == "ar":
            ask_msg = "بالتأكيد! أقدر أساعدك في تتبع طلبك. ما هو رقم الطلب الخاص بك؟"
        else:
            ask_msg = "Of course! I'd be happy to check your order. Could you please share your order ID number?"

        state["answer"]               = ask_msg
        state["action_taken"]         = "not_found"
        state["sql_result"]           = []
        state["pending_action"]       = "order_status"
        state["conversation_context"] = {"step": "waiting_for_order_id"}
        return state

    result = get_order_status(order_id)

    if not result["success"]:
        if lang == "ar":
            state["answer"] = f"ما قدرت أحصل على الطلب رقم #{order_id}. تأكد من رقم الطلب وحاول مرة ثانية."
        else:
            state["answer"] = f"I couldn't find order #{order_id}. Please double-check the order ID and try again."
        state["action_taken"]         = "not_found"
        state["sql_result"]           = []
        state["pending_action"]       = None
        state["conversation_context"] = {}
        return state

    order_data = result["rows"][0]

    
    lang_instruction = "Arabic" if lang == "ar" else "English"
    format_prompt = f"""The customer asked: "{message}"

Here is the order information from the database:
{order_data}

Write a clear, professional, friendly response in {lang_instruction}.
Include: order status, product name, order date, and city.
Be concise and helpful. If the status is "shipped", add an encouraging note."""

    response = ask_llm(
        
        f"You are a professional customer service agent. Always respond in {lang_instruction}. "
        f"Never use placeholder names like [Your Name] in your signature — "
        f"sign off as 'Customer Service Team' only.",
        format_prompt
    )

    state["answer"]               = response["response"] if response["success"] else str(order_data)
    state["action_taken"]         = "looked_up"
    state["sql_result"]           = result["rows"]
    state["pending_action"]       = None
    state["conversation_context"] = {}
    return state


# ==============================================================
# Node 3: Availability
# ==============================================================

def availability_node(state: AgentState) -> AgentState:
    """
    Checks if a product is available in a specific color or city.

    LANGUAGE: reads state["language"] — never calls detect_language()
    """
    message        = state["message"]
    extracted_data = state.get("extracted_data", {})
    lang           = state.get("language", "en")   # read from state

    product_name = extracted_data.get("product_name")
    product_id   = extracted_data.get("product_id")
    color        = extracted_data.get("color")
    city         = extracted_data.get("city")

    if not product_name and not product_id:
        if lang == "ar":
            ask_msg = "بكل سرور! أي منتج تريد الاستفسار عنه؟ أذكر لي اسم المنتج أو الماركة."
        else:
            ask_msg = "Sure! Which product are you looking for? Please tell me the product name or brand."

        state["answer"]               = ask_msg
        state["action_taken"]         = "not_found"
        state["sql_result"]           = []
        state["pending_action"]       = "availability"
        state["conversation_context"] = {"step": "waiting_for_product_name"}
        return state

    result = get_product_info(
        product_name=product_name,
        color=color,
        city=city,
        product_id=product_id,
    )

    if not result["success"]:
        if lang == "ar":
            state["answer"] = "ما لقينا منتجات تطابق طلبك. جرب اسم ماركة أو منتج مختلف."
        else:
            state["answer"] = "I couldn't find any products matching your request. Please try a different product name or brand."
        state["action_taken"]         = "not_found"
        state["sql_result"]           = []
        state["pending_action"]       = None
        state["conversation_context"] = {}
        return state

    formatted        = format_product_table(result["rows"])
    lang_instruction = "Arabic" if lang == "ar" else "English"

    format_prompt = f"""The customer asked: "{message}"

Here are the matching products from our inventory:
{formatted}

Write a clear, professional, friendly response in {lang_instruction}.
- Include availability status, price, color, and city for each product.
- If the exact color or city is unavailable, mention what IS available.
- Be helpful like a knowledgeable sales assistant."""

    response = ask_llm(
        
        f"You are a professional customer service agent. Always respond in {lang_instruction}. "
        f"Never use placeholder names like [Your Name] in your signature — "
        f"sign off as 'Customer Service Team' only.",
        format_prompt
    )

    state["answer"]               = response["response"] if response["success"] else formatted
    state["action_taken"]         = "looked_up"
    state["sql_result"]           = result["rows"]
    state["pending_action"]       = None
    state["conversation_context"] = {}
    return state


# ==============================================================
# Node 4: Return
# ==============================================================

def return_node(state: AgentState) -> AgentState:
    """
    Creates a return request for the customer's order.

    LANGUAGE: reads state["language"] — never calls detect_language()

    Natural flow — asks for order ID then reason, then submits.
    customer_id is optional; admin verifies ownership when processing.
    """
    message        = state["message"]
    extracted_data = state.get("extracted_data", {})
    conv_context   = state.get("conversation_context") or {}
    lang           = state.get("language", "en")   # read from state

    order_id    = conv_context.get("order_id") or extracted_data.get("order_id")
    reason      = conv_context.get("reason")   or extracted_data.get("reason")
    customer_id = extracted_data.get("customer_id") or state.get("customer_id")

    if not order_id:
        order_id = extract_number_from_text(message)

    
    if not order_id:
        if lang == "ar":
            ask_msg = "بكل سرور! سأساعدك في إرجاع طلبك. ما هو رقم الطلب الذي تريد إرجاعه؟"
        else:
            ask_msg = "I'd be happy to help you with a return! What is the order ID you'd like to return?"

        state["answer"]               = ask_msg
        state["action_taken"]         = "not_found"
        state["sql_result"]           = []
        state["pending_action"]       = "return"
        state["conversation_context"] = {"step": "waiting_for_order_id"}
        return state

    
    if not reason:
        if lang == "ar":
            ask_msg = f"شكراً! ما هو سبب إرجاع الطلب رقم #{order_id}؟"
        else:
            ask_msg = (
                f"Got it! What is the reason for returning order #{order_id}? "
                f"(e.g. arrived damaged, wrong item, doesn't match description)"
            )

        state["answer"]               = ask_msg
        state["action_taken"]         = "not_found"
        state["sql_result"]           = []
        state["pending_action"]       = "return"
        state["conversation_context"] = {"step": "waiting_for_reason", "order_id": order_id}
        return state

    
    if customer_id:
        result = create_return(
            order_id=int(order_id),
            customer_id=int(customer_id),
            reason=truncate_text(reason, 500),
        )
    else:
        
        from src.db.sql_client import run_action
        result = run_action(
            "INSERT INTO return_requests (order_id, reason, status) "
            "VALUES (:order_id, :reason, 'pending')",
            {"order_id": int(order_id), "reason": truncate_text(reason, 500)}
        )

    
    if result.get("success"):
        ref_id = result.get("inserted_id", "N/A")
        if lang == "ar":
            state["answer"] = (
                f"✅ تم تسجيل طلب الإرجاع بنجاح!\n\n"
                f"رقم مرجعي: #{ref_id}\n"
                f"رقم الطلب: #{order_id}\n"
                f"السبب: {reason}\n\n"
                f"سيتواصل معك أحد مسؤولينا في أقرب وقت ممكن. احتفظ بالرقم المرجعي للمتابعة."
            )
        else:
            state["answer"] = (
                f"✅ Your return request has been submitted successfully!\n\n"
                f"Reference Number: #{ref_id}\n"
                f"Order ID: #{order_id}\n"
                f"Reason: {reason}\n\n"
                f"Our team will review your request and contact you as soon as possible. "
                f"Please keep your reference number for follow-up."
            )
        state["action_taken"] = "inserted"
    else:
        if lang == "ar":
            state["answer"] = (
                f"عذراً، لم نتمكن من تسجيل طلب الإرجاع للطلب #{order_id}. "
                f"يرجى التواصل مع فريق الدعم مباشرة."
            )
        else:
            state["answer"] = (
                f"I wasn't able to submit the return request for order #{order_id}. "
                f"Please contact our support team directly."
            )
        state["action_taken"] = "error"

    state["sql_result"]           = []
    state["pending_action"]       = None
    state["conversation_context"] = {}
    return state


# ==============================================================
# Node 5: Complaint
# ==============================================================

def complaint_node(state: AgentState) -> AgentState:
    """
    Logs a customer complaint about a product or order.

    LANGUAGE: reads state["language"] — never calls detect_language()

    Natural flow — asks for details if vague, then submits.
    customer_id is optional.
    """
    message        = state["message"]
    extracted_data = state.get("extracted_data", {})
    conv_context   = state.get("conversation_context") or {}
    lang           = state.get("language", "en")   # read from state

    customer_id    = extracted_data.get("customer_id") or state.get("customer_id")
    complaint_text = (
        conv_context.get("complaint_text")
        or extracted_data.get("complaint_text")
    )
    order_id   = conv_context.get("order_id")   or extracted_data.get("order_id")
    product_id = conv_context.get("product_id") or extracted_data.get("product_id")

    
    vague_phrases = {
        "i have a complaint", "i have a problem", "complaint", "problem",
        "عندي مشكلة", "عندي شكوى", "ابغا اشتكي", "اريد تقديم شكوى"
    }
    if not complaint_text and message.strip().lower() not in vague_phrases:
        complaint_text = message.strip()

    # STEP 1: Need complaint details
    if not complaint_text or len(complaint_text.strip()) < 10:
        if lang == "ar":
            ask_msg = "أنا آسف على ما واجهته. ممكن تخبرني بتفاصيل المشكلة حتى أتمكن من تسجيل شكواك بشكل صحيح؟"
        else:
            ask_msg = (
                "I'm sorry to hear you're having an issue. "
                "Could you please describe the problem in detail so I can log your complaint accurately?"
            )
        state["answer"]               = ask_msg
        state["action_taken"]         = "not_found"
        state["sql_result"]           = []
        state["pending_action"]       = "complaint"
        state["conversation_context"] = {
            "step":       "waiting_for_complaint_text",
            "order_id":   order_id,
            "product_id": product_id,
        }
        return state

    
    if customer_id:
        result = create_complaint(
            customer_id=int(customer_id),
            complaint_text=truncate_text(complaint_text, 500),
            order_id=int(order_id) if order_id else None,
            product_id=int(product_id) if product_id else None,
        )
    else:
        from src.db.sql_client import run_action
        if order_id and product_id:
            query  = ("INSERT INTO complaints (order_id, product_id, complaint_text, status) "
                      "VALUES (:order_id, :product_id, :complaint_text, 'open')")
            params = {"order_id": int(order_id), "product_id": int(product_id),
                      "complaint_text": truncate_text(complaint_text, 500)}
        elif order_id:
            query  = ("INSERT INTO complaints (order_id, complaint_text, status) "
                      "VALUES (:order_id, :complaint_text, 'open')")
            params = {"order_id": int(order_id),
                      "complaint_text": truncate_text(complaint_text, 500)}
        else:
            query  = ("INSERT INTO complaints (complaint_text, status) "
                      "VALUES (:complaint_text, 'open')")
            params = {"complaint_text": truncate_text(complaint_text, 500)}
        result = run_action(query, params)

    
    if result.get("success"):
        ref_id = result.get("inserted_id", "N/A")
        if lang == "ar":
            state["answer"] = (
                f"شكراً لتواصلك معنا. نعتذر على هذه التجربة.\n\n"
                f"✅ تم تسجيل شكواك بنجاح!\n"
                f"رقم مرجعي: #{ref_id}\n\n"
                f"سيتواصل معك أحد مسؤولينا خلال 24-48 ساعة لإيجاد حل مناسب."
            )
        else:
            state["answer"] = (
                f"Thank you for letting us know. We sincerely apologize for the inconvenience.\n\n"
                f"✅ Your complaint has been logged successfully!\n"
                f"Reference Number: #{ref_id}\n\n"
                f"A member of our team will follow up with you within 24-48 hours."
            )
        state["action_taken"] = "inserted"
    else:
        if lang == "ar":
            state["answer"] = (
                "عذراً، لم نتمكن من تسجيل شكواك في هذه اللحظة. "
                "يرجى التواصل مع فريق الدعم مباشرة."
            )
        else:
            state["answer"] = (
                "I wasn't able to log your complaint at this time. "
                "Please contact our support team directly."
            )
        state["action_taken"] = "error"

    state["sql_result"]           = []
    state["pending_action"]       = None
    state["conversation_context"] = {}
    return state


# ==============================================================
# Node 6: FAQ
# ==============================================================

def faq_node(state: AgentState) -> AgentState:
    """
    Answers general questions from FAQ/policy documents using RAG.

    LANGUAGE: reads state["language"] — never calls detect_language()

    Used for: return policy, warranty, shipping, product info.
    """
    message = state["message"]
    lang    = state.get("language", "en")   # read from state

    result = search_faqs(message, top_k=4)

    if not result["success"]:
        if lang == "ar":
            state["answer"] = (
                "عذراً، ما قدرت أحصل على إجابة لسؤالك. "
                "يرجى التواصل مع فريق الدعم على support@techstore-arabia.com."
            )
        else:
            state["answer"] = (
                "I'm sorry, I couldn't find specific information about your question. "
                "Please contact our support team at support@techstore-arabia.com."
            )
        state["action_taken"]         = "error"
        state["sql_result"]           = []
        state["pending_action"]       = None
        state["conversation_context"] = {}
        return state

    state["answer"]               = result["answer"]
    state["action_taken"]         = "looked_up"
    state["sql_result"]           = []
    state["pending_action"]       = None
    state["conversation_context"] = {}
    return state