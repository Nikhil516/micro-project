import { useEffect, useState } from "react";
import client from "../api/client.js";
import { useToast } from "../context/ToastContext.jsx";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

const empty = {
  name: "",
  category: "dress",
  colour: "black",
  pattern: "solid",
  sleeve_type: "sleeveless",
  description: "",
};

export default function Products() {
  const { push } = useToast();
  const [items, setItems] = useState([]);
  const [form, setForm] = useState(empty);
  const [editing, setEditing] = useState(null);

  const load = () => client.get("/api/products").then((r) => setItems(r.data));
  useEffect(() => {
    load().catch(() => push("Failed to load products", "error"));
  }, []);

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editing) {
        await client.patch(`/api/products/${editing}`, form);
      } else {
        await client.post("/api/products", form);
      }
      setForm(empty);
      setEditing(null);
      await load();
      push("Product saved");
    } catch {
      push("Save failed", "error");
    }
  };

  const remove = async (id) => {
    if (!confirm("Delete this product?")) return;
    await client.delete(`/api/products/${id}`);
    await load();
  };

  const onFile = async (id, file) => {
    const data = new FormData();
    data.append("file", file);
    await client.post(`/api/products/${id}/image`, data);
    await load();
  };

  return (
    <div className="grid gap-6 lg:grid-cols-[340px_1fr]">
      <form className="card p-5" onSubmit={save}>
        <h1 className="font-display text-3xl">{editing ? "Edit product" : "Add product"}</h1>
        {Object.keys(empty).map((k) => (
          <div key={k} className="mt-3">
            <label className="text-xs uppercase tracking-wide text-stone-500">{k.replace("_", " ")}</label>
            {k === "description" ? (
              <textarea className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2" value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
            ) : (
              <input className="mt-1 w-full rounded-lg border border-stone-300 px-3 py-2" value={form[k]} onChange={(e) => setForm({ ...form, [k]: e.target.value })} />
            )}
          </div>
        ))}
        <button className="mt-4 w-full rounded-lg bg-stone-900 py-2 text-white">Save</button>
      </form>
      <div className="card overflow-hidden">
        {items.length === 0 ? (
          <p className="p-8 text-stone-500">No products yet. Add one or run the seed script.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-stone-50 text-stone-500">
                <tr>
                  <th className="px-4 py-3">Product</th>
                  <th>Category</th>
                  <th>Colour</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {items.map((p) => (
                  <tr key={p.product_id} className="border-t border-stone-100">
                    <td className="px-4 py-3">
                      {p.image_url ? (
                        <img
                          src={p.image_url.startsWith("http") ? p.image_url : `${API_URL}${p.image_url}`}
                          alt={p.name}
                          className="mb-2 h-16 w-16 rounded-lg object-cover"
                        />
                      ) : null}
                      <p className="font-medium">{p.name}</p>
                      <p className="text-xs text-stone-400">{p.product_id}</p>
                      {p.has_history ? null : <p className="text-xs text-rose-800">cold-start</p>}
                    </td>
                    <td className="capitalize">{p.category}</td>
                    <td>{p.colour}</td>
                    <td className="space-x-2 px-3 py-2 text-right">
                      <label className="cursor-pointer text-xs text-rose-800">
                        Image
                        <input type="file" className="hidden" onChange={(e) => e.target.files[0] && onFile(p.product_id, e.target.files[0])} />
                      </label>
                      <button className="text-xs" onClick={() => { setEditing(p.product_id); setForm(p); }}>
                        Edit
                      </button>
                      <button className="text-xs text-rose-800" onClick={() => remove(p.product_id)}>
                        Delete
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
