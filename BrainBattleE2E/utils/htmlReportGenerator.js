/**
 * HTML Report Generator — Dark-themed execution report
 * Renders execution-report.html with:
 *   - Total statistics dashboard
 *   - Pass/fail badges
 *   - Category breakdown table
 *   - Error stack details
 *   - Type distribution charts (CSS-based)
 */

const fs = require('fs');
const path = require('path');

function generateHtmlReport(results, options = {}) {
  const {
    startTime = new Date(),
    endTime = new Date(),
    outputPath = path.resolve(__dirname, '..', 'Test_Results', 'HTML', 'execution-report.html')
  } = options;

  const totalTests = results.length;
  const passed = results.filter(r => r.status === 'PASS').length;
  const failed = results.filter(r => r.status !== 'PASS').length;
  const passRate = ((passed / totalTests) * 100).toFixed(1);
  const durations = results.map(r => r.duration);
  const avgDuration = Math.round(durations.reduce((a, b) => a + b, 0) / durations.length);
  const minDuration = Math.min(...durations);
  const maxDuration = Math.max(...durations);
  const totalDuration = durations.reduce((a, b) => a + b, 0);
  const elapsedMs = endTime - startTime;

  // Aggregate by type
  const typeMap = {};
  results.forEach(r => {
    if (!typeMap[r.type]) typeMap[r.type] = { total: 0, passed: 0, failed: 0, durations: [] };
    typeMap[r.type].total++;
    if (r.status === 'PASS') typeMap[r.type].passed++;
    else typeMap[r.type].failed++;
    typeMap[r.type].durations.push(r.duration);
  });

  // Aggregate by category
  const categoryMap = {};
  results.forEach(r => {
    const key = `${r.type} > ${r.category}`;
    if (!categoryMap[key]) categoryMap[key] = { type: r.type, category: r.category, total: 0, passed: 0, failed: 0, durations: [] };
    categoryMap[key].total++;
    if (r.status === 'PASS') categoryMap[key].passed++;
    else categoryMap[key].failed++;
    categoryMap[key].durations.push(r.duration);
  });

  const failedTests = results.filter(r => r.status !== 'PASS');

  const typeColors = {
    'Functional': '#3b82f6', 'UI/UX': '#8b5cf6', 'Compatibility': '#06b6d4',
    'Performance': '#f59e0b', 'Security': '#ef4444', 'API': '#10b981',
    'Database': '#6366f1', 'Accessibility': '#ec4899', 'Mobile': '#14b8a6',
    'Regression': '#f97316', 'End-to-End': '#84cc16'
  };

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BioPolymer AI — E2E Execution Report</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Inter', -apple-system, sans-serif;
      background: #0f172a; color: #e2e8f0;
      line-height: 1.6; padding: 0;
    }
    .container { max-width: 1400px; margin: 0 auto; padding: 2rem; }

    /* Header */
    .header {
      background: linear-gradient(135deg, #1e3a5f 0%, #0d9488 50%, #059669 100%);
      padding: 3rem 2rem; text-align: center; margin-bottom: 2rem;
      border-radius: 16px; position: relative; overflow: hidden;
    }
    .header::before {
      content: ''; position: absolute; top: -50%; left: -50%;
      width: 200%; height: 200%; background: radial-gradient(circle, rgba(255,255,255,0.05) 0%, transparent 70%);
      animation: pulse 4s infinite;
    }
    @keyframes pulse { 0%,100% { transform: scale(1); } 50% { transform: scale(1.05); } }
    .header h1 { font-size: 2.5rem; font-weight: 800; position: relative; z-index: 1; }
    .header p { font-size: 1.1rem; opacity: 0.9; margin-top: 0.5rem; position: relative; z-index: 1; }
    .header .badge {
      display: inline-block; padding: 0.4rem 1.2rem; border-radius: 20px;
      font-size: 0.85rem; font-weight: 600; margin-top: 1rem; position: relative; z-index: 1;
    }
    .badge-pass { background: rgba(5, 150, 105, 0.3); border: 1px solid #059669; color: #34d399; }
    .badge-fail { background: rgba(220, 38, 38, 0.3); border: 1px solid #dc2626; color: #fca5a5; }

    /* Stats Grid */
    .stats-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem; margin-bottom: 2rem;
    }
    .stat-card {
      background: linear-gradient(135deg, #1e293b, #334155);
      border: 1px solid #475569; border-radius: 12px; padding: 1.5rem;
      text-align: center; transition: transform 0.2s, box-shadow 0.2s;
    }
    .stat-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.3); }
    .stat-card h3 { font-size: 2rem; font-weight: 800; margin-bottom: 0.25rem; }
    .stat-card p { color: #94a3b8; font-size: 0.85rem; }
    .text-green { color: #34d399; }
    .text-red { color: #f87171; }
    .text-blue { color: #60a5fa; }
    .text-yellow { color: #fbbf24; }
    .text-purple { color: #a78bfa; }
    .text-cyan { color: #22d3ee; }

    /* Section */
    .section { margin-bottom: 2rem; }
    .section h2 {
      font-size: 1.5rem; font-weight: 700; margin-bottom: 1rem;
      padding-bottom: 0.5rem; border-bottom: 2px solid #334155;
    }

    /* Type Distribution */
    .type-grid {
      display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
      gap: 1rem;
    }
    .type-card {
      background: #1e293b; border: 1px solid #334155; border-radius: 10px;
      padding: 1.2rem; position: relative; overflow: hidden;
    }
    .type-card::before {
      content: ''; position: absolute; left: 0; top: 0; bottom: 0;
      width: 4px; border-radius: 4px 0 0 4px;
    }
    .type-card h4 { font-size: 1rem; font-weight: 600; margin-bottom: 0.5rem; padding-left: 0.5rem; }
    .type-card .type-stats { display: flex; gap: 1rem; padding-left: 0.5rem; font-size: 0.85rem; }
    .type-bar { height: 6px; background: #334155; border-radius: 3px; margin-top: 0.75rem; overflow: hidden; }
    .type-bar-fill { height: 100%; border-radius: 3px; transition: width 1s ease; }

    /* Table */
    .results-table { width: 100%; border-collapse: collapse; font-size: 0.85rem; }
    .results-table th {
      background: #1e293b; color: #94a3b8; text-align: left;
      padding: 0.75rem 1rem; font-weight: 600; text-transform: uppercase;
      font-size: 0.75rem; letter-spacing: 0.05em;
      position: sticky; top: 0; z-index: 1;
    }
    .results-table td { padding: 0.6rem 1rem; border-bottom: 1px solid #1e293b; }
    .results-table tr:hover { background: rgba(99, 102, 241, 0.05); }
    .results-table tr:nth-child(even) { background: rgba(30, 41, 59, 0.5); }
    .status-pass { color: #34d399; font-weight: 600; }
    .status-fail { color: #f87171; font-weight: 600; }

    /* Failed tests */
    .error-card {
      background: rgba(220, 38, 38, 0.05); border: 1px solid rgba(220, 38, 38, 0.2);
      border-radius: 8px; padding: 1rem; margin-bottom: 0.75rem;
    }
    .error-card h5 { color: #fca5a5; font-size: 0.9rem; margin-bottom: 0.5rem; }
    .error-card pre {
      background: #0f172a; padding: 0.75rem; border-radius: 6px;
      font-size: 0.8rem; color: #f87171; overflow-x: auto; white-space: pre-wrap;
    }

    /* Footer */
    .footer {
      text-align: center; padding: 2rem; color: #64748b;
      border-top: 1px solid #334155; margin-top: 2rem; font-size: 0.85rem;
    }

    /* Progress ring */
    .pass-rate-ring {
      width: 120px; height: 120px; margin: 0 auto 1rem;
      position: relative; display: flex; align-items: center; justify-content: center;
    }
    .pass-rate-ring svg { transform: rotate(-90deg); }
    .pass-rate-ring .rate-text {
      position: absolute; font-size: 1.5rem; font-weight: 800;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🧬 BioPolymer AI — E2E Execution Report</h1>
      <p>Selenium Web Test Suite • ${totalTests} Assertions</p>
      <span class="badge ${failed === 0 ? 'badge-pass' : 'badge-fail'}">
        ${failed === 0 ? '✅ ALL TESTS PASSED' : '⚠️ ' + failed + ' TESTS FAILED'}
      </span>
    </div>

    <!-- Stats -->
    <div class="stats-grid">
      <div class="stat-card">
        <h3 class="text-blue">${totalTests}</h3>
        <p>Total Tests</p>
      </div>
      <div class="stat-card">
        <h3 class="text-green">${passed}</h3>
        <p>Passed</p>
      </div>
      <div class="stat-card">
        <h3 class="text-red">${failed}</h3>
        <p>Failed</p>
      </div>
      <div class="stat-card">
        <h3 class="text-yellow">${passRate}%</h3>
        <p>Pass Rate</p>
      </div>
      <div class="stat-card">
        <h3 class="text-purple">${avgDuration}ms</h3>
        <p>Avg Duration</p>
      </div>
      <div class="stat-card">
        <h3 class="text-cyan">${(totalDuration / 1000).toFixed(1)}s</h3>
        <p>Total Duration</p>
      </div>
    </div>

    <!-- Pass Rate Ring -->
    <div class="section" style="text-align:center;">
      <div class="pass-rate-ring">
        <svg width="120" height="120" viewBox="0 0 120 120">
          <circle cx="60" cy="60" r="52" stroke="#334155" stroke-width="8" fill="none"/>
          <circle cx="60" cy="60" r="52" stroke="${failed === 0 ? '#059669' : '#f59e0b'}"
            stroke-width="8" fill="none" stroke-linecap="round"
            stroke-dasharray="${(passRate / 100) * 326.73} 326.73"/>
        </svg>
        <span class="rate-text ${failed === 0 ? 'text-green' : 'text-yellow'}">${passRate}%</span>
      </div>
    </div>

    <!-- Type Distribution -->
    <div class="section">
      <h2>📊 Testing Type Distribution</h2>
      <div class="type-grid">
        ${Object.entries(typeMap).map(([type, data]) => {
          const rate = ((data.passed / data.total) * 100).toFixed(0);
          const color = typeColors[type] || '#6366f1';
          return `
          <div class="type-card" style="border-left: 4px solid ${color};">
            <h4>${type}</h4>
            <div class="type-stats">
              <span>${data.total} tests</span>
              <span class="text-green">${data.passed} pass</span>
              <span class="text-red">${data.failed} fail</span>
              <span style="color:${color}">${rate}%</span>
            </div>
            <div class="type-bar">
              <div class="type-bar-fill" style="width:${rate}%; background:${color};"></div>
            </div>
          </div>`;
        }).join('')}
      </div>
    </div>

    <!-- Category Breakdown -->
    <div class="section">
      <h2>📋 Category Breakdown</h2>
      <div style="overflow-x:auto; border-radius:10px; border:1px solid #334155;">
        <table class="results-table">
          <thead>
            <tr>
              <th>Type</th><th>Category</th><th>Total</th><th>Passed</th><th>Failed</th><th>Rate</th><th>Avg (ms)</th>
            </tr>
          </thead>
          <tbody>
            ${Object.values(categoryMap).map(c => {
              const rate = ((c.passed / c.total) * 100).toFixed(0);
              const avg = Math.round(c.durations.reduce((a, b) => a + b, 0) / c.durations.length);
              return `<tr>
                <td>${c.type}</td><td>${c.category}</td><td>${c.total}</td>
                <td class="status-pass">${c.passed}</td>
                <td class="${c.failed > 0 ? 'status-fail' : ''}">${c.failed}</td>
                <td>${rate}%</td><td>${avg}</td>
              </tr>`;
            }).join('')}
          </tbody>
        </table>
      </div>
    </div>

    ${failedTests.length > 0 ? `
    <!-- Failed Tests -->
    <div class="section">
      <h2>❌ Failed Tests (${failedTests.length})</h2>
      ${failedTests.map(t => `
        <div class="error-card">
          <h5>[${t.type}] ${t.category} — ${t.name}</h5>
          <pre>${t.error || 'No error details captured'}</pre>
        </div>
      `).join('')}
    </div>` : ''}

    <div class="footer">
      <p>🧬 BioPolymer AI Screening Platform — E2E Test Report</p>
      <p>Generated: ${new Date().toISOString()} | Duration: ${(elapsedMs / 1000).toFixed(1)}s</p>
      <p>Selenium WebDriver • Mocha • ExcelJS • Headless Chrome</p>
    </div>
  </div>
</body>
</html>`;

  // Ensure output directory exists
  const dir = path.dirname(outputPath);
  fs.mkdirSync(dir, { recursive: true });
  fs.writeFileSync(outputPath, html, 'utf8');
  console.log(`📄 HTML report saved: ${outputPath}`);
}

module.exports = { generateHtmlReport };
