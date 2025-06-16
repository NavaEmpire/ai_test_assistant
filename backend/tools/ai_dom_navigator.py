# === tools/ai_dom_navigator.py ===
from playwright.async_api import async_playwright
import json
import os
import re
from llm.llm_client import query_llm
import asyncio
from tools.assertion_utils import handle_assertion

FRAMEWORK_FOLDER = "framework_output"
DEFAULT_TIMEOUT = 10000
MAX_STEPS = 50

def parse_llm_response(raw_response):
    try:
        # Remove markdown fences and whitespace
        cleaned = clean_json_response(raw_response)
        parsed = json.loads(cleaned)

        if isinstance(parsed, dict):
            if not parsed.get("type") and not parsed.get("action"):
                raise ValueError("LLM response missing required keys in dict")
            return [parsed]

        # If it's a list, validate all elements
        elif isinstance(parsed, list):
            for item in parsed:
                if not isinstance(item, dict):
                    raise ValueError("Each item in list must be a dict")
                if not item.get("type") and not item.get("action"):
                    raise ValueError("Each action must have a type/action field")
            return parsed

        else:
            raise ValueError("Parsed response is neither a dict nor a list")

        # return parsed

    except Exception as e:
        print(f"[ERROR] LLM response parse error: {e}")
        return None
    
def is_valid_css_selector(selector: str) -> bool:
    return not re.search(r'[:\s]', selector)  # simple invalid char check

def enhance_with_smart_locator(el : dict) -> dict:
    """Enhanced locator generation with better prioritization and validation."""

    tag = el.get("tag", "")
    candidates = []
    attrs = el.get('attrs', {})
    text = el.get('text', '').strip()

    form_id = el.get("form_id")

    # Priority attributes
    if attrs.get("data-testid"):
        candidates.append(f"[data-testid='{attrs['data-testid']}']")
    if attrs.get("aria-label"):
        candidates.append(f"[aria-label='{attrs['aria-label']}']")
    if el.get("id") and is_valid_css_selector(f"#{el['id']}"):
        candidates.append(f"#{el['id']}")
    if el.get("name"):
        candidates.append(f"[name='{el['name']}']")
    
    # Text-based selectors for common interactive elements
    if tag and text:
        # Clean unstable prefixes like numbers, currency symbols, etc.
        cleaned_text = re.sub(r"^[\d₹$€¥\s\-]+", "", text).strip()
        escaped_text = cleaned_text.replace("'", "\\'")
        if len(cleaned_text) >= 2:
            if tag in ['button', 'a', 'label']:
                candidates.append(f"{tag}:has-text('{escaped_text}')")
            elif tag in ['span', 'p', 'div'] and not candidates:
                candidates.append(f"{tag}:has-text('{escaped_text}')")
            if tag:
                class_selector = ""
                candidates.append(f"{tag}{class_selector}:has-text('{escaped_text}')")
                if el.get("type"):
                    candidates.append(f"{tag}[type='{el['type']}']:has-text('{escaped_text}')")
    
    # Fallback XPath
    if not candidates and text:
        safe_text = text.replace("'", "\\'")
        candidates.append(f"//{el.get('tag')}[contains(normalize-space(text()), '{safe_text}')]")
    # Attach form context for reference
    if form_id:
        el["form_context"] = f"Belongs to form with id '{form_id}'"

    el["preferred_locators"] = candidates
    return el

def clean_json_response(text: str) -> str:
    """
    Remove markdown code fences (```json ... ```) or ``` ... ``` from LLM output.
    """
    cleaned = re.sub(r"```json\n(.+?)\n```", r"\1", text, flags=re.DOTALL)
    cleaned = re.sub(r"```[\w]*\n(.+?)\n```", r"\1", cleaned, flags=re.DOTALL)
    return cleaned.strip()
        
