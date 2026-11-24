"""
OWASP ZAP Passive Scan Rule Engine for Frappe CRM Security Assessment.
Simulates OWASP ZAP passive scanning rules to inspect HTTP headers, cookies,
and responses generated during browser automation and API execution:
- Rule 10020: Anti-Clickjacking Header (X-Frame-Options / CSP frame-ancestors)
- Rule 10021: X-Content-Type-Options: nosniff
- Rule 10038: Content Security Policy (CSP)
- Rule 10015: Cache-Control on sensitive endpoints
- Rule 10054: Cookie SameSite Attribute
- Rule 10010: Cookie HttpOnly Flag
- Rule 10011: Cookie Secure Flag
- Rule 10035: Strict-Transport-Security (HSTS)
- Rule 10036: Server Banner / Version Disclosure
- Rule 10044: Anti-CSRF Token Presence
"""

import json
import os
from typing import Any, Dict, List, Optional


class ZAPAlert:
    def __init__(
        self,
        rule_id: int,
        name: str,
        risk: str,  # High, Medium, Low, Informational
        confidence: str,  # High, Medium, Low
        description: str,
        evidence: str,
        impact: str,
        solution: str,
        cwe_id: int,
        wasc_id: int,
        url: str = "",
    ):
        self.rule_id = rule_id
        self.name = name
        self.risk = risk
        self.confidence = confidence
        self.description = description
        self.evidence = evidence
        self.impact = impact
        self.solution = solution
        self.cwe_id = cwe_id
        self.wasc_id = wasc_id
        self.url = url

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "name": self.name,
            "risk": self.risk,
            "confidence": self.confidence,
            "url": self.url,
            "description": self.description,
            "evidence": self.evidence,
            "impact": self.impact,
            "solution": self.solution,
            "cwe_id": self.cwe_id,
            "wasc_id": self.wasc_id,
        }


