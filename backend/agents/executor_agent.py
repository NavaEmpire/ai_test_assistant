# === Executor_agent.py ===
import subprocess
import shutil
import os
from agent_framework import Agent

FRAMEWORK_FOLDER = "framework_output"

async def test_executor_fn(prompt: str, llm_provider: str):
    try:
        if not os.path.exists(FRAMEWORK_FOLDER):
            return f"No framework found at {FRAMEWORK_FOLDER}"
   
        env = os.environ.copy()
        env["PLAYWRIGHT_HEADLESS"] = "0"   # Run in headed mode
        env["PWDEBUG"] = "1" # To Make sure Playwright tests run in DEBUG mode

        # Determine where conftest.py exists, fallback to default 'tests'
        root_conftest = os.path.join(FRAMEWORK_FOLDER, "conftest.py")
        tests_conftest = os.path.join(FRAMEWORK_FOLDER, "tests", "conftest.py")

        # Determine test folder
        test_folder = "tests" if os.path.exists(tests_conftest) else ('.' if os.path.exists(root_conftest) else None)
        if test_folder is None:
            print("[DEBUG] No conftest.py found in root or tests directory.")
            return "conftest.py not found in root or tests directory."

        # Ensure allure-results directory
        allure_result_path = os.path.join(FRAMEWORK_FOLDER, "allure-results")
        os.makedirs(allure_result_path, exist_ok=True)  # to ensure directory exists

        # Check if pytest is installed
        pytest_path = shutil.which("pytest")
        if not pytest_path:
            return "pytest is not installed or not found in PATH."
        
        # Run tests
        result = subprocess.run(
            [
                pytest_path, test_folder,
                "-v", 
                "--tb=short", 
                "--maxfail=1",
                "--disable-warnings",
                # "--browser=chromium",
                "--alluredir=allure-results",
                "-rs"
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=FRAMEWORK_FOLDER,
            env=env
        )

        # Check if Allure is installed
        allure_path = shutil.which("allure")
        if not allure_path:
            return "Allure CLI is not installed or not found in PATH."

        # Start allure serve and extract URL from output
        subprocess.Popen(
            [allure_path, "serve", "allure-results"],
            cwd=FRAMEWORK_FOLDER,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        return f"""Test Execution Completed: 
        \n\nSTDOUT:
        {result.stdout}
        \n\nSTDERR:
        {result.stderr}
        
        Allure report has been opened in your default browser.

        Press Ctrl+C in the terminal to stop the server
        """
# Allure report is being served at: {report_url}
    except Exception as e:
        return f"Test Execution failed: {str(e)}"

    
test_executor_agent = Agent(
    name="Test Executor Agent",
    instructions = "Execute the generated Playwright + pytest test automation framework tests using pytest-playwright and return the Allure report output.",
    handoffs=[],
    handler=test_executor_fn,
)
