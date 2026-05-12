# ==============================================================
# app.py — Streamlit Customer Service UI
# ==============================================================

import streamlit as st
import os
import html

from src.graph.workflow import run_agent

# ==============================================================
# Page config
# ==============================================================

st.set_page_config(
    page_title="Customer Service Agent",
    page_icon="🎧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ==============================================================
# Custom CSS
# ==============================================================

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] {
        font-family: 'IBM Plex Sans', sans-serif;
    }

    #MainMenu, footer, header {
        visibility: hidden;
    }

    /* ── Hide the << sidebar collapse/expand button — every known selector ── */
    [data-testid="collapsedControl"],
    [data-testid="baseButton-header"],
    button[kind="header"],
    .st-emotion-cache-1aw8i8e,
    section[data-testid="stSidebar"] > div > div > button,
    /* Streamlit 1.30+ wraps it in an extra div */
    [data-testid="stSidebarCollapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    /* Catch-all: any button that is a direct child of the sidebar header area */
    [data-testid="stSidebar"] button[data-testid],
    [data-testid="stSidebar"] > div:first-child > div:first-child > button {
        display: none !important;
        visibility: hidden !important;
        pointer-events: none !important;
        width: 0 !important;
        height: 0 !important;
        min-width: 0 !important;
        min-height: 0 !important;
        overflow: hidden !important;
        opacity: 0 !important;
        position: absolute !important;
        left: -9999px !important;
    }

    [data-testid="stSidebar"] {
        background-color: #0f1117;
        border-right: 1px solid #1e2130;
    }

    [data-testid="stSidebar"] * {
        color: #c9d1d9 !important;
    }

    .msg-user {
        background: #1a1f2e;
        border: 1px solid #2a3045;
        border-radius: 12px 12px 4px 12px;
        padding: 12px 16px;
        margin: 8px 0 8px 60px;
        color: #e6edf3;
        font-size: 15px;
        line-height: 1.6;
    }

    .msg-assistant {
        background: #161b27;
        border: 1px solid #1e2d40;
        border-left: 3px solid #2f81f7;
        border-radius: 4px 12px 12px 12px;
        padding: 12px 16px;
        margin: 8px 60px 8px 0;
        color: #e6edf3;
        font-size: 15px;
        line-height: 1.6;
    }

    /* Message text sits above the badge row */
    .msg-content {
        margin-bottom: 8px;
        white-space: pre-wrap;
    }

    .meta-row {
        display: flex;
        gap: 6px;
        margin-top: 6px;
        flex-wrap: wrap;
    }

    /* All badges share the same base size */
    .badge {
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        padding: 2px 8px;
        border-radius: 4px;
        font-weight: 500;
        display: inline-block;
    }

    .badge-intent {
        background: #1f2d40;
        color: #58a6ff;
        border: 1px solid #2f4a6e;
    }

    .badge-action {
        background: #1f2d1f;
        color: #3fb950;
        border: 1px solid #2d5a2d;
    }

    .badge-inserted {
        background: #2d1f2d;
        color: #d2a8ff;
        border: 1px solid #5a2d5a;
    }

    .status-dot {
        display: inline-block;
        width: 8px;
        height: 8px;
        border-radius: 50%;
        margin-right: 6px;
    }

    .dot-green { background: #3fb950; box-shadow: 0 0 6px #3fb950; }
    .dot-red   { background: #f85149; box-shadow: 0 0 6px #f85149; }
    .dot-amber { background: #d29922; box-shadow: 0 0 6px #d29922; }

    .sidebar-section {
        font-size: 11px;
        font-weight: 600;
        letter-spacing: 0.1em;
        text-transform: uppercase;
        color: #484f58 !important;
        margin: 20px 0 8px;
    }

    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #484f58;
    }

    .empty-state h2 {
        font-size: 22px;
        font-weight: 300;
        color: #8b949e;
        margin-bottom: 8px;
    }

    .empty-state p {
        font-size: 14px;
        line-height: 1.8;
    }

    .example-chip {
        display: inline-block;
        background: #1a1f2e;
        border: 1px solid #2a3045;
        border-radius: 20px;
        padding: 4px 14px;
        margin: 4px;
        font-size: 13px;
        color: #8b949e;
    }
</style>
""", unsafe_allow_html=True)


st.markdown("""
<script>
    function hideCollapseButton() {
        const selectors = [
            '[data-testid="collapsedControl"]',
            '[data-testid="baseButton-header"]',
            '[data-testid="stSidebarCollapsedControl"]',
            '[data-testid="stSidebarCollapseButton"]',
            'button[kind="header"]'
        ];
        selectors.forEach(function(sel) {
            document.querySelectorAll(sel).forEach(function(el) {
                el.style.setProperty('display',    'none',    'important');
                el.style.setProperty('visibility', 'hidden',  'important');
                el.style.setProperty('width',      '0',       'important');
                el.style.setProperty('height',     '0',       'important');
                el.style.setProperty('opacity',    '0',       'important');
                el.style.setProperty('position',   'absolute','important');
                el.style.setProperty('left',       '-9999px', 'important');
            });
        });
    }

    // Run immediately, then repeatedly to catch React re-renders
    hideCollapseButton();
    window.addEventListener('load', hideCollapseButton);
    [100, 300, 500, 1000, 2000, 3000].forEach(function(ms) {
        setTimeout(hideCollapseButton, ms);
    });

    // MutationObserver — fires whenever the DOM changes (catches every re-render)
    var observer = new MutationObserver(hideCollapseButton);
    observer.observe(document.body, { childList: true, subtree: true });
</script>
""", unsafe_allow_html=True)


# ==============================================================
# Session state
# ==============================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

if "api_key_set" not in st.session_state:
    st.session_state.api_key_set = False

if "pending_action" not in st.session_state:
    st.session_state.pending_action = None

if "conversation_context" not in st.session_state:
    st.session_state.conversation_context = {}


if "language" not in st.session_state:
    st.session_state.language = ""


# ==============================================================
# Sidebar
# ==============================================================

with st.sidebar:
    st.markdown("## 🎧 Customer Service")
    st.markdown("---")

    # ── Settings expander ─────────────────────────────────────
    with st.expander("⚙️ Settings", expanded=not st.session_state.api_key_set):

        st.markdown("**OpenAI API Key**")

        user_api_key = st.text_input(
            "API Key",
            type="password",
            placeholder="sk-...",
            label_visibility="collapsed",
            help="Your key is used only for this session and never stored."
        )

        if user_api_key and user_api_key.startswith("sk-"):
            # Inject key into environment for all os.getenv() calls
            os.environ["OPENAI_API_KEY"] = user_api_key

            try:
                from src.tools import mcp_tools as _mcp
                from openai import OpenAI as _OAI
                _mcp._openai_client = _OAI(api_key=user_api_key)
                st.session_state.api_key_set = True
            except Exception:
                st.session_state.api_key_set = True

        elif user_api_key:
            st.caption("⚠️ Key should start with sk-")
            st.session_state.api_key_set = False

        else:
            st.markdown(
                '<span style="font-size:12px;color:#484f58">'
                '<a href="https://platform.openai.com/api-keys" '
                'target="_blank" style="color:#58a6ff">Get a key →</a>'
                '</span>',
                unsafe_allow_html=True
            )
            st.session_state.api_key_set = False

        st.markdown("---")

        if st.button("🗑️ Clear chat", use_container_width=True):
            st.session_state.messages             = []
            st.session_state.pending_action       = None
            st.session_state.conversation_context = {}
            st.session_state.language             = ""
            st.rerun()

    # ── System status ─────────────────────────────────────────
    st.markdown(
        '<p class="sidebar-section">System status</p>',
        unsafe_allow_html=True
    )

    
    if st.session_state.api_key_set:
        st.markdown(
            '<span class="status-dot dot-green"></span> API key accepted',
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            '<span class="status-dot dot-red"></span> No API key',
            unsafe_allow_html=True
        )

    
    try:
        from src.db.sql_client import get_engine
        with get_engine().connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        st.markdown(
            '<span class="status-dot dot-green"></span> Database connected',
            unsafe_allow_html=True
        )
    except Exception:
        st.markdown(
            '<span class="status-dot dot-red"></span> Database offline',
            unsafe_allow_html=True
        )

    
    try:
        from src.db.vector_store import get_qdrant_client
        get_qdrant_client().get_collections()
        st.markdown(
            '<span class="status-dot dot-green"></span> Qdrant connected',
            unsafe_allow_html=True
        )
    except Exception:
        st.markdown(
            '<span class="status-dot dot-amber"></span> Qdrant unavailable',
            unsafe_allow_html=True
        )

    # ── Info ─────────────────────────────────────────────────
    st.markdown("---")
    st.markdown(
        '<p style="font-size:12px;color:#484f58;line-height:1.7">'
        'Supports Arabic & English.<br>'
        'Your API key is used only in this session.<br><br>'
        '<a href="https://github.com/khaled-abdulaziz/customer-service-agent" '
        'target="_blank" style="color:#58a6ff">View on GitHub →</a>'
        '</p>',
        unsafe_allow_html=True
    )


# ==============================================================
# Main — Chat area
# ==============================================================

st.markdown("### 🎧 How can I help you today?")


if not st.session_state.api_key_set:
    st.markdown("""
    <div class="empty-state">
        <h2>Enter your OpenAI API key to start</h2>
        <p>
            Your key powers the AI responses.<br>
            It is used only in this session and never stored.<br><br>
            <a href="https://platform.openai.com/api-keys"
               target="_blank" style="color:#3fb950">
               Get an API key →
            </a><br><br>
            <span style="color:#484f58">
                ⬅️ Open ⚙️ Settings in the sidebar.
            </span>
        </p>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ── Empty state with example prompts ─────────────────────────

if not st.session_state.messages:
    st.markdown("""
    <div class="empty-state">
        <h2>Ask me anything about your order</h2>
        <p>
            I can help you track orders, check product availability,<br>
            submit return requests, or file complaints.<br><br>
            <span style="color:#3fb950">Supports Arabic and English.</span><br><br>
            <strong style="color:#8b949e">Try asking:</strong>
        </p>
        <div>
            <span class="example-chip">What is the status of order 3?</span>
            <span class="example-chip">Is MacBook Pro available in Riyadh?</span>
            <span class="example-chip">I want to return order 8</span>
            <span class="example-chip">I have a complaint about my order</span>
            <span class="example-chip">What is your return policy?</span>
            <span class="example-chip">ما هو حالة طلبي رقم 5؟</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── Chat history ──────────────────────────────────────────────

else:
    for msg in st.session_state.messages:

        if msg["role"] == "user":
            
            safe_user = html.escape(msg["content"])
            st.markdown(
                f'<div class="msg-user">{safe_user}</div>',
                unsafe_allow_html=True
            )

        else:
            meta         = msg.get("meta", {})
            intent       = meta.get("intent", "")
            action_taken = meta.get("action_taken", "")

            
            badge_intent = (
                f'<span class="badge badge-intent">🎯 {intent}</span>'
                if intent else ""
            )

            if action_taken == "inserted":
                badge_action = '<span class="badge badge-inserted">✅ submitted</span>'
            elif action_taken == "looked_up":
                badge_action = '<span class="badge badge-action">🔍 looked up</span>'
            else:
                badge_action = ""

            
            safe_content = html.escape(msg["content"]).replace("\n", "<br>")

            st.markdown(f"""
            <div class="msg-assistant">
                <div class="msg-content">{safe_content}</div>
                <div class="meta-row">
                    {badge_intent}{badge_action}
                </div>
            </div>
            """, unsafe_allow_html=True)


# ── Chat input ────────────────────────────────────────────────

question = st.chat_input("Type your question in Arabic or English...")

if question:
    
    st.session_state.messages.append({
        "role":    "user",
        "content": question,
    })

    with st.spinner("Thinking..."):
        try:
            result = run_agent(
                message=question,
                pending_action=st.session_state.pending_action,
                conversation_context=st.session_state.conversation_context,
                language=st.session_state.language,   
            )

            st.session_state.pending_action       = result.get("pending_action")
            st.session_state.conversation_context = result.get("conversation_context", {})
            st.session_state.language             = result.get("language", "")

            st.session_state.messages.append({
                "role":    "assistant",
                "content": result["answer"],
                "meta": {
                    "intent":       result["intent"],
                    "action_taken": result["action_taken"],
                    "llm_used":     result["llm_used"],
                }
            })

        except Exception as e:
            st.session_state.messages.append({
                "role":    "assistant",
                "content": f"❌ Something went wrong: {str(e)}",
                "meta":    {}
            })

    st.rerun()