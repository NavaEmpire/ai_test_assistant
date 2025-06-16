import streamlit as st
import asyncio
import os

# Dummy placeholders (replace with actual implementations later)
async def query_gemini(user_prompt: str, system_prompt: str) -> str:
    await asyncio.sleep(1)
    return f"# AI-generated test script for: {user_prompt}\nprint('Test started...')"

async def scrape_dom(url: str) -> str:
    await asyncio.sleep(1)
    return "//button[1], //input[@id='username']"

def run_code(code: str) -> str:
    return "✅ Script executed successfully.\nLogs:\n- Clicked login\n- Entered username"

def is_prompt_valid(prompt: str) -> bool:
    return any(keyword in prompt.lower() for keyword in ["click", "login", "test", "form", "submit", "automation"])


# --- Streamlit UI Setup ---
st.set_page_config("🧪 AI Automation Assistant", layout="wide")
st.title("🤖 AI Test Automation Assistant")
st.markdown("Automate web testing with **Gemini 2.0**, **Playwright**, and **Streamlit**.")

# Sidebar for Inputs
with st.sidebar:
    st.header("📝 Test Configuration")
    prompt = st.text_area("Enter your test prompt", height=150, placeholder="e.g., Test the login form on example.com")
    url = st.text_input("Page URL for DOM scraping", placeholder="https://example.com")
    run_button = st.button("🧠 Generate Automation Script")
    scrape_button = st.button("🔍 Scrape DOM")

# Guardrail
if prompt and not is_prompt_valid(prompt):
    st.warning("⚠️ Prompt doesn't seem automation-related. Please refine it.")
    st.stop()

# Layout Columns for Main Content
col1, col2 = st.columns([1.5, 1])

# ---- Code Generation ----
with col1:
    st.subheader("🧠 Generated Automation Code")
    if run_button:
        with st.spinner("Generating code using Gemini..."):
            code = asyncio.run(query_gemini(prompt, "You are an expert automation assistant using Playwright."))
            st.session_state.generated_code = code
    code = st.session_state.get("generated_code", "# Generated code will appear here...")
    edited_code = st.text_area("✏️ Edit or review the code:", value=code, height=300, key="editable_code")

# ---- Run and Save Actions ----
with col2:
    st.subheader("🚀 Run & Manage Script")
    
    if st.button("▶️ Run Script"):
        with st.spinner("Executing script..."):
            output = run_code(edited_code)
            st.success("Script executed.")
            st.text_area("📋 Execution Output:", value=output, height=200)

    st.markdown("### 💾 Save Script")
    filename = st.text_input("Save as:", value="test_script.py")
    if st.button("💾 Save"):
        os.makedirs("generated", exist_ok=True)
        with open(f"generated/{filename}", "w") as f:
            f.write(edited_code)
        st.success(f"Saved to generated/{filename}")

# ---- DOM Scraping Results ----
if scrape_button and url:
    with st.expander("🕷️ DOM Scraping Output"):
        with st.spinner("Scraping DOM..."):
            selectors = asyncio.run(scrape_dom(url))
            st.code(selectors, language="text")
else:
    if scrape_button:
        st.warning("Please enter a valid URL to scrape.")

# ---- Test Report Section ----
with st.expander("📊 Test Report Generator"):
    if st.button("📝 Generate Report"):
        os.makedirs("reports", exist_ok=True)
        with open("reports/latest_report.txt", "w") as f:
            f.write(f"Test Prompt: {prompt}\n\nGenerated Code:\n{edited_code}\n\nResult:\n{run_code(edited_code)}")
        st.success("Report saved to reports/latest_report.txt")
    if os.path.exists("reports/latest_report.txt"):
        with open("reports/latest_report.txt", "r") as f:
            report = f.read()
            st.text_area("📄 Latest Report:", value=report, height=250)

# Footer
st.markdown("---")
st.caption("Built with ❤️ by Navaneeth — powered by Gemini 2.0, Playwright, and Streamlit.")