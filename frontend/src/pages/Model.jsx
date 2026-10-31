import { useEffect, useState } from "react";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import client from "../api/client.js";

export default function Model() {
  const [info, setInfo] = useState(null);

  useEffect(() => {
    client.get("/api/model/info").then((r) => setInfo(r.data));
  }, []);

  if (!info) return <p>Loading model metadata…</p>;
  const metrics = info.metrics;
  const importance = Object.entries(info.feature_importance || {})
    .slice(0, 15)
    .map(([name, value]) => ({ name, value }));

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Model performance</h1>
      <p className="text-sm text-stone-500">{info.disclaimer}</p>
      <div className="grid gap-4 md:grid-cols-4">
        <Stat label="Status" value={info.status} />
        <Stat label="Version" value={info.model_version || "—"} />
        <Stat label="Trained" value={info.trained_at ? info.trained_at.slice(0, 19) : "—"} />
        <Stat label="ResNet-50" value={info.resnet50?.architecture || "not loaded"} />
      </div>
      {metrics ? (
        <div className="grid gap-4 md:grid-cols-3">
          <Stat label="MAE" value={Number(metrics.mae).toFixed(3)} />
          <Stat label="RMSE" value={Number(metrics.rmse).toFixed(3)} />
          <Stat label="WAPE" value={Number(metrics.wape).toFixed(3)} />
        </div>
      ) : (
        <p className="card p-5 text-stone-500">
          No evaluation metrics found. Train the pipeline so MAE/RMSE/WAPE can be displayed from disk — values are never invented.
        </p>
      )}
      {info.baseline_metrics ? (
        <p className="text-sm text-stone-500">
          Lag-1 baseline MAE {Number(info.baseline_metrics.mae).toFixed(3)} · RMSE {Number(info.baseline_metrics.rmse).toFixed(3)} · WAPE{" "}
          {Number(info.baseline_metrics.wape).toFixed(3)}
        </p>
      ) : null}
      <div className="card p-5">
        <h2 className="font-medium">Feature importance</h2>
        <div className="h-80">
          <ResponsiveContainer>
            <BarChart data={importance} layout="vertical">
              <XAxis type="number" />
              <YAxis type="category" dataKey="name" width={140} tick={{ fontSize: 10 }} />
              <Tooltip />
              <Bar dataKey="value" fill="#9a4a4a" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div className="card p-5">
      <p className="text-xs uppercase tracking-wide text-stone-500">{label}</p>
      <p className="mt-2 break-all font-display text-3xl">{value}</p>
    </div>
  );
}
