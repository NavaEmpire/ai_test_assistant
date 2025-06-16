import streamlit as st
import asyncio
import os
import uuid
from datetime import datetime

# Dummy placeholders – replace with real implementations
async def query_gemini(user_prompt: str, dom_data: str) -> str:
    await asyncio.sleep(1)
    return f"# AI-generated test script for: {user_prompt}\n# Using DOM: {dom_data}\nprint('Executing automation...')"

async def scrape_dom(prompt: str) -> str:
    await asyncio.sleep(1)
    return "//button[1]\n//input[@id='username']\n//input[@id='password']"

def run_code(code: str) -> str:
    return "✅ Executed successfully.\nLog:\n- Clicked button\n- Entered username\n- Entered password"

def generate_allure_report(output_dir: str):
    report_path = os.path.join(output_dir, "allure_report.html")
    with open(report_path, "w") as f:
        f.write("<html><body><h1>Allure Report Placeholder</h1></body></html>")

def is_prompt_valid(prompt: str) -> bool:
    return any(keyword in prompt.lower() for keyword in ["click", "login", "test", "form", "submit", "automation", "visit", "navigate", "example.com"])

# --- Streamlit UI ---
st.set_page_config("AI Automation Assistant", layout="wide")
st.title("AI Test Automation Assistant")
st.markdown("Automate web testing with Gemini, Playwright & Allure. Just enter a prompt:")

# Prompt Input
prompt = st.text_area("Test Prompt", height=150, placeholder="e.g., Test the login on https://example.com")
execute = st.button("Execute")

# Validate prompt
if prompt and not is_prompt_valid(prompt):
    st.warning("⚠️ Prompt doesn't seem automation-related. Please refine it.")
    st.stop()

# --- Execution Block ---
if execute and prompt:
    with st.spinner("Running full automation pipeline..."):

        # Create unique session directory
        session_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_dir = os.path.join("automation_output", f"{timestamp}_{session_id}")
        os.makedirs(session_dir, exist_ok=True)

        # Step 1: Scrape DOM
        dom_data = asyncio.run(scrape_dom(prompt))
        dom_file = os.path.join(session_dir, "dom_selectors.txt")
        with open(dom_file, "w") as f:
            f.write(dom_data)

        # Show DOM
        with st.expander("Scraped DOM Elements"):
            st.code(dom_data, language="text")

        # Step 2: Generate code using Gemini
        code = asyncio.run(query_gemini(prompt, dom_data))
        code_file = os.path.join(session_dir, "test_script.py")
        with open(code_file, "w") as f:
            f.write(code)

        # Step 3: Run the code (mocked)
        result = run_code(code)

        # Step 4: Generate report
        report_path = os.path.join(session_dir, "report.txt")
        with open(report_path, "w") as f:
            f.write(f"Prompt:\n{prompt}\n\nGenerated Code:\n{code}\n\nExecution Result:\n{result}")

        # Step 5: Allure Report (mock)
        generate_allure_report(session_dir)

    # Display Results
    st.success("✅ Automation completed.")

    st.subheader("Generated Code")
    st.code(code, language="python")

    st.subheader("Execution Log")
    st.text(result)

    st.subheader("Report")
    with open(report_path) as f:
        st.text(f.read())

    st.subheader("Allure Report (HTML)")
    st.markdown(f"[📄 Open Allure Report]({session_dir}/allure_report.html)", unsafe_allow_html=True)

# Footer
st.markdown("---")
# st.caption("Powered by Playwright, Gemini, and Allure")
