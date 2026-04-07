import os
import re
import pytest

def get_public_path(filename):
    return os.path.join(os.path.dirname(__file__), '..', 'public', filename)

def test_no_solid_glow_boxes():
    """
    Test that elements intended for glows do not have solid background colors 
    which might appear as 'boxes' if filters fail or are misconfigured.
    """
    css_path = get_public_path('audience.css')
    with open(css_path, 'r') as f:
        content = f.read()

    # Pattern to find background colors in specific 'glow' elements
    # We want to ensure text-based glows use background: transparent
    patterns = [
        (r'#countdownText\s*\{[^}]*?background:\s*([^;!]+)', 'transparent'),
        (r'#countdownText\.goldsprint-text\s*\{[^}]*?background:\s*([^;!]+)', 'transparent'),
        (r'\.champion-name\s*\{[^}]*?background:\s*([^;!]+)', 'transparent')
    ]

    for pattern, expected in patterns:
        match = re.search(pattern, content, re.DOTALL)
        if match:
            actual = match.group(1).strip()
            assert actual == expected, f"Glow element background should be {expected}, found '{actual}'"

def test_no_obsolete_glow_elements():
    """
    Test that separate divs used for glows (prone to artifacting) are removed 
    in favor of box-shadows.
    """
    html_path = get_public_path('audience.html')
    with open(html_path, 'r') as f:
        content = f.read()

    # champion-glow was a common source of 'visible boxes'
    assert 'class="champion-glow"' not in content, "Obsolete 'champion-glow' div should be removed."

def test_animations_defined():
    """
    Ensure all referenced animations in audience.css are actually defined.
    """
    css_path = get_public_path('audience.css')
    with open(css_path, 'r') as f:
        content = f.read()

    # Find all animation: NAME ...
    animations = re.findall(r'animation:\s*([a-zA-Z0-9_-]+)', content)
    # Also find animation-name: NAME
    animations += re.findall(r'animation-name:\s*([a-zA-Z0-9_-]+)', content)
    
    # Unique referenced animations
    referenced = set(animations)
    
    # Find all @keyframes NAME
    defined = set(re.findall(r'@keyframes\s*([a-zA-Z0-9_-]+)', content))
    
    for anim in referenced:
        # Ignore some common browser-specific or dynamic animations if any
        if anim in ['none', 'initial', 'inherit']: continue
        assert anim in defined, f"Animation '{anim}' is referenced but not defined in CSS."

def test_high_contrast_visibility():
    """
    Check for potential low-visibility or grey-on-grey issues in critical UI elements.
    """
    css_path = get_public_path('audience.css')
    with open(css_path, 'r') as f:
        content = f.read()
        
    # Check that loser opacity is low but not invisible
    loser_match = re.search(r'\.aud-bracket-slot\.loser\s*\{[^}]*?opacity:\s*([^;!]+)', content)
    if loser_match:
        opacity = float(loser_match.group(1))
        assert 0.1 <= opacity <= 0.4, "Loser opacity should be low for contrast but still slightly visible."

def test_audience_view_sync_bug():
    """
    REPRODUCTION: Bug 2 (Audience View Sync).
    Checks if audience.js actually updates the #targetDistValue DOM element.
    This test statically audits the JS for the required update logic.
    """
    js_path = get_public_path('audience.js')
    with open(js_path, 'r') as f:
        content = f.read()

    # The bug is that state.targetDist is received but UI.targetDist is never updated.
    # We look for a line that sets UI.targetDist.textContent or .innerText.
    # Specifically, it should look something like: UI.targetDist.textContent = state.targetDist;
    
    # We want to see 'UI.targetDist.textContent' (or innerText) being assigned.
    update_patterns = [
        r'UI\.targetDist\.textContent\s*=',
        r'UI\.targetDist\.innerText\s*=',
        r'UI\.targetDist\.innerHTML\s*='
    ]
    
    found = False
    for p in update_patterns:
        if re.search(p, content):
            found = True
            break
            
    assert found, "BUG 2 CONFIRMED: audience.js does NOT contain logic to update the target distance DOM element (#targetDistValue)!"

def test_admin_drag_and_context_logic_audit():
    """
    REPRODUCTION: Audit for Bug 1 (Broken Drag/Drop) and Bug 2 (Disappearing Menu).
    Statically audits admin.js for robust logic.
    """
    js_path = get_public_path('admin.js')
    with open(js_path, 'r') as f:
        content = f.read()

    # Bug 1 Audit: canDrag must check for winners across all rounds, not just active_match
    # We expect a check that uses .some() or .flat() on the bracket.
    assert 'bracket.flat().some' in content or '.some(round => round.some' in content, "BUG 1: canDrag logic is not checking across all rounds."
    
    # Bug 2 Audit: Menu closing must have a time-based or flag-based debounce
    assert 'Date.now() - menuOpenTime' in content or 'setTimeout' in content, "BUG 2: Context menu closing has no debounce/delay logic."

def test_admin_champion_button_audit():
    """
    REPRODUCTION: Phase 1 (Admin Champion Button Fix).
    Audits admin.js to ensure it uses the new .champions dictionary instead of .champion.
    """
    js_path = get_public_path('admin.js')
    with open(js_path, 'r') as f:
        content = f.read()

    # The bug is using bracketState.champion (old) vs bracketState.champions (new dict)
    # We want to see 'bracketState.champions' and specific category indexing.
    assert 'bracketState.champions' in content, "Admin View is not using the new 'champions' dictionary."
    
    # Check that we are looking for the champion of the active category
    assert 'bracketState.champions[activeCategory]' in content or 'bracketState.champions[cat]' in content, "Admin View is not checking for champions per-category."

