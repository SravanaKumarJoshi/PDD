/**
 * Fallback Report Generator — Mobile Appium E2E
 * Generates a failure report Excel if WDIO exits early due to Appium crash.
 */

const ExcelJS = require('exceljs');
const fs = require('fs');
const path = require('path');

async function generateFallbackReport() {
  const outputDir = path.resolve(__dirname, '..', 'Test_Results', 'Excel');
  fs.mkdirSync(outputDir, { recursive: true });

  const workbook = new ExcelJS.Workbook();
  workbook.creator = 'BioPolymer AI — Fallback Reporter';

  const sheet = workbook.addWorksheet('Fallback Report');
  sheet.columns = [
    { header: 'Metric', key: 'metric', width: 30 },
    { header: 'Value', key: 'value', width: 30 }
  ];

  const hdr = sheet.getRow(1);
  hdr.font = { bold: true, color: { argb: 'FFFFFF' } };
  hdr.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'DC2626' } };

  [
    { metric: 'Status', value: 'FAILED — Appium/WDIO Setup Error' },
    { metric: 'Total Tests', value: '0 (suite did not execute)' },
    { metric: 'Error', value: 'Appium session could not be established' },
    { metric: 'Timestamp', value: new Date().toISOString() },
    { metric: 'Action Required', value: 'Check Appium logs and emulator status' }
  ].forEach(r => sheet.addRow(r));

  const outputPath = path.join(outputDir, 'mobile-report.xlsx');
  await workbook.xlsx.writeFile(outputPath);
  console.log(`⚠️ Fallback report generated: ${outputPath}`);

  // Also generate minimal HTML
  const htmlDir = path.resolve(__dirname, '..', 'Test_Results', 'HTML');
  fs.mkdirSync(htmlDir, { recursive: true });
  fs.writeFileSync(path.join(htmlDir, 'execution-report.html'), `<!DOCTYPE html>
<html><head><title>Fallback Report</title></head>
<body style="font-family:sans-serif;background:#0f172a;color:#e2e8f0;padding:2rem;text-align:center;">
<h1 style="color:#f87171;">⚠️ Mobile E2E — Setup Failed</h1>
<p>Appium session could not be established. Check logs for details.</p>
<p>Generated: ${new Date().toISOString()}</p>
</body></html>`, 'utf8');
}

generateFallbackReport().catch(console.error);
