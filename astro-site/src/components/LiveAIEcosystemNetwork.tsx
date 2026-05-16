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
  internalEdges?: StoryGraphEdge[];
  supplyChainOrder?: string[];
  hidden?: boolean;
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
const FALLBACK_COLOR = '#5CD8CE';
const graphTone = {
  supply: '#5A9EFF',
  center: '#5CD8CE',
  output: '#A78BFA',
  competitor: '#F87171',
};

function safeColor(color?: string | null) {
  return color || FALLBACK_COLOR;
}

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
                    全セクターに戻る</button>
                  <a
                    href={`/company/${selectedCompany.id}/`}
                    className="company-cta"
                    style={{ background: getSector(selectedCompany.sector).color }}
                  >
                    ↗ 企業データベースで詳しく見る →</a>
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

type FlowMapLayer = {
  id: string;
  title: string;
  subtitle?: string;
  color: string;
  nodes: StoryGraphNode[];
  internalEdges?: StoryGraphEdge[];
  featured?: boolean;
};

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
  const sectorColor = safeColor(sector.color);
  const finalBasisGroup = layers.supply[layers.supply.length - 1];
  const upstreamSupply = finalBasisGroup ? layers.supply.slice(0, -1) : layers.supply;
  const upstreamNodes = mergeStoryNodes([], upstreamSupply.flatMap((group) => visibleNodes(group.nodes)));
  const finalBasisNodes = visibleNodes(finalBasisGroup?.nodes || []);
  const outputNodes = mergeStoryNodes([], layers.outputs.flatMap((group) => visibleNodes(group.nodes)));
  const relationNodes = mergeStoryNodes(
    [],
    [
      ...(layers.investments || []),
      ...flattenGroups([...(layers.partnerships || []), ...(layers.distribution || [])]),
    ]
  );
  const hasBottomRelations = relationNodes.length > 0 || layers.competitors.length > 0;

  const flowLayers: FlowMapLayer[] = [
    upstreamNodes.length > 0
      ? {
          id: 'upstream',
          title: '半導体 / GPU',
          subtitle: '供給・技術基盤',
          color: graphTone.supply,
          nodes: upstreamNodes,
          internalEdges: buildInternalEdgesFromGroups(upstreamSupply),
        }
      : null,
    finalBasisNodes.length > 0
      ? {
          id: 'basis',
          title: jaGroup(finalBasisGroup?.group || 'クラウド基盤'),
          subtitle: '最終的に届く基盤',
          color: finalBasisGroup ? groupColor(finalBasisGroup) : relationStyle.cloud.color,
          nodes: finalBasisNodes,
          internalEdges: finalBasisGroup?.internalEdges,
        }
      : null,
    {
      id: 'selected-company',
      title: company.name,
      subtitle: '選択企業',
      color: sectorColor,
      nodes: [layers.center],
      featured: true,
    },
    outputNodes.length > 0
      ? {
          id: 'outputs',
          title: '製品・サービス',
          subtitle: 'ユーザー接点',
          color: graphTone.output,
          nodes: outputNodes,
          internalEdges: flattenLayerEdges(layers.outputs),
        }
      : null,
  ].filter(Boolean) as FlowMapLayer[];

  return (
    <div className="min-h-[620px]">
      <div className="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div className="max-w-4xl">
          <p className="font-mono text-[11px] font-bold uppercase tracking-[.14em]" style={{ color: sectorColor }}>
            {sector.name}
          </p>
          <h3 className="mt-2 text-3xl font-black tracking-[-.04em] md:text-4xl">{detail.title}</h3>
          <p className="mt-3 text-sm leading-7 text-slate-400">{detail.summary}</p>
        </div>
        <a
          href={`/company/${company.id}/`}
          className="company-cta"
          style={{ background: sectorColor }}
        >
          ↗ 企業データベースで詳しく見る →
        </a>
      </div>

      <div className="storygraph-map-shell">
        <div className="storygraph-flow-row">
          {flowLayers.map((layer, index) => (
            <React.Fragment key={layer.id}>
              <StoryGraphFlowStage
                layer={layer}
                hoveredNodeId={hoveredNodeId}
                onHoverNode={onHoverNode}
                onNodeClick={onNodeClick}
              />
              {index < flowLayers.length - 1 && (
                <FlowConnector label={flowConnectorLabel(layer, flowLayers[index + 1])} orientation="horizontal" color={layer.color} />
              )}
            </React.Fragment>
          ))}
        </div>
      </div>

      {hasBottomRelations && (
        <section className="storygraph-competitors">
          <div className="storygraph-logo-panels">
            {relationNodes.length > 0 && (
              <LogoChipPanel
                title="出資・提携"
                nodes={relationNodes}
                tone={relationStyle.partnership.color}
                onNodeClick={onNodeClick}
              />
            )}
            {layers.competitors.length > 0 && (
              <LogoChipPanel
                title="競合"
                nodes={layers.competitors}
                tone={graphTone.competitor}
                onNodeClick={onNodeClick}
              />
            )}
          </div>
        </section>
      )}

      <RelatedArticlesSection articles={relatedArticles} />
    </div>
  );
}

