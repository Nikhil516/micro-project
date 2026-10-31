import { useEffect, useState } from "react";
import client from "../api/client.js";
import { useToast } from "../context/ToastContext.jsx";

export default function Sales() {
  const { push } = useToast();
  const [rows, setRows] = useState([]);
  const [weekly, setWeekly] = useState([]);
  const [form, setForm] = useState({ product_id: "", date: "", quantity: "" });
  const [filter, setFilter] = useState({ product_id: "", start: "", end: "" });

  const load = async () => {
    const params = {};
    if (filter.product_id) params.product_id = filter.product_id;
    if (filter.start) params.start = filter.start;
    if (filter.end) params.end = filter.end;
    const [s, w] = await Promise.all([client.get("/api/sales", { params }), client.get("/api/sales/weekly", { params: { product_id: filter.product_id || undefined } })]);
    setRows(s.data);
    setWeekly(w.data.slice(-40));
  };

  useEffect(() => {
    load().catch(() => push("Sales load failed", "error"));
  }, []);

  const add = async (e) => {
    e.preventDefault();
    await client.post("/api/sales", { ...form, quantity: Number(form.quantity) });
    push("Sale added");
    await load();
  };

  const upload = async (file) => {
    const data = new FormData();
    data.append("file", file);
    const res = await client.post("/api/sales/upload", data);
    push(`Inserted ${res.data.inserted} rows`);
    await load();
  };

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Sales</h1>
      <form className="card grid gap-3 p-5 md:grid-cols-4" onSubmit={add}>
        <input placeholder="product_id" className="rounded-lg border border-stone-300 px-3 py-2" value={form.product_id} onChange={(e) => setForm({ ...form, product_id: e.target.value })} />
        <input type="date" className="rounded-lg border border-stone-300 px-3 py-2" value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} />
        <input placeholder="quantity" className="rounded-lg border border-stone-300 px-3 py-2" value={form.quantity} onChange={(e) => setForm({ ...form, quantity: e.target.value })} />
        <button className="rounded-lg bg-stone-900 text-white">Add record</button>
      </form>
      <div className="card flex flex-wrap gap-3 p-5">
        <input placeholder="Filter product" className="rounded-lg border border-stone-300 px-3 py-2" value={filter.product_id} onChange={(e) => setFilter({ ...filter, product_id: e.target.value })} />
        <input type="date" className="rounded-lg border border-stone-300 px-3 py-2" value={filter.start} onChange={(e) => setFilter({ ...filter, start: e.target.value })} />
        <input type="date" className="rounded-lg border border-stone-300 px-3 py-2" value={filter.end} onChange={(e) => setFilter({ ...filter, end: e.target.value })} />
        <button className="rounded-lg border px-3" onClick={load} type="button">
          Apply
        </button>
        <label className="cursor-pointer rounded-lg bg-white px-3 py-2 text-sm ring-1 ring-stone-300">
          Upload CSV
          <input type="file" className="hidden" accept=".csv" onChange={(e) => e.target.files[0] && upload(e.target.files[0])} />
        </label>
      </div>
      <div className="card p-5">
        <h2 className="font-medium">Weekly summaries</h2>
        <p className="text-sm text-stone-500">{weekly.length} week rows</p>
      </div>
      <div className="card overflow-x-auto">
        <table className="w-full text-left text-sm">
          <thead className="bg-stone-50">
            <tr>
              <th className="px-4 py-2">Date</th>
              <th>Product</th>
              <th>Qty</th>
            </tr>
          </thead>
          <tbody>
            {rows.slice(0, 100).map((r) => (
              <tr key={r.id} className="border-t border-stone-100">
                <td className="px-4 py-2">{r.date}</td>
                <td>{r.product_id}</td>
                <td>{r.quantity}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 ? <p className="p-6 text-stone-500">No sales match the filter.</p> : null}
      </div>
    </div>
  );
}