def test_audience_smart_visualization_audit():
    """
    REPRODUCTION: Phase 2 (Audience Smart Visualization).
    Audits audience.js for auto-cycling and auto-centering logic.
    """
    js_path = get_public_path('audience.js')
    with open(js_path, 'r') as f:
        content = f.read()

    # 1. Check for Auto-Cycling (Timer based)
    assert 'setInterval' in content and '15000' in content, "Audience View lacks 15s auto-cycling timer."
    
    # 2. Check for Race Override (Locking to active match category)
    assert 'active_match?.category' in content or 'active_match.category' in content, "Audience View does not lock to active race category."
    
    # 3. Check for Auto-Centering (Scrolling to active match)
    assert 'scrollIntoView' in content, "Audience View lacks active match auto-centering (scrollIntoView)."

def test_audience_auto_cycle_render():
    """
    REPRODUCTION: Phase 2 (Auto-Cycle Render Bug).
    Audits audience.js to ensure handleBracket is explicitly called during cycling.
    """
    js_path = get_public_path('audience.js')
    with open(js_path, 'r') as f:
        content = f.read()
        
    # Get the code block inside setInterval
    set_interval_block = content.split('setInterval(() => {')[1].split('}, 15000)')[0]
    assert 'handleBracket' in set_interval_block, "handleBracket is not called inside setInterval to trigger a re-render during cycling."

def test_audience_css_scaling():
    """
    REPRODUCTION: Phase 2 (Audience CSS Scaling for 16-participant bracket).
    Audits audience.css to ensure matches shrink sufficiently to fit 8 vertically.
    """
    css_path = get_public_path('audience.css')
    with open(css_path, 'r') as f:
        content = f.read()
        
    # Margin should be small or 0 for flex-shrink to work nicely, and flex-shrink should not be 0.
    # Currently it might be 'flex-shrink: 0' and 'margin: 1vh 0'
    assert 'flex-shrink: 0' not in content.split('.aud-bracket-match')[1].split('}')[0], "aud-bracket-match must be allowed to shrink (no flex-shrink: 0)."
    assert 'clamp(0.8rem' in content or 'clamp(0.5rem' in content, "aud-bracket-slot font size clamp is not small enough to fit 16 participants."

def test_audience_no_scroll_audit():
    """
    REPRODUCTION: Bracket No-Scroll Fit Bug.
    Ensures .bracket-wrapper uses overflow: hidden and flexbox is properly constrained.
    """
    css_path = get_public_path('audience.css')
    with open(css_path, 'r') as f:
        content = f.read()
    
    wrapper_block = content.split('.bracket-wrapper {')[1].split('}')[0]
    assert 'overflow: hidden' in wrapper_block, "bracket-wrapper MUST have overflow: hidden to prevent scrolling."
    assert 'display: flex' in wrapper_block, "bracket-wrapper must be a flex container to constrain its children."

    slot_block = content.split('.aud-bracket-slot {')[1].split('}')[0]
    assert 'min(' in slot_block or 'vh' in slot_block, "aud-bracket-slot font size clamp must incorporate vh constraints to prevent vertical overflow."

def test_svg_relative_rect_audit():
    """
    REPRODUCTION: Missing SVG Lines Bug.
    Ensures drawBracketLines uses getBoundingClientRect relative to the container.
    """
    js_path = get_public_path('audience.js')
    with open(js_path, 'r') as f:
        content = f.read()
        
    func_block = content.split('function drawBracketLines')[1].split('function')[0]
    assert 'getBoundingClientRect()' in func_block, "drawBracketLines MUST use getBoundingClientRect() to avoid offsetParent bugs."
    assert 'containerRect.left' in func_block and 'containerRect.top' in func_block, "SVG coordinates must be calculated relative to containerRect."

def test_bracket_svg_hierarchy():
    """
    REPRODUCTION: Audit for SVG Disconnection bug.
    Ensures that the bracket SVG is a child of the scrollable container.
    """
    html_path = get_public_path('audience.html')
    with open(html_path, 'r') as f:
        content = f.read()
        
    # SVG should be inside audienceBracketContainer
    # We look for <div id="audienceBracketContainer"... followed by <svg id="bracketSvg"
    assert '<div id="audienceBracketContainer" class="audience-bracket-container">\n                    <svg id="bracketSvg"' in content or '<div id="audienceBracketContainer" class="audience-bracket-container"><svg id="bracketSvg"' in content, "SVG is not a child of the scrollable container."

def test_bracket_vertical_compression_audit():
    """
    REPRODUCTION: Audit for 16-participant fit bug.
    Ensures margins and paddings are tight enough.
    """
    css_path = get_public_path('audience.css')
    with open(css_path, 'r') as f:
        content = f.read()
        
    # Check for small match margin
    assert 'margin: 0.5vh 0' in content or 'margin: 0.2vh 0' in content, "Bracket match margins are too large for 16 participants."
    # Check for small slot padding
    assert 'padding: 0.5vh 1vw' in content or 'padding: 0.4vh 1vw' in content or 'padding: 0.2vh 1vw' in content, "Bracket slot vertical padding is too large."






