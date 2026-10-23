from pathlib import Path


def test_navigation_theme_and_accessibility_are_wired():
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    js = (root / "static" / "stage-o.js").read_text(encoding="utf-8")
    css = (root / "static" / "stage-o.css").read_text(encoding="utf-8")
    for value in ('id="primary-nav"', 'id="theme-choice"', 'href="#ask-lazhelper"',
                  'href="#owner-controls"', 'class="skip-link"'):
        assert value in html
    assert 'localStorage.setItem("lazhelper-theme"' in js
    assert 'aria-expanded' in js
    assert 'prefers-reduced-motion:reduce' in css
    assert 'data-theme="dark"' in css
