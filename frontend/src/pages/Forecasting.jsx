import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import client from "../api/client.js";
import { useToast } from "../context/ToastContext.jsx";

export default function Forecasting() {
  const { push } = useToast();
  const [products, setProducts] = useState([]);
  const [productId, setProductId] = useState("");
  const [horizon, setHorizon] = useState(4);
  const [result, setResult] = useState(null);
  const [compare, setCompare] = useState(null);

  useEffect(() => {
    client.get("/api/products").then((r) => {
      setProducts(r.data);
      if (r.data[0]) setProductId(r.data[0].product_id);
    });
  }, []);

  const run = async () => {
    try {
      const res = await client.post("/api/forecasts/predict", {
        product_id: productId,
        horizon_weeks: Number(horizon),
      });
      setResult(res.data.results[0]);
      const cmp = await client.get(`/api/forecasts/compare/${productId}`);
      setCompare(cmp.data);
      push("Forecast generated");
    } catch (err) {
      push(err.response?.data?.detail || "Forecast failed", "error");
    }
  };

  const chartData = [
    ...(compare?.history || []).map((h) => ({ week: h.date, actual: h.quantity })),
    ...(result?.forecasts || []).map((f) => ({ week: f.week_start, predicted: f.predicted_units })),
  ];

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Weekly demand forecast</h1>
      <div className="card flex flex-wrap items-end gap-4 p-5">
        <label className="text-sm">
          Product
          <select className="mt-1 block rounded-lg border border-stone-300 px-3 py-2" value={productId} onChange={(e) => setProductId(e.target.value)}>
            {products.map((p) => (
              <option key={p.product_id} value={p.product_id}>
                {p.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm">
          Horizon (weeks)
          <input type="number" min="1" max="12" className="mt-1 block rounded-lg border border-stone-300 px-3 py-2" value={horizon} onChange={(e) => setHorizon(e.target.value)} />
        </label>
        <button onClick={run} className="rounded-lg bg-stone-900 px-4 py-2 text-white">
          Generate
        </button>
      </div>
      {result ? (
        <div className="grid gap-4 lg:grid-cols-3">
          <div className="card p-5 lg:col-span-2">
            <h2 className="font-medium">History vs predicted</h2>
            <div className="h-80">
              <ResponsiveContainer>
                <LineChart data={chartData}>
                  <XAxis dataKey="week" hide />
                  <YAxis />
                  <Tooltip />
                  <Line dataKey="actual" stroke="#1c1917" dot={false} />
                  <Line dataKey="predicted" stroke="#9a4a4a" />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
          <div className="card p-5 text-sm">
            <p className="font-medium">Prediction notes</p>
            <p className="mt-2">Method: {result.forecasts[0]?.method}</p>
            <p>Cold start: {result.cold_start ? "yes" : "no"}</p>
            {result.cold_start_note ? <p className="mt-2 text-stone-500">{result.cold_start_note}</p> : null}
            <p className="mt-4 font-medium">Global feature importance</p>
            <ul className="mt-2 space-y-1">
              {Object.entries(result.explainability.top_features || {}).map(([k, v]) => (
                <li key={k} className="flex justify-between gap-3">
                  <span className="truncate">{k}</span>
                  <span>{Number(v).toFixed(3)}</span>
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-stone-400">{result.explainability.caveat}</p>
          </div>
        </div>
      ) : (
        <p className="text-stone-500">Select a product and generate a weekly forecast.</p>
      )}
    </div>
  );
}