function StoryGraphFlowStage({
  layer,
  hoveredNodeId,
  onHoverNode,
  onNodeClick,
}: {
  layer: FlowMapLayer;
  hoveredNodeId: string | null;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  const color = safeColor(layer.color);
  const orderedNodes = orderLayerNodes(layer.nodes, layer.internalEdges);
  const shouldFrame = !layer.featured && orderedNodes.length > 1;

  if (layer.featured) {
    return (
      <section className="flow-stage flow-stage-featured" style={{ ['--stage-color' as string]: color }}>
        <SelectedCompanyFlowCard
          node={orderedNodes[0]}
          color={color}
          hoveredNodeId={hoveredNodeId}
          onHoverNode={onHoverNode}
          onNodeClick={onNodeClick}
        />
      </section>
    );
  }

  if (!shouldFrame) {
    const node = orderedNodes[0];
    if (!node) return null;
    return (
      <section className="flow-stage flow-stage-single" style={{ ['--stage-color' as string]: color }}>
        <StoryNodeCard
          node={node}
          tone={color}
          compact
          highlighted={hoveredNodeId === node.id}
          onHoverNode={onHoverNode}
          onNodeClick={onNodeClick}
        />
      </section>
    );
  }

  return (
    <section className="flow-stage layer-frame" style={{ ['--stage-color' as string]: color }}>
      <div className="layer-frame-head">
        <div>
          <h4>{layer.title}</h4>
          {layer.subtitle && <p>{layer.subtitle}</p>}
        </div>
        <span className="layer-frame-dot" />
      </div>
      <div className="layer-frame-body">
        {orderedNodes.map((node, index) => {
          const nextNode = orderedNodes[index + 1];
          const edge = nextNode ? findInternalEdge(layer.internalEdges, node.id, nextNode.id) : undefined;
          return (
            <React.Fragment key={node.id}>
              <StoryNodeCard
                node={node}
                tone={color}
                compact
                highlighted={hoveredNodeId === node.id}
                onHoverNode={onHoverNode}
                onNodeClick={onNodeClick}
              />
              {edge && <InternalFlowConnector label={edge.label || node.relation || '供給'} color={relationColor(edge.type, color)} />}
            </React.Fragment>
          );
        })}
      </div>
    </section>
  );
}

function SelectedCompanyFlowCard({
  node,
  color,
  hoveredNodeId,
  onHoverNode,
  onNodeClick,
}: {
  node: StoryGraphNode;
  color: string;
  hoveredNodeId: string | null;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  return (
    <div className="selected-flow-card">
      <StoryNodeCard
        node={node}
        tone={color}
        highlighted={hoveredNodeId === node.id}
        onHoverNode={onHoverNode}
        onNodeClick={onNodeClick}
      />
    </div>
  );
}

function InternalFlowConnector({ label, color }: { label: string; color: string }) {
  return (
    <div className="internal-flow" style={{ ['--internal-color' as string]: safeColor(color) }}>
      <span className="internal-line" />
      <span className="internal-particle" />
      <span className="internal-label">{jaRelation(label)}</span>
    </div>
  );
}

function LogoChipPanel({
  title,
  nodes,
  tone,
  onNodeClick,
}: {
  title: string;
  nodes: StoryGraphNode[];
  tone: string;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  const color = safeColor(tone);
  return (
    <div className="logo-chip-panel" style={{ ['--chip-tone' as string]: color }}>
      <LayerHeader label={title} color={color} />
      <div className="logo-chip-list">
        {nodes.map((node) => (
          <LogoChip key={`${title}-${node.id}`} node={node} tone={color} onNodeClick={onNodeClick} />
        ))}
      </div>
    </div>
  );
}

function LogoChip({ node, tone, onNodeClick }: { node: StoryGraphNode; tone: string; onNodeClick: (node: StoryGraphNode) => void }) {
  const company = findCompanyForNode(node);
  const clickable = Boolean(company);
  const logoText = node.logoText || company?.logoText || initials(node.label);
  const title = node.relation ? `${node.label} / ${jaRelation(node.relation)}` : node.label;

  return (
    <button
      type="button"
      title={title}
      disabled={!clickable}
      onClick={() => onNodeClick(node)}
      className={["logo-chip", clickable ? "is-clickable" : ""].join(" ")}
      style={{ ['--chip-tone' as string]: safeColor(tone) }}
      aria-label={title}
    >
      {node.logo ? <img src={node.logo} alt="" /> : <span>{logoText}</span>}
    </button>
  );
}

function flattenGroups(groups: StoryGraphGroup[]) {
  return mergeStoryNodes([], groups.flatMap((group) => group.nodes));
}

function visibleNodes(nodes: StoryGraphNode[]) {
  return nodes.filter((node) => node.id && !node.hidden);
}

function flattenLayerEdges(groups: StoryGraphGroup[]) {
  return groups.flatMap((group) => group.internalEdges || []);
}

function buildInternalEdgesFromGroups(groups: StoryGraphGroup[]): StoryGraphEdge[] {
  const explicitEdges = flattenLayerEdges(groups);
  if (explicitEdges.length > 0) return explicitEdges;

  const groupNodes = groups.map((group) => firstVisibleNode(group)).filter(Boolean) as StoryGraphNode[];
  return groupNodes.slice(0, -1).map((node, index) => {
    const sourceGroup = groups[index];
    return {
      source: node.id,
      target: groupNodes[index + 1].id,
      type: normalizeRelationType(node.type),
      label: sourceGroup ? connectorLabel(sourceGroup) : node.relation,
    };
  });
}

function orderLayerNodes(nodes: StoryGraphNode[], edges: StoryGraphEdge[] = []) {
  const visible = visibleNodes(nodes);
  if (edges.length === 0) return visible;

  const nodeMap = new Map(visible.map((node) => [node.id, node]));
  const targets = new Set(edges.map((edge) => edge.target));
  const ordered: StoryGraphNode[] = [];
  let current = edges.map((edge) => edge.source).find((source) => nodeMap.has(source) && !targets.has(source));

  while (current && nodeMap.has(current) && !ordered.some((node) => node.id === current)) {
    const node = nodeMap.get(current);
    if (node) ordered.push(node);
    current = edges.find((edge) => edge.source === current && nodeMap.has(edge.target))?.target;
  }

  visible.forEach((node) => {
    if (!ordered.some((item) => item.id === node.id)) ordered.push(node);
  });

  return ordered;
}

function findInternalEdge(edges: StoryGraphEdge[] = [], source: string, target: string) {
  return edges.find((edge) => edge.source === source && edge.target === target && !edge.hidden);
}

function relationColor(type: string | undefined, fallback: string) {
  return safeColor(type ? relationStyle[normalizeRelationType(type)]?.color : fallback);
}

function flowConnectorLabel(current: FlowMapLayer, next: FlowMapLayer) {
  if (current.id === 'outputs') return '展開';
  if (next.id === 'selected-company') return '利用企業へ';
  if (next.id === 'outputs') return '製品化';
  return '供給';
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
          StoryGraphと関係データから表示しています。今後は記事collectionのcompany / topic IDと連携できます。
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
              {article.importance && (
                <span className={`related-badge ${article.importance === '重要' ? 'is-important' : 'is-watch'}`}>
                  {article.importance}
                </span>
              )}
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
function CompanyDetail(_props: {
  company: Company;
  detail: StoryGraph;
  relatedArticles: RelatedArticle[];
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  return null;
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
    compute: '計算資源',
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
      .storygraph-map-shell {
        overflow-x: auto;
        overflow-y: hidden;
        overscroll-behavior-x: contain;
        padding: 8px 2px 18px;
      }
      .storygraph-flow-row {
        position: relative;
        display: flex;
        align-items: center;
        gap: 14px;
        min-width: max-content;
        padding: 10px 4px;
      }
      .storygraph-flow-row::before {
        content: "";
        position: absolute;
        left: 4px;
        right: 4px;
        top: 50%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,.08), transparent);
        pointer-events: none;
      }
      .flow-stage {
        position: relative;
        z-index: 1;
        flex: 0 0 auto;
        width: min(260px, 28vw);
        min-width: 210px;
        align-self: center;
      }
      .flow-stage-single {
        width: 220px;
      }
      .flow-stage-featured {
        width: 250px;
      }
      .layer-frame {
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 16px;
        background: rgba(255,255,255,.035);
        box-shadow: 0 18px 48px rgba(0,0,0,.20);
        backdrop-filter: blur(12px);
      }
      .layer-frame::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 2px;
        background: var(--stage-color);
        opacity: .85;
      }
      .layer-frame-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 10px;
        border-bottom: 1px solid rgba(255,255,255,.08);
        padding: 14px 15px 11px 17px;
      }
      .layer-frame-head h4 {
        color: #f7fbff;
        font-size: 14px;
        font-weight: 900;
        letter-spacing: -.02em;
      }
      .layer-frame-head p {
        margin-top: 3px;
        color: #8492aa;
        font-size: 11px;
        line-height: 1.6;
      }
      .layer-frame-dot {
        margin-top: 4px;
        width: 8px;
        height: 8px;
        flex: 0 0 auto;
        border-radius: 999px;
        background: var(--stage-color);
        box-shadow: 0 0 14px color-mix(in srgb, var(--stage-color) 70%, transparent);
      }
      .layer-frame-body {
        display: grid;
        gap: 8px;
        padding: 13px;
      }
      .selected-flow-card {
        position: relative;
        border: 1px solid color-mix(in srgb, var(--stage-color) 50%, rgba(255,255,255,.12));
        border-radius: 18px;
        background:
          radial-gradient(circle at 50% 0%, color-mix(in srgb, var(--stage-color) 18%, transparent), transparent 12rem),
          rgba(255,255,255,.045);
        box-shadow: 0 0 42px color-mix(in srgb, var(--stage-color) 16%, transparent), 0 18px 54px rgba(0,0,0,.24);
        padding: 14px;
        backdrop-filter: blur(14px);
      }
      .selected-flow-card .node-card {
        border-color: color-mix(in srgb, var(--stage-color) 48%, rgba(255,255,255,.12));
        background: rgba(0,0,0,.18);
      }
      .layer-box {
        width: 100%;
      }
      .node-card {
        max-width: 180px;
        justify-self: center;
      }
      .flow-stage .node-card,
      .layer-frame .node-card {
        max-width: none;
        justify-self: stretch;
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
      .internal-flow {
        position: relative;
        display: grid;
        place-items: center;
        min-height: 30px;
        color: var(--internal-color);
      }
      .internal-line {
        width: 1px;
        height: 28px;
        background: linear-gradient(180deg, transparent, var(--internal-color), transparent);
        opacity: .72;
      }
      .internal-particle {
        position: absolute;
        top: 2px;
        width: 4px;
        height: 4px;
        border-radius: 999px;
        background: var(--internal-color);
        box-shadow: 0 0 10px var(--internal-color);
        animation: ecosystemFlowY 2.1s linear infinite;
      }
      .internal-label {
        position: absolute;
        left: calc(50% + 10px);
        top: 50%;
        transform: translateY(-50%);
        max-width: 135px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 999px;
        background: rgba(7,9,13,.72);
        padding: 2px 6px;
        color: #aebbd0;
        font-size: 9px;
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
        min-width: 0;
        margin-top: 16px;
        border: 1px solid rgba(255,255,255,.09);
        border-radius: 16px;
        background: rgba(255,255,255,.035);
        padding: 14px;
      }
      .storygraph-logo-panels {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
      }
      .logo-chip-panel {
        min-width: 0;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 13px;
        background: rgba(0,0,0,.18);
        padding: 12px;
      }
      .logo-chip-list {
        display: flex;
        gap: 8px;
        overflow-x: auto;
        overscroll-behavior-x: contain;
        padding: 2px 2px 8px;
        scrollbar-width: thin;
      }
      .logo-chip {
        display: grid;
        place-items: center;
        width: 42px;
        height: 42px;
        flex: 0 0 auto;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 12px;
        background: rgba(255,255,255,.045);
        color: #f8fbff;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 10px;
        font-weight: 900;
        transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease;
      }
      .logo-chip img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        padding: 7px;
      }
      .logo-chip.is-clickable:hover {
        transform: translateY(-2px);
        border-color: var(--chip-tone);
        background: color-mix(in srgb, var(--chip-tone) 10%, rgba(255,255,255,.045));
        box-shadow: 0 0 22px color-mix(in srgb, var(--chip-tone) 18%, transparent);
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
        z-index: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 58px;
        color: var(--flow-color);
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 9px;
        font-weight: 800;
        letter-spacing: .04em;
      }
      .flow-connector-y { min-height: 34px; flex-direction: column; }
      .flow-connector-x {
        width: 58px;
        min-height: 46px;
      }
      .flow-line {
        display: block;
        background: linear-gradient(90deg, transparent, var(--flow-color), transparent);
        opacity: .66;
        box-shadow: 0 0 10px color-mix(in srgb, var(--flow-color) 45%, transparent);
      }
      .flow-connector-x .flow-line { width: 100%; height: 1px; }
      .flow-connector-y .flow-line {
        width: 1px;
        height: 28px;
        background: linear-gradient(180deg, transparent, var(--flow-color), transparent);
      }
      .flow-particle {
        position: absolute;
        width: 4px;
        height: 4px;
        border-radius: 999px;
        background: var(--flow-color);
        box-shadow: 0 0 10px var(--flow-color);
      }
      .flow-connector-x .flow-particle { animation: ecosystemFlowX 2s linear infinite; }
      .flow-connector-y .flow-particle { animation: ecosystemFlowY 2s linear infinite; }
      .flow-label {
        position: absolute;
        left: 50%;
        top: calc(50% + 10px);
        transform: translateX(-50%);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 999px;
        background: rgba(7,9,13,.78);
        padding: 2px 6px;
        color: #9aa8bd;
        white-space: nowrap;
      }
      .flow-connector-y .flow-label {
        top: 50%;
        left: calc(50% + 12px);
        transform: translateY(-50%);
      }
      @keyframes ecosystemFlowX {
        0% { left: 4px; opacity: 0; }
        18% { opacity: 1; }
        100% { left: calc(100% - 8px); opacity: 0; }
      }
      @keyframes ecosystemFlowY {
        0% { top: 2px; opacity: 0; }
        18% { opacity: 1; }
        100% { top: calc(100% - 7px); opacity: 0; }
      }
      @media (max-width: 1024px) {
        .storygraph-map-shell {
          margin-inline: -16px;
          padding-inline: 16px;
        }
        .storygraph-flow-row {
          min-width: 980px;
        }
        .flow-stage {
          width: 230px;
        }
        .storygraph-logo-panels {
          grid-template-columns: 1fr;
        }
        .related-article-grid { grid-template-columns: 1fr; }
      }
    `}</style>
  );
}