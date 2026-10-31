import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import client from "../api/client.js";

export default function Analytics() {
  const [pack, setPack] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      client.get("/api/analytics/weekly-trend"),
      client.get("/api/analytics/categories"),
      client.get("/api/analytics/trends"),
      client.get("/api/analytics/weather"),
      client.get("/api/analytics/festivals"),
      client.get("/api/analytics/inventory-risk"),
      client.get("/api/analytics/momentum"),
    ])
      .then(([w, c, t, weather, f, risk, m]) =>
        setPack({
          weekly: w.data,
          categories: c.data,
          trends: t.data,
          weather: weather.data,
          festivals: f.data,
          risk: risk.data,
          momentum: m.data,
        })
      )
      .catch(() => setError("Analytics unavailable."));
  }, []);

  if (error) return <p className="text-rose-800">{error}</p>;
  if (!pack) return <p className="text-stone-500">Loading analytics…</p>;

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Trend analytics</h1>
      <div className="grid gap-4 lg:grid-cols-2">
        <ChartCard title="Weekly demand">
          <LineChart data={pack.weekly}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="week_start" hide />
            <YAxis />
            <Tooltip />
            <Line dataKey="units" stroke="#9a4a4a" dot={false} />
          </LineChart>
        </ChartCard>
        <ChartCard title="Category sales">
          <BarChart data={pack.categories}>
            <XAxis dataKey="category" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="units" fill="#1c1917" />
          </BarChart>
        </ChartCard>
        <ChartCard title="Google Trends (if seeded)">
          {pack.trends.available ? (
            <LineChart data={pack.trends.series.filter((s) => s.keyword === pack.trends.series[0]?.keyword)}>
              <XAxis dataKey="week_start" hide />
              <YAxis />
              <Tooltip />
              <Line dataKey="interest" stroke="#9a4a4a" dot={false} />
            </LineChart>
          ) : (
            <p className="p-6 text-sm text-stone-500">Google Trends was not available during acquisition. No fabricated series is shown.</p>
          )}
        </ChartCard>
        <ChartCard title="London weather (Open-Meteo)">
          {pack.weather.available ? (
            <LineChart data={pack.weather.series}>
              <XAxis dataKey="date" hide />
              <YAxis />
              <Tooltip />
              <Line dataKey="temperature" stroke="#1c1917" dot={false} />
            </LineChart>
          ) : (
            <p className="p-6 text-sm text-stone-500">Weather collection is empty until you seed after training.</p>
          )}
        </ChartCard>
      </div>
      <div className="card p-5">
        <h2 className="font-medium">Festival calendar (UK holidays)</h2>
        <p className="mt-2 text-sm text-stone-500">{pack.festivals.length} holiday dates stored.</p>
      </div>
      <div className="card p-5">
        <h2 className="font-medium">Demand momentum</h2>
        <ul className="mt-3 grid gap-2 md:grid-cols-2">
          {pack.momentum.map((m) => (
            <li key={m.product_id} className="flex justify-between text-sm">
              <span className="truncate pr-2">{m.product_id}</span>
              <span className={m.direction === "increasing" ? "text-emerald-700" : m.direction === "decreasing" ? "text-rose-800" : ""}>
                {m.direction} ({m.delta.toFixed(1)})
              </span>
            </li>
          ))}
        </ul>
      </div>
      <div className="card p-5">
        <h2 className="font-medium">Inventory risk flags</h2>
        <p className="text-xs text-stone-500">These are indicators, not replenishment orders.</p>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="text-stone-500">
                <th className="py-2">Product</th>
                <th>On hand</th>
                <th>Next week fcst</th>
                <th>Flags</th>
              </tr>
            </thead>
            <tbody>
              {pack.risk.slice(0, 30).map((r) => (
                <tr key={r.product_id} className="border-t border-stone-100">
                  <td className="py-2">{r.name || r.product_id}</td>
                  <td>{r.on_hand}</td>
                  <td>{r.next_week_forecast}</td>
                  <td>
                    {[r.potential_stockout && "stockout", r.low_demand && "low", r.high_demand && "high", r.unusual_change && "unusual"]
                      .filter(Boolean)
                      .join(", ")}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function ChartCard({ title, children }) {
  return (
    <div className="card p-5">
      <h2 className="mb-3 font-medium">{title}</h2>
      <div className="h-64">
        <ResponsiveContainer>{children}</ResponsiveContainer>
      </div>
    </div>
  );
}
