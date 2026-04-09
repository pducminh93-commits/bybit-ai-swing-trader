import axios from "axios";

export interface Kline {
  startTime: string;
  open: string;
  high: string;
  low: string;
  close: string;
  volume: string;
  turnover: string;
}

export const fetchKlines = async (symbol: string, interval: string = "240"): Promise<Kline[]> => {
  const response = await axios.get("http://localhost:8000/api/bybit/kline", {
    params: { symbol, interval, limit: "200" },
  });

  if (response.data.retCode !== 0) {
    throw new Error(response.data.retMsg || "Failed to fetch klines");
  }

  return response.data.result.list.map((item: any) => ({
    startTime: item[0],
    open: item[1],
    high: item[2],
    low: item[3],
    close: item[4],
    volume: item[5],
    turnover: item[6],
  })).reverse(); // Bybit returns newest first, we want oldest first for charts
};

export const fetchTickers = async (): Promise<any[]> => {
  const response = await axios.get("http://localhost:8000/api/bybit/tickers");
  if (response.data.retCode !== 0) {
    throw new Error(response.data.retMsg || "Failed to fetch tickers");
  }
  return response.data.result.list;
};

export interface Signal {
  symbol: string;
  signal: string;
  confidence: number;
  reason: string;
  take_profit: number;
  stop_loss: number;
  indicators?: any;
  timestamp?: string;
}

export const fetchSignals = async (symbols?: string): Promise<Signal[]> => {
  const response = await axios.get("http://localhost:8000/api/signals", {
    params: { symbols },
  });
  return response.data;
};

export const fetchSignal = async (symbol: string): Promise<Signal> => {
  const response = await axios.get(`http://localhost:8000/api/signals/${symbol}`);
  return response.data;
};

// Demo Trading API
export interface DemoPosition {
  symbol: string;
  side: string;
  entry_price: number;
  current_price: number;
  quantity: number;
  entry_time: string;
  unrealized_pnl: number;
  pnl_percentage: number;
}

export interface DemoTrade {
  symbol: string;
  side: string;
  entry_price: number;
  exit_price: number;
  quantity: number;
  entry_time: string;
  exit_time: string;
  realized_pnl: number;
  pnl_percentage: number;
}

export interface DemoStatus {
  is_running: boolean;
  balance: number;
  capital: number;
  leverage: number;
  position_size_pct: number;
  total_positions: number;
  total_trades: number;
}

export const startDemoSimulation = async (): Promise<{status: string; message: string}> => {
  const response = await axios.post("http://localhost:8000/api/demo/start");
  return response.data;
};

export const stopDemoSimulation = async (): Promise<{status: string; message: string}> => {
  const response = await axios.post("http://localhost:8000/api/demo/stop");
  return response.data;
};

export const processDemoSignals = async (signals: Signal[]): Promise<{executed_trades: any[]; count: number}> => {
  const response = await axios.post("http://localhost:8000/api/demo/process-signals", signals);
  return response.data;
};

export const getDemoStatus = async (): Promise<DemoStatus> => {
  const response = await axios.get("http://localhost:8000/api/demo/status");
  return response.data;
};

export const getDemoPositions = async (): Promise<{positions: DemoPosition[]; count: number}> => {
  const response = await axios.get("http://localhost:8000/api/demo/positions");
  return response.data;
};

export const getDemoHistory = async (): Promise<{history: DemoTrade[]; count: number}> => {
  const response = await axios.get("http://localhost:8000/api/demo/history");
  return response.data;
};

export const updateDemoSettings = async (settings: {
  capital?: number;
  leverage?: number;
  position_size_pct?: number;
  reset_data?: boolean;
}): Promise<{status: string; settings: any}> => {
  const response = await axios.post("http://localhost:8000/api/demo/settings", settings);
  return response.data;
};

export const resetDemoSimulation = async (): Promise<{status: string; message: string}> => {
  const response = await axios.post("http://localhost:8000/api/demo/reset");
  return response.data;
};