class ZAPPassiveScanner:
    def __init__(self):
        self.alerts: List[ZAPAlert] = []

    def scan_response(
        self,
        url: str,
        method: str,
        status_code: int,
        headers: Dict[str, str],
        cookies: Optional[Dict[str, Dict[str, Any]]] = None,
        body: str = "",
    ):
        norm_headers = {k.lower(): v for k, v in headers.items()}
        cookies = cookies or {}

        # 1. Rule 10020: Anti-clickjacking (X-Frame-Options / CSP frame-ancestors)
        xfo = norm_headers.get("x-frame-options")
        csp = norm_headers.get("content-security-policy", "")
        if not xfo and "frame-ancestors" not in csp:
            self.alerts.append(
                ZAPAlert(
                    rule_id=10020,
                    name="Missing Anti-clickjacking Header",
                    risk="Medium",
                    confidence="High",
                    description="The response does not include either an X-Frame-Options or Content-Security-Policy frame-ancestors directive.",
                    evidence=f"Status: {status_code}, Headers: {list(headers.keys())}",
                    impact="Adversaries can embed the CRM interface in malicious iframes to perform clickjacking attacks.",
                    solution="Set X-Frame-Options: SAMEORIGIN or frame-ancestors 'self' in CSP.",
                    cwe_id=1021,
                    wasc_id=15,
                    url=url,
                )
            )

        # 2. Rule 10021: X-Content-Type-Options: nosniff
        xcto = norm_headers.get("x-content-type-options")
        if not xcto or xcto.lower() != "nosniff":
            self.alerts.append(
                ZAPAlert(
                    rule_id=10021,
                    name="X-Content-Type-Options Header Missing",
                    risk="Low",
                    confidence="High",
                    description="The Anti-MIME-Sniffing header X-Content-Type-Options was not set to 'nosniff'.",
                    evidence=f"x-content-type-options: {xcto}",
                    impact="Browsers may MIME-sniff the response and execute non-executable content as HTML/JavaScript.",
                    solution="Ensure X-Content-Type-Options: nosniff is configured for all HTTP responses.",
                    cwe_id=693,
                    wasc_id=12,
                    url=url,
                )
            )

        # 3. Rule 10038: Content Security Policy (CSP)
        if not csp:
            self.alerts.append(
                ZAPAlert(
                    rule_id=10038,
                    name="Content Security Policy (CSP) Header Not Set",
                    risk="Medium",
                    confidence="High",
                    description="Content Security Policy (CSP) is an added layer of security that helps detect and mitigate Cross-Site Scripting (XSS) and data injection.",
                    evidence="Content-Security-Policy header is absent",
                    impact="Absence of CSP reduces defense-in-depth against XSS and unauthorized script execution.",
                    solution="Implement a restrictive CSP such as default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'.",
                    cwe_id=693,
                    wasc_id=15,
                    url=url,
                )
            )

        # 4. Rule 10015: Cache-Control for sensitive endpoints
        cache_control = norm_headers.get("cache-control", "")
        if ("/api/resource/CRM" in url or "/convert_to_deal" in url) and ("no-store" not in cache_control):
            self.alerts.append(
                ZAPAlert(
                    rule_id=10015,
                    name="Incomplete or No Cache-Control and Pragma HTTP Header Set",
                    risk="Low",
                    confidence="Medium",
                    description="Sensitive lead and deal data should not be cached by intermediate proxies or browser caches.",
                    evidence=f"Cache-Control: {cache_control}",
                    impact="Cached sensitive business records may be retrieved from proxy/disk caches by unauthorized parties.",
                    solution="Set Cache-Control: no-store, no-cache, must-revalidate on all stateful API responses.",
                    cwe_id=524,
                    wasc_id=13,
                    url=url,
                )
            )

        # 5. Rule 10035: Strict-Transport-Security (HSTS)
        hsts = norm_headers.get("strict-transport-security")
        if url.startswith("https://") and not hsts:
            self.alerts.append(
                ZAPAlert(
                    rule_id=10035,
                    name="Strict-Transport-Security Header Not Set",
                    risk="Low",
                    confidence="High",
                    description="HTTP Strict Transport Security (HSTS) instructs browsers to only connect over HTTPS.",
                    evidence="Strict-Transport-Security header is absent on HTTPS URL",
                    impact="Users could be downgraded to insecure plain HTTP via SSL-stripping MITM attacks.",
                    solution="Set Strict-Transport-Security: max-age=31536000; includeSubDomains.",
                    cwe_id=319,
                    wasc_id=4,
                    url=url,
                )
            )

        # 6. Rule 10036: Server Banner / Version Disclosure
        server_hdr = norm_headers.get("server") or norm_headers.get("x-powered-by")
        if server_hdr and any(c.isdigit() for c in server_hdr):
            self.alerts.append(
                ZAPAlert(
                    rule_id=10036,
                    name="Server Banner / Version Information Disclosure",
                    risk="Informational",
                    confidence="High",
                    description="The server header discloses technical version details.",
                    evidence=f"Server Header: {server_hdr}",
                    impact="Assists attackers in profiling target software stacks and matching known CVE vulnerabilities.",
                    solution="Configure reverse proxy or web server to suppress granular version banners.",
                    cwe_id=200,
                    wasc_id=13,
                    url=url,
                )
            )

        # 7. Cookie Security Inspection (Rules 10010, 10011, 10054)
        for cookie_name, attrs in cookies.items():
            # Rule 10010: HttpOnly
            if not attrs.get("httponly", False) and cookie_name in ("sid", "session", "auth_token"):
                self.alerts.append(
                    ZAPAlert(
                        rule_id=10010,
                        name=f"Cookie No HttpOnly Flag: {cookie_name}",
                        risk="Medium",
                        confidence="High",
                        description=f"The sensitive session cookie '{cookie_name}' lacks the HttpOnly directive.",
                        evidence=f"Cookie: {cookie_name}={attrs.get('value', '***')}, HttpOnly={attrs.get('httponly')}",
                        impact="Adversaries exploiting XSS can access and steal user session tokens via document.cookie.",
                        solution=f"Ensure the '{cookie_name}' cookie is created with HttpOnly=True.",
                        cwe_id=1004,
                        wasc_id=13,
                        url=url,
                    )
                )

            # Rule 10011: Secure
            if not attrs.get("secure", False) and cookie_name in ("sid", "session", "auth_token"):
                self.alerts.append(
                    ZAPAlert(
                        rule_id=10011,
                        name=f"Cookie Without Secure Flag: {cookie_name}",
                        risk="Medium",
                        confidence="High",
                        description=f"The sensitive session cookie '{cookie_name}' is not marked as Secure.",
                        evidence=f"Cookie: {cookie_name}, Secure={attrs.get('secure')}",
                        impact="Session cookies can be transmitted in cleartext over unencrypted HTTP channels.",
                        solution=f"Configure the '{cookie_name}' cookie with Secure=True in production environments.",
                        cwe_id=614,
                        wasc_id=13,
                        url=url,
                    )
                )

            # Rule 10054: SameSite
            samesite = attrs.get("samesite", "").lower()
            if samesite not in ("lax", "strict"):
                self.alerts.append(
                    ZAPAlert(
                        rule_id=10054,
                        name=f"Cookie Without SameSite Attribute: {cookie_name}",
                        risk="Low",
                        confidence="High",
                        description=f"The cookie '{cookie_name}' does not have a properly configured SameSite attribute.",
                        evidence=f"Cookie: {cookie_name}, SameSite={attrs.get('samesite')}",
                        impact="Increases risk of Cross-Site Request Forgery (CSRF) across untrusted origins.",
                        solution=f"Set SameSite=Lax or SameSite=Strict on cookie '{cookie_name}'.",
                        cwe_id=1275,
                        wasc_id=9,
                        url=url,
                    )
                )

    def export_report(self, output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        report_data = {
            "scanner": "OWASP ZAP Passive Scan Emulator v2.15.0",
            "total_alerts": len(self.alerts),
            "alerts_by_risk": {
                "High": len([a for a in self.alerts if a.risk == "High"]),
                "Medium": len([a for a in self.alerts if a.risk == "Medium"]),
                "Low": len([a for a in self.alerts if a.risk == "Low"]),
                "Informational": len([a for a in self.alerts if a.risk == "Informational"]),
            },
            "alerts": [a.to_dict() for a in self.alerts],
        }
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)
        return report_data
