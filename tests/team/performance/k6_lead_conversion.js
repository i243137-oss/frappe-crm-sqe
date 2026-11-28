import http from 'k6/http';
import { check, sleep } from 'k6';

// Performance SLA Thresholds defined before execution
export const options = __ENV.STAGES
  ? {
      stages: [
        { duration: '10s', target: 5 }, // Ramp-up to 5 VUs
        { duration: '40s', target: 5 }, // Steady-state load
        { duration: '10s', target: 0 }, // Ramp-down
      ],
      thresholds: {
        http_req_duration: ['p(95)<300'], // 95% of requests must complete below 300ms
        http_req_failed: ['rate<0.01'],    // Error rate must remain below 1.0%
        checks: ['rate>0.99'],             // 99%+ of checks must succeed
      },
    }
  : {
      vus: __ENV.VUS ? parseInt(__ENV.VUS) : 1,
      duration: __ENV.DURATION || '60s',
      thresholds: {
        http_req_duration: ['p(95)<300'], // 95% of requests must complete below 300ms
        http_req_failed: ['rate<0.01'],    // Error rate must remain below 1.0%
        checks: ['rate>0.99'],             // 99%+ of checks must succeed
      },
    };

const TARGET_URL = __ENV.TARGET_URL || 'http://127.0.0.1:9123/api/method/crm.fcrm.doctype.crm_lead.crm_lead.convert_to_deal';

const PAYLOAD = JSON.stringify({
  lead: 'CRM-LEAD-PERF-001',
  deal: {
    deal_name: 'Enterprise Cloud Deployment',
    deal_value: 85000.0,
    status: 'Qualification',
  },
  if_converted: 'Return Existing',
});

const HEADERS = {
  'Content-Type': 'application/json',
  'X-Frappe-CSRF-Token': 'perf_csrf_token_secure_456',
};

export default function () {
  const res = http.post(TARGET_URL, PAYLOAD, { headers: HEADERS });

  check(res, {
    'status is 200': (r) => r.status === 200,
    'response has deal message': (r) => {
      try {
        const body = JSON.parse(r.body);
        return body && body.message && body.message.startsWith('CRM-DEAL-');
      } catch (e) {
        return false;
      }
    },
    'latency under 300ms': (r) => r.timings.duration < 300,
  });

  // Small pacing interval between iterations
  sleep(0.05);
}
