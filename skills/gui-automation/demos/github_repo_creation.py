#!/usr/bin/env python3
"""
End-to-end GitHub repository creation using CDP browser automation.

Prerequisites:
- Chromium headless running with --remote-debugging-port=9222
- GitHub cookies synced from the user's main browser profile
  (see sync_browser_cookies() or run: cp ~/.../chromium/Default/Cookies ~/.../clawui-profile-9222/Default/Cookies)

The script will:
1. Navigate to github.com/new
2. Fill in repo name and description
3. Click "Create repository"
4. Verify success via URL check
"""

import sys, os, time, json, re

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from cdp_helper import CDPClient


def sync_browser_cookies(port: int = 9222) -> bool:
    """Copy cookies from the user's main Chromium profile to the CDP headless profile.
    
    This enables the headless browser to share the user's authenticated sessions
    (GitHub, etc.) without needing separate login flows.
    
    Returns True if cookies were synced successfully.
    """
    import shutil
    
    snap_common = os.path.join(os.path.expanduser("~"), "snap", "chromium", "common")
    src = os.path.join(snap_common, "chromium", "Default", "Cookies")
    dst = os.path.join(snap_common, f"clawui-profile-{port}", "Default", "Cookies")
    
    if not os.path.exists(src):
        print(f"  [cookie-sync] Source cookies not found: {src}")
        return False
    
    if not os.path.isdir(os.path.dirname(dst)):
        print(f"  [cookie-sync] CDP profile not found: {os.path.dirname(dst)}")
        return False
    
    try:
        shutil.copy2(src, dst)
        # Also copy WAL/SHM if they exist
        for ext in ['-wal', '-shm']:
            src_ext = src + ext
            dst_ext = dst + ext
            if os.path.exists(src_ext):
                shutil.copy2(src_ext, dst_ext)
        print("  [cookie-sync] Cookies synced from main profile")
        return True
    except Exception as e:
        print(f"  [cookie-sync] Failed: {e}")
        return False


def main():
    c = CDPClient()
    if not c.is_available():
        print("ERROR: CDP not available. Start Chromium with --remote-debugging-port=9222")
        return False

    print("=== GitHub Repo Creation E2E Demo ===\n")

    # 1. Navigate to new repo page
    url = "https://github.com/new"
    print(f"1. Navigate to {url}")
    c.navigate(url)
    time.sleep(4)

    # 2. Check if we're logged in
    title = c.evaluate('document.title')['result']['value']
    if 'Sign in' in title or 'Login' in title:
        print("   Not logged in. Attempting cookie sync...")
        if sync_browser_cookies():
            # Reload after cookie sync
            c.navigate(url)
            time.sleep(4)
            title = c.evaluate('document.title')['result']['value']
            if 'Sign in' in title or 'Login' in title:
                print("   ERROR: Still not logged in after cookie sync.")
                return False
        else:
            print("   ERROR: Cookie sync failed. Sign in manually in the browser.")
            return False

    login_check = c.evaluate('document.querySelector(\'a[href*="login"]\') !== null')
    if login_check.get('result', {}).get('value'):
        print("   WARNING: Login link detected, may not be fully authenticated.")

    print(f"   Page: {title}")

    # 3. Generate a unique repo name
    repo_name = f"clawui-demo-repo-{int(time.time())}"
    print(f"2. Repository name: {repo_name}")

    # 4. Fill repository name
    # GitHub's React UI uses id="repository-name-input" (updated 2025+)
    # Fallback to legacy id="repository_name"
    print("3. Filling repository name field...")
    fill_result = c.evaluate(f'''
        (function() {{
            var el = document.getElementById("repository-name-input") ||
                     document.getElementById("repository_name");
            if (!el) return "input-not-found";
            var setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, "value").set;
            setter.call(el, "{repo_name}");
            el.dispatchEvent(new Event("input", {{ bubbles: true }}));
            el.dispatchEvent(new Event("change", {{ bubbles: true }}));
            return "filled";
        }})()
    ''')
    status = fill_result.get('result', {}).get('value', '')
    if status != 'filled':
        print(f"   ERROR: Could not fill repo name: {status}")
        return False
    time.sleep(2)

    # 5. Fill description
    c.evaluate('''
        (function() {
            var el = document.querySelector('input[name="Description"]') ||
                     document.getElementById("repository_description");
            if (!el) return "not-found";
            var setter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, "value").set;
            setter.call(el, "Created by ClawUI CDP automation demo");
            el.dispatchEvent(new Event("input", { bubbles: true }));
            return "filled";
        })()
    ''')
    time.sleep(1)

    # 6. Click "Create repository" button
    print("4. Creating repository...")
    create_result = c.evaluate('''
        (function() {
            var btns = Array.from(document.querySelectorAll('button, [type="submit"]'));
            var createBtn = btns.find(b => b.textContent.trim().includes('Create repository'));
            if (createBtn) {
                if (createBtn.disabled) return 'disabled';
                createBtn.click();
                return 'clicked';
            }
            return 'not-found';
        })()
    ''')
    click_status = create_result.get('result', {}).get('value', '')
    print(f"   Button status: {click_status}")
    if click_status != 'clicked':
        print(f"   ERROR: Could not click create button")
        return False
    time.sleep(5)

    # 7. Verify success: URL should contain /<username>/<repo_name>
    current_url = c.get_page_url()
    print(f"5. Current URL: {current_url}")

    if re.search(r"github\.com/[^/]+/" + re.escape(repo_name), current_url):
        print(f"\n✅ SUCCESS: Repository '{repo_name}' created!")
        return True
    else:
        print("\n❌ FAIL: Could not confirm creation.")
        # Take a screenshot for debugging
        ss = c.take_screenshot()
        if ss:
            import base64
            with open("/tmp/e2e-fail-screenshot.png", "wb") as f:
                f.write(base64.b64decode(ss))
            print("   Screenshot saved to /tmp/e2e-fail-screenshot.png")
        return False


if __name__ == "__main__":
    success = main()
    print("\n=== E2E Demo finished ===")
    sys.exit(0 if success else 1)
