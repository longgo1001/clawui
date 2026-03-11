#!/usr/bin/env python3
"""
CDP-based GitHub repo creation automation.
Steps:
1. Launch Chromium with CDP
2. Navigate to github.com/login (or assume logged in)
3. If login needed, prompt user (skip in demo)
4. Navigate to /new
5. Fill repo name, description, options
6. Create repository
7. Verify creation
"""

import sys, os, subprocess, time, json

sys.path.insert(0, '/home/hung/.openclaw/workspace/skills/gui-automation')
from src.cdp_helper import CDPClient

# Config
REPO_NAME = "clawui-test-repo-" + str(int(time.time()))
REPO_DESC = "Test repository created via CDP automation"

def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}")

def ensure_chromium():
    """Start Chromium with CDP if not running."""
    client = CDPClient()
    if client.is_available():
        log("Chromium CDP already available")
        return client
    log("Launching Chromium...")
    subprocess.Popen(['snap', 'run', 'chromium',
        '--remote-debugging-port=9222',
        '--remote-allow-origins=*',
        '--no-first-run',
        'about:blank'],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(10):
        if client.is_available():
            log("Chromium ready")
            return client
        time.sleep(1)
    raise RuntimeError("Chromium failed to start")

def navigate_and_check_login(client: CDPClient):
    """Go to GitHub, check if logged in."""
    client.navigate("https://github.com")
    time.sleep(3)
    title = client.get_page_title()
    log(f"Page: {title}")

    # Look for "Sign in" link or button
    if "sign in" in title.lower():
        log("Not logged in. Opening login page...")
        client.navigate("https://github.com/login")
        time.sleep(2)
        log("⚠️  Not logged in. Skipping automation (would need credentials).")
        return False  # cannot proceed
    else:
        log("Already logged in")
        return True

def create_repo_via_cdp(client: CDPClient):
    """Navigate to new repo page and create."""
    log("Navigating to new repo page...")
    client.navigate("https://github.com/new")
    time.sleep(3)

    # Fill repo name: document.querySelector('input[name="repository[name]"]').value = '...'
    js = f'''
    (function() {{
        const nameInput = document.querySelector('input[name="repository[name]"]');
        if (!nameInput) return "no-name-field";
        nameInput.value = "{REPO_NAME}";
        nameInput.dispatchEvent(new Event('input', {{bubbles:true}}));
        // Also fill description if field exists
        const descInput = document.querySelector('input[name="repository[description]"], textarea[name="repository[description]"]');
        if (descInput) {{
            descInput.value = "{REPO_DESC}";
            descInput.dispatchEvent(new Event('input', {{bubbles:true}}));
        }}
        // Enable public repo (uncheck "Private" if needed)
        const publicRadio = document.querySelector('input[name="repository[visibility]"]');
        if (publicRadio) publicRadio.checked = true;
        return "filled";
    }})()
    '''
    result = client.evaluate(js)
    log(f"Form fill result: {result}")

    # Click Create repository button
    # Wait a bit for any UI updates
    time.sleep(1)
    click_js = '''
    (function() {
        const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim().includes('Create repository'));
        if (btn) { btn.click(); return "clicked"; }
        return "not-found";
    })()
    '''
    click_res = client.evaluate(click_js)
    log(f"Create button click: {click_res}")

    time.sleep(3)  # Wait for redirect
    current_url = client.get_page_url()
    log(f"Current URL: {current_url}")
    return REPO_NAME in current_url

def verify_via_git():
    """Verify repo exists via git ls-remote."""
    repo_url = f"git@github.com:longgo1001/{REPO_NAME}.git"
    log(f"Verifying via git: {repo_url}")
    result = subprocess.run(['git', 'ls-remote', repo_url], capture_output=True, text=True, timeout=10)
    if result.returncode == 0:
        log("✅ Repository verified")
        return True
    else:
        log(f"❌ Repo not found: {result.stderr}")
        return False

def main():
    log(f"=== GitHub Repo Creation via CDP ===")
    log(f"Target repository: {REPO_NAME}")

    try:
        client = ensure_chromium()
        # Quick check login status; if not logged in, abort gracefully
        client.navigate("https://github.com")
        time.sleep(2)
        title = client.get_page_title()
        if "sign in" in title.lower():
            log("⚠️  Not logged in to GitHub. Please log in first, then re-run.")
            return 2  # special code for auth needed
        # Proceed to create repo
        if create_repo_via_cdp(client):
            log("✅ Repo created in browser")
            if verify_via_git():
                log("✅ End-to-End SUCCESS")
                return 0
            else:
                log("⚠️ Browser created but git verification failed")
                return 1
        else:
            log("❌ Failed to create repo")
            return 1
    except Exception as e:
        log(f"❌ Error: {e}")
        import traceback
        log(traceback.format_exc())
        return 1

if __name__ == "__main__":
    sys.exit(main())
