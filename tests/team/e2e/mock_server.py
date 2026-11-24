"""
Mock server providing static Frappe CRM single-page application UI for Playwright E2E testing.
Emulates:
- Lead detail page with 'Convert to Deal' modal dialog
- Deal detail page with status progression buttons (Won, Lost modal)
- Keyboard navigation shortcuts and accessible form controls
- REST & RPC backend responses
"""

import http.server
import socketserver
import threading
import json
import os
import urllib.parse

PORT = 9123

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="description" content="Frappe CRM Lead and Deal Management Workspace for Enterprise Sales">
  <title>Frappe CRM E2E Workspace</title>
  <style>
    body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; padding: 20px; background: #f8fafc; color: #1e293b; }
    .container { max-width: 900px; margin: 0 auto; background: #ffffff; padding: 24px; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
    h1, h2 { margin-top: 0; }
    .btn { padding: 8px 16px; border-radius: 6px; border: none; font-weight: 500; cursor: pointer; }
    .btn-primary { background: #1d4ed8; color: #ffffff; }
    .btn-success { background: #15803d; color: #ffffff; }
    .btn-danger { background: #b91c1c; color: #ffffff; }
    .btn-secondary { background: #e2e8f0; color: #334155; }
    .form-group { margin-bottom: 16px; }
    label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 14px; }
    input, select, textarea { width: 100%; padding: 8px; border: 1px solid #cbd5e1; border-radius: 6px; box-sizing: border-box; }
    .modal { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.5); justify-content: center; align-items: center; }
    .modal-content { background: #ffffff; padding: 24px; border-radius: 8px; width: 440px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .modal.open { display: flex; }
    .toast { display: none; position: fixed; bottom: 20px; right: 20px; padding: 12px 24px; border-radius: 6px; background: #1e293b; color: white; }
    .toast.error { background: #b91c1c; }
    .toast.success { background: #15803d; }
    .status-badge { display: inline-block; padding: 4px 10px; border-radius: 12px; font-size: 12px; font-weight: 600; }
    .status-lead { background: #e0f2fe; color: #0369a1; }
    .status-won { background: #dcfce7; color: #15803d; }
    .status-lost { background: #fee2e2; color: #b91c1c; }
  </style>
</head>
<body>
  <main class="container" id="app">
    <div id="lead-view">
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px;">
        <div>
          <h1 id="lead-title" style="margin-bottom: 4px;">CRM-LEAD-2026-00001</h1>
          <span id="lead-status" class="status-badge status-lead">Open</span>
        </div>
        <div>
          <button id="btn-convert-deal" class="btn btn-primary" onclick="openConvertModal()">Convert to Deal</button>
        </div>
      </div>
      <div style="margin-top: 20px;">
        <p><strong>First Name:</strong> <span id="lead-first-name">Ada</span></p>
        <p><strong>Last Name:</strong> <span id="lead-last-name">Lovelace</span></p>
        <p><strong>Email:</strong> <span id="lead-email">ada@analytical-engine.org</span></p>
        <p><strong>Organization:</strong> <span id="lead-org">Analytical Engines Inc</span></p>
        <p><strong>Annual Revenue:</strong> $<span id="lead-revenue">500,000.00</span></p>
      </div>
    </div>

    <!-- Convert Modal -->
    <div id="modal-convert" class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-convert-title">
      <div class="modal-content">
        <h2 id="modal-convert-title">Convert Lead to Deal</h2>
        <div class="form-group">
          <label for="input-deal-name">Deal Name</label>
          <input id="input-deal-name" type="text" value="Enterprise Engine Expansion">
        </div>
        <div class="form-group">
          <label for="input-deal-value">Deal Value ($)</label>
          <input id="input-deal-value" type="number" step="0.01" value="75000.00">
        </div>
        <div class="form-group">
          <label for="select-convert-policy">If Converted</label>
          <select id="select-convert-policy">
            <option value="Create">Create New Deal</option>
            <option value="Return Existing">Return Existing Deal</option>
            <option value="Fail">Fail if Converted</option>
          </select>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px;">
          <button id="btn-modal-cancel" class="btn btn-secondary" onclick="closeConvertModal()">Cancel</button>
          <button id="btn-modal-submit" class="btn btn-primary" onclick="submitConvert()">Confirm Conversion</button>
        </div>
      </div>
    </div>

    <!-- Deal View -->
    <div id="deal-view" style="display: none;">
      <div style="display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #e2e8f0; padding-bottom: 12px;">
        <div>
          <h1 id="deal-title" style="margin-bottom: 4px;">CRM-DEAL-2026-00001</h1>
          <span id="deal-status" class="status-badge status-lead">Opportunity</span>
        </div>
        <div style="display: flex; gap: 8px;">
          <button id="btn-mark-won" class="btn btn-success" onclick="markWon()">Mark as Won</button>
          <button id="btn-mark-lost" class="btn btn-danger" onclick="openLostModal()">Mark as Lost</button>
        </div>
      </div>
      <div style="margin-top: 20px;">
        <p><strong>Linked Lead:</strong> <span id="deal-linked-lead">CRM-LEAD-2026-00001</span></p>
        <p><strong>Deal Value:</strong> $<span id="deal-value-display">75,000.00</span></p>
        <p><strong>Closed Date:</strong> <span id="deal-closed-date">None</span></p>
        <p><strong>Probability:</strong> <span id="deal-probability">50</span>%</p>
      </div>
    </div>

    <!-- Lost Reason Modal -->
    <div id="modal-lost" class="modal" role="dialog" aria-modal="true" aria-labelledby="modal-lost-title">
      <div class="modal-content">
        <h2 id="modal-lost-title">Mark Deal as Lost</h2>
        <div class="form-group">
          <label for="select-lost-reason">Lost Reason <span style="color:red">*</span></label>
          <select id="select-lost-reason" onchange="toggleLostNotes(this.value)">
            <option value="">Select Reason...</option>
            <option value="Price">Price</option>
            <option value="Competitor">Competitor</option>
            <option value="Feature Gap">Feature Gap</option>
            <option value="Other">Other</option>
          </select>
        </div>
        <div class="form-group" id="grp-lost-notes" style="display: none;">
          <label for="input-lost-notes">Lost Notes <span style="color:red">*</span></label>
          <textarea id="input-lost-notes" rows="3" placeholder="Provide reason details..."></textarea>
        </div>
        <div style="display: flex; justify-content: flex-end; gap: 8px; margin-top: 16px;">
          <button id="btn-lost-cancel" class="btn btn-secondary" onclick="closeLostModal()">Cancel</button>
          <button id="btn-lost-submit" class="btn btn-danger" onclick="submitLost()">Confirm Lost</button>
        </div>
      </div>
    </div>

    <div id="toast" class="toast" role="status" aria-live="polite"></div>
  </main>

  <script>
    function showToast(msg, isError = false) {
      const t = document.getElementById('toast');
      t.innerText = msg;
      t.className = 'toast ' + (isError ? 'error' : 'success');
      t.style.display = 'block';
      setTimeout(() => { t.style.display = 'none'; }, 3000);
    }

    function openConvertModal() {
      const status = document.getElementById('lead-status').innerText;
      if (status === 'Lost') {
        showToast('Cannot convert a Lost lead', true);
        return;
      }
      document.getElementById('modal-convert').classList.add('open');
      document.getElementById('input-deal-name').focus();
    }

    function closeConvertModal() {
      document.getElementById('modal-convert').classList.remove('open');
    }

    function submitConvert() {
      const val = parseFloat(document.getElementById('input-deal-value').value);
      if (val < 0) {
        showToast('Deal value cannot be negative', true);
        return;
      }
      closeConvertModal();
      document.getElementById('lead-view').style.display = 'none';
      document.getElementById('deal-view').style.display = 'block';
      document.getElementById('deal-value-display').innerText = val.toFixed(2);
      showToast('Lead converted successfully!');
    }

    function markWon() {
      document.getElementById('deal-status').innerText = 'Won';
      document.getElementById('deal-status').className = 'status-badge status-won';
      document.getElementById('deal-closed-date').innerText = new Date().toISOString().split('T')[0];
      document.getElementById('deal-probability').innerText = '100';
      showToast('Deal marked as Won!');
    }

    function openLostModal() {
      document.getElementById('modal-lost').classList.add('open');
      document.getElementById('select-lost-reason').focus();
    }

    function closeLostModal() {
      document.getElementById('modal-lost').classList.remove('open');
    }

    function toggleLostNotes(val) {
      document.getElementById('grp-lost-notes').style.display = (val === 'Other') ? 'block' : 'none';
    }

    function submitLost() {
      const reason = document.getElementById('select-lost-reason').value;
      if (!reason) {
        showToast('Lost reason is mandatory', true);
        return;
      }
      if (reason === 'Other') {
        const notes = document.getElementById('input-lost-notes').value.trim();
        if (!notes) {
          showToast('Lost notes are mandatory for reason Other', true);
          return;
        }
      }
      closeLostModal();
      document.getElementById('deal-status').innerText = 'Lost';
      document.getElementById('deal-status').className = 'status-badge status-lost';
      showToast('Deal marked as Lost');
    }

    // Keyboard navigation support
    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        closeConvertModal();
        closeLostModal();
      }
    });
  </script>
</body>
</html>
"""


class ReusableTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


class MockCRMHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/" or self.path.startswith("/crm"):
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode("utf-8"))
        elif self.path == "/deal":
            deal_html = HTML_TEMPLATE.replace(
                '<div id="lead-view">', '<div id="lead-view" style="display: none;">'
            ).replace(
                '<div id="deal-view" style="display: none;">', '<div id="deal-view" style="display: block;">'
            )
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(deal_html.encode("utf-8"))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok"}).encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        if self.path == "/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal":
            content_length = int(self.headers.get("Content-Length", 0))
            body = self.rfile.read(content_length) if content_length > 0 else b"{}"
            try:
                payload = json.loads(body.decode("utf-8"))
            except Exception:
                payload = {}
            deal_name = "CRM-DEAL-2026-00001"
            res = json.dumps({"message": deal_name})
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.end_headers()
            self.wfile.write(res.encode("utf-8"))
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass


def run_mock_server():
    server = socketserver.TCPServer(("127.0.0.1", PORT), MockCRMHandler)
    server.serve_forever()


if __name__ == "__main__":
    run_mock_server()