async def get_next_steps(prompt: str, llm_provider: str) -> dict:
    """
    Generate next steps for DOM navigation using an LLM.
    """
    system_prompt= """
    You are an expert in web UI automation and DOM navigation.
    Your job is to analyze the current page's DOM structure and suggest the next best action in a multi-step user flow.
    You must ensure the steps are followed **exactly in order**, without skipping intermediate actions — even if later fields are already visible in the DOM.

    **Important behavioral rules:**

    - Follow the user-defined steps in the exact sequence provided in the goal prompt.
    - DO NOT click or interact with fields/buttons meant for later steps, even if they appear in the DOM now.
    - Each DOM element includes a list of `preferred_locators`. You must use one of these locators — DO NOT invent or hallucinate new selectors.
    - Prioritize robust selectors in this order: `data-testid`, `id`, `name`, `aria-label`, `class`, then text-based selectors (e.g., `:has-text()` or XPath with `contains(text())`).
    - If an action fails (e.g., element not found), suggest an alternative selector or recovery action (e.g., wait, refresh, or check for error messages).
    - DO NOT skip steps or assume a step is complete unless the DOM clearly indicates the action was successful (e.g., a login form is no longer present after submission).
    - Only return `"end"` if all steps are complete or a critical element is missing (explain why).
    - For forms (e.g., login): 
        - First, return all 'fill' actions for required fields as a JSON array.
        - Next, return a 'click' or 'submit' action on the likely submit button. Identify it by:
            - type="submit", role="button" inside a <form>
            - Text like "Submit", "Login", "Continue", "Sign in", "Next"
            - Proximity to filled fields or inside the same form
    - Respond with either a single JSON object or a JSON array of objects (actions) in the specified format.
    - Track the current step number and ensure the suggest the next steps action.
    - Match the visible text **exactly** when identifying confirm buttons in modals (e.g., 'Remove' vs 'Cancel'). Do not confuse them.
    - When suggesting a selector:
        - If multiple elements contain the same visible text 
        - Choose the once based on the index provided by the user or select the first one.
        - Avoid large containers like `<div>` or `<section>` if the actual action should occur on a nested `<button>`, `<a>`, or `<input>`.
        - Always prefer elements with tag: `button`, `a`, `input[type="submit"]`, or `role='button'`.
        - Only use `div:has-text(...)` or `span:has-text(...)` if there is no more specific clickable tag available.

    Allowed actions types:
    - click, input, fill, enter, select, submit, press, navigate, verify, assert, end
    
    Output Format:
    {
        "type": "<action type>",    // click | input | fill | select | submit | press | navigate | end | assert| verify
        "action": "<same as type>",
        "selector": "<CSS selector or XPath> or null if url to be verified", 
        "index": <optional index for multiple matches>,  // optional, only if multiple elements match
        "value": "<value to input or select>",
        "key": "<key to press>",
        "url": "<URL to navigate to> or <URL to verify if applicable>",
        "description": "<optional description of the action>"
    }
    Use this Output format for assert/verify types:
    {
        "type": "assert",
        "action": "assert",
        "subtype": "<subtype of assertion>, // text | url | title | element_present |attribute | not_present | count | assert_value | visiblity",>",
        "selector": "<CSS selector (if applicable)>",
        "url": "<url to verify (only if subtype is 'url')>",
        "value": "<expected value (for text or attribute assertions)>",
        "description": "<What exactly is being verified>"
    }
    If no further steps are needed, respond with:
    {
        "type": "end",
        "action": "end",
        "description": "Flow completed or no further actions required."
    }
    """
    response = await query_llm(
        user_prompt=prompt,
        system_prompt=system_prompt,
        provider=llm_provider
    )
    print("[DEBUG] Raw LLM response:", response)
    
    parsed_response = parse_llm_response(response)
    if not parsed_response:
            print("[WARN] Could not parse LLM response, skipping step.")
            return [{"type": "end", "action": "end", "description": "Invalid LLM response"}]

    return parsed_response if isinstance(parsed_response, list) else [parsed_response]
    

