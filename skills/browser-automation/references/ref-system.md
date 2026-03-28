# Ref System — Element Addressing

## Overview

Instead of CSS selectors or XPath, elements are addressed by short refs: `@e1`, `@e2`, etc. Refs are built from the page's accessibility tree, making them resilient to CSS class changes, framework hydration, and Shadow DOM.

## How Refs Are Built

1. Daemon captures accessibility tree via `page.accessibility.snapshot()`
2. Walks tree, assigns refs to interactive elements:
   - Buttons, links, text inputs, checkboxes, radio buttons
   - Select dropdowns, textareas, sliders
   - Any element with an explicit ARIA role
3. Each ref maps to a Playwright locator (not a CSS selector)

## Ref Format

```
@e1: button "Sign In"
@e2: textbox "Email address"
@e3: textbox "Password"
@e4: link "Forgot password?"
@e5: checkbox "Remember me"
```

## Usage in Commands

```bash
# Click the Sign In button
browser-cli.py click @e1

# Type into email field
browser-cli.py type @e2 "user@example.com"

# Check the remember me box
browser-cli.py click @e5
```

## Lifecycle

- **Created:** After each navigation or page-changing action
- **Cleared:** On new navigation (old refs become invalid)
- **Refreshed:** Call `refs` to get current mapping
- **Stale detection:** If ref's element count changes, warn agent

## Limitations

- Refs only cover interactive/labeled elements
- Decorative elements (images, divs) without ARIA roles are excluded
- For non-interactive elements, fall back to CSS selector via `/evaluate`
