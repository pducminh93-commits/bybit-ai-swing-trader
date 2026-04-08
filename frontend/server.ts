import express from "express";
import { createServer as createViteServer } from "vite";
import path from "path";
import axios from "axios";

async function startServer() {
  const app = express();
  const PORT = process.env.PORT ? parseInt(process.env.PORT) : 3000;

  app.use(express.json());

  // Bybit Proxy API
  app.get("/api/bybit/kline", async (req, res) => {
    try {
      const { symbol, interval, limit } = req.query;
      const response = await axios.get("https://api.bybit.com/v5/market/kline", {
        params: {
          category: "linear",
          symbol: symbol || "BTCUSDT",
          interval: interval || "240", // 4h for swing trading
          limit: limit || "100",
        },
      });
      res.json(response.data);
    } catch (error: any) {
      console.error("Bybit API Error:", error.message);
      res.status(500).json({ error: "Failed to fetch data from Bybit" });
    }
  });

  // Get current tickers
  app.get("/api/bybit/tickers", async (req, res) => {
    try {
      const response = await axios.get("https://api.bybit.com/v5/market/tickers", {
        params: {
          category: "linear",
        },
      });
      res.json(response.data);
    } catch (error: any) {
      res.status(500).json({ error: "Failed to fetch tickers" });
    }
  });

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true, hmr: { port: 24679 } },
      appType: "spa",
      root: path.join(process.cwd(), "src"),
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), "dist");
    app.use(express.static(distPath));
    app.get("*", (req, res) => {
      res.sendFile(path.join(distPath, "index.html"));
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Server running on http://localhost:${PORT}`);
  });
}

startServer();
