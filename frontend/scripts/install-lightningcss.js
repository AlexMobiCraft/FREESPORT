#!/usr/bin/env node
/**
 * Ensures required native binaries for linux-x64-musl (Alpine) are available.
 * Runs only inside Docker (linux + musl). No-op for other platforms.
 */
const { execSync } = require('child_process');

const platform = process.platform;
const arch = process.arch;

function isMusl() {
  // Available starting Node 12+, returns true on musl builds
  if (process.report && typeof process.report.getReport === 'function') {
    const report = process.report.getReport();
    return report.header && report.header.glibcVersionRuntime === undefined;
  }
  // Fallback: check ldd output
  try {
    const output = execSync('ldd --version', { stdio: 'pipe' }).toString();
    return output.toLowerCase().includes('musl');
  } catch (e) {
    return false;
  }
}

if (platform === 'linux' && arch === 'x64' && isMusl()) {
  const packages = [
    {
      name: 'lightningcss-linux-x64-musl',
      version: '1.30.1',
    },
    {
      name: '@tailwindcss/oxide-linux-x64-musl',
      version: '4.1.11',
    },
  ];

  for (const pkg of packages) {
    const spec = `${pkg.name}@${pkg.version}`;
    try {
      console.log(`Detected linux-x64-musl environment. Installing ${spec}...`);
      execSync(`npm install ${spec} --no-save --force`, { stdio: 'inherit' });
      console.log(`${spec} installed successfully.`);
    } catch (error) {
      console.error(`Failed to install ${spec}:`, error.message);
      process.exit(1);
    }
  }
} else {
  console.log('Non-musl environment detected. Skipping lightningcss binary install.');
}
