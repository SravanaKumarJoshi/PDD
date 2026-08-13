/**
 * HTML Report Generator — Mobile Appium E2E
 * Dark-themed styled HTML page (execution-report.html)
 */

const fs = require('fs');
const path = require('path');

function generateHtmlReport(outputDir) {
  const resultsFile = path.resolve(__dirname, '..', '.wdio-results.jsonl');
  let results = [];

  if (fs.existsSync(resultsFile)) {
    results = fs.readFileSync(resultsFile, 'utf8')
      .split('\n').filter(Boolean)
      .map(line => {
        try { return JSON.parse(line); } catch { return null; }
      }).filter(Boolean);
  }

  const total = results.length;
  const passed = results.filter(r => r.passed).length;
  const failed = total - passed;
  const passRate = total > 0 ? ((passed / total) * 100).toFixed(1) : '0.0';
  const durations = results.map(r => r.duration || 0);
  const avgDuration = total > 0 ? Math.round(durations.reduce((a, b) => a + b, 0) / total) : 0;
  const totalDuration = durations.reduce((a, b) => a + b, 0);

  const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>BioPolymer AI — Mobile Appium E2E Report</title>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    * { margin:0; padding:0; box-sizing:border-box; }
    body { font-family:'Inter',sans-serif; background:#0f172a; color:#e2e8f0; padding:2rem; }
    .header {
      background:linear-gradient(135deg,#1e3a5f,#7c3aed 50%,#8b5cf6);
      padding:3rem 2rem; text-align:center; border-radius:16px; margin-bottom:2rem;
    }
    .header h1 { font-size:2.5rem; font-weight:800; }
    .header p { opacity:0.9; margin-top:0.5rem; }
    .stats { display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:1rem; margin-bottom:2rem; }
    .stat {
      background:linear-gradient(135deg,#1e293b,#334155);
      border:1px solid #475569; border-radius:12px; padding:1.5rem; text-align:center;
    }
    .stat h3 { font-size:2rem; font-weight:800; }
    .stat p { color:#94a3b8; font-size:0.85rem; }
    .green { color:#34d399; } .red { color:#f87171; } .blue { color:#60a5fa; } .yellow { color:#fbbf24; }
    table { width:100%; border-collapse:collapse; font-size:0.85rem; }
    th { background:#1e293b; color:#94a3b8; text-align:left; padding:0.75rem 1rem; font-weight:600; text-transform:uppercase; }
    td { padding:0.6rem 1rem; border-bottom:1px solid #1e293b; }
    tr:hover { background:rgba(99,102,241,0.05); }
    .footer { text-align:center; padding:2rem; color:#64748b; border-top:1px solid #334155; margin-top:2rem; }
  </style>
</head>
<body>
  <div class="header">
    <h1>📱 Mobile Appium — E2E Report</h1>
    <p>Android Test Suite • ${total} Assertions</p>
  </div>
  <div class="stats">
    <div class="stat"><h3 class="blue">${total}</h3><p>Total Tests</p></div>
    <div class="stat"><h3 class="green">${passed}</h3><p>Passed</p></div>
    <div class="stat"><h3 class="red">${failed}</h3><p>Failed</p></div>
    <div class="stat"><h3 class="yellow">${passRate}%</h3><p>Pass Rate</p></div>
    <div class="stat"><h3 class="blue">${avgDuration}ms</h3><p>Avg Duration</p></div>
    <div class="stat"><h3>${(totalDuration/1000).toFixed(1)}s</h3><p>Total Time</p></div>
  </div>
  <div style="overflow-x:auto;border-radius:10px;border:1px solid #334155;">
    <table>
      <thead><tr><th>#</th><th>Test</th><th>Status</th><th>Duration</th></tr></thead>
      <tbody>
        ${results.map((r, i) => `<tr>
          <td>${i+1}</td>
          <td>${r.fullTitle || r.title}</td>
          <td class="${r.passed ? 'green' : 'red'}">${r.passed ? 'PASS' : 'FAIL'}</td>
          <td>${r.duration || 0}ms</td>
        </tr>`).join('')}
      </tbody>
    </table>
  </div>
  <div class="footer">
    <p>📱 BioPolymer AI — Mobile E2E Report | Generated: ${new Date().toISOString()}</p>
  </div>
</body>
</html>`;

  const htmlDir = path.join(outputDir, 'HTML');
  fs.mkdirSync(htmlDir, { recursive: true });
  const outputPath = path.join(htmlDir, 'execution-report.html');
  fs.writeFileSync(outputPath, html, 'utf8');
  console.log(`📄 Mobile HTML report: ${outputPath}`);
}

module.exports = { generateHtmlReport };
