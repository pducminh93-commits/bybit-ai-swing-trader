import { useState, useEffect } from "react";
import {
  AlertCircle,
  Zap,
  Search,
  RefreshCw,
  BarChart3,
  XCircle
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import { fetchTickers, fetchSignals } from "./services/bybit";
import { cn } from "@/lib/utils";

export default function App() {
  const [tickers, setTickers] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"signals" | "demo" | "training">("signals");
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);

  // Fetch tickers on mount and get top 10
  useEffect(() => {
    const loadTickers = async () => {
      try {
        const data = await fetchTickers();
        const top10 = data
          .filter(t => t.symbol.endsWith("USDT"))
          .sort((a, b) => parseFloat(b.turnover24h) - parseFloat(a.turnover24h))
          .slice(0, 10);
        setTickers(top10);
      } catch (err) {
        console.error(err);
        setError("Failed to load market data");
      }
    };
    loadTickers();
  }, []);

  const handleScanAll = async () => {
    if (tickers.length === 0) return;
    setIsScanning(true);
    setScanProgress(0);

    try {
      const symbols = tickers.map(t => t.symbol).join(",");
      setScanProgress(50);
      const signalData = await fetchSignals(symbols);
      setSignals(signalData);
      setScanProgress(100);
    } catch (err) {
      console.error(err);
      setError("Failed to scan signals");
    } finally {
      setIsScanning(false);
      setScanProgress(0);
    }
  };

  return (
  <div className="min-h-screen bg-[#050505] text-zinc-300 font-sans selection:bg-orange-500/30">
      {/* Header */}
      <header className="border-b border-zinc-800/50 bg-black/40 backdrop-blur-xl sticky top-0 z-50">
        <div className="container mx-auto px-4 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 bg-gradient-to-br from-orange-400 to-orange-600 rounded-xl flex items-center justify-center shadow-lg shadow-orange-500/20">
              <Zap className="text-black w-5 h-5 fill-current" />
            </div>
            <div>
              <h1 className="text-lg font-black tracking-tighter text-white leading-none">
                BYBIT <span className="text-orange-500">AI</span> SCANNER
              </h1>
              <p className="text-[10px] text-zinc-500 font-bold tracking-widest uppercase mt-0.5">Quantum Swing Analysis</p>
            </div>
          </div>
          
          <div className="flex items-center gap-4">
            <div className="hidden md:flex flex-col items-end">
              <span className="text-[10px] text-zinc-500 font-bold uppercase">Top 10 Liquidity</span>
              <span className="text-xs text-zinc-400 font-mono">USDT Perpetuals</span>
            </div>
          </div>
        </div>

        {/* Sub-navbar */}
        <div className="border-t border-zinc-800/30 bg-zinc-900/10">
          <div className="container mx-auto px-4 h-12 flex items-center justify-between">
            <div className="flex items-center gap-6">
              {/* Tín hiệu */}
              <div 
                onClick={() => setActiveTab("signals")}
                className={cn(
                  "flex items-center gap-2 cursor-pointer group transition-all",
                  activeTab === "signals" ? "opacity-100" : "opacity-40 hover:opacity-80"
                )}
              >
                <div className={cn(
                  "w-2 h-2 rounded-full shadow-[0_0_8px_rgba(249,115,22,0.6)]",
                  activeTab === "signals" ? "bg-orange-500" : "bg-zinc-600"
                )} />
                <span className={cn(
                  "text-xs font-black tracking-widest uppercase transition-colors",
                  activeTab === "signals" ? "text-zinc-100" : "text-zinc-400 group-hover:text-zinc-200"
                )}>Tín hiệu</span>
              </div>
              
              {/* Demo */}
              <div 
                onClick={() => setActiveTab("demo")}
                className={cn(
                  "flex items-center gap-2 cursor-pointer group transition-all",
                  activeTab === "demo" ? "opacity-100" : "opacity-40 hover:opacity-80"
                )}
              >
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  activeTab === "demo" ? "bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.6)]" : "bg-zinc-600"
                )} />
                <span className={cn(
                  "text-xs font-black tracking-widest uppercase transition-colors",
                  activeTab === "demo" ? "text-zinc-100" : "text-zinc-400 group-hover:text-zinc-200"
                )}>Demo</span>
              </div>

              {/* Training */}
              <div 
                onClick={() => setActiveTab("training")}
                className={cn(
                  "flex items-center gap-2 cursor-pointer group transition-all",
                  activeTab === "training" ? "opacity-100" : "opacity-40 hover:opacity-80"
                )}
              >
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  activeTab === "training" ? "bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.6)]" : "bg-zinc-600"
                )} />
                <span className={cn(
                  "text-xs font-black tracking-widest uppercase transition-colors",
                  activeTab === "training" ? "text-zinc-100" : "text-zinc-400 group-hover:text-zinc-200"
                )}>Training</span>
              </div>

              <div className="h-4 w-[1px] bg-zinc-800 hidden md:block" />
              <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-[0.2em] hidden lg:block">Market Intelligence Hub</span>
            </div>
          </div>
        </div>

        {/* Action Row */}
        {activeTab === "signals" && (
          <div className="border-t border-zinc-800/30 bg-black/20">
            <div className="container mx-auto px-4 h-14 flex items-center justify-end">
              <Button 
                onClick={handleScanAll} 
                disabled={isScanning || tickers.length === 0}
                className="bg-orange-500 hover:bg-orange-600 text-black font-black px-8 h-9 text-xs rounded-full shadow-lg shadow-orange-500/20 transition-all active:scale-95 flex items-center gap-2"
              >
                {isScanning ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    SCANNING {scanProgress}%
                  </>
                ) : (
                  <>
                    <BarChart3 className="w-4 h-4" />
                    START FULL SCAN
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </header>

      <main className="container mx-auto px-4 py-8 space-y-8">
        {activeTab === "signals" && (
          <div className="space-y-6">
            <h2 className="text-xl font-bold text-white">AI Trading Signals</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {signals.map((signal) => (
                <Card key={signal.symbol} className="bg-zinc-900/50 border-zinc-800">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-white flex items-center justify-between">
                      {signal.symbol}
                      <Badge
                        variant={signal.signal === 'BUY' ? 'default' : signal.signal === 'SELL' ? 'destructive' : 'secondary'}
                        className={signal.signal === 'BUY' ? 'bg-green-500' : signal.signal === 'SELL' ? 'bg-red-500' : ''}
                      >
                        {signal.signal}
                      </Badge>
                    </CardTitle>
                    <CardDescription>Confidence: {(signal.confidence * 100).toFixed(1)}%</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <p className="text-sm text-zinc-400">{signal.reason}</p>
                    <div className="text-xs text-zinc-500 space-y-1">
                      <div>TP: {signal.take_profit}</div>
                      <div>SL: {signal.stop_loss}</div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {activeTab === "demo" && (
          <div className="text-center space-y-4">
            <h2 className="text-xl font-bold text-white">Market Overview</h2>
            <ScrollArea className="h-96">
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {tickers.map((ticker) => (
                  <Card key={ticker.symbol} className="bg-zinc-900/50 border-zinc-800">
                    <CardHeader className="pb-3">
                      <CardTitle className="text-white">{ticker.symbol}</CardTitle>
                      <CardDescription>Price: {ticker.lastPrice}</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="text-xs text-zinc-500">
                        Volume: {ticker.volume24h}
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            </ScrollArea>
          </div>
        )}

        {activeTab === "training" && (
          <div className="text-center space-y-4">
            <h2 className="text-xl font-bold text-white">AI Training Center</h2>
            <p className="text-zinc-500 text-sm max-w-md text-center">
              Fine-tune the AI model with your own historical data and custom indicators.
              Improve signal accuracy by training the engine on specific market conditions.
            </p>
            <Button variant="outline" className="border-zinc-800 text-zinc-400 hover:text-white">
              COMING SOON
            </Button>
          </div>
        )}

        {/* Footer Info */}
        <div className="flex flex-col md:flex-row items-center justify-between gap-4 pt-8 border-t border-zinc-800/50 text-[10px] font-bold uppercase tracking-widest text-zinc-600">
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              Live Bybit Data
            </div>
            <div className="flex items-center gap-1">
              <div className="w-1.5 h-1.5 rounded-full bg-orange-500" />
              Gemini 3 Flash AI
            </div>
          </div>
          <p>© 2026 BYBIT AI TRADER PRO • SWING TRADING ENGINE</p>
        </div>
      </main>

      {/* Error Toast */}
      {error && (
        <div className="fixed bottom-6 right-6 bg-red-500 text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center gap-3 animate-in slide-in-from-right-full duration-300">
          <AlertCircle className="w-6 h-6" />
          <div className="flex flex-col">
            <span className="font-bold text-sm">System Error</span>
            <span className="text-xs opacity-90">{error}</span>
          </div>
          <button onClick={() => setError(null)} className="ml-4 hover:bg-white/20 p-1 rounded-lg transition-colors">
            <XCircle className="w-5 h-5" />
          </button>
        </div>
      )}
    </div>
  );
}

