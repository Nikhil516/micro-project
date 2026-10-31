import { useEffect, useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import client from "../api/client.js";
import Skeleton from "../components/Skeleton.jsx";

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([
      client.get("/api/analytics/overview"),
      client.get("/api/analytics/weekly-trend"),
      client.get("/api/analytics/demand-extremes"),
      client.get("/api/analytics/categories"),
      client.get("/api/forecasts"),
    ])
      .then(([o, w, e, c, f]) => {
        setData({
          overview: o.data,
          weekly: w.data,
          extremes: e.data,
          categories: c.data,
          forecasts: f.data.slice(0, 6),
        });
      })
      .catch(() => setError("Could not load dashboard. Check the API and MongoDB connection."));
  }, []);

  if (error) return <Empty message={error} />;
  if (!data) {
    return (
      <div className="grid gap-4 md:grid-cols-4">
        <Skeleton />
        <Skeleton />
        <Skeleton />
        <Skeleton />
      </div>
    );
  }

  const cards = [
    ["Products", data.overview.total_products],
    ["Historical units", Math.round(data.overview.total_historical_units)],
    ["Upcoming predicted units", Math.round(data.overview.predicted_upcoming_demand)],
    ["Forecast runs", data.overview.forecast_runs],
  ];

  return (
    <div className="space-y-6">
      <header>
        <h1 className="font-display text-4xl">Demand overview</h1>
        <p className="text-stone-500">Weekly units from aligned UCI fashion sales and catalog images.</p>
      </header>
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {cards.map(([label, value]) => (
          <div key={label} className="card p-5">
            <p className="text-xs uppercase tracking-wide text-stone-500">{label}</p>
            <p className="mt-2 font-display text-4xl">{value}</p>
          </div>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-3">
        <div className="card p-5 lg:col-span-2">
          <h2 className="font-medium">Weekly demand</h2>
          {data.weekly.length === 0 ? (
            <Empty message="No sales yet. Seed the database after training." />
          ) : (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.weekly}>
                  <XAxis dataKey="week_start" hide />
                  <YAxis />
                  <Tooltip />
                  <Line type="monotone" dataKey="units" stroke="#9a4a4a" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
        <div className="card p-5">
          <h2 className="font-medium">Trending categories</h2>
          <ul className="mt-3 space-y-2 text-sm">
            {data.categories.slice(0, 8).map((c) => (
              <li key={c.category} className="flex justify-between">
                <span className="capitalize">{c.category}</span>
                <span>{Math.round(c.units)}</span>
              </li>
            ))}
            {data.categories.length === 0 ? <Empty message="No category totals yet." /> : null}
          </ul>
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <Box title="High demand" items={data.extremes.high_demand} />
        <Box title="Low demand" items={data.extremes.low_demand} />
      </div>
      <div className="card p-5">
        <h2 className="font-medium">Recent forecasts</h2>
        {data.forecasts.length === 0 ? (
          <Empty message="No forecast runs stored yet." />
        ) : (
          <ul className="mt-3 divide-y divide-stone-100 text-sm">
            {data.forecasts.map((f) => (
              <li key={f.id} className="flex justify-between py-2">
                <span>{f.product_id}</span>
                <span className="text-stone-500">{f.cold_start ? "cold-start" : "history"}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

function Box({ title, items }) {
  return (
    <div className="card p-5">
      <h2 className="font-medium">{title}</h2>
      <ul className="mt-3 space-y-2 text-sm">
        {(items || []).map((i) => (
          <li key={i._id} className="flex justify-between">
            <span className="truncate pr-4">{i._id}</span>
            <span>{Math.round(i.units)}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

function Empty({ message }) {
  return <p className="mt-6 text-sm text-stone-500">{message}</p>;
}
