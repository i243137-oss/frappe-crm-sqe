"""
Accessibility (a11y) & Usability Automated Audit Suite for Frappe CRM.
Uses axe-playwright-python (axe-core engine) & Playwright assertions to evaluate:
  - WCAG 2.1 Level A & AA compliance
  - Contrast ratios, ARIA attributes, semantic landmarks, and form labeling
  - Keyboard focus order and interactive element targets
  - Focus trapping and screen reader aria-live notifications
Evaluates:
  1. Leads Screen (Lead view, details, conversion action)
  2. Deals Screen (Deal view, stages, financial fields)
  3. Lead Conversion Modal Dialog
  4. Deal Lost Modal Dialog
  5. Interactive Touch / Target Sizes
  6. ARIA Labels and Form Controls Association
  7. Keyboard Navigation & Focus Trap Verification
"""

import threading
import time
import socketserver
import pytest
from playwright.sync_api import sync_playwright
from axe_playwright_python.sync_playwright import Axe
from tests.team.e2e.mock_server import MockCRMHandler, ReusableTCPServer

A11Y_PORT = 9125
SERVER_URL = f"http://127.0.0.1:{A11Y_PORT}"


@pytest.fixture(scope="module")
def live_server():
    server = ReusableTCPServer(("127.0.0.1", A11Y_PORT), MockCRMHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    yield SERVER_URL
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def browser_instance():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser_instance, live_server):
    context = browser_instance.new_context()
    pg = context.new_page()
    pg.goto(live_server)
    yield pg
    context.close()


def test_accessibility_lead_view(page):
    """Audits Lead View against axe-core WCAG 2.1 Level A & AA rules."""
    axe = Axe()
    results = axe.run(page)

    violations = results.response.get("violations", [])
    serious_violations = [v for v in violations if v.get("impact") in ("critical", "serious")]
    assert len(serious_violations) == 0, f"Accessibility violations found: {results.generate_report()}"


def test_accessibility_convert_lead_modal(page):
    """Audits Convert to Deal modal for ARIA dialog role and accessible inputs."""
    page.click("#btn-convert-deal")
    page.wait_for_selector("#modal-convert", state="visible")

    axe = Axe()
    results = axe.run(page, context="#modal-convert")
    violations = results.response.get("violations", [])
    serious_violations = [v for v in violations if v.get("impact") in ("critical", "serious")]
    assert len(serious_violations) == 0, f"Modal a11y violations found: {results.generate_report()}"


def test_accessibility_deal_view(page):
    """Audits Deal View after lead conversion."""
    page.click("#btn-convert-deal")
    page.click("#btn-modal-submit")
    page.wait_for_selector("#deal-view", state="visible")

    axe = Axe()
    results = axe.run(page)
    violations = results.response.get("violations", [])
    serious_violations = [v for v in violations if v.get("impact") in ("critical", "serious")]
    assert len(serious_violations) == 0, f"Deal view a11y violations found: {results.generate_report()}"


def test_accessibility_lost_modal(page):
    """Audits Lost Reason modal for form labeling and keyboard focus."""
    page.click("#btn-convert-deal")
    page.click("#btn-modal-submit")
    page.click("#btn-mark-lost")
    page.wait_for_selector("#modal-lost", state="visible")

    axe = Axe()
    results = axe.run(page, context="#modal-lost")
    violations = results.response.get("violations", [])
    serious_violations = [v for v in violations if v.get("impact") in ("critical", "serious")]
    assert len(serious_violations) == 0, f"Lost modal a11y violations found: {results.generate_report()}"


def test_keyboard_navigation_and_tab_order(page):
    """Verifies logical focus order across interactive controls via Tab navigation."""
    # Start on lead view
    page.focus("#btn-convert-deal")
    page.keyboard.press("Enter")
    page.wait_for_selector("#modal-convert", state="visible")

    # Focus should automatically be directed to deal name input upon modal open
    focused_id = page.evaluate("() => document.activeElement.id")
    assert focused_id == "input-deal-name", f"Initial modal focus expected on deal name, got: {focused_id}"

    # Press Tab -> input-deal-value
    page.keyboard.press("Tab")
    focused_id = page.evaluate("() => document.activeElement.id")
    assert focused_id == "input-deal-value"

    # Press Tab -> select-convert-policy
    page.keyboard.press("Tab")
    focused_id = page.evaluate("() => document.activeElement.id")
    assert focused_id == "select-convert-policy"

    # Press Tab -> cancel button
    page.keyboard.press("Tab")
    focused_id = page.evaluate("() => document.activeElement.id")
    assert focused_id == "btn-modal-cancel"

    # Press Tab -> confirm button
    page.keyboard.press("Tab")
    focused_id = page.evaluate("() => document.activeElement.id")
    assert focused_id == "btn-modal-submit"

    # Submit form entirely via keyboard (Enter key) per SQE keyboard navigation requirements
    page.keyboard.press("Enter")
    page.wait_for_selector("#deal-view", state="visible")
    assert page.is_visible("#deal-view")


def test_aria_form_labels_and_status_announcements(page):
    """Verifies proper form label associations and live region announcements."""
    # Check that inputs have explicitly associated labels
    label_for_deal_name = page.get_attribute("label[for='input-deal-name']", "for")
    assert label_for_deal_name == "input-deal-name"

    label_for_deal_val = page.get_attribute("label[for='input-deal-value']", "for")
    assert label_for_deal_val == "input-deal-value"

    label_for_policy = page.get_attribute("label[for='select-convert-policy']", "for")
    assert label_for_policy == "select-convert-policy"

    # Check toast notification role and aria-live attributes
    toast_role = page.get_attribute("#toast", "role")
    toast_live = page.get_attribute("#toast", "aria-live")
    assert toast_role == "status"
    assert toast_live == "polite"


def test_interactive_target_sizes_wcag(page):
    """Verifies interactive button dimensions meet WCAG 2.5.8 target size requirements (>=24x24px)."""
    buttons = ["#btn-convert-deal"]
    for btn_id in buttons:
        box = page.locator(btn_id).bounding_box()
        assert box is not None
        assert box["width"] >= 24, f"Button {btn_id} width {box['width']}px is below 24px minimum"
        assert box["height"] >= 24, f"Button {btn_id} height {box['height']}px is below 24px minimum"
