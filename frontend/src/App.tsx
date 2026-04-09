import { useState, useEffect } from "react";
import {
  AlertCircle,
  Zap,
  Search,
  RefreshCw,
  BarChart3,
  XCircle,
  Settings
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Skeleton } from "@/components/ui/skeleton";
import {
  fetchTickers,
  fetchSignals,
  startDemoSimulation,
  stopDemoSimulation,
  processDemoSignals,
  getDemoStatus,
  getDemoPositions,
  getDemoHistory,
  resetDemoSimulation,
  DemoPosition,
  DemoTrade,
  DemoStatus
} from "./services/bybit";
import { cn } from "@/lib/utils";

export default function App() {
  const [tickers, setTickers] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"signals" | "settings" | "demo" | "training">("signals");
  const [isScanning, setIsScanning] = useState(false);
  const [scanProgress, setScanProgress] = useState(0);

  // Auto scan settings
  const [autoScanEnabled, setAutoScanEnabled] = useState(false);
  const [autoScanInterval, setAutoScanInterval] = useState(30); // minutes
  const [autoScanTimer, setAutoScanTimer] = useState<NodeJS.Timeout | null>(null);

  // Demo trading state
  const [demoStatus, setDemoStatus] = useState<DemoStatus | null>(null);
  const [demoPositions, setDemoPositions] = useState<DemoPosition[]>([]);
  const [demoHistory, setDemoHistory] = useState<DemoTrade[]>([]);
  const [isDemoLoading, setIsDemoLoading] = useState(false);

  // Load settings from localStorage
  useEffect(() => {
    const savedAutoScanEnabled = localStorage.getItem('autoScanEnabled') === 'true';
    const savedAutoScanInterval = parseInt(localStorage.getItem('autoScanInterval') || '30');
    setAutoScanEnabled(savedAutoScanEnabled);
    setAutoScanInterval(savedAutoScanInterval);
  }, []);

  // Auto scan logic
  useEffect(() => {
    if (autoScanEnabled) {
      const interval = setInterval(() => {
        handleScanAll();
      }, autoScanInterval * 60 * 1000); // Convert minutes to milliseconds
      setAutoScanTimer(interval);
      return () => clearInterval(interval);
    } else {
      if (autoScanTimer) {
        clearInterval(autoScanTimer);
        setAutoScanTimer(null);
      }
    }
  }, [autoScanEnabled, autoScanInterval]);

  // Save settings to localStorage
  const saveSettings = (enabled: boolean, interval: number) => {
    localStorage.setItem('autoScanEnabled', enabled.toString());
    localStorage.setItem('autoScanInterval', interval.toString());
    setAutoScanEnabled(enabled);
    setAutoScanInterval(interval);
  };

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

      // Auto-process signals for demo if demo is running
      if (demoStatus?.is_running && signalData.length > 0) {
        try {
          const result = await processDemoSignals(signalData);
          if (result.count > 0) {
            // Refresh demo data after processing
            loadDemoData();
          }
        } catch (demoErr) {
          console.error("Failed to process demo signals:", demoErr);
        }
      }
    } catch (err) {
      console.error(err);
      setError("Failed to scan signals");
    } finally {
      setIsScanning(false);
      setScanProgress(0);
    }
  };

  // Demo trading functions
  const loadDemoData = async () => {
    try {
      const [status, positions, history] = await Promise.all([
        getDemoStatus(),
        getDemoPositions(),
        getDemoHistory()
      ]);
      setDemoStatus(status);
      setDemoPositions(positions.positions);
      setDemoHistory(history.history);
    } catch (err) {
      console.error("Failed to load demo data:", err);
    }
  };

  const handleStartDemo = async () => {
    setIsDemoLoading(true);
    try {
      await startDemoSimulation();
      const status = await getDemoStatus();
      setDemoStatus(status);
    } catch (err) {
      console.error(err);
      setError("Failed to start demo simulation");
    } finally {
      setIsDemoLoading(false);
    }
  };

  const handleStopDemo = async () => {
    setIsDemoLoading(true);
    try {
      await stopDemoSimulation();
      const status = await getDemoStatus();
      setDemoStatus(status);
    } catch (err) {
      console.error(err);
      setError("Failed to stop demo simulation");
    } finally {
      setIsDemoLoading(false);
    }
  };

  const handleResetDemo = async () => {
    setIsDemoLoading(true);
    try {
      await resetDemoSimulation();
      const status = await getDemoStatus();
      setDemoStatus(status);
      setDemoPositions([]);
      setDemoHistory([]);
    } catch (err) {
      console.error(err);
      setError("Failed to reset demo simulation");
    } finally {
      setIsDemoLoading(false);
    }
  };

  // Load demo data when tab is active
  useEffect(() => {
    if (activeTab === "demo") {
      loadDemoData();
    }
  }, [activeTab]);

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

              {/* Settings */}
              <div
                onClick={() => setActiveTab("settings")}
                className={cn(
                  "flex items-center gap-2 cursor-pointer group transition-all",
                  activeTab === "settings" ? "opacity-100" : "opacity-40 hover:opacity-80"
                )}
              >
                <Settings className={cn(
                  "w-4 h-4",
                  activeTab === "settings" ? "text-orange-500" : "text-zinc-400 group-hover:text-zinc-200"
                )} />
                <span className={cn(
                  "text-xs font-black tracking-widest uppercase transition-colors",
                  activeTab === "settings" ? "text-zinc-100" : "text-zinc-400 group-hover:text-zinc-200"
                )}>Settings</span>
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

        {/* Settings Action Row */}
        {activeTab === "settings" && (
          <div className="border-t border-zinc-800/30 bg-black/20">
            <div className="container mx-auto px-4 h-14 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-xs text-zinc-400">
                  Auto scan: {autoScanEnabled ? 'ON' : 'OFF'} | Interval: {autoScanInterval} minutes
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${autoScanEnabled ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`} />
                <span className="text-xs text-zinc-400">Auto Scan {autoScanEnabled ? 'Active' : 'Inactive'}</span>
              </div>
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
                        variant={
                          signal.signal === 'LONG' ? 'default' :
                          signal.signal === 'SHORT' ? 'destructive' :
                          signal.signal === 'EXIT' ? 'outline' : 'secondary'
                        }
                        className={
                          signal.signal === 'LONG' ? 'bg-green-500' :
                          signal.signal === 'SHORT' ? 'bg-red-500' :
                          signal.signal === 'EXIT' ? 'border-yellow-500 text-yellow-500' : ''
                        }
                      >
                        {signal.signal}
                      </Badge>
                    </CardTitle>
                    <CardDescription>Confidence: {(signal.confidence * 100).toFixed(1)}%</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <p className="text-sm text-zinc-400">{signal.reason}</p>
                    <div className="text-xs text-zinc-500 space-y-1">
                      {signal.entry_price && signal.signal === 'LONG' && (
                        <div>Entry: {signal.entry_price}</div>
                      )}
                      {signal.entry_price && signal.signal === 'SHORT' && (
                        <div>Entry: {signal.entry_price}</div>
                      )}
                      <div>TP: {signal.take_profit}</div>
                      <div>SL: {signal.stop_loss}</div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {activeTab === "settings" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Signal Settings</h2>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Auto Scan Settings */}
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Settings className="w-5 h-5" />
                    Auto Scan Settings
                  </CardTitle>
                  <CardDescription>Configure automatic signal scanning</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Auto Scan Toggle */}
                  <div className="flex items-center justify-between">
                    <div>
                      <label className="text-sm font-medium text-zinc-200">Auto Scan</label>
                      <p className="text-xs text-zinc-500">Automatically scan for signals at set intervals</p>
                    </div>
                    <button
                      onClick={() => saveSettings(!autoScanEnabled, autoScanInterval)}
                      className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                        autoScanEnabled ? 'bg-orange-500' : 'bg-zinc-600'
                      }`}
                    >
                      <span
                        className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                          autoScanEnabled ? 'translate-x-6' : 'translate-x-1'
                        }`}
                      />
                    </button>
                  </div>

                  {/* Scan Interval */}
                  <div className="space-y-3">
                    <div>
                      <label className="text-sm font-medium text-zinc-200">Scan Interval</label>
                      <p className="text-xs text-zinc-500">Time between automatic scans (15-240 minutes)</p>
                    </div>

                    {/* Number Input */}
                    <div className="flex items-center gap-3">
                      <input
                        type="number"
                        min="15"
                        max="240"
                        value={autoScanInterval}
                        onChange={(e) => {
                          const value = Math.max(15, Math.min(240, parseInt(e.target.value) || 15));
                          saveSettings(autoScanEnabled, value);
                        }}
                        className="w-20 px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                      />
                      <span className="text-sm text-zinc-400">minutes</span>
                    </div>

                    {/* Slider */}
                    <div className="space-y-2">
                      <input
                        type="range"
                        min="15"
                        max="240"
                        step="15"
                        value={autoScanInterval}
                        onChange={(e) => saveSettings(autoScanEnabled, parseInt(e.target.value))}
                        className="w-full h-2 bg-zinc-700 rounded-lg appearance-none cursor-pointer slider"
                      />
                      <div className="flex justify-between text-xs text-zinc-500">
                        <span>15m</span>
                        <span>2h</span>
                        <span>4h</span>
                      </div>
                    </div>

                    <div className="text-xs text-zinc-400">
                      Next scan: {autoScanEnabled ? `${autoScanInterval} minutes` : 'Disabled'}
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Current Status */}
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Current Status
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="bg-zinc-800/50 rounded-lg p-3">
                      <div className="text-xs text-zinc-500">Auto Scan</div>
                      <div className={`text-lg font-bold ${autoScanEnabled ? 'text-green-500' : 'text-red-500'}`}>
                        {autoScanEnabled ? 'ON' : 'OFF'}
                      </div>
                    </div>
                    <div className="bg-zinc-800/50 rounded-lg p-3">
                      <div className="text-xs text-zinc-500">Interval</div>
                      <div className="text-lg font-bold text-orange-500">
                        {autoScanInterval}m
                      </div>
                    </div>
                  </div>

                  <div className="bg-zinc-800/50 rounded-lg p-3">
                    <div className="text-xs text-zinc-500 mb-2">Settings Info</div>
                    <div className="text-sm text-zinc-300 space-y-1">
                      <div>• Auto scan scans top 10 USDT pairs</div>
                      <div>• Settings saved in browser localStorage</div>
                      <div>• Demo auto-executes signals ≥60% confidence</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </div>
        )}

        {activeTab === "demo" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Demo Trading Simulation</h2>
              <div className="flex items-center gap-3">
                <Button
                  onClick={handleResetDemo}
                  disabled={isDemoLoading}
                  variant="outline"
                  size="sm"
                  className="border-zinc-700 text-zinc-300 hover:text-white hover:border-zinc-600"
                >
                  Reset
                </Button>
                {demoStatus?.is_running ? (
                  <Button
                    onClick={handleStopDemo}
                    disabled={isDemoLoading}
                    variant="destructive"
                    size="sm"
                    className="bg-red-600 hover:bg-red-700"
                  >
                    Stop Simulation
                  </Button>
                ) : (
                  <Button
                    onClick={handleStartDemo}
                    disabled={isDemoLoading}
                    className="bg-green-600 hover:bg-green-700"
                    size="sm"
                  >
                    Start Simulation
                  </Button>
                )}
              </div>
            </div>

            {/* Demo Status */}
            {demoStatus && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardContent className="p-4">
                    <div className="text-sm text-zinc-400">Balance</div>
                    <div className="text-lg font-bold text-white">
                      ${demoStatus.balance.toFixed(2)}
                    </div>
                    <div className="text-xs text-zinc-500">
                      Capital: ${demoStatus.capital.toFixed(2)}
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardContent className="p-4">
                    <div className="text-sm text-zinc-400">Open Positions</div>
                    <div className="text-lg font-bold text-orange-500">
                      {demoStatus.total_positions}
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardContent className="p-4">
                    <div className="text-sm text-zinc-400">Total Trades</div>
                    <div className="text-lg font-bold text-blue-500">
                      {demoStatus.total_trades}
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardContent className="p-4">
                    <div className="text-sm text-zinc-400">Status</div>
                    <div className={`text-lg font-bold ${demoStatus.is_running ? 'text-green-500' : 'text-red-500'}`}>
                      {demoStatus.is_running ? 'Running' : 'Stopped'}
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Open Positions */}
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Open Positions ({demoPositions.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-80">
                    {demoPositions.length === 0 ? (
                      <div className="text-center text-zinc-500 py-8">
                        No open positions
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {demoPositions.map((position) => (
                          <div key={position.symbol} className="bg-zinc-800/50 rounded-lg p-3">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-white">{position.symbol}</span>
                                <Badge
                                  variant={position.side === 'LONG' ? 'default' : 'destructive'}
                                  className={position.side === 'LONG' ? 'bg-green-600' : 'bg-red-600'}
                                >
                                  {position.side}
                                </Badge>
                              </div>
                              <span className={`font-bold ${position.unrealized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                ${position.unrealized_pnl.toFixed(2)}
                              </span>
                            </div>
                            <div className="text-xs text-zinc-400 space-y-1">
                              <div>Entry: ${position.entry_price.toFixed(4)} | Current: ${position.current_price.toFixed(4)}</div>
                              <div>Quantity: {position.quantity.toFixed(6)} | P&L: {position.pnl_percentage.toFixed(2)}%</div>
                              <div>Entry Time: {new Date(position.entry_time).toLocaleString()}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>

              {/* Trade History */}
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <RefreshCw className="w-5 h-5" />
                    Trade History ({demoHistory.length})
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ScrollArea className="h-80">
                    {demoHistory.length === 0 ? (
                      <div className="text-center text-zinc-500 py-8">
                        No trade history
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {demoHistory.slice().reverse().map((trade, index) => (
                          <div key={index} className="bg-zinc-800/50 rounded-lg p-3">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-white">{trade.symbol}</span>
                                <Badge
                                  variant={trade.side === 'LONG' ? 'default' : 'destructive'}
                                  className={trade.side === 'LONG' ? 'bg-green-600' : 'bg-red-600'}
                                >
                                  {trade.side}
                                </Badge>
                              </div>
                              <span className={`font-bold ${trade.realized_pnl >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                                ${trade.realized_pnl.toFixed(2)}
                              </span>
                            </div>
                            <div className="text-xs text-zinc-400 space-y-1">
                              <div>Entry: ${trade.entry_price.toFixed(4)} | Exit: ${trade.exit_price.toFixed(4)}</div>
                              <div>Quantity: {trade.quantity.toFixed(6)} | P&L: {trade.pnl_percentage.toFixed(2)}%</div>
                              <div>Entry: {new Date(trade.entry_time).toLocaleString()}</div>
                              <div>Exit: {new Date(trade.exit_time).toLocaleString()}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </ScrollArea>
                </CardContent>
              </Card>
            </div>

            <div className="text-center text-zinc-500 text-sm">
              <p>Demo simulation uses 100 USDT capital and automatically executes signals with ≥60% confidence from Signals tab</p>
              <p>Positions update automatically when scanning signals • Uses real Bybit market data</p>
            </div>
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

