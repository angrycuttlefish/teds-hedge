import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import {
  runResearchPipeline,
  ResearchPipelineRequest,
  ResearchStageUpdate,
} from '@/services/research-api';
import {
  AlertCircle,
  BookOpen,
  Check,
  ChevronDown,
  Loader2,
  Play,
  Square,
} from 'lucide-react';
import { useCallback, useRef, useState } from 'react';

type StageStatus = 'idle' | 'running' | 'complete' | 'error';

interface PipelineStage {
  key: string;
  name: string;
  description: string;
  status: StageStatus;
  message: string;
  output: any;
}

const PIPELINE_STAGES: Omit<PipelineStage, 'status' | 'message' | 'output'>[] = [
  {
    key: 'podcast_signal_extractor',
    name: 'Signal Extractor',
    description: 'Extracts investable themes from content',
  },
  {
    key: 'hedge_fund_analyst',
    name: 'Hedge Fund Analyst',
    description: 'Transforms themes into investment theses',
  },
  {
    key: 'deep_research_synthesizer',
    name: 'Deep Research',
    description: 'Generates targeted research questions',
  },
  {
    key: 'research_consolidator',
    name: 'Research Consolidator',
    description: 'Weighs evidence and assigns confidence scores',
  },
  {
    key: 'equity_screener',
    name: 'Equity Screener',
    description: 'Identifies first/second/third-order equity winners',
  },
];

function createInitialStages(): PipelineStage[] {
  return PIPELINE_STAGES.map(s => ({
    ...s,
    status: 'idle' as StageStatus,
    message: '',
    output: null,
  }));
}

