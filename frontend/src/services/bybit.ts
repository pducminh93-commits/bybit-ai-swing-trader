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
