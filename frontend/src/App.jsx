import { Navigate, Route, Routes } from "react-router-dom";
import { useAuth } from "./context/AuthContext.jsx";
import Layout from "./components/Layout.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Products from "./pages/Products.jsx";
import Forecasting from "./pages/Forecasting.jsx";
import Analytics from "./pages/Analytics.jsx";
import Sales from "./pages/Sales.jsx";
import Model from "./pages/Model.jsx";
import Reports from "./pages/Reports.jsx";

function Protected({ children }) {
  const { user, loading } = useAuth();
  if (loading) {
    return <div className="p-10 text-stone-500">Restoring session…</div>;
  }
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="products" element={<Products />} />
        <Route path="forecasting" element={<Forecasting />} />
        <Route path="analytics" element={<Analytics />} />
        <Route path="sales" element={<Sales />} />
        <Route path="model" element={<Model />} />
        <Route path="reports" element={<Reports />} />
      </Route>
    </Routes>
  );
}
