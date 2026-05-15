import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

import sectorsData from '../data/ecosystem/sectors.json';
import companiesData from '../data/ecosystem/companies.json';
import modelsData from '../data/ecosystem/models.json';
import relationsData from '../data/ecosystem/relations.json';
import storygraphsData from '../data/ecosystem/storygraphs.json';

type SectorId =
  | 'all'
  | 'infrastructure'
  | 'foundation'
  | 'agents'
  | 'robotics'
  | 'opensource'
  | 'enterprise'
  | 'video'
  | 'voice'
  | 'china';

type CompanySize = 'large' | 'medium' | 'small';

type RelationType =
  | 'semiconductor'
  | 'accelerator'
  | 'investment'
  | 'gpu_supply'
  | 'cloud'
  | 'partnership'
  | 'distribution'
  | 'product'
  | 'competitor'
  | 'competition'
  | 'model'
  | 'platform'
  | 'research';

type ModelType = 'model' | 'product' | 'agent';

type Sector = {
  id: Exclude<SectorId, 'all'>;
  name: string;
  short: string;
  color: string;
  description: string;
};

type Company = {
  id: string;
  name: string;
  sector: Exclude<SectorId, 'all'>;
  logo?: string;
  logoText: string;
  size: CompanySize;
  description: string;
  score: number;
  tags: string[];
  country?: string;
  role?: string;
};

type EcosystemModel = {
  id: string;
  name: string;
  company: string;
  sector: Exclude<SectorId, 'all'>;
  type: ModelType;
  description: string;
};

type Relation = {
  source: string;
  target: string;
  type: RelationType;
  strength: number;
  description: string;
  label: string;
  articles: string[];
};

type LegacyFlowNode = {
  name: string;
  relation?: string;
  type?: RelationType;
  description?: string;
};

type StoryGraphNode = {
  id: string;
  label: string;
  relation?: string;
  type?: string;
  logo?: string;
  logoText?: string;
  description?: string;
  hidden?: boolean;
  x?: number | null;
  y?: number | null;
};

type StoryGraphGroup = {
  group: string;
  nodes: StoryGraphNode[];
};

type StoryGraphEdge = {
  source: string;
  target: string;
  type?: RelationType | string;
  label?: string;
  hidden?: boolean;
};

type StoryGraphLayers = {
  supply: StoryGraphGroup[];
  center: StoryGraphNode;
  outputs: StoryGraphGroup[];
  investments?: StoryGraphNode[];
  partnerships?: StoryGraphGroup[];
  distribution?: StoryGraphGroup[];
  competitors: StoryGraphNode[];
  edges?: StoryGraphEdge[];
};

type StoryGraph = {
  company: string;
  title: string;
  summary: string;
  layers?: StoryGraphLayers;
  left?: LegacyFlowNode[];
  center?: { name: string; relation?: string };
  right?: LegacyFlowNode[];
  tree?: string[];
  articles: { title: string; href: string }[];
};

type RelatedArticle = {
  title: string;
  href: string;
  source: 'storygraph' | 'relation';
  sourceLabel: string;
  category: string;
  publishedAt: string;
  importance?: '重要' | '注目';
};

const SECTORS = sectorsData as Sector[];
const COMPANIES = companiesData as Company[];
const MODELS = modelsData as EcosystemModel[];
const RELATIONS = relationsData as Relation[];
const STORYGRAPHS = storygraphsData as StoryGraph[];

const relationStyle: Record<RelationType, { label: string; color: string; verb: string }> = {
  semiconductor: { label: '半導体製造', color: '#3B82F6', verb: '先端半導体を製造' },
  accelerator: { label: 'AIアクセラレータ', color: '#F97316', verb: '計算資源を提供' },
  gpu_supply: { label: 'GPU供給', color: '#F97316', verb: 'GPUを供給' },
  cloud: { label: 'クラウド基盤', color: '#06B6D4', verb: 'クラウド基盤を提供' },
  investment: { label: '出資', color: '#22C55E', verb: '出資・資本支援' },
  partnership: { label: '提携', color: '#8B5CF6', verb: '提携' },
  distribution: { label: '提供チャネル', color: '#EAB308', verb: '法人向けに提供' },
  product: { label: '製品', color: '#EC4899', verb: '製品として提供' },
  model: { label: 'モデル', color: '#A78BFA', verb: 'モデルを提供' },
  competitor: { label: '競合企業', color: '#F87171', verb: '競合' },
  competition: { label: '競合企業', color: '#F87171', verb: '競合' },
  platform: { label: '基盤', color: '#06B6D4', verb: '基盤を提供' },
  research: { label: '研究', color: '#94A3B8', verb: '研究開発' },
};

const graphTone = {
  supply: '#5A9EFF',
  center: '#5CD8CE',
  output: '#A78BFA',
  competitor: '#F87171',
};