export function ResearchPipelineView() {
  const [source, setSource] = useState('');
  const [isRunning, setIsRunning] = useState(false);
  const [stages, setStages] = useState<PipelineStage[]>(createInitialStages());
  const [result, setResult] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedResults, setExpandedResults] = useState<Record<string, boolean>>({
    themes: true,
    theses: true,
    equities: true,
  });
  const abortRef = useRef<(() => void) | null>(null);

  const handleRun = useCallback(() => {
    if (!source.trim()) return;

    setIsRunning(true);
    setStages(createInitialStages());
    setResult(null);
    setError(null);

    const request: ResearchPipelineRequest = {
      source: source.trim(),
    };

    const abort = runResearchPipeline(request, {
      onStart: () => {
        // Mark first stage as running
        setStages(prev => {
          const next = [...prev];
          if (next[0]) next[0] = { ...next[0], status: 'running', message: 'Starting...' };
          return next;
        });
      },
      onProgress: (update: ResearchStageUpdate) => {
        setStages(prev => {
          const next = prev.map(stage => {
            if (stage.key === update.agent) {
              const isDone =
                update.status.toLowerCase().includes('done') ||
                update.status.toLowerCase().includes('complete');
              return {
                ...stage,
                status: (isDone ? 'complete' : 'running') as StageStatus,
                message: update.status,
                output: update.analysis || stage.output,
              };
            }
            return stage;
          });

          // If a stage just completed, start the next idle stage
          const completedIdx = next.findIndex(
            s => s.key === update.agent && s.status === 'complete'
          );
          if (completedIdx >= 0 && completedIdx < next.length - 1) {
            const nextStage = next[completedIdx + 1];
            if (nextStage && nextStage.status === 'idle') {
              next[completedIdx + 1] = { ...nextStage, status: 'running', message: 'Starting...' };
            }
          }

          return next;
        });
      },
      onComplete: (data: any) => {
        setStages(prev => prev.map(s => ({ ...s, status: 'complete' as StageStatus })));
        setResult(data);
        setIsRunning(false);
      },
      onError: (message: string) => {
        setError(message);
        setIsRunning(false);
        setStages(prev =>
          prev.map(s =>
            s.status === 'running' ? { ...s, status: 'error' as StageStatus, message } : s
          )
        );
      },
    });

    abortRef.current = abort;
  }, [source]);

  const handleStop = useCallback(() => {
    abortRef.current?.();
    setIsRunning(false);
    setStages(prev =>
      prev.map(s =>
        s.status === 'running' ? { ...s, status: 'idle' as StageStatus, message: 'Cancelled' } : s
      )
    );
  }, []);

  const toggleResultSection = (key: string) => {
    setExpandedResults(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="flex flex-col h-full overflow-hidden bg-panel">
      {/* Header */}
      <div className="flex items-center gap-3 px-6 py-4 border-b">
        <BookOpen className="h-5 w-5 text-blue-500" />
        <h1 className="text-lg font-semibold text-primary">Research Pipeline</h1>
      </div>

      <div className="flex-1 overflow-auto p-6 space-y-6">
        {/* Input Section */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Source Input</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex gap-3">
              <Input
                placeholder="Enter a URL (YouTube, Substack) or paste text..."
                value={source}
                onChange={e => setSource(e.target.value)}
                disabled={isRunning}
                className="flex-1"
                onKeyDown={e => {
                  if (e.key === 'Enter' && !isRunning) handleRun();
                }}
              />
              {isRunning ? (
                <Button variant="destructive" size="sm" onClick={handleStop} className="gap-2">
                  <Square className="h-4 w-4" />
                  Stop
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={handleRun}
                  disabled={!source.trim()}
                  className="gap-2"
                >
                  <Play className="h-4 w-4" />
                  Run Pipeline
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Pipeline Stepper */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm">Pipeline Stages</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-0">
              {stages.map((stage, index) => (
                <div key={stage.key} className="flex gap-4">
                  {/* Vertical timeline */}
                  <div className="flex flex-col items-center">
                    <StageIndicator status={stage.status} />
                    {index < stages.length - 1 && (
                      <div
                        className={cn(
                          'w-px flex-1 min-h-[24px]',
                          stage.status === 'complete' ? 'bg-green-500' : 'bg-border'
                        )}
                      />
                    )}
                  </div>

                  {/* Stage info */}
                  <div className="pb-6 flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          'text-sm font-medium',
                          stage.status === 'running' && 'text-blue-400',
                          stage.status === 'complete' && 'text-green-400',
                          stage.status === 'error' && 'text-red-400',
                          stage.status === 'idle' && 'text-muted-foreground'
                        )}
                      >
                        {stage.name}
                      </span>
                      {stage.status === 'running' && (
                        <Badge variant="success" className="text-[10px] px-1.5 py-0">
                          Running
                        </Badge>
                      )}
                      {stage.status === 'complete' && (
                        <Badge variant="success" className="text-[10px] px-1.5 py-0 bg-green-600">
                          Done
                        </Badge>
                      )}
                      {stage.status === 'error' && (
                        <Badge variant="destructive" className="text-[10px] px-1.5 py-0">
                          Error
                        </Badge>
                      )}
                    </div>
                    <p className="text-xs text-muted-foreground mt-0.5">{stage.description}</p>
                    {stage.message && stage.status !== 'idle' && (
                      <p className="text-xs text-muted-foreground mt-1 italic">{stage.message}</p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {/* Error display */}
        {error && (
          <Card className="border-red-500/50">
            <CardContent className="pt-6">
              <div className="flex items-center gap-2 text-red-400">
                <AlertCircle className="h-4 w-4" />
                <span className="text-sm font-medium">Pipeline Error</span>
              </div>
              <p className="text-sm text-muted-foreground mt-2">{error}</p>
            </CardContent>
          </Card>
        )}

        {/* Results */}
        {result && (
          <div className="space-y-4">
            <h2 className="text-sm font-semibold text-primary">Results</h2>

            {/* Top Picks */}
            {result.equity_ideas?.top_picks?.length > 0 && (
              <Card className="border-green-500/30">
                <CardContent className="pt-6">
                  <div className="flex items-center gap-2 mb-2">
                    <span className="text-sm font-medium text-primary">Top Picks</span>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    {result.equity_ideas.top_picks.map((ticker: string, i: number) => (
                      <Badge key={i} variant="success" className="font-mono text-sm px-3 py-1">
                        {ticker}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Themes */}
            {result.themes?.themes?.length > 0 && (
              <ResultSection
                title={`Themes (${result.themes.themes.length})`}
                expanded={expandedResults.themes}
                onToggle={() => toggleResultSection('themes')}
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="pb-2 pr-4 font-medium">Theme</th>
                        <th className="pb-2 pr-4 font-medium">Category</th>
                        <th className="pb-2 pr-4 font-medium">Signal</th>
                        <th className="pb-2 font-medium">Tickers</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.themes.themes.map((theme: any, i: number) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-2 pr-4 font-medium text-primary">
                            {theme.theme || `Theme ${i + 1}`}
                          </td>
                          <td className="py-2 pr-4 text-muted-foreground">
                            {theme.category || '-'}
                          </td>
                          <td className="py-2 pr-4">
                            <SignalBadge strength={theme.signal_strength} />
                          </td>
                          <td className="py-2 text-muted-foreground">
                            {theme.mentioned_tickers?.join(', ') || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </ResultSection>
            )}

            {/* Thesis Confidence */}
            {result.consolidated_research?.assessments?.length > 0 && (
              <ResultSection
                title={`Thesis Confidence (${result.consolidated_research.assessments.length})`}
                expanded={expandedResults.theses}
                onToggle={() => toggleResultSection('theses')}
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="pb-2 pr-4 font-medium">Thesis</th>
                        <th className="pb-2 pr-4 font-medium w-48">Confidence</th>
                        <th className="pb-2 font-medium">Key Assumption</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.consolidated_research.assessments.map((a: any, i: number) => (
                        <tr key={i} className="border-b border-border/50">
                          <td className="py-2 pr-4 font-medium text-primary max-w-xs truncate">
                            {a.thesis || `Thesis ${i + 1}`}
                          </td>
                          <td className="py-2 pr-4">
                            <ConfidenceBar score={a.confidence_score || 0} />
                          </td>
                          <td className="py-2 text-muted-foreground max-w-xs truncate">
                            {a.key_assumption || '-'}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </ResultSection>
            )}

            {/* Equity Ideas */}
            {result.equity_ideas?.sectors?.length > 0 && (
              <ResultSection
                title={`Equity Ideas (${result.equity_ideas.sectors.reduce((sum: number, s: any) => sum + (s.equities?.length || 0), 0)})`}
                expanded={expandedResults.equities}
                onToggle={() => toggleResultSection('equities')}
              >
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b text-left text-muted-foreground">
                        <th className="pb-2 pr-4 font-medium">Ticker</th>
                        <th className="pb-2 pr-4 font-medium">Company</th>
                        <th className="pb-2 pr-4 font-medium">Sector</th>
                        <th className="pb-2 pr-4 font-medium">Order</th>
                        <th className="pb-2 font-medium">Conviction</th>
                      </tr>
                    </thead>
                    <tbody>
                      {result.equity_ideas.sectors.flatMap((sector: any) =>
                        (sector.equities || []).map((idea: any, i: number) => (
                          <tr key={`${sector.sector}-${i}`} className="border-b border-border/50">
                            <td className="py-2 pr-4">
                              <Badge variant="outline" className="font-mono">
                                {idea.ticker || '-'}
                              </Badge>
                            </td>
                            <td className="py-2 pr-4 font-medium text-primary">
                              {idea.company_name || '-'}
                            </td>
                            <td className="py-2 pr-4 text-muted-foreground">
                              {idea.sector || sector.sector || '-'}
                            </td>
                            <td className="py-2 pr-4">
                              <OrderBadge order={idea.order} />
                            </td>
                            <td className="py-2">
                              <ConvictionBadge conviction={idea.conviction} />
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Portfolio Construction Notes */}
                {result.equity_ideas.portfolio_construction_notes && (
                  <div className="mt-4 p-3 bg-muted/50 rounded-md">
                    <p className="text-xs font-medium text-primary mb-1">Portfolio Construction Notes</p>
                    <p className="text-xs text-muted-foreground">{result.equity_ideas.portfolio_construction_notes}</p>
                  </div>
                )}
              </ResultSection>
            )}

            {/* Raw JSON fallback */}
            {!result.themes && !result.consolidated_research && !result.equity_ideas && (
              <Card>
                <CardContent className="pt-6">
                  <pre className="text-xs text-muted-foreground whitespace-pre-wrap overflow-auto max-h-96">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                </CardContent>
              </Card>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

/* ---- Sub-components ---- */

function StageIndicator({ status }: { status: StageStatus }) {
  const base = 'h-6 w-6 rounded-full flex items-center justify-center flex-shrink-0';

  switch (status) {
    case 'running':
      return (
        <div className={cn(base, 'bg-blue-500/20 border border-blue-500')}>
          <Loader2 className="h-3 w-3 text-blue-400 animate-spin" />
        </div>
      );
    case 'complete':
      return (
        <div className={cn(base, 'bg-green-500/20 border border-green-500')}>
          <Check className="h-3 w-3 text-green-400" />
        </div>
      );
    case 'error':
      return (
        <div className={cn(base, 'bg-red-500/20 border border-red-500')}>
          <AlertCircle className="h-3 w-3 text-red-400" />
        </div>
      );
    default:
      return <div className={cn(base, 'bg-muted border border-border')} />;
  }
}

function ResultSection({
  title,
  expanded,
  onToggle,
  children,
}: {
  title: string;
  expanded: boolean;
  onToggle: () => void;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <button
        onClick={onToggle}
        className="w-full flex items-center justify-between p-4 text-left"
      >
        <span className="text-sm font-medium text-primary">{title}</span>
        <ChevronDown
          className={cn(
            'h-4 w-4 text-muted-foreground transition-transform',
            expanded && 'rotate-180'
          )}
        />
      </button>
      {expanded && <CardContent className="pt-0">{children}</CardContent>}
    </Card>
  );
}

function SignalBadge({ strength }: { strength: string | number | undefined }) {
  if (!strength) return <span className="text-muted-foreground">-</span>;

  const label = typeof strength === 'number' ? `${strength}/10` : strength;
  const numVal = typeof strength === 'number' ? strength : parseFloat(strength) || 5;

  let variant: 'success' | 'warning' | 'destructive' | 'secondary' = 'secondary';
  if (numVal >= 7) variant = 'success';
  else if (numVal >= 4) variant = 'warning';
  else variant = 'destructive';

  return <Badge variant={variant}>{label}</Badge>;
}

function ConfidenceBar({ score }: { score: number }) {
  // Score is 0-100 from the pipeline
  const pct = Math.min(Math.max(score, 0), 100);
  const color =
    pct >= 70 ? 'bg-green-500' : pct >= 40 ? 'bg-yellow-500' : 'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className={cn('h-full rounded-full', color)} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs text-muted-foreground w-10 text-right">
        {Math.round(pct)}%
      </span>
    </div>
  );
}

function OrderBadge({ order }: { order: string | number | undefined }) {
  if (!order) return <span className="text-muted-foreground">-</span>;

  const label = typeof order === 'number' ? `${order}${ordinalSuffix(order)} Order` : order;

  return <Badge variant="outline">{label}</Badge>;
}

function ordinalSuffix(n: number): string {
  const s = ['th', 'st', 'nd', 'rd'];
  const v = n % 100;
  return s[(v - 20) % 10] || s[v] || s[0];
}

function ConvictionBadge({ conviction }: { conviction: string | undefined }) {
  if (!conviction) return <span className="text-muted-foreground">-</span>;

  const lower = conviction.toLowerCase();
  let variant: 'success' | 'warning' | 'secondary' = 'secondary';
  if (lower === 'high') variant = 'success';
  else if (lower === 'medium') variant = 'warning';

  return <Badge variant={variant}>{conviction}</Badge>;
}
