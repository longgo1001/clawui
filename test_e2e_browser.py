#!/usr/bin/env python3
"""E2E Browser Automation Test - Create repo flow.

Tests CDP-based browser automation capabilities.
If GitHub is not authenticated, tests form interaction on login page
and reports auth as the blocking issue.
"""

import sys, os, time, logging, json

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] %(message)s',
    handlers=[logging.FileHandler('/tmp/e2e_browser.log', mode='w'), logging.StreamHandler()])
log = logging.info

sys.path.insert(0, '/home/hung/.openclaw/workspace/skills/gui-automation')
from src.cdp_helper import CDPClient

def ensure_cdp():
    """Ensure CDP is available."""
    import subprocess
    client = CDPClient()
    if client.is_available():
        return client
    log("Launching Chromium with CDP...")
    subprocess.Popen(['snap', 'run', 'chromium',
        '--remote-debugging-port=9222', '--remote-allow-origins=*',
        '--no-first-run', 'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    if client.is_available():
        return client
    return None

def test_navigation(client):
    """Test basic navigation."""
    log("--- Navigation Test ---")
    ok = client.navigate("https://github.com")
    time.sleep(2)
    title = client.get_page_title()
    url = client.get_page_url()
    log(f"  Title: {title}")
    log(f"  URL: {url}")
    passed = "github" in (title + url).lower()
    log(f"  Result: {'PASS' if passed else 'FAIL'}")
    return passed

def test_form_interaction(client):
    """Test form field interaction via CDP JS injection."""
    log("--- Form Interaction Test ---")
    client.navigate("https://github.com/login")
    time.sleep(2)

    # Type into login field
    client.type_in_element('input#login_field', 'e2e_test_user')
    val = client.evaluate('document.querySelector("input#login_field").value')
    typed_ok = val and val.get("result", {}).get("value") == "e2e_test_user"
    log(f"  Type text: {'PASS' if typed_ok else 'FAIL'}")

    # Click test (button exists?)
    btn = client.evaluate('!!document.querySelector("input[type=submit]")')
    btn_ok = btn and btn.get("result", {}).get("value") == True
    log(f"  Button found: {'PASS' if btn_ok else 'FAIL'}")

    # Clean up
    client.evaluate('document.querySelector("input#login_field").value = ""')
    client.evaluate('document.querySelector("input[name=password]").value = ""')

    passed = typed_ok and btn_ok
    log(f"  Result: {'PASS' if passed else 'FAIL'}")
    return passed

def test_github_auth(client):
    """Check if GitHub is authenticated (required for repo creation)."""
    log("--- GitHub Auth Check ---")
    client.navigate("https://github.com/new")
    time.sleep(3)
    url = client.get_page_url()
    is_authed = "/login" not in url
    log(f"  URL: {url}")
    log(f"  Authenticated: {is_authed}")
    if not is_authed:
        log("  BLOCKER: Not logged into GitHub in browser.")
        log("  Fix: Log into GitHub in Chromium, or install `gh` CLI with token.")
    return is_authed

def test_create_repo(client):
    """Create a test repo via browser automation (requires auth)."""
    log("--- Create Test Repo ---")
    url = client.get_page_url()
    if "/login" in url:
        log("  SKIP: Not authenticated")
        return None  # Skip, not fail

    # Fill repo name
    repo_name = f"e2e-test-{int(time.time())}"
    client.type_in_element('input#repository_name', repo_name)
    time.sleep(1)

    # Check for name availability
    avail = client.evaluate('document.querySelector(".js-repo-name-validity")?.textContent?.trim()')
    log(f"  Repo name '{repo_name}': {avail}")

    # Select private
    client.click_element('input#repository_visibility_private')
    time.sleep(0.5)

    # Add README
    client.click_element('input#repository_auto_init')
    time.sleep(0.5)

    # Click create
    client.click_element('button[data-disable-with="Creating repository…"]')
    time.sleep(5)

    # Verify
    final_url = client.get_page_url()
    created = repo_name in final_url
    log(f"  Final URL: {final_url}")
    log(f"  Result: {'PASS' if created else 'FAIL'}")

    if created:
        log(f"  Cleanup: delete repo {repo_name} manually or via API")

    return created

def main():
    client = ensure_cdp()
    if not client:
        log("FATAL: Cannot connect to CDP")
        return 1

    results = {}
    results["navigation"] = test_navigation(client)
    results["form_interaction"] = test_form_interaction(client)
    results["github_auth"] = test_github_auth(client)

    if results["github_auth"]:
        results["create_repo"] = test_create_repo(client)
    else:
        results["create_repo"] = None  # skipped

    log("\n=== Summary ===")
    all_pass = True
    for name, ok in results.items():
        if ok is None:
            status = "SKIP"
        elif ok:
            status = "PASS"
        else:
            status = "FAIL"
            all_pass = False
        log(f"  {name}: {status}")

    if not results["github_auth"]:
        log("\n⚠️  BOTTLENECK: GitHub not authenticated in browser.")
        log("   To fix: Log into github.com in Chromium (port 9222),")
        log("   or set GITHUB_TOKEN env and install gh CLI.")
        # Return special code for auth issue
        return 2

    return 0 if all_pass else 1

if __name__ == "__main__":
    sys.exit(main())
