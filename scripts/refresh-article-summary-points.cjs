const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..', 'astro-site', 'src', 'content', 'articles');

function walk(dir) {
  const out = [];
  for (const name of fs.readdirSync(dir)) {
    const p = path.join(dir, name);
    const st = fs.statSync(p);
    if (st.isDirectory()) out.push(...walk(p));
    else if (p.endsWith('.md')) out.push(p);
  }
  return out;
}

function clean(value) {
  return String(value || '')
    .replace(/[#*`\[\]\r\n]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function field(front, key) {
  const match = front.match(new RegExp(`^${key}:\\s*"([^"\\n]*)"`, 'm'));
  return match ? match[1].trim() : '';
}

function arrayField(front, key) {
  const match = front.match(new RegExp(`^${key}:\\s*(\\[[\\s\\S]*?\\])\\s*$`, 'm'));
  if (!match) return [];
  try {
    const parsed = JSON.parse(match[1]);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function inferSubject(title, description) {
  const text = `${title} ${description}`;
  const names = [
    'OpenAI',
    'NVIDIA',
    'Microsoft',
    'Google',
    'Anthropic',
    'Meta',
    'Amazon',
    'AWS',
    'Apple',
    'TSMC',
    'AMD',
    'Intel',
    'xAI',
    'DeepSeek',
    'Hugging Face',
    'SoftBank',
    'Salesforce',
    'Oracle',
    'IBM',
    'Tesla',
    'Foxconn',
    'フォックスコン',
    'サムスン',
    'SKハイニックス',
    'ソフトバンク',
  ];
  return names.find((name) => text.includes(name)) || clean(title).split(/[、。：「」\s]/)[0].slice(0, 24) || 'このニュース';
}

function inferTheme(text, categorySlug) {
  if (/ランサム|脆弱|サイバー|攻撃|セキュリティ|防御|侵害/.test(text)) return 'cyber';
  if (/GPU|NVIDIA|半導体|TSMC|HBM|チップ|データセンター|電力|CUDA|AIサーバー/.test(text)) return 'infra';
  if (/OpenAI|Anthropic|Claude|GPT|Gemini|Llama|モデル|LLM|推論|学習/.test(text)) return 'model';
  if (/エージェント|Agent|Codex|自律|自動化|ワークフロー/.test(text)) return 'agent';
  if (/出資|投資|調達|評価額|株|市場|IPO|買収|売上|利益/.test(text) || categorySlug === 'markets') return 'market';
  if (/ロボット|Robotics|ヒューマノイド|自動運転/.test(text)) return 'robotics';
  if (/生成AI|動画|画像|音声|クリエイティブ/.test(text)) return 'generative';
  return 'general';
}

function trimPoint(point) {
  if (point.length <= 90) return point;
  return `${point.slice(0, 88).replace(/[、，,.。]*$/, '')}。`;
}

function buildSummaryPoints({ title, description, body, categorySlug }) {
  const text = `${title} ${description} ${body.slice(0, 700)}`;
  const subject = inferSubject(title, description);
  const theme = inferTheme(text, categorySlug);
  const pointsByTheme = {
    cyber: [
      `${subject}の事例は、AI時代の競争力がサイバー防御と供給網管理にも左右されることを示している。`,
      '製造委託先、クラウド、認証情報を含む防御体制が、AI関連企業の事業継続リスクになっている。',
      '単発の攻撃被害ではなく、AIインフラを支える企業群全体の安全性を点検する材料になる。',
    ],
    infra: [
      `${subject}をめぐる動きは、AI競争の主戦場がモデルだけでなく計算資源の確保に広がったことを示す。`,
      'GPU、半導体、クラウド、電力の制約が、生成AIサービスの成長速度を左右する段階に入っている。',
      '投資家や利用企業は、製品発表だけでなく供給網とデータセンター投資の持続性を見る必要がある。',
    ],
    model: [
      `${subject}の動きは、基盤モデル競争が性能比較だけでなく配布網や企業導入の争いになったことを示す。`,
      'モデルの価値は、API、クラウド、開発ツール、業務データと結びつくほど大きくなりやすい。',
      '読者はベンチマークの優劣だけでなく、どの企業基盤に組み込まれるかを見る必要がある。',
    ],
    agent: [
      `${subject}のニュースは、AIエージェントが実験段階から業務プロセスの中核へ入り始めたことを示す。`,
      '競争軸はチャット性能ではなく、ツール連携、権限管理、実行環境をどう設計するかに移っている。',
      '企業導入では効率化だけでなく、誤実行や情報漏洩を防ぐ運用設計が重要になる。',
    ],
    market: [
      `${subject}の動きは、AI投資が短期のテーマ株ではなく産業インフラ再編と結びついていることを示す。`,
      '資金調達、買収、株価反応は、計算資源や販売網を押さえる競争の一部として読む必要がある。',
      '市場評価を見る際は、成長期待だけでなく設備投資、収益化、供給制約のバランスが論点になる。',
    ],
    robotics: [
      `${subject}の動きは、AIモデルが画面上の支援から物理世界のロボット制御へ広がる流れを示す。`,
      'ロボティクス競争では、モデル性能だけでなくセンサー、GPU、データ収集、製造体制が重要になる。',
      '実用化の焦点はデモの派手さではなく、現場で安全に反復運用できるかに移っている。',
    ],
    generative: [
      `${subject}の動きは、生成AIが研究技術ではなくクリエイティブ制作の産業基盤になり始めたことを示す。`,
      '競争軸は品質だけでなく、配布チャネル、著作権対応、制作ワークフローへの統合に広がっている。',
      '利用企業はツール単体ではなく、既存の制作工程やブランド管理にどう組み込むかを見る必要がある。',
    ],
    general: [
      `${subject}のニュースは、AI業界の競争が単体技術ではなく企業間の接続関係で決まり始めたことを示す。`,
      '読者は発表内容だけでなく、背後にあるクラウド、データ、資本、販売網の関係を見る必要がある。',
      'この動きは、日本企業がAI活用や調達戦略を考えるうえでも無視しにくい論点になる。',
    ],
  };
  return pointsByTheme[theme].map(trimPoint);
}

function shouldReplace(front, description, body) {
  const points = arrayField(front, 'summaryPoints');
  if (points.length !== 3) return true;
  const first = clean(body).slice(0, 60);
  const desc = clean(description).slice(0, 60);
  return points.some((point) => {
    const text = clean(point);
    return text.length < 35 || text.length > 100 || (desc && text.includes(desc.slice(0, 35))) || (first && text.includes(first.slice(0, 35)));
  });
}

let changed = 0;
let inserted = 0;
let replaced = 0;

for (const file of walk(root)) {
  const src = fs.readFileSync(file, 'utf8').replace(/^\uFEFF/, '');
  const match = src.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n?/);
  if (!match) continue;

  const front = match[1];
  const body = src.slice(match[0].length);
  const title = field(front, 'title');
  const description = field(front, 'description') || field(front, 'meta_description');
  const categorySlug = field(front, 'category_slug') || path.basename(path.dirname(file));

  if (!shouldReplace(front, description, body)) continue;

  const summaryLine = `summaryPoints: ${JSON.stringify(buildSummaryPoints({ title, description, body, categorySlug }))}`;
  let nextFront;

  if (/^summaryPoints:\s*\[[\s\S]*?\]\s*$/m.test(front)) {
    nextFront = front.replace(/^summaryPoints:\s*\[[\s\S]*?\]\s*$/m, summaryLine);
    replaced += 1;
  } else {
    const lines = front.split(/\r?\n/);
    const idx = lines.findIndex((line) => line.startsWith('meta_description:'));
    if (idx >= 0) lines.splice(idx + 1, 0, summaryLine);
    else lines.push(summaryLine);
    nextFront = lines.join('\n');
    inserted += 1;
  }

  fs.writeFileSync(file, `---\n${nextFront}\n---\n\n${body.replace(/^\s+/, '')}`, 'utf8');
  changed += 1;
}

console.log(JSON.stringify({ changed, inserted, replaced }, null, 2));
