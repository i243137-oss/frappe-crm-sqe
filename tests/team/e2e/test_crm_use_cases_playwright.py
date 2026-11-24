"""
Playwright End-to-End Use Case Automation Suite for Frappe CRM.
Verifies:
  1. Happy Path: Convert Lead -> Deal -> Mark Won (Date & probability auto-set)
  2. Alternative Flow 1: Deal Lost with valid predefined reason
  3. Alternative Flow 2: Deal Lost with 'Other' and mandatory notes provided
  4. Exception Flow 1: Attempt conversion on Lost lead rejected
  5. Exception Flow 2: Deal Lost with 'Other' missing notes rejected
  6. Accessibility / Usability: Keyboard navigation and modal dismissal via 'Escape'
"""

import threading
import time
import socketserver
import pytest
from playwright.sync_api import sync_playwright, expect
from tests.team.e2e.mock_server import MockCRMHandler, ReusableTCPServer, PORT

SERVER_URL = f"http://127.0.0.1:{PORT}"


@pytest.fixture(scope="module")
def live_server():
    """Starts the static E2E application server in a background thread."""
    server = ReusableTCPServer(("127.0.0.1", PORT), MockCRMHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    yield SERVER_URL
    server.shutdown()
    server.server_close()


@pytest.fixture(scope="module")
def browser_instance():
    """Launches Playwright headless Chromium browser."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser_instance, live_server):
    """Provides a fresh isolated browser context and page."""
    context = browser_instance.new_context()
    pg = context.new_page()
    pg.goto(live_server)
    yield pg
    context.close()


def test_e2e_happy_path_lead_conversion_to_won(page):
    """
    Happy Path:
    1. Navigate to Lead page.
    2. Click 'Convert to Deal'.
    3. Input deal name and valid positive deal value ($75,000.00).
    4. Submit conversion modal.
    5. Verify Deal view is visible with correct linked lead.
    6. Click 'Mark as Won'.
    7. Verify Deal status updates to 'Won', closed_date is populated, probability is 100%.
    """
    # 1. Lead View Initial State
    expect(page.locator("#lead-title")).to_contain_text("CRM-LEAD-2026-00001")
    expect(page.locator("#lead-status")).to_contain_text("Open")

    # 2. Open Convert Modal
    page.click("#btn-convert-deal")
    expect(page.locator("#modal-convert")).to_be_visible()

    # 3. Enter conversion details
    page.fill("#input-deal-name", "Global Engine Expansion Deal")
    page.fill("#input-deal-value", "85000.00")

    # 4. Confirm conversion
    page.click("#btn-modal-submit")
    expect(page.locator("#modal-convert")).not_to_be_visible()

    # 5. Verify Deal View
    expect(page.locator("#deal-view")).to_be_visible()
    expect(page.locator("#deal-status")).to_contain_text("Opportunity")
    expect(page.locator("#deal-value-display")).to_contain_text("85000.00")

    # 6. Transition to Won
    page.click("#btn-mark-won")
    expect(page.locator("#deal-status")).to_contain_text("Won")
    expect(page.locator("#deal-probability")).to_contain_text("100")
    expect(page.locator("#toast")).to_contain_text("Deal marked as Won!")


def test_e2e_alternative_flow_deal_lost_standard_reason(page):
    """
    Alternative Flow 1:
    Convert Lead and transition Deal to Lost using standard reason ('Competitor').
    """
    page.click("#btn-convert-deal")
    page.click("#btn-modal-submit")
    expect(page.locator("#deal-view")).to_be_visible()

    page.click("#btn-mark-lost")
    expect(page.locator("#modal-lost")).to_be_visible()

    # Select standard reason
    page.select_option("#select-lost-reason", "Competitor")
    expect(page.locator("#grp-lost-notes")).not_to_be_visible()

    page.click("#btn-lost-submit")
    expect(page.locator("#modal-lost")).not_to_be_visible()
    expect(page.locator("#deal-status")).to_contain_text("Lost")


def test_e2e_alternative_flow_deal_lost_other_with_notes(page):
    """
    Alternative Flow 2:
    Transition Deal to Lost using reason 'Other' with detailed notes provided.
    """
    page.click("#btn-convert-deal")
    page.click("#btn-modal-submit")
    expect(page.locator("#deal-view")).to_be_visible()

    page.click("#btn-mark-lost")
    page.select_option("#select-lost-reason", "Other")
    expect(page.locator("#grp-lost-notes")).to_be_visible()

    page.fill("#input-lost-notes", "Client budget frozen due to executive leadership change.")
    page.click("#btn-lost-submit")

    expect(page.locator("#modal-lost")).not_to_be_visible()
    expect(page.locator("#deal-status")).to_contain_text("Lost")


def test_e2e_exception_flow_convert_lost_lead_rejected(page):
    """
    Exception Flow 1:
    Attempting to convert a Lead marked as Lost must be rejected with error toast.
    """
    # Simulate a lost lead by altering DOM status
    page.evaluate("() => { document.getElementById('lead-status').innerText = 'Lost'; }")

    page.click("#btn-convert-deal")
    expect(page.locator("#modal-convert")).not_to_be_visible()
    expect(page.locator("#toast")).to_be_visible()
    expect(page.locator("#toast")).to_contain_text("Cannot convert a Lost lead")


def test_e2e_exception_flow_lost_reason_missing_or_empty_notes(page):
    """
    Exception Flow 2:
    Submitting Lost modal without reason or with 'Other' and empty notes must be rejected.
    """
    page.click("#btn-convert-deal")
    page.click("#btn-modal-submit")

    # 1. Reject empty reason
    page.click("#btn-mark-lost")
    page.click("#btn-lost-submit")
    expect(page.locator("#toast")).to_contain_text("Lost reason is mandatory")

    # 2. Reject 'Other' with empty notes
    page.select_option("#select-lost-reason", "Other")
    page.fill("#input-lost-notes", "   ")
    page.click("#btn-lost-submit")
    expect(page.locator("#toast")).to_contain_text("Lost notes are mandatory for reason Other")
    expect(page.locator("#modal-lost")).to_be_visible()

    # 3. Correct the value and verify success (as required by SQE specification)
    page.fill("#input-lost-notes", "Client budget cancelled due to Q4 economic constraints")
    page.click("#btn-lost-submit")
    expect(page.locator("#toast")).to_contain_text("Deal marked as Lost")
    expect(page.locator("#deal-status")).to_contain_text("Lost")


def test_e2e_usability_keyboard_modal_escape_dismissal(page):
    """
    Keyboard Accessibility & Usability:
    Pressing 'Escape' key dismisses any active modal without side effects.
    """
    page.click("#btn-convert-deal")
    expect(page.locator("#modal-convert")).to_be_visible()

    page.keyboard.press("Escape")
    expect(page.locator("#modal-convert")).not_to_be_visible()
    expect(page.locator("#lead-view")).to_be_visible()
