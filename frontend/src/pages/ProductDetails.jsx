import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import api, { errorMessage } from "../services/api";
import { useAuth } from "../context/AuthContext";
import PageHeader from "../components/PageHeader";
import Spinner from "../components/Spinner";
import StockBadge from "../components/StockBadge";
import UrgencyBadge from "../components/UrgencyBadge";
import DataTable from "../components/DataTable";
import { formatDate, formatDateTime, formatDays, formatMoney, formatQty, titleCase } from "../utils/format";

export default function ProductDetails() {
  const { productId } = useParams();
  const { user } = useAuth();
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/products/${productId}`)
      .then((response) => setData(response.data.data))
      .catch((err) => setError(errorMessage(err)));
  }, [productId]);

  if (error) return <p className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</p>;
  if (!data) return <Spinner label="Loading product" />;
  const product = data.product;
  const forecast = data.forecast;

  return (
    <div>
      <PageHeader
        title={product.name}
        subtitle={`${product.code} · ${product.category}`}
        actions={<Link to="/inventory" className="text-sm font-medium text-teal-800">Back to inventory</Link>}
      />
      <div className="grid gap-4 lg:grid-cols-3">
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm lg:col-span-2">
          <div className="flex flex-wrap gap-2">
            <StockBadge status={product.stock_status} />
            <UrgencyBadge urgency={product.urgency} />
          </div>
          <dl className="mt-4 grid gap-3 sm:grid-cols-2">
            <Fact label="Current stock" value={formatQty(product.current_stock, product.unit)} />
            <Fact label="Minimum threshold" value={formatQty(product.minimum_stock, product.unit)} />
            <Fact label="Selling price" value={formatMoney(product.selling_price, user.currency)} />
            <Fact label="Purchase price" value={formatMoney(product.purchase_price, user.currency)} />
            <Fact label="Average daily consumption" value={formatQty(forecast.average_daily_demand, product.unit)} />
            <Fact label="Estimated stockout" value={forecast.stockout_date ? `${formatDays(forecast.days_until_stockout)} · ${formatDate(forecast.stockout_date)}` : formatDays(forecast.days_until_stockout)} />
            <Fact label="Reorder point" value={formatQty(forecast.reorder_point, product.unit)} />
            <Fact label="Recommended reorder" value={`${formatQty(forecast.suggested_quantity, product.unit)} · ${formatMoney(forecast.estimated_cost, user.currency)}`} />
          </dl>
          {forecast.data_warning ? <p className="mt-4 rounded-lg bg-amber-50 px-3 py-2 text-sm text-amber-900">{forecast.data_warning}</p> : null}
          <p className="mt-4 text-sm leading-6 text-slate-600">{forecast.reason}</p>
          <p className="mt-2 text-xs text-slate-500">This is an estimate from recent sales and consumption, not a guaranteed future outcome.</p>
        </section>
        <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <h2 className="font-semibold text-slate-900">Suppliers</h2>
          <div className="mt-3 space-y-3">
            {data.suppliers.length ? data.suppliers.map((supplier) => (
              <div key={supplier.supplier_id} className="rounded-lg border border-slate-100 p-3 text-sm">
                <p className="font-medium text-slate-900">{supplier.name} {supplier.is_preferred ? "· preferred" : ""}</p>
                <p className="text-slate-500">{supplier.delivery_days} day lead · {formatMoney(supplier.purchase_price, user.currency)} · MOQ {formatQty(supplier.minimum_order_quantity, product.unit)}</p>
                <p className="text-slate-500">{supplier.phone || supplier.email || "No contact saved"}</p>
              </div>
            )) : <p className="text-sm text-slate-500">No supplier is linked. Recommendations use a 3-day default lead time.</p>}
          </div>
        </section>
      </div>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <h2 className="px-4 pt-4 font-semibold text-slate-900">Stock movement</h2>
          <DataTable
            columns={[
              { key: "transaction_date", label: "When", render: (row) => formatDateTime(row.transaction_date) },
              { key: "transaction_type", label: "Type", render: (row) => titleCase(row.transaction_type) },
              { key: "signed_quantity", label: "Change", render: (row) => formatQty(row.signed_quantity, row.unit) },
              { key: "stock_after", label: "Stock after", render: (row) => formatQty(row.stock_after, row.unit) },
              { key: "reason", label: "Reason", render: (row) => row.reason || "—" },
            ]}
            rows={data.movements}
            rowKey="transaction_id"
            emptyTitle="No movements yet"
          />
        </section>
        <section className="rounded-xl border border-slate-200 bg-white shadow-sm">
          <h2 className="px-4 pt-4 font-semibold text-slate-900">Sales history</h2>
          <DataTable
            columns={[
              { key: "transaction_date", label: "When", render: (row) => formatDateTime(row.transaction_date) },
              { key: "quantity", label: "Sold", render: (row) => formatQty(row.quantity, row.unit) },
              { key: "unit_price", label: "Price", render: (row) => formatMoney(row.unit_price, user.currency) },
            ]}
            rows={data.sales}
            rowKey="transaction_id"
            emptyTitle="No sales recorded"
          />
        </section>
      </div>
      <section className="mt-4 rounded-xl border border-slate-200 bg-white shadow-sm">
        <h2 className="px-4 pt-4 font-semibold text-slate-900">Previous purchase orders</h2>
        <DataTable
          columns={[
            { key: "code", label: "Order" },
            { key: "supplier_name", label: "Supplier" },
            { key: "status", label: "Status", render: (row) => titleCase(row.status) },
            { key: "quantity", label: "Ordered", render: (row) => formatQty(row.quantity, product.unit) },
            { key: "received_quantity", label: "Received", render: (row) => formatQty(row.received_quantity, product.unit) },
            { key: "expected_delivery", label: "Expected", render: (row) => formatDate(row.expected_delivery) },
          ]}
          rows={data.purchase_orders}
          rowKey="order_id"
          emptyTitle="No purchase orders for this product"
        />
      </section>
    </div>
  );
}

function Fact({ label, value }) {
  return (
    <div>
      <dt className="text-xs uppercase tracking-wide text-slate-500">{label}</dt>
      <dd className="mt-1 text-sm font-medium text-slate-900">{value}</dd>
    </div>
  );
}
