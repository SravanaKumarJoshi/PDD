/**
 * k6 Load Test — BioPolymer AI Screening API
 *
 * Baseline/Load Testing Configuration:
 *   - 100 Virtual Users (VUs)
 *   - Duration: 1 minute
 *   - Thresholds: <5% failure rate, p(95) < 1500ms
 *
 * Metrics reported:
 *   - Requests per second (RPS)
 *   - Response times (avg, min, max, p95)
 *   - Error rate
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ─── Custom Metrics ──────────────────────────────────────────────
const errorRate = new Rate('errors');
const healthLatency = new Trend('health_latency', true);
const materialsLatency = new Trend('materials_latency', true);

// ─── Options ─────────────────────────────────────────────────────
export const options = {
  vus: 100,
  duration: '1m',
  thresholds: {
    // Global thresholds
    'http_req_failed': ['rate<0.05'],          // <5% request failure rate
    'http_req_duration': ['p(95)<1500'],        // 95th percentile < 1.5s
    // Custom thresholds
    'health_latency': ['p(95)<500'],            // Health check p95 < 500ms
    'errors': ['rate<0.05'],                    // Custom error rate < 5%
  },
  // Summary output configuration
  summaryTrendStats: ['avg', 'min', 'med', 'max', 'p(90)', 'p(95)', 'p(99)'],
};

// ─── Configuration ───────────────────────────────────────────────
const BASE_URL = __ENV.BACKEND_URL || 'http://127.0.0.1:8000';

// ─── Test Endpoints ──────────────────────────────────────────────
const ENDPOINTS = [
  { path: '/health',           name: 'Health Check',    weight: 3 },
  { path: '/',                 name: 'Root',            weight: 2 },
  { path: '/api/v1/materials', name: 'Materials List',  weight: 2 },
  { path: '/api/v1/statistics',name: 'Statistics',      weight: 1 },
];

// ─── Weighted Random Selection ───────────────────────────────────
function selectEndpoint() {
  const totalWeight = ENDPOINTS.reduce((sum, ep) => sum + ep.weight, 0);
  let random = Math.random() * totalWeight;
  for (const ep of ENDPOINTS) {
    random -= ep.weight;
    if (random <= 0) return ep;
  }
  return ENDPOINTS[0];
}

// ─── Default Function (VU Loop) ─────────────────────────────────
export default function () {
  const endpoint = selectEndpoint();
  const url = `${BASE_URL}${endpoint.path}`;

  const params = {
    headers: {
      'Accept': 'application/json',
      'User-Agent': 'k6-load-test/1.0',
    },
    timeout: '10s',
    tags: { endpoint: endpoint.name },
  };

  const res = http.get(url, params);

  // Assertions
  const checkResult = check(res, {
    'status is 200': (r) => r.status === 200,
    'response is JSON': (r) => {
      const ct = r.headers['Content-Type'] || '';
      return ct.includes('application/json');
    },
    'response time < 2s': (r) => r.timings.duration < 2000,
    'body is not empty': (r) => r.body && r.body.length > 0,
  });

  // Record errors
  errorRate.add(!checkResult);

  // Record custom latency by endpoint
  if (endpoint.path === '/health' || endpoint.path === '/api/v1/health') {
    healthLatency.add(res.timings.duration);
  }
  if (endpoint.path === '/api/v1/materials') {
    materialsLatency.add(res.timings.duration);
  }

  // Pacing: small random sleep between requests
  sleep(Math.random() * 0.5 + 0.1); // 100ms - 600ms
}

// ─── Setup Function ──────────────────────────────────────────────
export function setup() {
  console.log(`🚀 Load Test Starting`);
  console.log(`   Target: ${BASE_URL}`);
  console.log(`   VUs: ${options.vus}`);
  console.log(`   Duration: ${options.duration}`);
  console.log(`   Endpoints: ${ENDPOINTS.map(e => e.path).join(', ')}`);

  // Verify target is accessible
  const healthRes = http.get(`${BASE_URL}/health`, { timeout: '5s' });
  if (healthRes.status !== 200) {
    console.warn(`⚠️ Health check returned status ${healthRes.status}`);
  } else {
    console.log(`✅ Target is accessible (health: ${healthRes.status})`);
  }

  return { startTime: new Date().toISOString() };
}

// ─── Teardown Function ───────────────────────────────────────────
export function teardown(data) {
  console.log(`\n🏁 Load Test Complete`);
  console.log(`   Started: ${data.startTime}`);
  console.log(`   Ended: ${new Date().toISOString()}`);
}