export default function LiveAIEcosystemNetwork() {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [activeSector, setActiveSector] = useState<SectorId>('all');
  const [selectedCompany, setSelectedCompany] = useState<Company | null>(null);
  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);

  const detail = useMemo(() => {
    if (!selectedCompany) return null;
    return (
      STORYGRAPHS.find((panel) => panel.company === selectedCompany.id) || {
        company: selectedCompany.id,
        title: `${selectedCompany.name} Ecosystem`,
        summary: selectedCompany.description,
        articles: buildDefaultArticles(selectedCompany),
      }
    );
  }, [selectedCompany]);

  const layers = useMemo(() => {
    if (!selectedCompany || !detail) return null;
    return buildStoryLayers(selectedCompany, detail);
  }, [selectedCompany, detail]);

  const relatedArticles = useMemo(() => {
    if (!selectedCompany || !detail) return [];
    return buildRelatedArticles(selectedCompany, detail);
  }, [selectedCompany, detail]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext('2d');
    if (!canvas || !ctx) return;

    let raf = 0;
    let frame = 0;
    const particles = Array.from({ length: 42 }, () => ({
      x: Math.random(),
      y: Math.random(),
      r: 0.7 + Math.random() * 1.3,
      vx: (Math.random() - 0.5) * 0.00032,
      vy: (Math.random() - 0.5) * 0.00032,
      a: 0.1 + Math.random() * 0.2,
    }));

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      const dpr = Math.min(window.devicePixelRatio || 1, 1.5);
      canvas.width = rect.width * dpr;
      canvas.height = rect.height * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const draw = () => {
      frame += 1;
      const rect = canvas.getBoundingClientRect();
      ctx.clearRect(0, 0, rect.width, rect.height);

      particles.forEach((p, index) => {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > 1) p.vx *= -1;
        if (p.y < 0 || p.y > 1) p.vy *= -1;
        const pulse = 0.45 + Math.sin(frame * 0.014 + index) * 0.45;
        ctx.beginPath();
        ctx.arc(p.x * rect.width, p.y * rect.height, p.r + pulse * 0.5, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(92,216,206,${p.a})`;
        ctx.fill();
      });

      raf = requestAnimationFrame(draw);
    };

    resize();
    draw();
    window.addEventListener('resize', resize);

    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', resize);
    };
  }, []);

  const handleCompanyClick = (company: Company) => {
    setSelectedCompany(company);
    setActiveSector(company.sector);
  };

  const handleStoryNodeClick = (node: StoryGraphNode) => {
    const company = findCompanyForNode(node);
    if (company) handleCompanyClick(company);
  };

  return (
    <section className="relative overflow-hidden border-y border-white/10 bg-[#07090d] py-10 text-slate-100">
      <StoryGraphStyles />
      <canvas ref={canvasRef} className="pointer-events-none absolute inset-0 h-full w-full opacity-70" />
      <div className="pointer-events-none absolute inset-0 bg-[linear-gradient(rgba(255,255,255,.035)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,.03)_1px,transparent_1px)] bg-[size:42px_42px]" />
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_25%_20%,rgba(90,158,255,.18),transparent_32rem),radial-gradient(circle_at_82%_25%,rgba(123,97,255,.13),transparent_34rem),radial-gradient(circle_at_50%_90%,rgba(92,216,206,.1),transparent_28rem)]" />

      <div className="relative mx-auto w-full max-w-[1680px] px-4">
        <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[.14em] text-[#5a9eff]">
              AI Ecosystem Visual Intelligence
            </p>
            <h2 className="mt-1 text-2xl font-black tracking-[-.03em] md:text-3xl">
              AI企業の構造を一瞬で理解する
            </h2>
          </div>
          <div className="flex flex-wrap gap-2 font-mono text-[11px] text-slate-400">
            {(['semiconductor', 'gpu_supply', 'cloud', 'investment', 'partnership', 'distribution', 'product', 'model', 'competitor'] as RelationType[]).map((key) => {
              const item = relationStyle[key];
              return (
              <span
                key={key}
                className="rounded-full border border-white/10 bg-white/[.035] px-3 py-1"
                style={{ color: item.color }}
              >
                {item.label}
              </span>
              );
            })}
          </div>
        </div>

        <div className="grid gap-4">
          <main className="relative min-h-[760px] overflow-hidden rounded-lg border border-white/10 bg-[#080d14]/80 p-4 shadow-2xl shadow-black/30 backdrop-blur md:p-6">
            <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
              <div className="flex items-center gap-2 rounded-full border border-white/10 bg-black/35 px-3 py-2 font-mono text-[11px] text-slate-300 backdrop-blur">
                <span className="h-2 w-2 rounded-full bg-emerald-400 shadow-[0_0_16px_rgba(74,222,128,.8)]" />
                <span>{selectedCompany ? 'STORYGRAPH' : 'SECTOR OVERVIEW'}</span>
                <strong className="text-[#5cd8ce]">{selectedCompany?.name || 'ALL'}</strong>
              </div>

              {selectedCompany && (
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => setSelectedCompany(null)}
                    className="w-fit rounded-full border border-white/10 bg-white/[.04] px-3 py-2 font-mono text-[11px] text-slate-300 transition hover:border-[#5cd8ce]/50 hover:text-white"
                  >
                    全セクターに戻る
                  </button>
                  <a
                    href={`/company/${selectedCompany.id}/`}
                    className="company-cta"
                    style={{ background: getSector(selectedCompany.sector).color }}
                  >
                    ↗ 企業データベースで詳しく見る →
                  </a>
                </div>
              )}
            </div>

            <AnimatePresence mode="wait">
              {selectedCompany && detail && layers ? (
                <motion.div
                  key={selectedCompany.id}
                  initial={{ opacity: 0, y: 16 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -12 }}
                  transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
                >
                  <LayeredStoryGraph
                    company={selectedCompany}
                    detail={detail}
                    layers={layers}
                    relatedArticles={relatedArticles}
                    hoveredNodeId={hoveredNodeId}
                    onHoverNode={setHoveredNodeId}
                    onNodeClick={handleStoryNodeClick}
                  />
                </motion.div>
              ) : (
                <motion.div
                  key="sector-overview"
                  initial={{ opacity: 0, scale: 0.985 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.985 }}
                  transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
                >
                  <SectorOverview
                    activeSector={activeSector}
                    onSectorClick={(sector) => setActiveSector((current) => (current === sector ? 'all' : sector))}
                    onCompanyClick={handleCompanyClick}
                  />
                </motion.div>
              )}
            </AnimatePresence>
          </main>
        </div>
      </div>
    </section>
  );
}

function SectorOverview({
  activeSector,
  onSectorClick,
  onCompanyClick,
}: {
  activeSector: SectorId;
  onSectorClick: (sector: SectorId) => void;
  onCompanyClick: (company: Company) => void;
}) {
  return (
    <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
      {SECTORS.map((sector) => {
        const sectorCompanies = COMPANIES.filter((company) => company.sector === sector.id);
        const isActive = activeSector === sector.id;
        const isDimmed = activeSector !== 'all' && !isActive;

        return (
          <motion.section
            key={sector.id}
            layout
            animate={{ opacity: isDimmed ? 0.34 : 1, scale: isActive ? 1.025 : 1 }}
            transition={{ duration: 0.25 }}
            className={[
              'group relative overflow-hidden rounded-lg border bg-white/[.045] p-4 text-left transition',
              isActive ? 'border-white/25 shadow-[0_0_38px_rgba(92,216,206,.14)]' : 'border-white/10',
            ].join(' ')}
            style={{ minHeight: isActive ? 280 : 224 }}
          >
            <button type="button" onClick={() => onSectorClick(sector.id)} className="absolute inset-0 z-0" aria-label={`${sector.name}を強調`} />
            <div className="relative z-10">
              <div className="mb-3 flex items-start justify-between gap-3">
                <div>
                  <p className="font-mono text-[10px] font-bold uppercase tracking-[.12em]" style={{ color: sector.color }}>
                    {sector.short}
                  </p>
                  <h3 className="mt-1 text-lg font-black tracking-[-.03em]">{sector.name}</h3>
                </div>
                <span className="rounded-full border border-white/10 bg-black/25 px-2 py-1 font-mono text-[10px] text-slate-400">
                  {sectorCompanies.length} nodes
                </span>
              </div>

              <p className="mb-4 min-h-[42px] text-xs leading-6 text-slate-400">{sector.description}</p>

              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                {sectorCompanies.slice(0, isActive ? 12 : 8).map((company) => (
                  <button
                    key={company.id}
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onCompanyClick(company);
                    }}
                    className="rounded-md border border-white/10 bg-black/25 px-3 py-2 text-left transition hover:border-[#5cd8ce]/60 hover:bg-[#5cd8ce]/10"
                  >
                    <span className="block font-mono text-[10px] text-slate-500">{company.logoText}</span>
                    <span className="mt-1 block truncate text-xs font-bold text-slate-100">{company.name}</span>
                  </button>
                ))}
              </div>
            </div>
            <div className="absolute -right-16 -top-16 h-36 w-36 rounded-full opacity-20 blur-3xl" style={{ background: sector.color }} />
            <div className="absolute inset-x-0 top-0 h-[2px]" style={{ background: sector.color }} />
          </motion.section>
        );
      })}
    </div>
  );
}

function LayeredStoryGraph({
  company,
  detail,
  layers,
  relatedArticles,
  hoveredNodeId,
  onHoverNode,
  onNodeClick,
}: {
  company: Company;
  detail: StoryGraph;
  layers: StoryGraphLayers;
  relatedArticles: RelatedArticle[];
  hoveredNodeId: string | null;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  const sector = getSector(company.sector);
  const finalBasisGroup = layers.supply[layers.supply.length - 1];
  const upstreamSupply = finalBasisGroup ? layers.supply.slice(0, -1) : layers.supply;
  const finalBasisLabel = finalBasisGroup ? connectorLabel(finalBasisGroup) : '基盤を提供';

  return (
    <div className="min-h-[620px]">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl">
          <p className="font-mono text-[11px] font-bold uppercase tracking-[.14em]" style={{ color: sector.color }}>
            {sector.name}
          </p>
          <h3 className="mt-2 text-3xl font-black tracking-[-.04em] md:text-4xl">{detail.title}</h3>
          <p className="mt-3 text-sm leading-7 text-slate-400">{detail.summary}</p>
        </div>
        <a
          href={`/company/${company.id}/`}
          className="company-cta"
          style={{ background: sector.color }}
        >
          ↗ 企業データベースで詳しく見る →
        </a>
      </div>

      <div className="storygraph-grid">
        <section className="storygraph-supply">
          <LayerHeader label="上流の供給・技術基盤" color={graphTone.supply} />
          <div className="grid gap-3">
            {upstreamSupply.map((group, index) => {
              const nextGroup = upstreamSupply[index + 1] || finalBasisGroup;
              const shouldConnectToNext = Boolean(firstVisibleNode(group) && firstVisibleNode(nextGroup));
              return (
                <React.Fragment key={`${group.group}-${index}`}>
                <LayerGroup
                  group={group}
                  tone={groupColor(group)}
                  hoveredNodeId={hoveredNodeId}
                  onHoverNode={onHoverNode}
                  onNodeClick={onNodeClick}
                />
                {shouldConnectToNext && (
                  <FlowConnector label={connectorLabel(group)} orientation="vertical" color={groupColor(group)} />
                )}
              </React.Fragment>
              );
            })}
          </div>
          </section>

        <section className="storygraph-center-wrap">
          <FinalFlowStage
            company={company}
            center={layers.center}
            finalBasisGroup={finalBasisGroup}
            finalBasisLabel={finalBasisLabel}
            color={sector.color}
            hoveredNodeId={hoveredNodeId}
            onHoverNode={onHoverNode}
            onNodeClick={onNodeClick}
          />
          {layers.outputs.length > 0 && <FlowConnector label="提供する" orientation="horizontal" color={graphTone.center} hideOnMobile />}
        </section>

        <section className="storygraph-output">
          <LayerHeader label="製品・サービス・接点" color={graphTone.output} />
          <div className="grid gap-3">
            {layers.outputs.map((group, index) => (
              <LayerGroup
                key={`${group.group}-${index}`}
                group={group}
                tone={groupColor(group)}
                hoveredNodeId={hoveredNodeId}
                onHoverNode={onHoverNode}
                onNodeClick={onNodeClick}
              />
            ))}
          </div>
        </section>

        {(layers.investments?.length || layers.partnerships?.length || layers.distribution?.length || layers.competitors.length > 0) && (
          <section className="storygraph-competitors">
            <div className="grid gap-4 xl:grid-cols-3">
              {Boolean(layers.investments?.length) && (
                <BottomNodePanel
                  title="出資・資本支援"
                  nodes={layers.investments || []}
                  tone={relationStyle.investment.color}
                  hoveredNodeId={hoveredNodeId}
                />
              )}
              {Boolean(layers.partnerships?.length || layers.distribution?.length) && (
                <BottomNodePanel
                  title="提携・提供チャネル"
                  groups={[...(layers.partnerships || []), ...(layers.distribution || [])]}
                  hoveredNodeId={hoveredNodeId}
                  onHoverNode={onHoverNode}
                  onNodeClick={onNodeClick}
                />
              )}
              {layers.competitors.length > 0 && (
                <BottomNodePanel
                  title="競合企業"
                  nodes={layers.competitors}
                  tone={graphTone.competitor}
                />
              )}
            </div>
          </section>
        )}
      </div>
      <RelatedArticlesSection articles={relatedArticles} />
    </div>
  );
}

function LayerHeader({ label, color }: { label: string; color: string }) {
  return (
    <div className="mb-3 flex items-center gap-2 font-mono text-[11px] font-bold uppercase tracking-[.12em] text-slate-400">
      <span className="h-2 w-2 rounded-full shadow-[0_0_14px_currentColor]" style={{ background: color, color }} />
      {label}
    </div>
  );
}

function BottomNodePanel({
  title,
  nodes,
  tone,
  hoveredNodeId,
  onHoverNode,
  onNodeClick,
}: {
  title: string;
  nodes: StoryGraphNode[];
  tone: string;
  hoveredNodeId: string | null;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/20 p-3">
      <LayerHeader label={title} color={tone} />
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
        {nodes.map((node) => (
          <StoryNodeCard
            key={node.id}
            node={node}
            tone={tone}
            compact
            highlighted={hoveredNodeId === node.id}
            onHoverNode={onHoverNode}
            onNodeClick={onNodeClick}
          />
        ))}
      </div>
    </div>
  );
}

function BottomGroupPanel({
  title,
  groups,
  hoveredNodeId,
  onHoverNode,
  onNodeClick,
}: {
  title: string;
  groups: StoryGraphGroup[];
  hoveredNodeId: string | null;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  return (
    <div className="rounded-lg border border-white/10 bg-black/20 p-3">
      <LayerHeader label={title} color={relationStyle.partnership.color} />
      <div className="grid gap-3">
        {groups.map((group, index) => (
          <LayerGroup
            key={`${group.group}-${index}`}
            group={group}
            tone={groupColor(group)}
            hoveredNodeId={hoveredNodeId}
            onHoverNode={onHoverNode}
            onNodeClick={onNodeClick}
          />
        ))}
      </div>
    </div>
  );
}

function LayerGroup({
  group,
  tone,
  compact = false,
  hoveredNodeId,
  onHoverNode,
  onNodeClick,
}: {
  group: StoryGraphGroup;
  tone: string;
  compact?: boolean;
  hoveredNodeId: string | null;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  return (
    <motion.div layout className="layer-box relative overflow-hidden rounded-lg border border-white/10 bg-white/[.055] p-3 shadow-xl shadow-black/20 backdrop-blur">
      <div className="absolute inset-y-0 left-0 w-[3px]" style={{ background: tone }} />
      <p className="mb-3 pl-1 font-mono text-[10px] font-bold uppercase tracking-[.12em] text-slate-500">{jaGroup(group.group)}</p>
      <div className="grid gap-2">
        {group.nodes.map((node) => (
          <StoryNodeCard
            key={node.id}
            node={node}
            tone={tone}
            compact={compact}
            highlighted={hoveredNodeId === node.id}
            onHoverNode={onHoverNode}
            onNodeClick={onNodeClick}
          />
        ))}
      </div>
    </motion.div>
  );
}

function StoryNodeCard({
  node,
  tone,
  compact = false,
  highlighted,
  onHoverNode,
  onNodeClick,
}: {
  node: StoryGraphNode;
  tone: string;
  compact?: boolean;
  highlighted: boolean;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  const company = findCompanyForNode(node);
  const clickable = Boolean(company);
  const logoText = node.logoText || company?.logoText || initials(node.label);
  const relationType = normalizeRelationType(node.type);
  const typeStyle = relationStyle[relationType];

  return (
    <button
      type="button"
      disabled={!clickable}
      onMouseEnter={() => onHoverNode(node.id)}
      onMouseLeave={() => onHoverNode(null)}
      onClick={() => onNodeClick(node)}
      className={[
        'node-card group relative w-full rounded-md border bg-black/20 text-left transition',
        compact ? 'px-3 py-2' : 'px-3 py-3',
        clickable ? 'cursor-pointer hover:-translate-y-0.5 hover:bg-white/[.07]' : 'cursor-default',
        highlighted ? 'border-white/30 shadow-[0_0_24px_rgba(92,216,206,.16)]' : 'border-white/10',
      ].join(' ')}
    >
      <div className="flex items-start gap-3">
        <div className="grid h-8 w-8 shrink-0 place-items-center overflow-hidden rounded-md border border-white/10 bg-white/[.045] font-mono text-[10px] font-black text-white">
          {node.logo ? <img src={node.logo} alt="" className="h-full w-full object-contain p-1" /> : logoText}
        </div>
        <div className="min-w-0 flex-1">
          <p className="node-title text-sm font-black text-slate-100">{node.label}</p>
          <div className="mt-1 flex flex-wrap items-center gap-2">
            {node.relation && <p className="text-[11px] leading-5 text-slate-400">{jaRelation(node.relation)}</p>}
            <span className="rounded-full px-2 py-0.5 font-mono text-[9px]" style={{ color: typeStyle.color, background: `${typeStyle.color}18` }}>
              {typeStyle.label}
            </span>
          </div>
        </div>
      </div>
      {clickable && <span className="absolute inset-x-3 bottom-0 h-px opacity-0 transition group-hover:opacity-100" style={{ background: tone }} />}
    </button>
  );
}

function FinalFlowStage({
  company,
  center,
  finalBasisGroup,
  finalBasisLabel,
  color,
  hoveredNodeId,
  onHoverNode,
  onNodeClick,
}: {
  company: Company;
  center: StoryGraphNode;
  finalBasisGroup: StoryGraphGroup | undefined;
  finalBasisLabel: string;
  color: string;
  hoveredNodeId: string | null;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  const basisTone = finalBasisGroup ? groupColor(finalBasisGroup) : graphTone.center;

  return (
    <div className="final-flow-stage">
      {finalBasisGroup && (
        <>
          <LayerGroup
            group={finalBasisGroup}
            tone={basisTone}
            compact
            hoveredNodeId={hoveredNodeId}
            onHoverNode={onHoverNode}
            onNodeClick={onNodeClick}
          />
          <FlowConnector label={finalBasisLabel} orientation="horizontal" color={basisTone} />
        </>
      )}
      <SelectedCompanyCard company={company} center={center} color={color} />
    </div>
  );
}

function SelectedCompanyCard({ company, center, color }: { company: Company; center: StoryGraphNode; color: string }) {
  return (
    <motion.div
      initial={{ scale: 0.94, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      transition={{ duration: 0.32 }}
      className="selected-company-card relative z-10 mx-auto grid min-h-[210px] w-full place-items-center rounded-[24px] border bg-[#07111b]/95 p-6 text-center shadow-[0_0_90px_rgba(92,216,206,.28)]"
      style={{ borderColor: color }}
    >
      <div className="absolute inset-3 rounded-[20px] border border-white/10" />
      <div className="absolute -inset-10 rounded-full opacity-20 blur-3xl" style={{ background: color }} />
      <div className="relative">
        <div className="mx-auto grid h-16 w-16 place-items-center rounded-2xl border border-white/15 bg-white/[.06] font-mono text-lg font-black text-white">
          {center.logo ? <img src={center.logo} alt="" className="h-full w-full object-contain p-2" /> : center.logoText || company.logoText}
        </div>
        <h4 className="mt-4 text-2xl font-black tracking-[-.04em] text-white">{center.label || company.name}</h4>
        <p className="mt-2 font-mono text-[10px] uppercase tracking-[.12em] text-slate-500">
          {center.type || company.role || 'Selected Company'}
        </p>
      </div>
    </motion.div>
  );
}

function FlowConnector({
  label,
  orientation,
  color,
  hideOnMobile = false,
}: {
  label: string;
  orientation: 'horizontal' | 'vertical';
  color: string;
  hideOnMobile?: boolean;
}) {
  return (
    <div
      className={[
        'flow-connector',
        orientation === 'horizontal' ? 'flow-connector-x' : 'flow-connector-y',
        hideOnMobile ? 'flow-hide-mobile' : '',
      ].join(' ')}
      style={{ ['--flow-color' as string]: color }}
    >
      <span className="flow-line" />
      <span className="flow-particle" />
      <span className="flow-label">{label}</span>
    </div>
  );
}

function RelatedArticlesSection({ articles }: { articles: RelatedArticle[] }) {
  if (articles.length === 0) return null;

  return (
    <section className="storygraph-related">
      <div className="mb-4 flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
        <div>
          <p className="font-mono text-[11px] font-bold uppercase tracking-[.14em] text-[#5a9eff]">
            関連記事
          </p>
          <h4 className="mt-1 text-xl font-black tracking-[-.03em]">この企業をさらに読む</h4>
        </div>
        <p className="text-xs leading-6 text-slate-500">
          現在はStoryGraphと関係データから表示しています。今後は記事Collectionのcompany / topic IDと連携できます。
        </p>
      </div>
      <div className="related-article-grid">
        {articles.map((article) => (
          <a
            key={`${article.source}-${article.href}-${article.title}`}
            href={article.href}
            className="related-article-card"
          >
            <div className="mb-3 flex flex-wrap items-center gap-2">
              <span className="related-category">{article.category}</span>
              {article.importance && <span className={`related-badge ${article.importance === '重要' ? 'is-important' : 'is-watch'}`}>{article.importance}</span>}
            </div>
            <h5>{article.title}</h5>
            <div className="mt-4 flex items-center justify-between gap-3 font-mono text-[10px] text-slate-500">
              <span>{article.sourceLabel}</span>
              <span>{article.publishedAt}</span>
            </div>
          </a>
        ))}
      </div>
    </section>
  );
}

function CompanyDetail({
  company,
  detail,
  relatedArticles,
}: {
  company: Company;
  detail: StoryGraph;
  relatedArticles: RelatedArticle[];
}) {
  const companyModels = MODELS.filter((model) => model.company === company.id);
  const companyRelations = RELATIONS.filter((relation) => relation.source === company.id || relation.target === company.id);

  return (
    <>
      <div className="mb-4 flex items-start gap-3">
        <div
          className="grid h-12 w-12 shrink-0 place-items-center rounded-md border bg-black/30 font-mono text-sm font-black text-white"
          style={{ borderColor: getSector(company.sector).color }}
        >
          {company.logo ? <img src={company.logo} alt="" className="h-full w-full object-contain p-2" /> : company.logoText}
        </div>
        <div>
          <h3 className="text-xl font-black tracking-[-.02em]">{company.name}</h3>
          <p className="font-mono text-[11px] text-slate-400">Score {company.score} · {getSector(company.sector).short}</p>
        </div>
      </div>

      <p className="mb-5 text-sm leading-7 text-slate-300">{company.description}</p>

      {companyModels.length > 0 && (
        <div className="mb-5">
          <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-[.12em] text-[#5a9eff]">製品・モデル</p>
          <div className="grid gap-2">
            {companyModels.slice(0, 6).map((model) => (
              <div key={model.id} className="rounded-md border border-white/10 bg-black/20 p-3">
                <p className="text-sm font-bold text-slate-100">{model.name}</p>
                <p className="mt-1 text-xs leading-5 text-slate-500">{model.description}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {companyRelations.length > 0 && (
        <div className="mb-5">
          <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-[.12em] text-[#5a9eff]">主要な関係</p>
          <div className="grid gap-2">
            {companyRelations.slice(0, 5).map((relation) => {
              const otherId = relation.source === company.id ? relation.target : relation.source;
              const style = relationStyle[normalizeRelationType(relation.type)];
              return (
                <div key={`${relation.source}-${relation.target}-${relation.type}`} className="rounded-md border border-white/10 bg-black/20 p-3">
                  <div className="flex items-center justify-between gap-3">
                    <span className="text-sm font-bold text-slate-100">{getCompanyName(otherId)}</span>
                    <span className="rounded-full px-2 py-1 font-mono text-[10px]" style={{ color: style.color, background: `${style.color}18` }}>
                      {jaRelation(relation.label)}
                    </span>
                  </div>
                  <p className="mt-2 text-xs leading-5 text-slate-400">{jaRelation(relation.description)}</p>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <div>
        <p className="mb-2 font-mono text-[11px] font-bold uppercase tracking-[.12em] text-[#5a9eff]">関連記事</p>
        <div className="grid gap-2">
          {relatedArticles.map((article) => (
            <a key={`${article.source}-${article.href}-${article.title}`} href={article.href} className="rounded-md border border-white/10 bg-white/[.035] p-3 transition hover:border-[#5cd8ce]/50 hover:bg-[#5cd8ce]/10">
              <p className="text-sm font-bold leading-6 text-slate-100">{article.title}</p>
              <p className="mt-1 font-mono text-[10px] uppercase tracking-[.1em] text-slate-500">
                {article.source === 'relation' ? 'relations.json' : 'storygraphs.json'}
              </p>
            </a>
          ))}
        </div>
      </div>
    </>
  );
}

function buildStoryLayers(company: Company, detail: StoryGraph): StoryGraphLayers {
  if (detail.layers) {
    return validateStoryGraph(
      detail,
      enforceStoryGraphRules(mergeRelationComplements(sanitizeLayers(detail.layers, company), company))
    );
  }

  const supply = detail.left && detail.left.length > 0
    ? detail.left.map((node, index) => ({ group: inferSupplyGroup(node, index), nodes: [legacyToStoryNode(node)] }))
    : buildSupplyFromRelations(company);

  const outputs = detail.right && detail.right.length > 0
    ? groupOutputNodes(detail.right.map(legacyToStoryNode))
    : buildOutputsFromModelsAndRelations(company);

  return validateStoryGraph(detail, enforceStoryGraphRules(sanitizeLayers({
    supply,
    center: {
      id: company.id,
      label: detail.center?.name || company.name,
      logoText: company.logoText,
      logo: company.logo,
      type: company.role || getSector(company.sector).name,
    },
    outputs,
    investments: buildInvestmentNodes(company),
    partnerships: buildRelationGroups(company, 'partnership'),
    distribution: buildRelationGroups(company, 'distribution'),
    competitors: buildCompetitors(company),
  }, company)));
}

function sanitizeLayers(layers: StoryGraphLayers, company: Company): StoryGraphLayers {
  return {
    supply: sanitizeGroups(layers.supply),
    center: {
      id: layers.center.id || company.id,
      label: layers.center.label || company.name,
      logo: layers.center.logo || company.logo,
      logoText: layers.center.logoText || company.logoText,
      type: layers.center.type || company.role || getSector(company.sector).name,
    },
    outputs: sanitizeGroups(layers.outputs),
    competitors: sanitizeNodes(layers.competitors || []),
    investments: sanitizeNodes(layers.investments || []),
    partnerships: sanitizeGroups(layers.partnerships || []),
    distribution: sanitizeGroups(layers.distribution || []),
    edges: layers.edges || [],
  };
}

function mergeRelationComplements(layers: StoryGraphLayers, company: Company): StoryGraphLayers {
  return {
    ...layers,
    investments: mergeStoryNodes(layers.investments || [], buildInvestmentNodes(company)),
    partnerships: mergeStoryGroups(layers.partnerships || [], buildRelationGroups(company, 'partnership')),
    distribution: mergeStoryGroups(layers.distribution || [], buildRelationGroups(company, 'distribution')),
    competitors: mergeStoryNodes(layers.competitors || [], buildCompetitors(company)),
  };
}

function enforceStoryGraphRules(layers: StoryGraphLayers): StoryGraphLayers {
  return {
    ...layers,
    supply: stripBottomRelations(layers.supply),
    outputs: stripBottomRelations(layers.outputs),
    investments: sanitizeNodes(layers.investments || []).map((node) => ({ ...node, type: 'investment' })),
    partnerships: sanitizeGroups(layers.partnerships || []),
    distribution: sanitizeGroups(layers.distribution || []),
    competitors: sanitizeNodes(layers.competitors || []).map((node) => ({ ...node, type: 'competitor' })),
  };
}

function stripBottomRelations(groups: StoryGraphGroup[]) {
  return groups
    .map((group) => ({
      ...group,
      nodes: group.nodes.filter((node) => !isBottomRelationType(node.type)),
    }))
    .filter((group) => group.nodes.length > 0);
}

function isBottomRelationType(type: string | undefined) {
  const normalized = normalizeRelationType(type);
  return ['investment', 'partnership', 'distribution', 'competitor'].includes(normalized);
}

function mergeStoryNodes(primary: StoryGraphNode[], supplemental: StoryGraphNode[]) {
  const nodes = new Map<string, StoryGraphNode>();
  [...primary, ...supplemental].forEach((node) => {
    if (!node.id || node.hidden || nodes.has(node.id)) return;
    nodes.set(node.id, node);
  });
  return Array.from(nodes.values());
}

function mergeStoryGroups(primary: StoryGraphGroup[], supplemental: StoryGraphGroup[]) {
  const groups = new Map<string, StoryGraphNode[]>();

  [...primary, ...supplemental].forEach((group) => {
    const existing = groups.get(group.group) || [];
    groups.set(group.group, mergeStoryNodes(existing, group.nodes));
  });

  return Array.from(groups.entries())
    .map(([group, nodes]) => ({ group, nodes }))
    .filter((group) => group.nodes.length > 0);
}

function sanitizeGroups(groups: StoryGraphGroup[]) {
  return groups
    .map((group) => ({ ...group, nodes: sanitizeNodes(group.nodes) }))
    .filter((group) => group.nodes.length > 0);
}

function sanitizeNodes(nodes: StoryGraphNode[]) {
  return nodes.filter((node) => node.id && !node.hidden);
}

function validateStoryGraph(detail: StoryGraph, layers: StoryGraphLayers): StoryGraphLayers {
  const nodeMap = buildVisibleNodeMap(layers);

  const edges = (layers.edges || []).flatMap((edge) => {
    const sourceNode = nodeMap.get(edge.source);
    const targetNode = nodeMap.get(edge.target);

    if (!sourceNode || !targetNode || edge.hidden) {
      console.warn('orphan edge skipped', { company: detail.company, edge });
      return [];
    }

    if (hasInvalidCoordinates(sourceNode) || hasInvalidCoordinates(targetNode)) {
      console.warn('orphan edge skipped', { company: detail.company, edge, reason: 'invalid node coordinates' });
      return [];
    }

    return [edge];
  });

  return { ...layers, edges };
}

function buildVisibleNodeMap(layers: StoryGraphLayers) {
  const nodes = [
    ...layers.supply.flatMap((group) => group.nodes),
    layers.center,
    ...layers.outputs.flatMap((group) => group.nodes),
    ...(layers.investments || []),
    ...(layers.partnerships || []).flatMap((group) => group.nodes),
    ...(layers.distribution || []).flatMap((group) => group.nodes),
    ...layers.competitors,
  ];

  return new Map(nodes.filter((node) => node.id && !node.hidden).map((node) => [node.id, node]));
}

function hasInvalidCoordinates(node: StoryGraphNode) {
  const hasCoordinateShape = 'x' in node || 'y' in node;
  if (!hasCoordinateShape) return false;
  return node.x == null || node.y == null || !Number.isFinite(node.x) || !Number.isFinite(node.y);
}

function legacyToStoryNode(node: LegacyFlowNode): StoryGraphNode {
  const company = findCompanyByName(node.name);
  return {
    id: company?.id || slugify(node.name),
    label: node.name,
    relation: jaRelation(node.relation || ''),
    type: normalizeRelationType(node.type),
    logo: company?.logo,
    logoText: company?.logoText || initials(node.name),
    description: node.description,
  };
}

function buildSupplyFromRelations(company: Company): StoryGraphGroup[] {
  const inbound = RELATIONS
    .filter((relation) => relation.target === company.id && !['competition', 'competitor', 'investment', 'partnership', 'distribution'].includes(relation.type))
    .sort((a, b) => b.strength - a.strength)
    .slice(0, 5);

  return inbound.map((relation, index) => ({
    group: inferRelationGroup(relation, index, 'supply'),
    nodes: [relationToNode(relation.source, relation)],
  }));
}

function buildOutputsFromModelsAndRelations(company: Company): StoryGraphGroup[] {
  const modelNodes = MODELS.filter((model) => model.company === company.id).map((model) => ({
    id: model.id,
    label: model.name,
    relation: model.type === 'agent' ? 'エージェント / 自動化' : model.type === 'product' ? '製品' : '基盤モデル',
    type: model.type === 'product' ? 'product' : 'model',
    logoText: initials(model.name),
    description: model.description,
  }));

  const relationNodes = RELATIONS
    .filter((relation) => relation.source === company.id && !['competition', 'competitor', 'investment', 'partnership', 'distribution'].includes(relation.type))
    .sort((a, b) => b.strength - a.strength)
    .slice(0, 4)
    .map((relation) => relationToNode(relation.target, relation));

  return groupOutputNodes([...modelNodes, ...relationNodes]);
}

function groupOutputNodes(nodes: StoryGraphNode[]): StoryGraphGroup[] {
  const groups = new Map<string, StoryGraphNode[]>();

  nodes.forEach((node) => {
    const group = inferOutputGroup(node);
    groups.set(group, [...(groups.get(group) || []), node]);
  });

  return Array.from(groups.entries()).map(([group, groupNodes]) => ({ group, nodes: groupNodes }));
}

function buildCompetitors(company: Company): StoryGraphNode[] {
  return RELATIONS
    .filter((relation) => ['competition', 'competitor'].includes(relation.type) && (relation.source === company.id || relation.target === company.id))
    .map((relation) => relation.source === company.id ? relation.target : relation.source)
    .filter((id, index, ids) => ids.indexOf(id) === index)
    .slice(0, 7)
    .map((id) => {
      const competitor = COMPANIES.find((item) => item.id === id);
      return {
        id,
        label: competitor?.name || id,
        relation: '競合',
        type: 'competitor',
        logo: competitor?.logo,
        logoText: competitor?.logoText || initials(competitor?.name || id),
      };
    });
}

function buildInvestmentNodes(company: Company): StoryGraphNode[] {
  return RELATIONS
    .filter((relation) => relation.type === 'investment' && (relation.source === company.id || relation.target === company.id))
    .map((relation) => relationToInvestmentNode(company, relation))
    .filter((node, index, nodes) => nodes.findIndex((item) => item.id === node.id) === index)
    .slice(0, 6);
}

function relationToInvestmentNode(company: Company, relation: Relation): StoryGraphNode {
  const isInvestorView = relation.source === company.id;
  const id = isInvestorView ? relation.target : relation.source;
  const relatedCompany = COMPANIES.find((item) => item.id === id);

  return {
    id,
    label: relatedCompany?.name || id,
    relation: isInvestorView ? '出資先' : '出資者',
    type: 'investment',
    logo: relatedCompany?.logo,
    logoText: relatedCompany?.logoText || initials(relatedCompany?.name || id),
    description: relation.description,
  };
}

function buildRelationGroups(company: Company, type: RelationType): StoryGraphGroup[] {
  const nodes = RELATIONS
    .filter((relation) => relation.type === type && (relation.source === company.id || relation.target === company.id))
    .map((relation) => relationToNode(relation.source === company.id ? relation.target : relation.source, relation));

  if (nodes.length === 0) return [];
  return [{ group: relationStyle[type].label, nodes }];
}

function relationToNode(id: string, relation: Relation): StoryGraphNode {
  const company = COMPANIES.find((item) => item.id === id);
  const style = relationStyle[relation.type];
  return {
    id,
    label: company?.name || id,
    relation: relation.label || style.verb,
    type: normalizeRelationType(relation.type),
    logo: company?.logo,
    logoText: company?.logoText || initials(company?.name || id),
    description: relation.description,
  };
}

function inferSupplyGroup(node: LegacyFlowNode, index: number) {
  const name = node.name.toLowerCase();
  if (name.includes('tsmc') || name.includes('asml')) return '半導体製造';
  if (name.includes('nvidia') || name.includes('gpu') || name.includes('hbm') || name.includes('cowos')) return 'GPU / AIアクセラレータ';
  if (name.includes('azure') || name.includes('aws') || name.includes('google') || name.includes('cloud')) return 'クラウド基盤';
  if (index === 0) return '上流供給';
  return '基盤レイヤー';
}

function inferRelationGroup(relation: Relation, index: number, side: 'supply' | 'output') {
  const type = normalizeRelationType(relation.type);
  if (type === 'semiconductor') return '半導体製造';
  if (type === 'gpu_supply' || type === 'accelerator') return index === 0 ? 'GPU / AIアクセラレータ' : '計算資源';
  if (type === 'cloud' || type === 'platform') return side === 'supply' ? 'クラウド基盤' : '提供基盤';
  if (type === 'partnership') return '提携';
  if (type === 'distribution') return '提供チャネル';
  if (type === 'research') return '研究開発';
  return side === 'supply' ? '基盤レイヤー' : '製品・サービス';
}

function inferOutputGroup(node: StoryGraphNode) {
  const text = `${node.label} ${node.relation || ''} ${node.type || ''}`.toLowerCase();
  if (text.includes('api') || text.includes('developer') || text.includes('codex') || text.includes('code')) return '開発者向け基盤';
  if (text.includes('sora') || text.includes('dall') || text.includes('video') || text.includes('creative') || text.includes('image')) return 'クリエイティブAI';
  if (text.includes('enterprise') || text.includes('work') || text.includes('bedrock') || text.includes('vertex') || text.includes('distribution')) return '法人向け提供';
  if (text.includes('chat') || text.includes('consumer')) return '一般向けサービス';
  if (text.includes('model') || text.includes('claude') || text.includes('gpt') || text.includes('llama')) return 'モデル';
  return '製品・サービス';
}

function connectorLabel(group: StoryGraphGroup) {
  return jaRelation(group.nodes[0]?.relation || '次へつながる');
}

function firstVisibleNode(group: StoryGraphGroup | undefined) {
  return group?.nodes.find((node) => node.id && !node.hidden);
}

function groupColor(group: StoryGraphGroup) {
  const firstType = normalizeRelationType(group.nodes[0]?.type);
  if (firstType) return relationStyle[firstType].color;
  return graphTone.supply;
}

function normalizeRelationType(type: string | undefined): RelationType {
  if (type === 'competition') return 'competitor';
  if (type === 'company' || type === 'component' || !type) return 'partnership';
  if (type in relationStyle) return type as RelationType;
  return 'partnership';
}

function jaGroup(group: string) {
  const table: Record<string, string> = {
    'Semiconductor Manufacturing': '半導体製造',
    Lithography: '露光装置',
    'Advanced Packaging / Memory': '先端パッケージング・メモリ',
    'GPU / AI Accelerator': 'GPU / AIアクセラレータ',
    'GPU / Accelerator': 'GPU / AIアクセラレータ',
    'Semiconductor / Accelerator': '半導体・AIアクセラレータ',
    'Cloud / Capital': 'クラウド基盤・資本',
    'Cloud Infrastructure': 'クラウド基盤',
    'Model Partners': 'モデル提携',
    Consumer: '一般向けサービス',
    'Developer Platform': '開発者向け基盤',
    'Developer Tools': '開発者向けツール',
    'Creative AI': 'クリエイティブAI',
    'Enterprise / Automation': '法人向け・自動化',
    Enterprise: '法人向け',
    'Enterprise AI': '法人向けAI',
    'Enterprise / Distribution': '法人向け提供',
    'Enterprise Distribution': '法人向け提供',
    Models: 'モデル',
    GPUs: 'GPU製品',
    'Software Platform': 'ソフトウェア基盤',
    'Cloud / Systems': 'クラウド・システム',
    Customers: '供給先企業',
    Infrastructure: 'インフラ基盤',
    'Model Access': 'モデル利用',
    'Products / Relationships': '製品・関係性',
    'Products / Services': '製品・サービス',
    'Upstream / Partners': '上流・提携先',
    'Foundation Layer': '基盤レイヤー',
  };
  return table[group] || group;
}

function jaRelation(value: string) {
  const table: Record<string, string> = {
    'manufactures advanced chips': '先端半導体を製造',
    'advanced manufacturing': '先端製造',
    manufactures: '製造',
    'lithography equipment': '露光装置を提供',
    'packaging and high-bandwidth memory': 'パッケージング・高帯域メモリ',
    'supplies GPUs': 'GPUを供給',
    'GPU supply': 'GPUを供給',
    'AI accelerator': 'AIアクセラレータ',
    'in-house AI accelerator': '自社AIアクセラレータ',
    'compute': '計算資源',
    'cloud infrastructure': 'クラウド基盤を提供',
    'cloud infrastructure / investment': 'クラウド基盤・出資',
    'investment and cloud': '出資・クラウド支援',
    'investment / cloud support': '出資・クラウド支援',
    'investment and capital support': '出資・資本支援',
    'strategic investment / model partner': '戦略出資・モデル提携',
    'enterprise distribution': '法人向け提供',
    'model marketplace and enterprise distribution': 'モデル市場・法人向け提供',
    'developer platform': '開発者向け基盤',
    'coding agent': '開発支援エージェント',
    'coding assistant': '開発支援',
    'consumer AI service': '一般向けAIサービス',
    'foundation model': '基盤モデル',
    'video generation': '動画生成',
    'image generation': '画像生成',
    'workflow automation': '業務自動化',
    'enterprise AI service': '法人向けAIサービス',
    'training GPU': '学習用GPU',
    'next-generation AI GPU': '次世代AI GPU',
    'developer moat': '開発者基盤',
    'enterprise AI compute': '法人向けAI計算基盤',
    'robotics and autonomy compute': 'ロボティクス・自動運転向け計算資源',
    'Azure GPU infrastructure': 'Azure向けGPU基盤',
    'competes in AI GPUs': 'AI GPUで競合',
    'competes in accelerators': 'AIアクセラレータで競合',
    'custom AI ASICs': 'カスタムAI ASICで競合',
    'alternative AI compute': '代替AI計算基盤で競合',
    'inference accelerators': '推論アクセラレータで競合',
    'competes in frontier models': '基盤モデルで競合',
    'competes in models and agents': 'モデル・エージェントで競合',
    'competes via open models': 'オープンモデルで競合',
    'competes via efficient models': '高効率モデルで競合',
    'cloud AI competition': 'クラウドAIで競合',
    'Claude on Bedrock': 'Bedrock経由でClaudeを提供',
  };
  return table[value] || value;
}

function buildRelatedArticles(company: Company, detail: StoryGraph): RelatedArticle[] {
  const articles = new Map<string, RelatedArticle>();

  detail.articles.forEach((article, index) => {
    articles.set(article.href, {
      ...article,
      source: 'storygraph',
      sourceLabel: 'AI経済新聞',
      category: categoryFromHref(article.href),
      publishedAt: '随時更新',
      importance: index === 0 ? '重要' : index === 1 ? '注目' : undefined,
    });
  });

  RELATIONS
    .filter((relation) => relation.source === company.id || relation.target === company.id)
    .sort((a, b) => b.strength - a.strength)
    .forEach((relation) => {
      const otherId = relation.source === company.id ? relation.target : relation.source;
      relation.articles.forEach((href) => {
        if (!articles.has(href)) {
          articles.set(href, {
            title: `${company.name} x ${getCompanyName(otherId)}: ${relation.label}`,
            href,
            source: 'relation',
            sourceLabel: getCompanyName(otherId),
            category: categoryFromHref(href),
            publishedAt: '随時更新',
            importance: relation.strength >= 85 ? '重要' : relation.strength >= 70 ? '注目' : undefined,
          });
        }
      });
    });

  return Array.from(articles.values()).slice(0, 6);
}

function categoryFromHref(href: string) {
  const table: Record<string, string> = {
    infrastructure: 'インフラ',
    model: 'モデル',
    markets: 'AI関連株',
    business: 'ビジネス',
    policy: '政策',
    products: 'プロダクト',
    research: '研究',
    topic: 'トピック',
    company: '企業',
  };
  const key = href.split('/').filter(Boolean)[0];
  return table[key] || '関連記事';
}

function buildDefaultArticles(company: Company) {
  const fromRelations = RELATIONS
    .filter((relation) => relation.source === company.id || relation.target === company.id)
    .flatMap((relation) => relation.articles)
    .filter(Boolean);

  const unique = Array.from(new Set(fromRelations)).slice(0, 3);

  if (unique.length > 0) {
    return unique.map((href) => ({ title: `${company.name} に関連する記事`, href }));
  }

  return [{ title: `${company.name} の関連記事を見る`, href: `/topic/${company.id}/` }];
}

function getSector(id: Exclude<SectorId, 'all'>) {
  return SECTORS.find((sector) => sector.id === id) || SECTORS[0];
}

function getCompanyName(id: string) {
  return COMPANIES.find((company) => company.id === id)?.name || id;
}

function findCompanyForNode(node: StoryGraphNode) {
  return COMPANIES.find((company) => company.id === node.id) || findCompanyByName(node.label);
}

function findCompanyByName(name: string) {
  const normalized = name.toLowerCase();
  return COMPANIES.find((company) => {
    const aliases = [company.name, company.logoText, ...(company.tags || [])].map((item) => item.toLowerCase());
    return aliases.includes(normalized) || normalized.includes(company.name.toLowerCase());
  });
}

function slugify(value: string) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/(^-|-$)/g, '');
}

function initials(value: string) {
  return value
    .split(/\s+|\//)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join('')
    .toUpperCase();
}

function StoryGraphStyles() {
  return (
    <style>{`
      .storygraph-grid {
        display: grid;
        grid-template-columns: 240px minmax(420px, 1fr) minmax(260px, .85fr);
        grid-template-areas:
          "supply center output"
          "competitors competitors competitors";
        gap: 24px;
        align-items: center;
        
      }
      .storygraph-supply { grid-area: supply; }
      .storygraph-output { grid-area: output; }
      .storygraph-center-wrap {
        grid-area: center;
        position: relative;
        display: grid;
        place-items: center;
        min-height: 360px;
      }
      .final-flow-stage {
        position: relative;
        z-index: 1;
        display: grid;
        grid-template-columns: minmax(180px, 220px) 78px minmax(190px, 240px);
        align-items: center;
        justify-content: center;
        gap: 10px;
        width: 100%;
      }
      .final-flow-stage .flow-connector-x {
        position: relative;
        top: auto;
        width: 100%;
        transform: none;
      }
      .selected-company-card {
        max-width: 240px;
      }
      .layer-box {
        max-width: 220px;
        width: 100%;
        justify-self: center;
      }
      .node-card {
        max-width: 180px;
        justify-self: center;
      }
      .node-title {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        line-height: 1.45;
      }
      .node-card p:not(.node-title) {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
      }
      .company-cta {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: fit-content;
        border: 1px solid rgba(255,255,255,.22);
        border-radius: 999px;
        padding: 9px 14px;
        color: #fff;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 11px;
        font-weight: 900;
        box-shadow: 0 14px 34px rgba(0,0,0,.28);
        transition: transform .18s ease, box-shadow .18s ease, filter .18s ease;
      }
      .company-cta:hover {
        transform: translateY(-2px);
        filter: brightness(1.08);
        box-shadow: 0 18px 44px rgba(0,0,0,.36);
      }
      .storygraph-competitors {
        grid-area: competitors;
        margin-top: 14px;
        border: 1px solid rgba(248, 113, 113, .18);
        border-radius: 14px;
        background: rgba(248, 113, 113, .045);
        padding: 14px;
      }
      .storygraph-related {
        margin-top: 22px;
        border-top: 1px solid rgba(255,255,255,.1);
        padding-top: 20px;
      }
      .related-article-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 12px;
      }
      .related-article-card {
        position: relative;
        overflow: hidden;
        min-height: 150px;
        border: 1px solid rgba(255,255,255,.1);
        border-radius: 12px;
        background:
          radial-gradient(circle at 14% 0%, rgba(92,216,206,.12), transparent 18rem),
          rgba(255,255,255,.045);
        padding: 16px;
        transition: transform .2s ease, border-color .2s ease, background .2s ease, box-shadow .2s ease;
      }
      .related-article-card:hover {
        transform: translateY(-3px);
        border-color: rgba(92,216,206,.52);
        background:
          radial-gradient(circle at 14% 0%, rgba(92,216,206,.18), transparent 18rem),
          rgba(92,216,206,.06);
        box-shadow: 0 0 34px rgba(92,216,206,.12);
      }
      .related-article-card h5 {
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        min-height: 48px;
        color: #f3f8ff;
        font-size: 14px;
        font-weight: 800;
        line-height: 1.7;
      }
      .related-category,
      .related-badge {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 4px 8px;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 10px;
        font-weight: 800;
        line-height: 1;
      }
      .related-category {
        border: 1px solid rgba(90,158,255,.22);
        background: rgba(90,158,255,.1);
        color: #9cc8ff;
      }
      .related-badge.is-important {
        background: rgba(248,113,113,.12);
        color: #fca5a5;
      }
      .related-badge.is-watch {
        background: rgba(234,179,8,.12);
        color: #fde68a;
      }
      .flow-connector {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--flow-color);
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 10px;
        font-weight: 800;
        letter-spacing: .1em;
        text-transform: uppercase;
      }
      .flow-connector-y { min-height: 34px; flex-direction: column; }
      .flow-connector-x {
        position: absolute;
        top: 50%;
        width: 76px;
        transform: translateY(-50%);
      }
      .storygraph-center-wrap .flow-connector-x:first-child { left: -42px; }
      .storygraph-center-wrap .flow-connector-x:last-child { right: -42px; }
      .flow-line {
        display: block;
        background: linear-gradient(90deg, transparent, var(--flow-color), transparent);
        box-shadow: 0 0 16px var(--flow-color);
      }
      .flow-connector-x .flow-line { width: 100%; height: 1px; }
      .flow-connector-y .flow-line {
        width: 1px;
        height: 28px;
        background: linear-gradient(180deg, transparent, var(--flow-color), transparent);
      }
      .flow-particle {
        position: absolute;
        width: 5px;
        height: 5px;
        border-radius: 999px;
        background: var(--flow-color);
        box-shadow: 0 0 14px var(--flow-color);
      }
      .flow-connector-x .flow-particle { animation: ecosystemFlowX 1.75s linear infinite; }
      .flow-connector-y .flow-particle { animation: ecosystemFlowY 1.75s linear infinite; }
      .flow-label {
        border: 1px solid rgba(255,255,255,.1);
        border-radius: 999px;
        background: rgba(7,9,13,.82);
        padding: 3px 7px;
        white-space: nowrap;
      }
      @keyframes ecosystemFlowX {
        0% { left: 0; opacity: 0; }
        18% { opacity: 1; }
        100% { left: calc(100% - 5px); opacity: 0; }
      }
      @keyframes ecosystemFlowY {
        0% { top: 2px; opacity: 0; }
        18% { opacity: 1; }
        100% { top: calc(100% - 7px); opacity: 0; }
      }
      @media (max-width: 1024px) {
        .storygraph-grid {
          grid-template-columns: 1fr;
          grid-template-areas:
            "supply"
            "center"
            "output"
            "competitors";
          align-items: stretch;
        }
        .storygraph-center-wrap { min-height: 260px; }
        .final-flow-stage {
          grid-template-columns: 1fr;
          gap: 12px;
        }
        .final-flow-stage .flow-connector-x {
          position: relative;
          top: auto;
          width: 100%;
          min-height: 34px;
          transform: none;
        }
        .layer-box,
        .node-card,
        .selected-company-card {
          max-width: none;
        }
        .flow-hide-mobile { display: none; }
        .related-article-grid { grid-template-columns: 1fr; }
      }
    `}</style>
  );
}
