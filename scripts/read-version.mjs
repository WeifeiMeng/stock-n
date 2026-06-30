import fs from 'node:fs';

const target = process.argv[2];

if (target === 'backend') {
  const pyproject = fs.readFileSync('backend/pyproject.toml', 'utf8');
  const match = pyproject.match(/^version\s*=\s*["']([^"']+)["']/m);
  if (!match) {
    throw new Error('Cannot find project.version in backend/pyproject.toml');
  }
  console.log(match[1]);
} else if (target === 'frontend') {
  const pkg = JSON.parse(fs.readFileSync('frontend/package.json', 'utf8'));
  if (!pkg.version) {
    throw new Error('Cannot find version in frontend/package.json');
  }
  console.log(pkg.version);
} else {
  throw new Error('Usage: node scripts/read-version.mjs <backend|frontend>');
}
