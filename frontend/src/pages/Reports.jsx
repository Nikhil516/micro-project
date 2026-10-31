import client from "../api/client.js";

export default function Reports() {
  const api = import.meta.env.VITE_API_URL || "http://localhost:8000";
  const token = localStorage.getItem("token");

  const download = async (path, filename) => {
    const res = await client.get(path, { responseType: "blob" });
    const url = URL.createObjectURL(res.data);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      <h1 className="font-display text-4xl">Reports</h1>
      <div className="grid gap-4 md:grid-cols-2">
        <div className="card p-6">
          <h2 className="font-medium">Forecast CSV</h2>
          <p className="mt-2 text-sm text-stone-500">All stored weekly predictions.</p>
          <button className="mt-4 rounded-lg bg-stone-900 px-4 py-2 text-white" onClick={() => download("/api/reports/forecasts.csv", "forecasts.csv")}>
            Download CSV
          </button>
        </div>
        <div className="card p-6">
          <h2 className="font-medium">Forecast PDF</h2>
          <p className="mt-2 text-sm text-stone-500">Printable summary with hold-out metrics if the model is loaded.</p>
          <button className="mt-4 rounded-lg bg-stone-900 px-4 py-2 text-white" onClick={() => download("/api/reports/forecasts.pdf", "forecasts.pdf")}>
            Download PDF
          </button>
        </div>
      </div>
      <p className="text-xs text-stone-400">
        Direct URL (authenticated via header in-app): {api}/api/reports/forecasts.csv token={token ? "present" : "missing"}
      </p>
    </div>
  );
}