async def extract_dom_structure(page) -> dict:
    
    await page.wait_for_load_state("networkidle", timeout=60000)  # Wait for dynamic content
    elements = []
    
    async def traverse_element(handle, depth = 0, parent_text=""):
        """Recursively traverse DOM elements and extract relevant information."""
        try:
            tag_name = await handle.evaluate("el => el.tagName.toLowerCase()")
            
            # Define different categories of elements
            interactive_tags = ['input', 'button', 'a', 'select', 'textarea', 'form']
            text_content_tags = ['p', 'span', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']  # removed 'label'
            clickable_containers = ['div', 'span', 'p']
            result = []
            
            # Extract attributes
            attrs = await handle.evaluate("""
                    el => {
                        const attributes = {};
                        for (const attr of el.attributes) {
                            attributes[attr.name] = attr.value;
                        }
                        return attributes;
                    }
            """)
                
            # Get direct text content (not from children)
            direct_text = await handle.evaluate("""
            el => {
                let directText = '';
                for (let node of el.childNodes) {
                    if (node.nodeType === Node.TEXT_NODE) {
                        directText += node.textContent;
                    }
                }
                return directText.trim();
                }
            """)
               
            full_text = (await handle.evaluate("el => el.innerText || el.textContent || ''")).strip()
                
            # Check if element is potentially clickable
            is_clickable = await handle.evaluate("""
                el => {
                    const style = window.getComputedStyle(el);
                    return (
                        style.cursor === 'pointer' ||
                        el.onclick !== null ||
                        el.getAttribute('role') === 'button' ||
                        el.getAttribute('tabindex') !== null ||
                        el.hasAttribute('data-testid') ||
                        el.classList.contains('clickable') ||
                        el.classList.contains('btn') ||
                        el.classList.contains('button') ||
                        el.classList.contains('card') ||
                        el.classList.contains('Card')
                    );
                }
            """)

            # Decide whether to include this element
            should_include = False
            text_to_use = ""
            
            if tag_name in interactive_tags:
                # Always include interactive elements
                should_include = True
                text_to_use = full_text[:150]
                
            elif tag_name in text_content_tags and direct_text:
                # Include text elements that have direct text content
                should_include = True
                text_to_use = direct_text[:150]
                
            elif tag_name in clickable_containers:
                # For containers (div), only include if they seem actionable and have unique characteristics
                has_meaningful_attrs = (
                    attrs.get('id') or 
                    attrs.get('data-testid') or 
                    attrs.get('role') == 'button' or
                    is_clickable
                )
                
                # Only include div if it has direct text or meaningful attributes, and text isn't inherited
                if (has_meaningful_attrs and direct_text) or (is_clickable and direct_text):
                    should_include = True
                    text_to_use = direct_text[:150]
                # Skip div if text comes from children (to avoid duplicates like 'Cake World')
                elif full_text and not direct_text:
                    should_include = False
            
            # Create element if it should be included
            if should_include:
                el = {
                    'tag': tag_name,
                    'id': attrs.get('id'),
                    'name': attrs.get('name'),
                    'type': attrs.get('type'),
                    'placeholder': attrs.get('placeholder'),
                    'value': attrs.get('value'),
                    'text': text_to_use,
                    'attrs': attrs,
                    'clickable': is_clickable,
                    'depth': depth,
                    'parent_text': parent_text # for debugging
                }
                
                # Enhance with smart locator
                enhanced = enhance_with_smart_locator(el)
                result.append(enhanced)
            
            # Recurse into children, passing current full_text as parent_text
            children = await handle.query_selector_all(":scope > *")
            for child in children:
                child_elements = await traverse_element(child, depth + 1)
                result.extend(child_elements)
            
            return result
            
        except Exception as e:
            print(f"Error processing element at depth {depth}: {e}")
            return []
    
    try:
        # Start traversal from the body element
        body = await page.query_selector("body")
        if body:
            elements = await traverse_element(body, depth=0)
        else:
            print("Warning: No body element found")
            elements = []

        # Filter duplicates: Keep element with deepest depth for same text
        text_to_elements = {}
        for el in elements:
            text = el.get('text')
            if text:
                if text not in text_to_elements or el['depth'] > text_to_elements[text]['depth']:
                    text_to_elements[text] = el
        elements = list(text_to_elements.values())

        return {"url": page.url, "elements": elements}
    
    except Exception as e:
        print(f"Error in extract_dom_structure: {e}")
        return {"url": page.url, "elements": []}

async def execute_action(page, action, retries=3, timeout=10000):
    """
    Executes a single action on the page. Always returns a dict with 'success' and 'message'.
    """
    selector = action.get('selector')
    index = action.get("index")
    action_subtype = action.get("subtype")
    action_type = action.get("type")
    result = {"success": False, "message": ""}

    for attempt in range(retries):
        try:
            if not selector and action_type not in ["navigate"] and action_subtype not in ["title", "url"]:
                result["message"] = "No selector provided for action."
                return result
            if selector:
                await page.wait_for_selector(selector, state="visible", timeout=timeout)
                locator = page.locator(selector)
                count = await locator.count()
                if count == 0:
                    raise Exception(f"No elements found for selector: {selector}")
                elif count > 1:
                    print(f"[WARN] Selector '{selector}' matched {count} elements, Attempting matches based on index specified in user prompt.")
                    if index is not None and 0 <= index < count:
                        print(f"[INFO] Using element at index {index} for selector '{selector}'")
                        locator = locator.nth(index)
                    else:
                        print(f"[INFO] No index provided — using first match.")
                        locator = locator.nth(0)
                # Check if element is interactable
                is_enabled = await locator.evaluate("el => !el.disabled && el.offsetParent !== null")
                if not is_enabled:
                    raise Exception(f"Element {selector} is not interactable (disabled or hidden)")
            else:
                locator = None
            # Execute the action
            match action_type:
                case 'click':
                    await locator.click(timeout=timeout)
                    result["success"] = True
                    result["message"] = "Click action performed successfully."
                case 'input' | 'fill':
                    await locator.fill(action.get('value', ""), timeout=timeout)
                    result["success"] = True
                    result["message"] = "Fill action performed successfully."
                case 'select':
                    await locator.select_option(action.get('value', ""), timeout=timeout)
                    result["success"] = True
                    result["message"] = "Select action performed successfully."
                case 'navigate':
                    if page.url == action.get('url', ""):
                        print(f"[INFO] Already at URL: {page.url}, skipping navigation.")
                        result["success"] = True
                        result["message"] = "Already at target URL."
                        return result
                    await page.goto(action.get('url', ""), wait_until="domcontentloaded", timeout=60000)
                    result["success"] = True
                    result["message"] = "Navigation performed successfully."
                case 'enter' | 'press':
                    await locator.press(action.get('key', "Enter"), timeout=timeout)
                    result["success"] = True
                    result["message"] = "Key press performed successfully."
                case 'submit':
                    await locator.evaluate("(form) => form.submit()", timeout=timeout)
                    result["success"] = True
                    result["message"] = "Form submitted successfully."
                case 'assert' | 'verify':
                    assertion_result = await handle_assertion(page, action, locator)
                    print(f"[ASSERT RESULT] {assertion_result['message']}")
                    return assertion_result
                case _:
                    result["message"] = f"Unknown action type: {action_type}"
            return result
        except Exception as e:
            print(f"[WARN] Attempt {attempt + 1} failed for action {action_type} on {selector}: {e}")
            result["message"] = str(e)
            if attempt == retries - 1:
                print(f"[ERROR] Action failed after {retries} attempts: {action}")
                return result
            await page.wait_for_timeout(2000)  # Wait before retrying
    return result

async def ai_guided_flow_navigator( url, llm_provider, goal_prompt) -> dict:
    """
    AI-guided DOM navigation tool that iteratively performs actions based on LLM guidance.
    """
    async with async_playwright() as p:
        steps_count = len(re.findall(r'^\s*\d+\.\s*', goal_prompt, re.MULTILINE))

        print("[DEBUG] Starting AI-guided DOM navigation...")
        browser = await p.chromium.launch(headless=False, # Set headless=True later
                                        #   slow_mo=50,  # remove or adjust for production
                                          args=["--start-fullscreen"]) 
        context = await browser.new_context(permissions=["geolocation"], locale="en-US")  # Add geolocation permission if needed
        page = await context.new_page()

        print(f"[DEBUG] Navigating to: {url}")
        await page.goto(url, wait_until='domcontentloaded', timeout=60000)
        print("[DEBUG] Page loaded successfully.")

        history = []
        history_dom = []  # <-- Collect DOM snapshots for each step
        prev_dom_elements = set()
        prev_element_count = 0
        prev_html = ""
        actions_log = []

        for step in range(50):
            await asyncio.sleep(1.5)  
            dom = await extract_dom_structure(page)
            history_dom.append(dom)  # Store current DOM snapshot

            # Stagnation check
            curr_html = await page.content()
            curr_dom_elements = set(
                el.get('id') or el.get('name') or el.get('text') for el in dom['elements']
            )

            if (
                curr_html == prev_html and
                prev_dom_elements == curr_dom_elements and
                len(dom["elements"]) == prev_element_count and
                step > 0
            ):
                print("[WARN] DOM unchanged . Attempting to continue with next action.")
                # break

            # Update for next step
            prev_dom_elements = curr_dom_elements
            prev_element_count = len(dom["elements"])
            prev_html = curr_html

            
            # Prompt to LLM
            title = await page.title()
            prompt = f"""
            Goal: Follow all of these steps without stopping early. Do NOT return a type "end" action until all steps have been completed:
            {goal_prompt}

            You are currently on Step {step + 1} of {steps_count}.
            Steps completed so far (up to Step {step}):
            {json.dumps(history, indent=2)}
            Current page title: {title}
            Current page URL: {page.url}
            Current DOM snapshot:
            {json.dumps(dom, indent=2)}
            Step to perform next:{step + 1}
            Only suggest actions that are relevant to the current step to move closer to the goal.
            Respond with a single valid JSON object in the format specified.
            """

            try:
                actions = await get_next_steps(prompt, llm_provider)
                print(f"[DEBUG] Executing action: {json.dumps(actions, indent=2)}")
            except Exception as e:
                print(f"[ERROR] LLM response could not be parsed: {e}")
                continue  

            # Check for 'end' action before executing actions
            if any(action.get("type") == "end" for action in actions):
                # Log the 'end' step
                actions_log.append({
                    "step": step + 1,
                    "action_type": actions[0].get("type", "end"),
                    "description": actions[0].get("description", ""),
                    "url": page.url,
                })
                if step + 1 < steps_count:
                    print("[ERROR] Flow ended prematurely, not all steps completed.")
                    return {
                        "error": f"LLM returned 'end' action before completing all steps. Expected {steps_count}, but got {len(history)}.",
                        "completed_steps": len(history),
                        "expected_steps": steps_count,
                        "actions_log": actions_log
                    }
                print(f"[INFO] Reached end of flow: {actions[0].get('description')}")
                break

            for action in actions:
                action_type = action.get("type")

                # Handle assert/verify
                if action_type in ["assert", "verify"]:
                    result = await execute_action(page, action)
                    actions_log.append({
                        "step": step + 1,
                        "action_type": action.get("type"),
                        "selector": action.get("selector"),
                        "expected": action.get("expected"),
                        "message": result.get("message", "No message"),
                        "description": action.get("description", ""),
                        "url": page.url,
                        "success": result.get("success", False)
                    })
                    # Add to history so LLM knows this step is done
                    history.append({
                        "step": step + 1,
                        "url": page.url,
                        "action": action,
                        "dom_snippet": dom
                    })
                    if not result.get("success", False):
                        print(f"[ERROR] Assertion failed: {result.get('message', '')}")
                        break
                    continue

                # Skip redundant navigation
                if action_type == "navigate" and page.url == action.get("url"):
                    print(f"[INFO] Skipping redundant navigation to {action.get('url')}")
                    history.append({
                        "step": step + 1,
                        "url": page.url,
                        "action": action,
                        "dom_snippet": dom
                    })
                    continue
                # Skip speculative close actions
                if (
                    action.get("description", "").lower().startswith("close")
                    and "close" not in goal_prompt.lower()
                    ):
                    print("[INFO] Skipping speculative close action not found in user prompt.")
                    continue

                print(f"[Step {step + 1}] Performing : {action.get('description', action)}")
                result = await execute_action(page, action)
                if not result.get("success", False):
                    print(f"[WARN] Skipping failed action: {action}")
                    actions_log.append({
                        "step": step + 1,
                        "action_type": action_type,
                        "selector": action.get("selector"),
                        "message": result.get("message", "No message"),
                        "url": page.url,
                        "success": False
                    })
                    continue

                actions_log.append({
                    "step": step + 1,
                    "action_type": action.get("type"),
                    "selector": action.get("selector"),
                    "index": action.get("index"),
                    "value": action.get("value"),
                    "description": action.get("description", ""),
                    "url": page.url,
                    "success": True
                })

                history.append({
                    "step": step + 1,
                    "url": page.url,
                    "action": action,
                    "dom_snippet": dom
                })

              
        # Save the final DOM structure
        final_dom = await extract_dom_structure(page)
        history_dom.append(final_dom)  # Store final DOM snapshot

        await browser.close()

        # Save the final DOM structure
        output_dir = os.path.join(FRAMEWORK_FOLDER)
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, "dom_flow_output.json")
        total_pages_scraped = len(history_dom)

        # Optionally save or print the actions log
        actions_log_path = os.path.join(FRAMEWORK_FOLDER, "actions_log.json")
        try:
            with open(actions_log_path, "w", encoding="utf-8") as f:
                json.dump(actions_log, f, indent=4)
            print(f"[INFO] Actions log saved to: {actions_log_path}")
        except Exception as e:
            print(f"[ERROR] Failed to save actions log: {e}")

        print(f"\n[DEBUG] Scraped {total_pages_scraped} DOM snapshots (pages)")
        print(f"[INFO] Attempting to write to: {output_path}")

        try:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(history_dom, f, indent=4)
            print(f"\n --> All DOM data saved to: {output_path}")
            print(f"\n --> All Action log data saved to: {actions_log_path}")
            return f"Scraped {len(history_dom)} pages. Output saved to {output_path}."

        except Exception as e:
            print(f"❌ Failed to write to {output_path}: {str(e)}")
            return f"❌ Failed to write output: {str(e)}"