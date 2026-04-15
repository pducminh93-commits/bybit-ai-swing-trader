import { useState, useEffect } from "react";
import {
  AlertCircle,
  Zap,
  Search,
  RefreshCw,
  BarChart3,
  XCircle,
  Settings,
  Brain,
  History,
  Activity
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
  updateDemoSettings,
  getDemoStatus,
  getDemoPositions,
  getDemoHistory,
  resetDemoSimulation,
  trainMlModel,
  trainUniversalModel,
  runBacktest,
  checkBackendConnection,
  DemoPosition,
  DemoTrade,
  DemoStatus
} from "./services/bybit";
import { cn } from "@/lib/utils";

export default function App() {
  const [tickers, setTickers] = useState<any[]>([]);
  const [signals, setSignals] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"signals" | "demo" | "training" | "backtest">("signals");
  const [signalsTab, setSignalsTab] = useState<"list" | "settings">("list");
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

  // Demo settings (loaded from backend)
  const [demoSettings, setDemoSettings] = useState({
    capital: 100,
    leverage: 1.0,
    position_size_pct: 10
  });

  // Training state
  const [trainingSymbol, setTrainingSymbol] = useState("BTCUSDT");
  const [trainingModelType, setTrainingModelType] = useState("rf");
  const [trainingResult, setTrainingResult] = useState<any>(null);
  const [isTraining, setIsTraining] = useState(false);

  // Backtest state
  const [backtestSymbol, setBacktestSymbol] = useState("BTCUSDT");
  const [backtestDays, setBacktestDays] = useState(30);
  const [backtestResult, setBacktestResult] = useState<any>(null);
  const [isBacktesting, setIsBacktesting] = useState(false);

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
        setError(null); // Clear any previous errors

        // First check if backend is available
        const isConnected = await checkBackendConnection();
        if (!isConnected) {
          setError("Cannot connect to backend server. Please start the backend server on port 8000.");
          return;
        }

        const data = await fetchTickers();
        const top10 = data
          .filter(t => t.symbol.endsWith("USDT"))
          .sort((a, b) => parseFloat(b.turnover24h) - parseFloat(a.turnover24h))
          .slice(0, 10);
        setTickers(top10);
      } catch (err) {
        console.error("Failed to load market data:", err);
        // Check if it's a connection error
        if (err.message?.includes('Network Error') || err.message?.includes('ECONNREFUSED')) {
          setError("Cannot connect to backend server. Please ensure the backend is running on port 8000.");
        } else {
          setError("Failed to load market data. Please check your internet connection and try again.");
        }
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

      // Sync settings with status
      if (status) {
        setDemoSettings({
          capital: status.capital,
          leverage: status.leverage,
          position_size_pct: status.position_size_pct
        });
      }
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

  const handleUpdateDemoSettings = async (newSettings: Partial<typeof demoSettings>) => {
    setIsDemoLoading(true);
    try {
      // Ensure all values are sent and are numbers
      const updatedSettings = {
        capital: Number(newSettings.capital ?? demoSettings.capital),
        leverage: Number(newSettings.leverage ?? demoSettings.leverage),
        position_size_pct: Number(newSettings.position_size_pct ?? demoSettings.position_size_pct)
      };

      const currentCapital = demoStatus?.capital ?? demoSettings.capital;
      const capitalChanged = updatedSettings.capital !== currentCapital;

      console.log("Updating demo settings:", updatedSettings, "reset_data:", capitalChanged);

      await updateDemoSettings({
        capital: updatedSettings.capital,
        leverage: updatedSettings.leverage,
        position_size_pct: updatedSettings.position_size_pct,
        reset_data: capitalChanged
      });

      // Update local state immediately for better UX
      setDemoSettings(updatedSettings);
      
      if (capitalChanged) {
        setDemoPositions([]);
        setDemoHistory([]);
      }

      // Refresh status from server
      const status = await getDemoStatus();
      setDemoStatus(status);
    } catch (err: any) {
      console.error("Settings update failed:", err);
      const errorMsg = err.response?.data?.detail || err.message || "Unknown error";
      setError(`Failed to update demo settings: ${errorMsg}`);
    } finally {
      setIsDemoLoading(false);
    }
  };

  const handleResetDemo = async () => {
    if (!window.confirm("Are you sure you want to reset all demo data? This will clear all positions and history.")) return;
    
    setIsDemoLoading(true);
    try {
      await resetDemoSimulation();
      
      // Clear local state
      setDemoPositions([]);
      setDemoHistory([]);
      
      // Get fresh status
      const status = await getDemoStatus();
      setDemoStatus(status);
      
      // Update settings UI
      const newSettings = {
        capital: status.capital,
        leverage: status.leverage,
        position_size_pct: status.position_size_pct
      };
      setDemoSettings(newSettings);
      
      // Sync with localStorage
      localStorage.setItem('demoCapital', newSettings.capital.toString());
      localStorage.setItem('demoLeverage', newSettings.leverage.toString());
      localStorage.setItem('demoPositionSizePct', newSettings.position_size_pct.toString());
      
    } catch (err: any) {
      console.error("Reset failed:", err);
      setError(`Failed to reset demo simulation: ${err.message}`);
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

  // Training functions
  const handleTrainModel = async () => {
    if (!trainingSymbol) return;
    setIsTraining(true);
    setTrainingResult(null);
    try {
      const result = await trainMlModel(trainingSymbol, trainingModelType);
      setTrainingResult(result);
    } catch (err: any) {
      console.error(err);
      setError(`Failed to train model: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsTraining(false);
    }
  };

  const handleTrainUniversalModel = async () => {
    setIsTraining(true);
    setTrainingResult(null);
    try {
      const result = await trainUniversalModel();
      setTrainingResult({
        status: result.status,
        accuracy: result.accuracy || 0,
        feature_importance: result.feature_importance || null,
        message: result.message
      });
    } catch (err: any) {
      console.error(err);
      setError(`Failed to train universal model: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsTraining(false);
    }
  };

  const handleRunBacktest = async () => {
    if (!backtestSymbol) return;
    setIsBacktesting(true);
    setBacktestResult(null);
    try {
      const result = await runBacktest(backtestSymbol, backtestDays);
      setBacktestResult(result);
    } catch (err: any) {
      console.error(err);
      setError(`Failed to run backtest: ${err.response?.data?.detail || err.message}`);
    } finally {
      setIsBacktesting(false);
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

              {/* Backtest */}
              <div
                onClick={() => setActiveTab("backtest")}
                className={cn(
                  "flex items-center gap-2 cursor-pointer group transition-all",
                  activeTab === "backtest" ? "opacity-100" : "opacity-40 hover:opacity-80"
                )}
              >
                <div className={cn(
                  "w-2 h-2 rounded-full",
                  activeTab === "backtest" ? "bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.6)]" : "bg-zinc-600"
                )} />
                <span className={cn(
                  "text-xs font-black tracking-widest uppercase transition-colors",
                  activeTab === "backtest" ? "text-zinc-100" : "text-zinc-400 group-hover:text-zinc-200"
                )}>Backtest</span>
              </div>

              <div className="h-4 w-[1px] bg-zinc-800 hidden md:block" />
              <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-[0.2em] hidden lg:block">Market Intelligence Hub</span>
            </div>
          </div>
        </div>

        {/* Action Row */}
        {activeTab === "signals" && (
          <div className="border-t border-zinc-800/30 bg-black/20">
            <div className="container mx-auto px-4 h-14 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <Button
                  onClick={() => setSignalsTab(signalsTab === "list" ? "settings" : "list")}
                  variant="outline"
                  size="sm"
                  className={cn(
                    "border-zinc-800 text-xs font-bold uppercase tracking-wider flex items-center gap-2",
                    signalsTab === "settings" ? "bg-zinc-800 text-orange-500" : "text-zinc-500 hover:text-zinc-200"
                  )}
                >
                  <Settings className="w-4 h-4" />
                  Settings
                </Button>
                {autoScanEnabled && (
                  <div className="flex items-center gap-2 px-3 py-1 bg-orange-500/10 rounded-full border border-orange-500/20">
                    <div className="w-1.5 h-1.5 rounded-full bg-orange-500 animate-pulse" />
                    <span className="text-[10px] font-bold text-orange-500 uppercase tracking-tight">Auto Scan: {autoScanInterval}m</span>
                  </div>
                )}
              </div>
              
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
            {signalsTab === "list" ? (
              <>
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
              </>
            ) : (
              <div className="space-y-6">
                <div className="flex items-center justify-between">
                  <h2 className="text-xl font-bold text-white">Signal Settings</h2>
                  <Button 
                    onClick={() => setSignalsTab("list")}
                    variant="ghost" 
                    size="sm"
                    className="text-zinc-400 hover:text-white"
                  >
                    Back to Signals
                  </Button>
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
              <div className="grid grid-cols-1 md:grid-cols-5 gap-4">
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
                    <div className="text-sm text-zinc-400">Leverage</div>
                    <div className="text-lg font-bold text-purple-500">
                      {demoStatus.leverage?.toFixed(1) || '1.0'}x
                    </div>
                  </CardContent>
                </Card>
                <Card className="bg-zinc-900/50 border-zinc-800">
                  <CardContent className="p-4">
                    <div className="text-sm text-zinc-400">Position Size</div>
                    <div className="text-lg font-bold text-cyan-500">
                      {demoStatus.position_size_pct || 10}%
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

            {/* Quick Demo Settings */}
            <div className="bg-zinc-900/30 rounded-lg p-4 border border-zinc-800/50">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-medium text-zinc-200">Quick Settings</h3>
                <Button
                  onClick={handleResetDemo}
                  disabled={isDemoLoading}
                  variant="outline"
                  size="sm"
                  className="border-zinc-700 text-zinc-400 hover:text-white text-xs"
                >
                  Reset Demo
                </Button>
              </div>

              <div className="grid grid-cols-3 gap-3 mb-3">
                <div>
                  <label className="text-xs text-zinc-400 block mb-1">Leverage</label>
                  <select
                    value={demoSettings.leverage}
                    onChange={(e) => handleUpdateDemoSettings({ leverage: parseFloat(e.target.value) })}
                    disabled={isDemoLoading}
                    className="w-full px-2 py-1 bg-zinc-800 border border-zinc-700 rounded text-zinc-200 text-xs focus:outline-none focus:ring-1 focus:ring-orange-500"
                  >
                    <option value="1">1x</option>
                    <option value="2">2x</option>
                    <option value="5">5x</option>
                    <option value="10">10x</option>
                    <option value="25">25x</option>
                    <option value="50">50x</option>
                    <option value="100">100x</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-zinc-400 block mb-1">Position Size</label>
                  <select
                    value={demoSettings.position_size_pct}
                    onChange={(e) => handleUpdateDemoSettings({ position_size_pct: parseInt(e.target.value) })}
                    disabled={isDemoLoading}
                    className="w-full px-2 py-1 bg-zinc-800 border border-zinc-700 rounded text-zinc-200 text-xs focus:outline-none focus:ring-1 focus:ring-orange-500"
                  >
                    <option value="5">5%</option>
                    <option value="10">10%</option>
                    <option value="25">25%</option>
                    <option value="50">50%</option>
                    <option value="100">100%</option>
                  </select>
                </div>

                <div>
                  <label className="text-xs text-zinc-400 block mb-1">Capital</label>
                  <select
                    value={demoSettings.capital}
                    onChange={(e) => handleUpdateDemoSettings({ capital: parseInt(e.target.value), reset_data: true })}
                    disabled={isDemoLoading}
                    className="w-full px-2 py-1 bg-zinc-800 border border-zinc-700 rounded text-zinc-200 text-xs focus:outline-none focus:ring-1 focus:ring-orange-500"
                  >
                    <option value="50">$50</option>
                    <option value="100">$100</option>
                    <option value="250">$250</option>
                    <option value="500">$500</option>
                    <option value="1000">$1000</option>
                  </select>
                </div>
              </div>

              <div className="text-xs text-zinc-500">
                Max Position: ${(demoSettings.capital * demoSettings.position_size_pct / 100 * demoSettings.leverage).toFixed(2)} USDT |
                Effective Capital: ${(demoSettings.capital * demoSettings.leverage).toFixed(0)} USDT
              </div>
            </div>

            <div className="text-center text-zinc-500 text-sm">
              <p>Demo simulation uses 100 USDT capital and automatically executes signals with ≥60% confidence from Signals tab</p>
              <p>Positions update automatically when scanning signals • Uses real Bybit market data</p>
            </div>
          </div>
        )}

        {activeTab === "training" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">AI Training & Backtesting Center</h2>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Machine Learning Training */}
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <Brain className="w-5 h-5" />
                    Train ML Model
                  </CardTitle>
                  <CardDescription>Auto-train AI on top market data to adapt to current conditions</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="flex flex-col gap-4">
                    <div className="bg-zinc-800/30 p-4 rounded-lg border border-zinc-800 text-sm text-zinc-400">
                      <p className="mb-2"><strong>Smart Training Pipeline:</strong></p>
                      <ul className="list-disc pl-4 space-y-1">
                        <li>Fetches latest 4-month data of Top 5 liquidity coins.</li>
                        <li>Generates 20 institutional-grade features (Funding Rate, OI, CMF, etc).</li>
                        <li>Trains an advanced Ensemble Model (Random Forest + Gradient Boosting).</li>
                        <li>Creates a Universal Brain capable of predicting any coin's trend.</li>
                      </ul>
                    </div>
                    <Button
                      onClick={handleTrainUniversalModel}
                      disabled={isTraining}
                      className="w-full bg-gradient-to-r from-orange-500 to-amber-500 hover:from-orange-600 hover:to-amber-600 text-white shadow-lg shadow-orange-500/20 h-14 text-base font-black tracking-widest uppercase"
                    >
                      {isTraining ? (
                        <>
                          <RefreshCw className="w-6 h-6 mr-3 animate-spin" />
                          TRAINING AI MODEL (PLEASE WAIT ~30S)...
                        </>
                      ) : (
                        <>
                          <Brain className="w-6 h-6 mr-3" />
                          START AI TRAINING
                        </>
                      )}
                    </Button>
                  </div>

                  {/* Training Results */}
                  {trainingResult && (
                    <div className="bg-zinc-800/50 rounded-lg p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-zinc-400">Status</span>
                        <Badge className="bg-green-500/20 text-green-500 border-green-500/30">
                          {trainingResult.status}
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-zinc-400">Accuracy</span>
                        <span className="text-sm font-bold text-white">
                          {(trainingResult.accuracy * 100).toFixed(2)}%
                        </span>
                      </div>
                      
                      {trainingResult.feature_importance && (
                        <div className="space-y-2 pt-2 border-t border-zinc-700">
                          <span className="text-xs text-zinc-400 font-medium">Top Features</span>
                          <div className="space-y-1">
                            {Object.entries(trainingResult.feature_importance)
                              .sort(([,a]: any, [,b]: any) => b - a)
                              .slice(0, 3)
                              .map(([feature, importance]: any) => (
                                <div key={feature} className="flex items-center justify-between text-xs">
                                  <span className="text-zinc-300">{feature.replace(/_/g, ' ')}</span>
                                  <span className="text-zinc-500">{(importance * 100).toFixed(1)}%</span>
                                </div>
                              ))
                            }
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>


            </div>
            
            <div className="text-center text-zinc-500 text-sm">
              <p>Training generates new models based on historical patterns to improve prediction accuracy.</p>
            </div>
          </div>
        )}

        {/* Backtest Tab */}
        {activeTab === "backtest" && (
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-xl font-bold text-white">Historical Backtesting</h2>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Historical Backtesting */}
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <History className="w-5 h-5" />
                    Historical Backtest
                  </CardTitle>
                  <CardDescription>Test the AI trading logic on historical data</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <label className="text-sm font-medium text-zinc-200">Symbol</label>
                      <select
                        value={backtestSymbol}
                        onChange={(e) => setBacktestSymbol(e.target.value)}
                        disabled={isBacktesting}
                        className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                      >
                        {tickers.length > 0 ? (
                          tickers.map(t => (
                            <option key={t.symbol} value={t.symbol}>{t.symbol}</option>
                          ))
                        ) : (
                          <option value="BTCUSDT">BTCUSDT</option>
                        )}
                      </select>
                    </div>

                    <div className="space-y-2">
                      <label className="text-sm font-medium text-zinc-200">Timeframe (Days)</label>
                      <input
                        type="number"
                        min="1"
                        max="90"
                        value={backtestDays}
                        onChange={(e) => setBacktestDays(parseInt(e.target.value) || 30)}
                        disabled={isBacktesting}
                        className="w-full px-3 py-2 bg-zinc-800 border border-zinc-700 rounded-lg text-zinc-200 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500"
                      />
                    </div>
                  </div>

                  <Button
                    onClick={handleRunBacktest}
                    disabled={isBacktesting}
                    className="w-full bg-blue-600 hover:bg-blue-700 text-white"
                  >
                    {isBacktesting ? (
                      <>
                        <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                        Running Backtest...
                      </>
                    ) : (
                      <>
                        <Activity className="w-4 h-4 mr-2" />
                        Run Backtest
                      </>
                    )}
                  </Button>

                  {/* Backtest Results */}
                  {backtestResult && backtestResult.metrics && (
                    <div className="bg-zinc-800/50 rounded-lg p-4 space-y-4">
                      <div className="grid grid-cols-2 gap-3">
                        <div className="space-y-1">
                          <span className="text-xs text-zinc-500">Win Rate</span>
                          <div className={`text-lg font-bold ${(backtestResult.metrics.win_rate || 0) >= 50 ? 'text-green-500' : 'text-red-500'}`}>
                            {(backtestResult.metrics.win_rate || 0).toFixed(1)}%
                          </div>
                        </div>
                        <div className="space-y-1">
                          <span className="text-xs text-zinc-500">Total Profit</span>
                          <div className={`text-lg font-bold ${(backtestResult.metrics.total_profit || 0) >= 0 ? 'text-green-500' : 'text-red-500'}`}>
                            {(backtestResult.metrics.total_profit || 0) > 0 ? '+' : ''}{(backtestResult.metrics.total_profit || 0).toFixed(2)}
                          </div>
                        </div>
                        <div className="space-y-1">
                          <span className="text-xs text-zinc-500">Total Trades</span>
                          <div className="text-sm font-medium text-white">
                            {backtestResult.metrics.total_trades || 0} ({(backtestResult.metrics.winning_trades || 0)}W / {(backtestResult.metrics.losing_trades || 0)}L)
                          </div>
                        </div>
                        <div className="space-y-1">
                          <span className="text-xs text-zinc-500">Profit Factor</span>
                          <div className="text-sm font-medium text-white">
                            {backtestResult.metrics.profit_factor === 'inf' ? 'INF' : typeof backtestResult.metrics.profit_factor === 'number' ? backtestResult.metrics.profit_factor.toFixed(2) : (backtestResult.metrics.profit_factor || 0)}
                          </div>
                        </div>
                        <div className="space-y-1">
                          <span className="text-xs text-zinc-500">Max Drawdown</span>
                          <div className="text-sm font-medium text-red-400">
                            {(backtestResult.metrics.max_drawdown || 0).toFixed(2)}%
                          </div>
                        </div>
                        <div className="space-y-1">
                          <span className="text-xs text-zinc-500">Avg Profit/Trade</span>
                          <div className={`text-sm font-medium ${(backtestResult.metrics.avg_profit_per_trade || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                            {(backtestResult.metrics.avg_profit_per_trade || 0) > 0 ? '+' : ''}{(backtestResult.metrics.avg_profit_per_trade || 0).toFixed(2)}
                          </div>
                        </div>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Backtest History/Results */}
              <Card className="bg-zinc-900/50 border-zinc-800">
                <CardHeader>
                  <CardTitle className="text-white flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Backtest Results
                  </CardTitle>
                  <CardDescription>View and analyze historical backtest performance</CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="text-center text-zinc-400 py-8">
                    <BarChart3 className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p className="text-sm">Backtest results will appear here</p>
                    <p className="text-xs text-zinc-500 mt-2">Run a backtest to see detailed analysis</p>
                  </div>

                  {/* Future: Add backtest history list here */}
                </CardContent>
              </Card>
            </div>

            <div className="text-center text-zinc-500 text-sm">
              <p>Backtesting simulates past trading performance to evaluate strategy effectiveness.</p>
              <p>Use historical data to optimize parameters and validate trading signals.</p>
            </div>
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

