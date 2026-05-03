import streamlit as st

# ── Must be FIRST streamlit command ──────────────────────────────────────────
st.set_page_config(
    page_title="Claude Chat",
    page_icon="🤖",
    layout="centered",
)

try:
    import anthropic
except ImportError:
    st.error("❌ 'anthropic' package not found. Check requirements.txt has: anthropic>=0.25.0")
    st.stop()

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

.stApp { background: #0d0d0d; color: #e8e8e8; }

.app-header {
    text-align: center;
    padding: 2rem 0 1rem 0;
    border-bottom: 1px solid #2a2a2a;
    margin-bottom: 1.5rem;
}
.app-header h1 {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 1.8rem;
    color: #e8612a;
    letter-spacing: -0.02em;
    margin: 0;
}
.app-header p {
    color: #666;
    font-size: 0.85rem;
    margin: 0.3rem 0 0 0;
    font-family: 'IBM Plex Mono', monospace;
}

.chat-user {
    background: #1a1a1a;
    border: 1px solid #2a2a2a;
    border-radius: 12px 12px 2px 12px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    margin-left: 15%;
    color: #e8e8e8;
    font-size: 0.95rem;
    line-height: 1.5;
    white-space: pre-wrap;
}
.chat-assistant {
    background: #141414;
    border: 1px solid #e8612a33;
    border-left: 3px solid #e8612a;
    border-radius: 2px 12px 12px 12px;
    padding: 0.8rem 1rem;
    margin: 0.5rem 0;
    margin-right: 15%;
    color: #e8e8e8;
    font-size: 0.95rem;
    line-height: 1.6;
    white-space: pre-wrap;
}
.label {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    margin-bottom: 0.3rem;
    opacity: 0.5;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}
.label-user { color: #aaa; text-align: right; }
.label-ai   { color: #e8612a; }

.stTextArea textarea {
    background: #141414 !important;
    border: 1px solid #2a2a2a !important;
    border-radius: 8px !important;
    color: #e8e8e8 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.95rem !important;
}
.stTextArea textarea:focus {
    border-color: #e8612a !important;
    box-shadow: 0 0 0 1px #e8612a44 !important;
}

.stButton > button {
    background: #e8612a !important;
    color: #fff !important;
    border: none !important;
    border-radius: 6px !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.85rem !important;
    font-weight: 600 !important;
    padding: 0.5rem 1.5rem !important;
}
.stButton > button:hover { opacity: 0.85 !important; }

section[data-testid="stSidebar"] { background: #0a0a0a !important; border-right: 1px solid #1e1e1e !important; }
section[data-testid="stSidebar"] .stTextInput input {
    background: #141414 !important;
    border: 1px solid #2a2a2a !important;
    color: #e8e8e8 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.8rem !important;
    border-radius: 6px !important;
}

hr { border-color: #1e1e1e !important; }
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Settings")
    st.markdown("---")

    api_key = st.text_input(
        "Anthropic API Key",
        type="password",
        placeholder="sk-ant-...",
        help="Get key at console.anthropic.com",
    )

    model = st.selectbox(
        "Model",
        [
            "claude-sonnet-4-20250514",
            "claude-haiku-4-5-20251001",
            "claude-opus-4-20250514",
        ],
        index=0,
    )

    max_tokens = st.slider("Max Tokens", 256, 4096, 1024, 128)

    system_prompt = st.text_area(
        "System Prompt (optional)",
        placeholder="You are a helpful assistant...",
        height=100,
    )

    st.markdown("---")
    st.markdown("""
    <div style='font-family:IBM Plex Mono,monospace;font-size:0.7rem;color:#444;line-height:1.8'>
    📌 API Key:<br>
    <a href='https://console.anthropic.com' style='color:#e8612a' target='_blank'>console.anthropic.com</a><br><br>
    🔒 Key is NOT stored anywhere
    </div>
    """, unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="app-header">
    <h1>◈ CLAUDE CHAT</h1>
    <p>powered by anthropic api</p>
</div>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

# ── Chat history ──────────────────────────────────────────────────────────────
for msg in st.session_state.messages:
    if msg["role"] == "user":
        st.markdown(f'<div class="label label-user">You</div><div class="chat-user">{msg["content"]}</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="label label-ai">Claude</div><div class="chat-assistant">{msg["content"]}</div>', unsafe_allow_html=True)

# ── Input ─────────────────────────────────────────────────────────────────────
st.markdown("<br>", unsafe_allow_html=True)

user_input = st.text_area(
    "Message",
    placeholder="Type your message here...",
    height=100,
    label_visibility="collapsed",
    key="user_input",
)

col1, col2, col3 = st.columns([3, 1, 1])

with col1:
    send = st.button("Send →", use_container_width=True)
with col3:
    clear = st.button("Clear 🗑", use_container_width=True)

# ── Actions ───────────────────────────────────────────────────────────────────
if clear:
    st.session_state.messages = []
    st.rerun()

if send and user_input.strip():
    if not api_key:
        st.error("⚠️ Please enter your Anthropic API Key in the sidebar.")
    else:
        st.session_state.messages.append({"role": "user", "content": user_input.strip()})

        with st.spinner("Claude is thinking..."):
            try:
                client = anthropic.Anthropic(api_key=api_key)

                kwargs = dict(
                    model=model,
                    max_tokens=max_tokens,
                    messages=st.session_state.messages,
                )
                if system_prompt.strip():
                    kwargs["system"] = system_prompt.strip()

                response = client.messages.create(**kwargs)
                reply = response.content[0].text
                st.session_state.messages.append({"role": "assistant", "content": reply})

            except anthropic.AuthenticationError:
                st.error("❌ Invalid API Key. Check console.anthropic.com")
                st.session_state.messages.pop()
            except anthropic.RateLimitError:
                st.error("⚠️ Rate limit hit. Wait a moment and retry.")
                st.session_state.messages.pop()
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.session_state.messages.pop()

        st.rerun()
