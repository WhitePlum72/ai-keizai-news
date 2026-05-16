import React, { useEffect, useMemo, useRef, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

import sectorsData from '../data/ecosystem/sectors.json';
import companiesData from '../data/ecosystem/companies.json';
import modelsData from '../data/ecosystem/models.json';
import productsData from '../data/ecosystem/products.json';
import relationsData from '../data/ecosystem/relations.json';
import storygraphsData from '../data/ecosystem/storygraphs.json';

type SectorId = 'all' | string;

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
  | 'research'
  | 'customer'
  | 'supplier'
  | 'ecosystem'
  | 'ownership';

type ModelType = 'model' | 'product' | 'agent';

type Sector = {
  id: Exclude<SectorId, 'all'>;
  name: string;
  short: string;
  color: string;
  description: string;
  hidden?: boolean;
};

type Company = {
  id: string;
  name: string;
  sector: Exclude<SectorId, 'all'>;
  domain?: string;
  logo?: string;
  logoText: string;
  brandColor?: string;
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
  sector: string;
  type: ModelType;
  color?: string;
  description: string;
};

type EcosystemProduct = {
  id: string;
  name: string;
  company?: string;
  sector?: string;
  type?: string;
  description?: string;
  logoText?: string;
  color?: string;
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
  id?: string;
  group: string;
  label?: string;
  nodes?: StoryGraphNode[];
  subgroups?: StoryGraphGroup[];
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
  flow?: StoryGraphGroup[];
  investors?: StoryGraphNode[];
  investments?: StoryGraphNode[];
  partnerships?: StoryGraphGroup[];
  distribution?: StoryGraphGroup[];
  customers?: StoryGraphGroup[];
  suppliers?: StoryGraphGroup[];
  ecosystem?: StoryGraphGroup[];
  ownership?: StoryGraphGroup[];
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

const SECTORS = (sectorsData as Sector[]).filter((sector) => !sector.hidden);
const COMPANIES = companiesData as Company[];
const MODELS = modelsData as EcosystemModel[];
const PRODUCTS = productsData as EcosystemProduct[];
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
  customer: { label: '顧客', color: '#EAB308', verb: '顧客・供給先' },
  supplier: { label: '供給元', color: '#F97316', verb: '供給元' },
  ecosystem: { label: 'エコシステム', color: '#8B5CF6', verb: 'エコシステム連携' },
  ownership: { label: '所有・親会社', color: '#22C55E', verb: '所有・親会社' },
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
    if (company.sector === 'generative-ai') {
      setSelectedCompany(null);
      setActiveSector('generative-ai');
      return;
    }

    setSelectedCompany(company);
    setActiveSector(company.sector);
  };

  const handleBackToAll = () => {
    setSelectedCompany(null);
    setActiveSector('all');
    setHoveredNodeId(null);
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

      <div className="ecosystem-container">
        <div className="ecosystem-section-head">
          <div className="ecosystem-title-block">
            <p className="font-mono text-[11px] font-semibold uppercase tracking-[.14em] text-[#5a9eff]">
              AI Ecosystem Map
            </p>
            <h2 className="mt-1 text-2xl font-black tracking-[-.03em] md:text-3xl">
              AI企業勢力図
            </h2>
            <p className="ecosystem-subcopy">
              半導体、GPU、クラウド、モデル、サービスまで。AI産業のつながりを構造で読む。
            </p>
          </div>
        </div>

        <div className="grid gap-4">
          <main className="relative min-h-[760px] overflow-hidden rounded-lg border border-white/10 bg-[#080d14]/80 p-4 shadow-2xl shadow-black/30 backdrop-blur md:p-6">
            <AnimatePresence mode="wait">
              {activeSector === 'generative-ai' ? (
                <motion.div
                  key="generative-ai-directory"
                  initial={{ opacity: 0, scale: 0.985 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.985 }}
                  transition={{ duration: 0.32, ease: [0.22, 1, 0.36, 1] }}
                >
                  <GenerativeAIServiceDirectory onBack={handleBackToAll} />
                </motion.div>
              ) : selectedCompany && detail && layers ? (
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
                    onBack={handleBackToAll}
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
    <div className="sector-overview-grid">
      {SECTORS.filter((sector) => COMPANIES.some((company) => company.sector === sector.id)).map((sector) => {
        const sectorCompanies = COMPANIES.filter((company) => company.sector === sector.id);
        const isActive = activeSector === sector.id;
        const isDimmed = activeSector !== 'all' && !isActive;
        const color = safeColor(sector.color);

        return (
          <motion.section
            key={sector.id}
            layout
            animate={{ opacity: isDimmed ? 0.34 : 1, scale: isActive ? 1.025 : 1 }}
            transition={{ duration: 0.25 }}
            className={['sector-card', isActive ? 'is-active' : '', isDimmed ? 'is-dimmed' : ''].join(' ')}
            style={{ ['--sector-color' as string]: color }}
          >
            <button type="button" onClick={() => onSectorClick(sector.id)} className="absolute inset-0 z-0" aria-label={`${sector.name}を強調`} />
            <div className="relative z-10">
              <div className="sector-card-head">
                <div>
                  <p className="sector-kicker">
                    {sector.short}
                  </p>
                  <h3>{sector.name}</h3>
                </div>
                <span className="sector-count">
                  {sectorCompanies.length}社
                </span>
              </div>

              <p className="sector-description">{sector.description}</p>

              <div className="sector-company-list">
                {sectorCompanies.slice(0, isActive ? 12 : 8).map((company) => (
                  <button
                    key={company.id}
                    type="button"
                    onClick={(event) => {
                      event.stopPropagation();
                      onCompanyClick(company);
                    }}
                    className="sector-company-chip"
                  >
                    <EntityLogo
                      logo={company.logo}
                      logoText={company.logoText}
                      alt={company.name}
                      className="sector-company-logo"
                    />
                    <span className="sector-company-name">{company.name}</span>
                  </button>
                ))}
                {sectorCompanies.length > (isActive ? 12 : 8) && (
                  <span className="sector-company-more">
                    +{sectorCompanies.length - (isActive ? 12 : 8)}
                  </span>
                )}
              </div>
            </div>
            <div className="sector-glow" />
            <div className="sector-topline" />
          </motion.section>
        );
      })}
    </div>
  );
}

const GENERATIVE_AI_DIRECTORY = [
  {
    label: '画像生成',
    ids: ['midjourney', 'stability-ai', 'adobe', 'firefly', 'dall-e', 'ideogram', 'leonardo-ai'],
  },
  {
    label: '動画生成',
    ids: ['sora', 'runway', 'pika', 'luma', 'kling', 'veo', 'heygen'],
  },
  {
    label: '音声・音楽生成',
    ids: ['elevenlabs', 'suno', 'udio', 'voice-engine', 'fish-audio'],
  },
  {
    label: '3D / Avatar',
    ids: ['meshy', 'tripo', 'inworld', 'character-ai'],
  },
  {
    label: 'Creative Tools',
    ids: ['adobe', 'canva', 'capcut', 'figma'],
  },
];

function GenerativeAIServiceDirectory({
  onBack,
}: {
  onBack: () => void;
}) {
  const sector = getSector('generative-ai');
  const color = safeColor(sector.color);

  return (
    <div className="generative-directory" style={{ ['--directory-color' as string]: color }}>
      <div className="directory-head">
        <button type="button" className="storygraph-back" onClick={onBack}>
          ← 全体に戻る
        </button>
        <div>
          <p className="directory-kicker">サービス一覧</p>
          <h3>生成AI</h3>
          <p>画像、動画、音声、3D、クリエイティブ制作の主要AIサービスをカテゴリ別に整理。</p>
        </div>
      </div>

      <div className="directory-grid">
        {GENERATIVE_AI_DIRECTORY.map((category) => (
          <section key={category.label} className="directory-card">
            <div className="directory-card-title">
              <span />
              <h4>{category.label}</h4>
            </div>
            <div className="directory-chip-list">
              {category.ids
                .map(resolveDirectoryEntity)
                .filter(Boolean)
                .map((entity) => {
                  return (
                    <div
                      key={`${category.label}-${entity.id}`}
                      className="directory-chip"
                      title={entity.name}
                    >
                      {entity.kind === 'company' ? (
                        <EntityLogo
                          logo={entity.logo}
                          logoText={entity.logoText}
                          alt={entity.name}
                          className="directory-logo"
                        />
                      ) : (
                        <span className="directory-badge" style={{ ['--badge-color' as string]: entity.color }}>
                          {entity.logoText}
                        </span>
                      )}
                      <span>{entity.name}</span>
                    </div>
                  );
                })}
            </div>
          </section>
        ))}
      </div>
    </div>
  );
}

function resolveDirectoryEntity(id: string) {
  const company = COMPANIES.find((item) => item.id === id);
  if (company) {
    return {
      kind: 'company' as const,
      id: company.id,
      name: company.name,
      logo: company.logo,
      logoText: company.logoText,
      color: safeColor(company.brandColor || getSector(company.sector).color),
      company,
    };
  }

  const model = MODELS.find((item) => item.id === id);
  if (model) {
    return {
      kind: 'model' as const,
      id: model.id,
      name: model.name,
      logoText: initials(model.name),
      color: safeColor(model.color || getEntityBrandColor(model.company)),
    };
  }

  const product = PRODUCTS.find((item) => item.id === id);
  if (product) {
    return {
      kind: 'product' as const,
      id: product.id,
      name: product.name,
      logoText: product.logoText || initials(product.name),
      color: safeColor(product.color || getEntityBrandColor(product.company || '')),
    };
  }

  return null;
}

function EntityLogo({
  logo,
  logoText,
  alt,
  className,
}: {
  logo?: string;
  logoText: string;
  alt: string;
  className?: string;
}) {
  const [failed, setFailed] = useState(false);

  return (
    <span className={className}>
      {logo && !failed ? (
        <img src={logo} alt={alt} loading="lazy" decoding="async" onError={() => setFailed(true)} />
      ) : (
        <span>{logoText}</span>
      )}
    </span>
  );
}

type FlowMapLayer = {
  id: string;
  title: string;
  subtitle?: string;
  color: string;
  nodes: StoryGraphNode[];
  subgroups?: StoryGraphGroup[];
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
  onBack,
}: {
  company: Company;
  detail: StoryGraph;
  layers: StoryGraphLayers;
  relatedArticles: RelatedArticle[];
  hoveredNodeId: string | null;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
  onBack: () => void;
}) {
  const sector = getSector(company.sector);
  const sectorColor = safeColor(sector.color);
  const investorNodes = mergeStoryNodes([], layers.investors || []);
  const investmentNodes = mergeStoryNodes([], layers.investments || []);
  const partnershipNodes = mergeStoryNodes([], flattenGroups(layers.partnerships || []));
  const distributionNodes = mergeStoryNodes([], flattenGroups(layers.distribution || []));
  const ecosystemNodes = mergeStoryNodes([], flattenGroups(layers.ecosystem || []));
  const ownershipNodes = mergeStoryNodes([], flattenGroups(layers.ownership || []));
  const hasBottomRelations =
    investorNodes.length > 0 ||
    investmentNodes.length > 0 ||
    partnershipNodes.length > 0 ||
    distributionNodes.length > 0 ||
    ecosystemNodes.length > 0 ||
    ownershipNodes.length > 0 ||
    layers.competitors.length > 0;

  const flowLayers: FlowMapLayer[] = [
    ...buildFlowColumns(layers),
    {
      id: 'selected-company',
      title: company.name,
      subtitle: '選択企業',
      color: sectorColor,
      nodes: [layers.center],
      featured: true,
    },
    ...buildOutputColumns(layers),
  ].filter(Boolean) as FlowMapLayer[];
  const flowNodeCount = flowLayers.reduce((total, layer) => {
    return total + visibleNodes(layer.nodes || []).length + (layer.subgroups || []).reduce((sum, group) => sum + countGroupNodes(group), 0);
  }, 0);
  const denseGraph = flowNodeCount >= 18;

  return (
    <div className="min-h-[620px]">
      <div className="storygraph-head">
        <button type="button" className="storygraph-back" onClick={onBack}>
          ← 全体に戻る
        </button>
        <div className="storygraph-title-row">
          <div className="max-w-4xl">
            <h3>{company.name}</h3>
            <p>{company.description || detail.summary}</p>
          </div>
          <a href={`/company/${company.id}/`} className="storygraph-detail-cta">
            詳細を見る →
          </a>
        </div>
      </div>

      <div className="storygraph-map-shell">
        <div className={['storygraph-flow-row', denseGraph ? 'is-dense' : ''].join(' ')}>
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
            {investorNodes.length > 0 && (
              <LogoChipPanel
                title="出資者"
                nodes={investorNodes}
                tone={relationStyle.investment.color}
                onNodeClick={onNodeClick}
              />
            )}
            {investmentNodes.length > 0 && (
              <LogoChipPanel
                title="投資先"
                nodes={investmentNodes}
                tone={relationStyle.investment.color}
                onNodeClick={onNodeClick}
              />
            )}
            {partnershipNodes.length > 0 && (
              <LogoChipPanel
                title="提携"
                nodes={partnershipNodes}
                tone={relationStyle.partnership.color}
                onNodeClick={onNodeClick}
              />
            )}
            {distributionNodes.length > 0 && (
              <LogoChipPanel
                title="提供チャネル"
                nodes={distributionNodes}
                tone={relationStyle.distribution.color}
                onNodeClick={onNodeClick}
              />
            )}
            {ecosystemNodes.length > 0 && (
              <LogoChipPanel
                title="エコシステム"
                nodes={ecosystemNodes}
                tone={relationStyle.partnership.color}
                onNodeClick={onNodeClick}
              />
            )}
            {ownershipNodes.length > 0 && (
              <LogoChipPanel
                title="親会社・所有"
                nodes={ownershipNodes}
                tone={relationStyle.investment.color}
                onNodeClick={onNodeClick}
              />
            )}
            {layers.competitors.length > 0 && (
              <LogoChipPanel
                title="競合企業"
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
  const orderedNodes = orderLayerNodes(layer.nodes || [], layer.internalEdges);
  const subgroups = (layer.subgroups || []).filter((group) => countGroupNodes(group) > 0);
  const shouldFrame = !layer.featured && orderedNodes.length > 1;
  const hasSubgroups = !layer.featured && subgroups.length > 0;
  const layerNodeCount = orderedNodes.length + subgroups.reduce((total, group) => total + countGroupNodes(group), 0);
  const denseLayer = layerNodeCount >= 6;

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

  if (hasSubgroups) {
    return (
      <section className={['flow-stage layer-frame layer-frame-subgroups', denseLayer ? 'is-dense-layer' : ''].join(' ')} style={{ ['--stage-color' as string]: color }}>
        <div className="layer-frame-head">
          <div>
            <h4>{layer.title}</h4>
            {layer.subtitle && <p>{layer.subtitle}</p>}
          </div>
          <span className="layer-frame-dot" />
        </div>
        <div className="layer-subgroup-grid">
          {subgroups.map((group) => (
            <div className="subgroup-card" key={group.id || group.label || group.group} style={{ ['--subgroup-color' as string]: groupColor(group) }}>
              <p className="subgroup-title">{group.label || jaGroup(group.group)}</p>
              <div className="subgroup-node-list">
                {visibleNodes(group.nodes || []).map((node) => (
                  <StoryNodeCard
                    key={node.id}
                    node={node}
                    tone={groupColor(group)}
                    compact
                    small
                    highlighted={hoveredNodeId === node.id}
                    onHoverNode={onHoverNode}
                    onNodeClick={onNodeClick}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      </section>
    );
  }

  if (!shouldFrame) {
    const node = orderedNodes[0];
    if (!node) return null;
    return (
      <section className={['flow-stage flow-stage-single', denseLayer ? 'is-dense-layer' : ''].join(' ')} style={{ ['--stage-color' as string]: color }}>
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
    <section className={['flow-stage layer-frame', denseLayer ? 'is-dense-layer' : ''].join(' ')} style={{ ['--stage-color' as string]: color }}>
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
  const company = findCompanyForNode(node);
  const clickable = Boolean(company);
  const logoText = node.logoText || company?.logoText || initials(node.label);
  const logo = node.logo || company?.logo;

  return (
    <button
      type="button"
      disabled={!clickable}
      onMouseEnter={() => onHoverNode(node.id)}
      onMouseLeave={() => onHoverNode(null)}
      onClick={() => onNodeClick(node)}
      className={['selected-flow-card', clickable ? 'is-clickable' : '', hoveredNodeId === node.id ? 'is-highlighted' : ''].join(' ')}
      style={{ ['--stage-color' as string]: safeColor(color) }}
    >
      <EntityLogo logo={logo} logoText={logoText} alt={node.label} className="selected-logo" />
      <span className="selected-name">{node.label}</span>
    </button>
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
  const logo = node.logo || company?.logo;
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
      <EntityLogo logo={logo} logoText={logoText} alt={node.label} />
    </button>
  );
}

function flattenGroups(groups: StoryGraphGroup[]) {
  return mergeStoryNodes([], groups.flatMap((group) => [
    ...visibleNodes(group.nodes || []),
    ...flattenGroups(group.subgroups || []),
  ]));
}

function visibleNodes(nodes: StoryGraphNode[] = []) {
  return nodes.filter((node) => node.id && !node.hidden);
}

function flattenLayerEdges(groups: StoryGraphGroup[]) {
  return groups.flatMap((group) => group.internalEdges || []);
}

function buildInternalEdgesFromGroups(groups: StoryGraphGroup[]): StoryGraphEdge[] {
  return flattenLayerEdges(groups);
}

function buildFlowColumns(layers: StoryGraphLayers): FlowMapLayer[] {
  if (layers.flow?.length) {
    return layers.flow.map(groupToFlowLayer).filter(Boolean) as FlowMapLayer[];
  }

  return layers.supply.map(groupToFlowLayer).filter(Boolean) as FlowMapLayer[];
}

function buildOutputColumns(layers: StoryGraphLayers): FlowMapLayer[] {
  if (layers.flow?.length) return [];
  return layers.outputs.map(groupToFlowLayer).filter(Boolean) as FlowMapLayer[];
}

function groupToFlowLayer(group: StoryGraphGroup, index: number): FlowMapLayer | null {
  if (!group || group.hidden || countGroupNodes(group) === 0) return null;

  return {
    id: group.id || slugify(group.label || group.group || `layer-${index}`),
    title: group.label || jaGroup(group.group),
    color: groupColor(group),
    nodes: visibleNodes(group.nodes || []),
    subgroups: (group.subgroups || []).filter((subgroup) => countGroupNodes(subgroup) > 0),
    internalEdges: group.internalEdges || [],
  };
}

function countGroupNodes(group: StoryGraphGroup) {
  return visibleNodes(group.nodes || []).length +
    (group.subgroups || []).reduce((total, subgroup) => total + countGroupNodes(subgroup), 0);
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
  if (current.id.includes('outputs') || current.id.includes('products')) return '展開';
  if (next.id === 'selected-company') return '利用企業へ';
  if (next.id.includes('outputs') || next.id.includes('products')) return '製品化';
  return '接続';
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
      <p className="mb-3 pl-1 font-mono text-[10px] font-bold uppercase tracking-[.12em] text-slate-500">{group.label || jaGroup(group.group)}</p>
      <div className="grid gap-2">
        {visibleNodes(group.nodes || []).map((node) => (
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
  small = false,
  highlighted,
  onHoverNode,
  onNodeClick,
}: {
  node: StoryGraphNode;
  tone: string;
  compact?: boolean;
  small?: boolean;
  highlighted: boolean;
  onHoverNode: (id: string | null) => void;
  onNodeClick: (node: StoryGraphNode) => void;
}) {
  const company = findCompanyForNode(node);
  const clickable = Boolean(company);
  const logoText = node.logoText || company?.logoText || initials(node.label);
  const logo = node.logo || company?.logo;
  const relationType = normalizeRelationType(node.type);
  const typeStyle = relationStyle[relationType] || { label: jaRelation(node.type || ''), color: safeColor(tone), verb: '' };
  const typeColor = safeColor(typeStyle.color);

  return (
    <button
      type="button"
      disabled={!clickable}
      onMouseEnter={() => onHoverNode(node.id)}
      onMouseLeave={() => onHoverNode(null)}
      onClick={() => onNodeClick(node)}
      className={[
        'node-card group relative w-full rounded-md border bg-black/20 text-center transition',
        compact ? 'px-3 py-2' : 'px-3 py-3',
        small ? 'is-small' : '',
        clickable ? 'cursor-pointer hover:-translate-y-0.5 hover:bg-white/[.07]' : 'cursor-default',
        highlighted ? 'border-white/30 shadow-[0_0_24px_rgba(92,216,206,.16)]' : 'border-white/10',
      ].join(' ')}
      style={{ ['--node-tone' as string]: safeColor(tone) }}
    >
      <div className="node-card-inner">
        <EntityLogo logo={logo} logoText={logoText} alt={node.label} className="node-logo" />
        <div className="node-copy">
          <p className="node-title">{node.label}</p>
          <div className="node-meta">
            {node.relation && <p className="node-relation">{jaRelation(node.relation)}</p>}
            <span className="node-type-pill" style={{ color: typeColor, background: `${typeColor}18` }}>
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
  const logo = center.logo || company.logo;
  const logoText = center.logoText || company.logoText;

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
        <EntityLogo logo={logo} logoText={logoText} alt={center.label || company.name} className="selected-company-logo" />
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
    investors: buildInvestorNodes(company),
    investments: buildInvesteeNodes(company),
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
    flow: sanitizeGroups(layers.flow || []),
    competitors: sanitizeNodes(layers.competitors || []),
    investors: sanitizeNodes(layers.investors || []),
    investments: sanitizeNodes(layers.investments || []),
    partnerships: sanitizeGroups(layers.partnerships || []),
    distribution: sanitizeGroups(layers.distribution || []),
    customers: sanitizeGroups(layers.customers || []),
    suppliers: sanitizeGroups(layers.suppliers || []),
    ecosystem: sanitizeGroups(layers.ecosystem || []),
    ownership: sanitizeGroups(layers.ownership || []),
    edges: layers.edges || [],
  };
}

function mergeRelationComplements(layers: StoryGraphLayers, company: Company): StoryGraphLayers {
  return {
    ...layers,
    investors: mergeStoryNodes(layers.investors || [], buildInvestorNodes(company)),
    investments: mergeStoryNodes(layers.investments || [], buildInvesteeNodes(company)),
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
    investors: sanitizeNodes(layers.investors || []).map((node) => ({ ...node, type: 'investment' })),
    investments: sanitizeNodes(layers.investments || []).map((node) => ({ ...node, type: 'investment' })),
    partnerships: sanitizeGroups(layers.partnerships || []),
    distribution: sanitizeGroups(layers.distribution || []),
    customers: sanitizeGroups(layers.customers || []),
    suppliers: sanitizeGroups(layers.suppliers || []),
    ecosystem: sanitizeGroups(layers.ecosystem || []),
    ownership: sanitizeGroups(layers.ownership || []),
    competitors: sanitizeNodes(layers.competitors || []).map((node) => ({ ...node, type: 'competitor' })),
  };
}

function stripBottomRelations(groups: StoryGraphGroup[]) {
  return groups
    .map((group) => ({
      ...group,
      nodes: visibleNodes(group.nodes || []).filter((node) => !isBottomRelationType(node.type)),
      subgroups: (group.subgroups || []).map((subgroup) => ({
        ...subgroup,
        nodes: visibleNodes(subgroup.nodes || []).filter((node) => !isBottomRelationType(node.type)),
      })).filter((subgroup) => countGroupNodes(subgroup) > 0),
    }))
    .filter((group) => countGroupNodes(group) > 0);
}

function isBottomRelationType(type: string | undefined) {
  const normalized = normalizeRelationType(type);
  return ['investment', 'competitor', 'ownership', 'research'].includes(normalized);
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
  const groups = new Map<string, StoryGraphGroup>();

  [...primary, ...supplemental].forEach((group) => {
    const key = group.id || group.label || group.group;
    const existing = groups.get(key);
    if (!existing) {
      groups.set(key, { ...group, nodes: visibleNodes(group.nodes || []) });
      return;
    }
    groups.set(key, {
      ...existing,
      nodes: mergeStoryNodes(visibleNodes(existing.nodes || []), visibleNodes(group.nodes || [])),
      subgroups: [...(existing.subgroups || []), ...(group.subgroups || [])],
    });
  });

  return Array.from(groups.values()).filter((group) => countGroupNodes(group) > 0);
}

function sanitizeGroups(groups: StoryGraphGroup[]) {
  return groups
    .map((group) => ({
      ...group,
      group: group.group || group.label || group.id || 'Layer',
      nodes: sanitizeNodes(group.nodes || []),
      subgroups: sanitizeGroups(group.subgroups || []),
      internalEdges: group.internalEdges || [],
    }))
    .filter((group) => countGroupNodes(group) > 0);
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
    ...flattenGroups(layers.flow || []),
    ...layers.supply.flatMap((group) => flattenGroups([group])),
    layers.center,
    ...layers.outputs.flatMap((group) => flattenGroups([group])),
    ...(layers.investors || []),
    ...(layers.investments || []),
    ...(layers.partnerships || []).flatMap((group) => flattenGroups([group])),
    ...(layers.distribution || []).flatMap((group) => flattenGroups([group])),
    ...(layers.customers || []).flatMap((group) => flattenGroups([group])),
    ...(layers.suppliers || []).flatMap((group) => flattenGroups([group])),
    ...(layers.ecosystem || []).flatMap((group) => flattenGroups([group])),
    ...(layers.ownership || []).flatMap((group) => flattenGroups([group])),
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

function buildInvestorNodes(company: Company): StoryGraphNode[] {
  return RELATIONS
    .filter((relation) => relation.type === 'investment' && relation.target === company.id)
    .map((relation) => relationToInvestmentNode(relation.source, relation, '出資者'))
    .filter((node, index, nodes) => nodes.findIndex((item) => item.id === node.id) === index)
    .slice(0, 6);
}

function buildInvesteeNodes(company: Company): StoryGraphNode[] {
  return RELATIONS
    .filter((relation) => relation.type === 'investment' && relation.source === company.id)
    .map((relation) => relationToInvestmentNode(relation.target, relation, '投資先'))
    .filter((node, index, nodes) => nodes.findIndex((item) => item.id === node.id) === index)
    .slice(0, 6);
}

function relationToInvestmentNode(id: string, relation: Relation, label: '出資者' | '投資先'): StoryGraphNode {
  const relatedCompany = COMPANIES.find((item) => item.id === id);

  return {
    id,
    label: relatedCompany?.name || id,
    relation: label,
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
  const node = firstVisibleNode(group);
  return jaRelation(node?.relation || '次へつながる');
}

function firstVisibleNode(group: StoryGraphGroup | undefined) {
  return visibleNodes(group?.nodes || [])[0] || flattenGroups(group?.subgroups || [])[0];
}

function groupColor(group: StoryGraphGroup) {
  const firstNode = firstVisibleNode(group);
  const firstType = normalizeRelationType(firstNode?.type);
  if (firstType) return safeColor(relationStyle[firstType]?.color);
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
  return getEntityName(id);
}

function getEntityName(id: string) {
  return (
    COMPANIES.find((company) => company.id === id)?.name ||
    MODELS.find((model) => model.id === id)?.name ||
    PRODUCTS.find((product) => product.id === id)?.name ||
    id
  );
}

function getEntityLogoText(id: string) {
  const company = COMPANIES.find((item) => item.id === id);
  if (company?.logoText) return company.logoText;
  const model = MODELS.find((item) => item.id === id);
  if (model?.name) return initials(model.name);
  const product = PRODUCTS.find((item) => item.id === id);
  return product?.logoText || initials(product?.name || id);
}

function getEntityBrandColor(id: string) {
  const company = COMPANIES.find((item) => item.id === id);
  if (company) return safeColor(company.brandColor || getSector(company.sector).color);

  const model = MODELS.find((item) => item.id === id);
  if (model) return safeColor(model.color || getEntityBrandColor(model.company));

  const product = PRODUCTS.find((item) => item.id === id);
  if (product) return safeColor(product.color || getEntityBrandColor(product.company || ''));

  return FALLBACK_COLOR;
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
      .ecosystem-shell {
        width: 100%;
      }

      .ecosystem-container {
        width: min(100% - 32px, 1440px);
        max-width: 1440px;
        margin-inline: auto;
      }

      .ecosystem-section-head {
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        gap: 18px;
        align-items: end;
        margin-bottom: 22px;
      }

      .ecosystem-title-block {
        min-width: 0;
      }

      .ecosystem-subcopy {
        margin-top: 8px;
        max-width: 720px;
        color: #93a3b8;
        font-size: 13px;
        line-height: 1.8;
      }

      .ecosystem-stats {
        display: flex;
        flex-wrap: wrap;
        justify-content: flex-end;
        gap: 8px;
      }

      .ecosystem-stat-chip {
        display: grid;
        gap: 2px;
        min-width: 104px;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 14px;
        background: rgba(255,255,255,.035);
        padding: 10px 12px;
        backdrop-filter: blur(12px);
      }

      .ecosystem-stat-chip span {
        color: #7f8da3;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 9px;
        font-weight: 800;
        letter-spacing: .12em;
        text-transform: uppercase;
      }

      .ecosystem-stat-chip strong {
        color: #f8fbff;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 15px;
        font-weight: 950;
      }

      .map-toolbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 12px;
        margin-bottom: 18px;
      }

      .map-status-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        width: fit-content;
        max-width: 100%;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 999px;
        background: rgba(0,0,0,.35);
        padding: 8px 12px;
        color: #cbd5e1;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 11px;
        backdrop-filter: blur(14px);
      }

      .sector-overview-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(280px, 1fr));
        gap: 18px;
        align-items: stretch;
        max-width: 1180px;
        margin: 0 auto;
      }

      .sector-card {
        position: relative;
        min-height: 252px;
        overflow: hidden;
        border: 1px solid color-mix(in srgb, var(--sector-color, #5CD8CE) 28%, rgba(255,255,255,.10));
        border-radius: 18px;
        background:
          linear-gradient(180deg, color-mix(in srgb, var(--sector-color, #5CD8CE) 8%, transparent), transparent 58%),
          rgba(255,255,255,.035);
        padding: 18px;
        box-shadow: 0 20px 54px rgba(0,0,0,.20);
        backdrop-filter: blur(14px);
        cursor: pointer;
        transition: transform .22s ease, border-color .22s ease, background .22s ease, box-shadow .22s ease;
      }

      .sector-card:hover,
      .sector-card.is-active {
        transform: translateY(-3px);
        border-color: color-mix(in srgb, var(--sector-color, #5CD8CE) 58%, rgba(255,255,255,.18));
        background:
          linear-gradient(180deg, color-mix(in srgb, var(--sector-color, #5CD8CE) 13%, transparent), transparent 62%),
          rgba(255,255,255,.045);
        box-shadow: 0 0 40px color-mix(in srgb, var(--sector-color, #5CD8CE) 13%, transparent), 0 24px 64px rgba(0,0,0,.26);
      }

      .sector-card.is-dimmed {
        filter: saturate(.65);
      }

      .sector-card-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 14px;
        margin-bottom: 12px;
      }

      .sector-card-head::after {
        content: "見る →";
        position: absolute;
        right: 18px;
        top: 18px;
        opacity: 0;
        transform: translateX(-4px);
        color: color-mix(in srgb, var(--sector-color, #5CD8CE) 72%, white 18%);
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 10px;
        font-weight: 950;
        transition: opacity .18s ease, transform .18s ease;
      }

      .sector-card:hover .sector-card-head::after {
        opacity: 1;
        transform: translateX(0);
      }

      .sector-kicker {
        color: var(--sector-color, #5CD8CE);
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 10px;
        font-weight: 900;
        letter-spacing: .12em;
        text-transform: uppercase;
      }

      .sector-card h3 {
        margin-top: 4px;
        color: #f7fbff;
        font-size: 18px;
        font-weight: 950;
        letter-spacing: -.03em;
      }

      .sector-count {
        flex: 0 0 auto;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 999px;
        background: rgba(0,0,0,.24);
        padding: 5px 9px;
        color: #aebbd0;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 10px;
        font-weight: 800;
      }

      .sector-description {
        min-height: 44px;
        margin-bottom: 15px;
        color: #97a6bb;
        font-size: 12px;
        line-height: 1.8;
      }

      .sector-company-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        align-items: flex-start;
      }

      .sector-company-chip {
        position: relative;
        z-index: 2;
        display: inline-flex;
        align-items: center;
        gap: 8px;
        min-width: 0;
        flex: 1 1 136px;
        max-width: 100%;
        justify-content: flex-start;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 12px;
        background: rgba(0,0,0,.24);
        padding: 8px 10px;
        color: #eef5ff;
        transition: transform .18s ease, border-color .18s ease, background .18s ease, box-shadow .18s ease;
      }

      .sector-company-chip:hover {
        transform: translateY(-2px);
        border-color: color-mix(in srgb, var(--sector-color, #5CD8CE) 55%, rgba(255,255,255,.16));
        background: color-mix(in srgb, var(--sector-color, #5CD8CE) 10%, rgba(0,0,0,.28));
        box-shadow: 0 0 20px color-mix(in srgb, var(--sector-color, #5CD8CE) 13%, transparent);
      }

      .sector-company-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 30px;
        height: 30px;
        flex: 0 0 auto;
        overflow: hidden;
        border: 1px solid color-mix(in srgb, var(--sector-color, #5CD8CE) 35%, rgba(255,255,255,.10));
        border-radius: 9px;
        background: rgba(255,255,255,.045);
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 9px;
        font-weight: 950;
      }

      .sector-company-logo img {
        display: block;
        width: auto;
        height: auto;
        max-width: 72%;
        max-height: 72%;
        object-fit: contain;
      }

      .sector-card:hover .sector-company-chip {
        background: rgba(255,255,255,.055);
      }

      .sector-company-name {
        min-width: 0;
        max-width: none;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 12px;
        font-weight: 850;
      }

      .sector-company-more {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-height: 38px;
        border: 1px dashed color-mix(in srgb, var(--sector-color, #5CD8CE) 42%, rgba(255,255,255,.12));
        border-radius: 12px;
        background: rgba(255,255,255,.026);
        padding: 8px 11px;
        color: color-mix(in srgb, var(--sector-color, #5CD8CE) 72%, white 12%);
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 11px;
        font-weight: 900;
      }

      .sector-glow {
        position: absolute;
        right: -56px;
        top: -56px;
        width: 150px;
        height: 150px;
        border-radius: 999px;
        background: var(--sector-color, #5CD8CE);
        opacity: .16;
        filter: blur(42px);
      }

      .sector-topline {
        position: absolute;
        inset: 0 0 auto;
        height: 2px;
        background: linear-gradient(90deg, transparent, var(--sector-color, #5CD8CE), transparent);
        opacity: .88;
      }

      .storygraph-map-shell {
        width: 100%;
        overflow-x: auto;
        overflow-y: hidden;
        overscroll-behavior-x: contain;
        padding: 12px 0 22px;
      }

      .storygraph-head,
      .directory-head {
        display: grid;
        gap: 14px;
        margin-bottom: 24px;
      }

      .storygraph-back {
        width: fit-content;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 999px;
        background: rgba(255,255,255,.035);
        padding: 8px 12px;
        color: #c7d3e3;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 11px;
        font-weight: 850;
        transition: transform .18s ease, border-color .18s ease, color .18s ease, background .18s ease;
      }

      .storygraph-back:hover {
        transform: translateY(-1px);
        border-color: rgba(92,216,206,.45);
        background: rgba(92,216,206,.08);
        color: #fff;
      }

      .storygraph-title-row {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 18px;
      }

      .storygraph-title-row h3,
      .directory-head h3 {
        color: #f8fbff;
        font-size: clamp(28px, 4vw, 44px);
        font-weight: 950;
        letter-spacing: -.045em;
        line-height: 1.05;
      }

      .storygraph-title-row p,
      .directory-head p {
        margin-top: 10px;
        max-width: 760px;
        color: #97a6bb;
        font-size: 13px;
        line-height: 1.8;
      }

      .storygraph-detail-cta {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 auto;
        border: 1px solid rgba(255,255,255,.16);
        border-radius: 999px;
        background: #5CD8CE;
        padding: 10px 15px;
        color: #07111B;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 11px;
        font-weight: 950;
        box-shadow: 0 18px 42px rgba(92,216,206,.16);
        transition: transform .18s ease, filter .18s ease, box-shadow .18s ease;
      }

      .storygraph-detail-cta:hover {
        transform: translateY(-2px);
        filter: brightness(1.08);
        box-shadow: 0 22px 54px rgba(92,216,206,.22);
      }

      .directory-kicker {
        color: var(--directory-color, #EC4899);
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 11px;
        font-weight: 950;
        letter-spacing: .14em;
        text-transform: uppercase;
      }

      .directory-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 14px;
      }

      .directory-card {
        border: 1px solid color-mix(in srgb, var(--directory-color, #EC4899) 28%, rgba(255,255,255,.10));
        border-radius: 18px;
        background:
          linear-gradient(180deg, color-mix(in srgb, var(--directory-color, #EC4899) 8%, transparent), transparent 64%),
          rgba(255,255,255,.035);
        padding: 16px;
        backdrop-filter: blur(14px);
        box-shadow: 0 20px 54px rgba(0,0,0,.18);
      }

      .directory-card-title {
        display: flex;
        align-items: center;
        gap: 9px;
        margin-bottom: 12px;
      }

      .directory-card-title span {
        width: 8px;
        height: 8px;
        border-radius: 999px;
        background: var(--directory-color, #EC4899);
        box-shadow: 0 0 18px var(--directory-color, #EC4899);
      }

      .directory-card-title h4 {
        color: #f8fbff;
        font-size: 15px;
        font-weight: 950;
      }

      .directory-chip-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .directory-chip {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        max-width: 100%;
        cursor: default;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 999px;
        background: rgba(0,0,0,.24);
        padding: 7px 10px 7px 7px;
        color: #edf4ff;
        font-size: 12px;
        font-weight: 850;
        transition: transform .18s ease, border-color .18s ease, background .18s ease;
      }

      .directory-logo,
      .directory-badge {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 28px;
        height: 28px;
        flex: 0 0 auto;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 999px;
        background: rgba(255,255,255,.055);
        color: #fff;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 9px;
        font-weight: 950;
      }

      .directory-logo img {
        display: block;
        width: auto;
        height: auto;
        max-width: 72%;
        max-height: 72%;
        object-fit: contain;
      }

      .directory-badge {
        border-color: color-mix(in srgb, var(--badge-color, #5CD8CE) 48%, rgba(255,255,255,.14));
        background: color-mix(in srgb, var(--badge-color, #5CD8CE) 16%, rgba(255,255,255,.04));
      }

      .storygraph-flow-row {
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 16px;
        width: max-content;
        min-width: min(100%, 1060px);
        margin: 0 auto;
        padding: 18px 18px;
      }

      .storygraph-flow-row::before {
        content: "";
        position: absolute;
        left: 42px;
        right: 42px;
        top: 50%;
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(255,255,255,.07), transparent);
        pointer-events: none;
      }

      .flow-stage {
        position: relative;
        z-index: 1;
        display: grid;
        place-items: center;
        flex: 0 0 auto;
        width: 236px;
        align-self: center;
      }

      .flow-stage-single { width: 212px; }
      .flow-stage-featured { width: 236px; }

      .layer-frame {
        overflow: hidden;
        border: 1px solid color-mix(in srgb, var(--stage-color, #5CD8CE) 30%, rgba(255,255,255,.10));
        border-radius: 18px;
        background:
          linear-gradient(180deg, color-mix(in srgb, var(--stage-color, #5CD8CE) 8%, transparent), transparent 58%),
          rgba(255,255,255,.035);
        box-shadow: 0 20px 54px rgba(0,0,0,.20);
        backdrop-filter: blur(14px);
      }

      .layer-frame::before {
        content: "";
        position: absolute;
        inset: 0 auto 0 0;
        width: 2px;
        background: linear-gradient(180deg, transparent, var(--stage-color, #5CD8CE), transparent);
        opacity: .86;
      }

      .layer-frame-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 12px;
        border-bottom: 1px solid rgba(255,255,255,.08);
        padding: 15px 16px 12px 18px;
      }

      .layer-frame-head h4 {
        color: #f7fbff;
        font-size: 14px;
        font-weight: 950;
        letter-spacing: -.02em;
      }

      .layer-frame-head p {
        margin-top: 4px;
        color: #8f9db3;
        font-size: 11px;
        line-height: 1.6;
      }

      .layer-frame-dot {
        margin-top: 5px;
        width: 8px;
        height: 8px;
        flex: 0 0 auto;
        border-radius: 999px;
        background: var(--stage-color, #5CD8CE);
        box-shadow: 0 0 14px color-mix(in srgb, var(--stage-color, #5CD8CE) 70%, transparent);
      }

      .layer-frame-body {
        display: grid;
        gap: 10px;
        padding: 14px;
      }

      .layer-subgroup-grid {
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        padding: 14px;
      }

      .subgroup-card {
        min-width: 0;
        border: 1px solid color-mix(in srgb, var(--subgroup-color, #5CD8CE) 30%, rgba(255,255,255,.08));
        border-radius: 14px;
        background: rgba(0,0,0,.18);
        padding: 10px;
      }

      .subgroup-title {
        margin-bottom: 8px;
        color: color-mix(in srgb, var(--subgroup-color, #5CD8CE) 76%, white 10%);
        font-size: 10px;
        font-weight: 900;
        line-height: 1.5;
      }

      .subgroup-node-list {
        display: grid;
        gap: 7px;
      }

      .selected-flow-card {
        display: grid;
        place-items: center;
        gap: 11px;
        width: 206px;
        min-height: 168px;
        border: 1px solid color-mix(in srgb, var(--stage-color, #5CD8CE) 58%, rgba(255,255,255,.14));
        border-radius: 22px;
        background:
          radial-gradient(circle at 50% 0%, color-mix(in srgb, var(--stage-color, #5CD8CE) 22%, transparent), transparent 11rem),
          linear-gradient(180deg, rgba(255,255,255,.065), rgba(255,255,255,.032));
        color: #fff;
        text-align: center;
        box-shadow: 0 0 42px color-mix(in srgb, var(--stage-color, #5CD8CE) 18%, transparent), 0 22px 62px rgba(0,0,0,.30);
        backdrop-filter: blur(16px);
        transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease;
      }

      .selected-flow-card.is-clickable:hover,
      .selected-flow-card.is-highlighted {
        transform: translateY(-3px) scale(1.015);
        border-color: color-mix(in srgb, var(--stage-color, #5CD8CE) 78%, white 8%);
        box-shadow: 0 0 56px color-mix(in srgb, var(--stage-color, #5CD8CE) 24%, transparent), 0 26px 74px rgba(0,0,0,.35);
      }

      .selected-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 58px;
        height: 58px;
        overflow: hidden;
        border: 1px solid color-mix(in srgb, var(--stage-color, #5CD8CE) 48%, rgba(255,255,255,.16));
        border-radius: 16px;
        background: color-mix(in srgb, var(--stage-color, #5CD8CE) 12%, rgba(255,255,255,.045));
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 14px;
        font-weight: 950;
      }

      .selected-logo img {
        display: block;
        width: auto;
        height: auto;
        max-width: 72%;
        max-height: 72%;
        object-fit: contain;
      }

      .selected-name {
        max-width: 160px;
        color: #f8fbff;
        font-size: 18px;
        font-weight: 950;
        letter-spacing: -.02em;
        line-height: 1.25;
      }

      .node-card {
        width: 100%;
        min-height: 92px;
        border-color: color-mix(in srgb, var(--node-tone, #5CD8CE) 22%, rgba(255,255,255,.10));
        border-radius: 15px;
        background:
          linear-gradient(180deg, color-mix(in srgb, var(--node-tone, #5CD8CE) 6%, transparent), transparent 70%),
          rgba(0,0,0,.24);
        box-shadow: 0 12px 30px rgba(0,0,0,.18);
      }

      .node-card:hover {
        border-color: color-mix(in srgb, var(--node-tone, #5CD8CE) 54%, rgba(255,255,255,.18));
        box-shadow: 0 0 24px color-mix(in srgb, var(--node-tone, #5CD8CE) 12%, transparent), 0 16px 36px rgba(0,0,0,.22);
      }

      .node-card.is-small {
        min-height: 74px;
        padding: 8px;
      }

      .node-card.is-small .node-logo {
        width: 30px;
        height: 30px;
      }

      .node-card.is-small .node-title {
        max-width: 96px;
        font-size: 11px;
      }

      .node-card.is-small .node-relation,
      .node-card.is-small .node-type-pill {
        display: none;
      }

      .storygraph-flow-row.is-dense .node-card,
      .flow-stage.is-dense-layer .node-card {
        min-height: 58px;
        padding: 8px;
      }

      .storygraph-flow-row.is-dense .node-card .node-copy,
      .flow-stage.is-dense-layer .node-card .node-copy {
        display: none;
      }

      .storygraph-flow-row.is-dense .node-logo,
      .flow-stage.is-dense-layer .node-logo {
        width: 36px;
        height: 36px;
      }

      .node-card-inner {
        display: grid;
        place-items: center;
        gap: 8px;
      }

      .node-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 36px;
        height: 36px;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 11px;
        background: rgba(255,255,255,.045);
        color: #fff;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 10px;
        font-weight: 950;
      }

      .node-logo img {
        display: block;
        width: auto;
        height: auto;
        max-width: 72%;
        max-height: 72%;
        object-fit: contain;
      }

      .node-copy {
        display: grid;
        justify-items: center;
        gap: 5px;
        min-width: 0;
      }

      .node-title {
        display: -webkit-box;
        max-width: 150px;
        overflow: hidden;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        color: #f3f8ff;
        font-size: 13px;
        font-weight: 900;
        line-height: 1.35;
      }

      .node-meta {
        display: flex;
        flex-wrap: wrap;
        justify-content: center;
        gap: 5px;
      }

      .node-relation {
        display: -webkit-box;
        max-width: 150px;
        overflow: hidden;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        color: #9aa8bd;
        font-size: 10px;
        line-height: 1.5;
      }

      .node-type-pill {
        display: inline-flex;
        align-items: center;
        border-radius: 999px;
        padding: 3px 7px;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 9px;
        font-weight: 850;
      }

      .internal-flow {
        position: relative;
        display: grid;
        place-items: center;
        min-height: 32px;
        color: var(--internal-color, #5CD8CE);
      }

      .internal-line {
        width: 1px;
        height: 29px;
        background: linear-gradient(180deg, transparent, var(--internal-color, #5CD8CE), transparent);
        opacity: .62;
      }

      .internal-particle {
        position: absolute;
        top: 2px;
        width: 4px;
        height: 4px;
        border-radius: 999px;
        background: var(--internal-color, #5CD8CE);
        box-shadow: 0 0 9px var(--internal-color, #5CD8CE);
        animation: ecosystemFlowY 2.2s linear infinite;
      }

      .internal-label {
        position: absolute;
        left: calc(50% + 10px);
        top: 50%;
        max-width: 132px;
        transform: translateY(-50%);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 999px;
        background: rgba(7,9,13,.76);
        padding: 2px 7px;
        color: #aebbd0;
        font-size: 9px;
      }

      .company-cta {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: fit-content;
        border: 1px solid rgba(255,255,255,.24);
        border-radius: 999px;
        padding: 10px 15px;
        color: #fff;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 11px;
        font-weight: 950;
        box-shadow: 0 16px 36px rgba(0,0,0,.30);
        transition: transform .18s ease, box-shadow .18s ease, filter .18s ease;
      }

      .company-cta:hover {
        transform: translateY(-2px);
        filter: brightness(1.08);
        box-shadow: 0 20px 48px rgba(0,0,0,.38);
      }

      .selected-company-logo {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 64px;
        height: 64px;
        margin-inline: auto;
        overflow: hidden;
        border: 1px solid rgba(255,255,255,.15);
        border-radius: 18px;
        background: rgba(255,255,255,.06);
        color: #fff;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 18px;
        font-weight: 950;
      }

      .selected-company-logo img {
        display: block;
        width: auto;
        height: auto;
        max-width: 74%;
        max-height: 74%;
        object-fit: contain;
      }

      .storygraph-competitors {
        margin-top: 18px;
        padding-top: 2px;
      }

      .storygraph-logo-panels {
        display: grid;
        grid-template-columns: repeat(4, minmax(0, 1fr));
        gap: 12px;
      }

      .logo-chip-panel {
        min-width: 0;
        overflow: hidden;
        border: 1px solid color-mix(in srgb, var(--chip-tone, #5CD8CE) 42%, rgba(255,255,255,.10));
        border-radius: 16px;
        background:
          linear-gradient(180deg, color-mix(in srgb, var(--chip-tone, #5CD8CE) 10%, transparent), transparent 66%),
          rgba(255,255,255,.035);
        padding: 13px;
        box-shadow: 0 18px 46px rgba(0,0,0,.18);
        backdrop-filter: blur(14px);
      }

      .logo-chip-list {
        display: flex;
        gap: 9px;
        overflow-x: auto;
        overscroll-behavior-x: contain;
        padding: 4px 2px 8px;
        scrollbar-width: thin;
      }

      .logo-chip {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        flex: 0 0 auto;
        overflow: hidden;
        border: 1px solid color-mix(in srgb, var(--chip-tone, #5CD8CE) 38%, rgba(255,255,255,.12));
        border-radius: 13px;
        background: rgba(0,0,0,.22);
        color: #f8fbff;
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 10px;
        font-weight: 950;
        transition: transform .18s ease, border-color .18s ease, box-shadow .18s ease, background .18s ease;
      }

      .logo-chip img {
        display: block;
        width: auto;
        height: auto;
        max-width: 72%;
        max-height: 72%;
        object-fit: contain;
      }

      .logo-chip.is-clickable:hover {
        transform: translateY(-2px);
        border-color: var(--chip-tone, #5CD8CE);
        background: color-mix(in srgb, var(--chip-tone, #5CD8CE) 12%, rgba(0,0,0,.24));
        box-shadow: 0 0 22px color-mix(in srgb, var(--chip-tone, #5CD8CE) 18%, transparent);
      }

      .storygraph-related {
        margin-top: 24px;
        border-top: 1px solid rgba(255,255,255,.10);
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
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 15px;
        background:
          radial-gradient(circle at 14% 0%, rgba(92,216,206,.12), transparent 18rem),
          rgba(255,255,255,.038);
        padding: 16px;
        transition: transform .2s ease, border-color .2s ease, background .2s ease, box-shadow .2s ease;
      }

      .related-article-card:hover {
        transform: translateY(-3px);
        border-color: rgba(92,216,206,.52);
        background:
          radial-gradient(circle at 14% 0%, rgba(92,216,206,.18), transparent 18rem),
          rgba(92,216,206,.055);
        box-shadow: 0 0 34px rgba(92,216,206,.12);
      }

      .related-article-card h5 {
        display: -webkit-box;
        min-height: 48px;
        overflow: hidden;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        color: #f3f8ff;
        font-size: 14px;
        font-weight: 850;
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
        font-weight: 850;
        line-height: 1;
      }

      .related-category {
        border: 1px solid rgba(90,158,255,.22);
        background: rgba(90,158,255,.10);
        color: #9cc8ff;
      }

      .related-badge.is-important { background: rgba(248,113,113,.12); color: #fca5a5; }
      .related-badge.is-watch { background: rgba(234,179,8,.12); color: #fde68a; }

      .flow-connector {
        position: relative;
        z-index: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        flex: 0 0 62px;
        color: var(--flow-color, #5CD8CE);
        font-family: IBM Plex Mono, ui-monospace, monospace;
        font-size: 9px;
        font-weight: 850;
        letter-spacing: .04em;
      }

      .flow-connector-x {
        width: 62px;
        min-height: 52px;
      }

      .flow-line {
        display: block;
        width: 100%;
        height: 1px;
        background: linear-gradient(90deg, transparent, var(--flow-color, #5CD8CE), transparent);
        opacity: .62;
        box-shadow: 0 0 9px color-mix(in srgb, var(--flow-color, #5CD8CE) 42%, transparent);
      }

      .flow-particle {
        position: absolute;
        width: 4px;
        height: 4px;
        border-radius: 999px;
        background: var(--flow-color, #5CD8CE);
        box-shadow: 0 0 9px var(--flow-color, #5CD8CE);
        animation: ecosystemFlowX 2.05s linear infinite;
      }

      .flow-label {
        position: absolute;
        left: 50%;
        top: calc(50% + 11px);
        transform: translateX(-50%);
        border: 1px solid rgba(255,255,255,.08);
        border-radius: 999px;
        background: rgba(7,9,13,.78);
        padding: 2px 7px;
        color: #9aa8bd;
        white-space: nowrap;
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

      @media (max-width: 1180px) {
        .ecosystem-section-head {
          grid-template-columns: 1fr;
          align-items: start;
        }
        .ecosystem-stats {
          justify-content: flex-start;
        }
        .sector-overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .directory-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .storygraph-logo-panels { grid-template-columns: repeat(2, minmax(0, 1fr)); }
      }

      @media (max-width: 768px) {
        .sector-overview-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); }
        .sector-company-chip { flex-basis: 120px; }
        .storygraph-title-row {
          align-items: flex-start;
          flex-direction: column;
        }
        .map-toolbar {
          align-items: flex-start;
          flex-direction: column;
        }
        .storygraph-map-shell {
          margin-inline: -16px;
          padding-inline: 16px;
        }
        .storygraph-flow-row {
          min-width: 980px;
          justify-content: flex-start;
        }
        .storygraph-logo-panels { grid-template-columns: 1fr; }
        .related-article-grid { grid-template-columns: 1fr; }
      }

      @media (max-width: 560px) {
        .sector-overview-grid { grid-template-columns: 1fr; }
        .directory-grid { grid-template-columns: 1fr; }
      }
    `}</style>
  );
}
