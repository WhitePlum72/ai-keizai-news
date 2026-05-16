import "dotenv/config";
import fs from "fs/promises";
import path from "path";

const TOKEN = process.env.LOGO_DEV_TOKEN;
console.log("TOKEN:", TOKEN);

const COMPANIES_PATH = "src/data/ecosystem/companies.json";
const OUT_DIR = "public/logos";


if (!TOKEN) {
  console.error("LOGO_DEV_TOKEN が未設定です");
  process.exit(1);
}

const companies = JSON.parse(await fs.readFile(COMPANIES_PATH, "utf-8"));
await fs.mkdir(OUT_DIR, { recursive: true });

function safeName(str) {
  return str
    .toLowerCase()
    .replace(/^https?:\/\//, "")
    .replace(/^www\./, "")
    .replace(/[^a-z0-9.-]/g, "-")
    .replace(/\.+/g, ".")
    .replace(/-+/g, "-");
}

for (const company of companies) {
  if (!company.domain) {
    console.log(`skip: ${company.name} domainなし`);
    continue;
  }

  const fileName = `${company.id || safeName(company.domain)}.png`;
  const filePath = path.join(OUT_DIR, fileName);

  const url = `https://img.logo.dev/${company.domain}?token=${TOKEN}&format=png&size=256`;

try {
  const res = await fetch(url);

  if (!res.ok) {
    const errorText = await res.text();
    console.log(`failed: ${company.name} ${res.status} ${errorText}`);
    continue;
  }

  const buffer = Buffer.from(await res.arrayBuffer());
  await fs.writeFile(filePath, buffer);

  company.logo = `/logos/${fileName}`;

  console.log(`saved: ${company.name} -> ${filePath}`);
} catch (e) {
  console.log(`error: ${company.name}`, e.message);
}
}

await fs.writeFile(
  COMPANIES_PATH,
  JSON.stringify(companies, null, 2),
  "utf-8"
);

console.log("完了: companies.json の logo も /logos/*.svg に更新しました");