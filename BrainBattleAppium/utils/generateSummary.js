/**
 * GHA Summary Generator — Mobile Appium E2E
 * Appends test statistics to GITHUB_STEP_SUMMARY.
 */

const fs = require('fs');
const path = require('path');

function generateSummary() {
  const resultsFile = path.resolve(__dirname, '..', '.wdio-results.jsonl');
  let results = [];

  if (fs.existsSync(resultsFile)) {
    results = fs.readFileSync(resultsFile, 'utf8')
      .split('\n').filter(Boolean)
      .map(line => { try { return JSON.parse(line); } catch { return null; } })
      .filter(Boolean);
  }

  const total = results.length;
  const passed = results.filter(r => r.passed).length;
  const failed = total - passed;
  const passRate = total > 0 ? ((passed / total) * 100).toFixed(1) : '0.0';

  const summary = `# 📱 Mobile Appium E2E — Test Results

| Metric | Value |
|--------|-------|
| Total Tests | ${total} |
| Passed | ${passed} |
| Failed | ${failed} |
| Pass Rate | ${passRate}% |
| Categories | 11 |
| Platform | Android API 29 |
| Runner | Appium + WebDriverIO |

## Result: ${failed === 0 ? '✅ ALL TESTS PASSED' : `⚠️ ${failed} TESTS FAILED`}
`;

  if (process.env.GITHUB_STEP_SUMMARY) {
    fs.appendFileSync(process.env.GITHUB_STEP_SUMMARY, '\n\n' + summary, 'utf8');
    console.log('✅ Summary written to GITHUB_STEP_SUMMARY');
  }

  console.log(summary);
}

if (require.main === module) {
  generateSummary();
}

module.exports = { generateSummary };
