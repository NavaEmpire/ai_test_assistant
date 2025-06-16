# === tools/generate_test_script.py ===
import os
import re
from llm.llm_client import query_llm
import subprocess

FRAMEWORK_FOLDER = "framework_output"

def write_default_pytest_ini(base_path: str, force_overwrite: bool = False) -> None:
    pytest_ini_path = os.path.join(base_path, "pytest.ini")
    # Check if file exists and skip only if valid and not forced
    if os.path.exists(pytest_ini_path) and not force_overwrite:
        try:
            with open(pytest_ini_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Basic validation: check if file has [pytest] section and key-value pairs
                if "[pytest]" in content and "=" in content:
                    print("Valid pytest.ini already exists, skipping write.")
                    return
                else:
                    print("Existing pytest.ini is invalid, overwriting.")
        except (IOError, UnicodeDecodeError) as e:
            print(f"Error reading pytest.ini: {e}, overwriting.")
    content = (
        "[pytest]\n"
        "asyncio_mode = auto\n"
        "asyncio_default_fixture_loop_scope = function\n"
    ).strip() + "\n"  # Ensure single trailing newline
    # Write file with error handling
    try:
        with open(os.path.join(base_path, "pytest.ini"), "w", encoding="utf-8") as f:
            f.write(content)
        print("Default pytest.ini written to: {pytest_ini_path}")
        # Verify file was written correctly
        with open(pytest_ini_path, "r", encoding="utf-8") as f:
            written_content = f.read()
            if written_content == content:
                print("pytest.ini content verified successfully.")
            else:
                print("Warning: Written pytest.ini content does not match expected content.")
    except IOError as e:
        print(f"Error writing pytest.ini: {e}")
        raise RuntimeError(f"Failed to write pytest.ini at {pytest_ini_path}")

# To ensure the code is formatted correctly, we can use the `black` formatter.
def format_with_black(filepath: str):
    if not filepath.endswith(".py"):
        return  # Skip formatting non-Python files
    try:
        subprocess.run(["black", filepath], check=True)
        print(f"Formatted {filepath} with black.")
    except subprocess.CalledProcessError as e:
        print(f"[WARN] Failed to format {filepath}: {e}")


def extract_and_save_code_blocks(response: str, base_path: str) -> str:
    os.makedirs(base_path, exist_ok=True)
    subfolders = ["tests", "pages", "utils"]
    for subfolder in subfolders:
        os.makedirs(os.path.join(base_path, subfolder), exist_ok=True)   
        init_path = os.path.join(base_path, subfolder, '__init__.py')
        open(init_path, 'a').close() 

    # Extract code blocks
    pattern = r"(?:#\s*([\w\-/\.]+)\s*)?```python\s*(#\s*[\w\-/\.]+\s*)?(.*?)```"
    matches = re.findall(pattern, response, re.DOTALL)
    
    file_blocks = []
    for path_above, path_inside, code in matches:
        # Prefer path from outside the code block, fallback to inside
        filepath = (path_above or path_inside or "").strip().lstrip("#").strip()
        if filepath:
            file_blocks.append((filepath, code.strip()))


    # Ensure conftest.py is at the root
    for i, (filepath, code) in enumerate(file_blocks):
        filename = os.path.basename(filepath)
        if filename == "conftest.py" and "/" in filepath:
            print(f"[WARN] conftest.py should be in root. Moving from {filepath} to conftest.py")
            file_blocks[i] = ("conftest.py", code)
        
   
    used_files = set()

    for filepath, code in file_blocks:
        cleaned_path = filepath.strip()
        code = code.strip()

        # Normalize to forward slashes and remove leading slashes
        cleaned_path = cleaned_path.replace("\\", "/").lstrip("/")

        # Avoid duplicates
        if cleaned_path in used_files:
            print(f"Duplicate file skipped: {cleaned_path}")
            continue
        used_files.add(cleaned_path)

        # Determine target directory
        full_path = os.path.join(base_path, cleaned_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

        # Write the file
        with open(full_path, "w", encoding="utf-8") as f:
            code = code.strip() + "\n"
            f.write(code)
        print(f"File saved: {full_path}")
        # Format the file with black
        format_with_black(full_path)
        
    # Extract README by removing all code blocks
    readme_parts = re.split(r"#\s*[\w\-/\.]+\s*```python.*?```", response, flags=re.DOTALL)
    readme_text = "\n\n".join([part.strip() for part in readme_parts if part.strip()])
    return readme_text
            

def save_readme(readme_text: str, base_path: str) -> None:
    readme_path = os.path.join(base_path, "README.md")
    with open(readme_path, "w", encoding="utf-8") as f:
        f.write("# Generated QA Automation framework \n\n")
        f.write(readme_text.strip())
    print(f"README saved: {readme_path}")


async def generate_test_scripts(user_story: str, llm_provider: str, dom_context: str) -> str:
# async def generate_test_scripts(user_story: str, llm_provider: str) -> str:
    system_prompt = f"""
        You are a QA Automation Engineer. Generate a Python Playwright automation framework using pytest and Page Object Model (POM).

        Requirements:
        - Page Object Model: Separate page classes with methods and locators.
        - Use `page.wait_for_selector(selector)` before each click/assert, or `locator.wait_for()` if using locator object.
        - Only use locators with data-testid, aria-label, or visible text
        - Test cases using pytest and allure for report generation
        - All tests must be runnable and active. Ensure no test cases are generated in a skipped state.
        - All tests must include the decorator `@pytest.mark.nondestructive` to guarantee they never get skipped.
        - All code blocks must have proper indentation, spacing and formatting.
        - Avoid third-party plugins like pytest-base-url. Do not use any implicit base_url fixtures.
        - Include any necessary utility files, configuration files, and a 'requirements.txt'.
        - Directory structure as markdown
        - Explanations for design decisions
        - Do NOT use `asyncio`, `async def`, or `async_playwright`. 
        - Ensure conftest.py uses sync_playwright().start() and stops it explicitly to avoid fixture issues.
        - Do NOT include @pytest.mark.skip or skipped tests. All generated tests must be active and runnable.
        - conftest.py must define fixtures for browser(), page(), and base_url(), and be fully functional with Playwright.
        - The `base_url` fixture in conftest.py must use `scope="session"` to avoid scope mismatches with plugins or session-scoped tests.
        
        Use this DOM reference (from an actual scrape) to guide your locator choices:
        {dom_context}

        **IMPORTANT:** Before each code block, include a single comment line with the relative file path where the code belongs, for example:
        # tests/test_login.py
        # pages/login_page.py
        # utils/helpers.py
        # conftest.py
        # requirements.txt
        Format all code blocks with triple backticks and python language specifier.
    """
        
    print("\n Starting framework generation...\n\n")
    response = await query_llm(user_story, system_prompt, llm_provider)
    # print("\nGenerate Response---------->\n", response)

    # Extract and save code files
    print("\n\n Saving files...\n")
    readme_text = extract_and_save_code_blocks(response, FRAMEWORK_FOLDER)
    save_readme(readme_text, FRAMEWORK_FOLDER)

    # Write pytest.ini, force overwrite if previous runs caused issues
    write_default_pytest_ini(FRAMEWORK_FOLDER, force_overwrite=True)  # Set to True to ensure fresh file

    print("\n\n All files saved. Exiting...\n")
    return f"Framework files saved in: {FRAMEWORK_FOLDER}"
