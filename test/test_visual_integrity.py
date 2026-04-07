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
