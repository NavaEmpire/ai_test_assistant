# === tools/assertion_utils.py ===
async def handle_assertion(page, action, locator=None, timeout=10000) -> dict:
    subtype = action.get("subtype")
    expected = action.get("expected")
    selector = action.get("selector")
    attribute = action.get("attribute")
    description = action.get("description", f"Assertion of type '{subtype}'")

    result = {
        "type": "assert",
        "subtype": subtype,
        "selector": selector,
        "expected": expected,
        "actual": None,
        "description": description,
        "success": False,
        "message": ""
    }

    try:
        match subtype:
            case "not_visible":
                is_hidden = await locator.evaluate("el => el.offsetParent === null")
                result["success"] = is_hidden
                result["message"] = (
                    "Element is not visible as expected " if is_hidden else "Element is still visible "
                )

            case "text":
                element_text = await locator.inner_text()
                result["actual_value"] = element_text
                expected_str = str(expected).strip().lower() if expected else ""
                result["success"] = expected_str in element_text.lower()
                result["message"] = (
                    f"Element text contains '{expected}' "
                    if result["success"]
                    else f"Element text '{element_text}' does not contain '{expected}'"
                )

            case "assert_value":
                if selector:
                    locator = page.locator(selector)
                    actual_value = await locator.input_value()
                    result["actual_value"] = actual_value
                    result["success"] = actual_value == expected
                    result["message"] = f"Input value: expected '{expected}', got '{actual_value}'"
                else:
                    result["message"] = "No selector provided for value check "

            case "attribute":
                if selector and attribute:
                    locator = page.locator(selector)
                    actual_attr = await locator.get_attribute(attribute)
                    result["actual_value"] = actual_attr
                    result["success"] = actual_attr == expected
                    result["message"] = f"Attribute '{attribute}': expected '{expected}', got '{actual_attr}'"
                else:
                    result["message"] = "Missing selector or attribute for attribute check "

            case "count":
                count = await locator.count()
                result["actual_value"] = count
                try:
                    expected_count = int(expected)
                except (TypeError, ValueError):
                    expected_count = expected
                result["success"] = count == expected_count
                result["message"] = (
                    f"Found {count} elements as expected "
                    if result["success"]
                    else f"Expected {expected_count} elements, but found {count} "
                )

            case "url":
                expected_url = expected if expected is not None else action.get("url")
                current_url = page.url
                result["actual_value"] = current_url
                if expected_url is not None:
                    result["success"] = str(expected_url) in str(current_url)
                    result["message"] = (
                        f"URL contains '{expected_url}' "
                        if result["success"]
                        else f"URL '{current_url}' does not contain '{expected_url}' "
                    )
                else:
                    result["success"] = False
                    result["message"] = "No expected URL provided for assertion."

            case "title":
                title = await page.title()
                result["actual_value"] = title
                result["success"] = expected.lower() in title.lower()
                result["message"] = (
                    f"Title contains '{expected}' "
                    if result["success"]
                    else f"Title '{title}' does not contain '{expected}' "
                )

            case "assert_enabled":
                if selector:
                    locator = page.locator(selector)
                    is_enabled = await locator.is_enabled()
                    result["actual_value"] = is_enabled
                    result["success"] = is_enabled == expected
                    result["message"] = f"Enabled state: expected {expected}, got {is_enabled}"
                else:
                    result["message"] = "No selector provided for enabled check "

            case "assert_selected":
                if selector:
                    locator = page.locator(selector)
                    is_checked = await locator.is_checked()
                    result["actual_value"] = is_checked
                    result["success"] = is_checked == expected
                    result["message"] = f"Selected state: expected {expected}, got {is_checked}"
                else:
                    result["message"] = "No selector provided for selected check "
            
            case "visibility":
                is_visible = await locator.is_visible()
                result["actual_value"] = is_visible
                result["success"] = bool(expected) == is_visible
                result["message"] = f"Visibility expected: {expected}, actual: {is_visible}"

            case _:
                result["message"] = f"Unknown assertion subtype: {subtype} "

    except Exception as e:
        result["message"] = f"Assertion execution failed: {str(e)} "
        result["success"] = False

    return result
