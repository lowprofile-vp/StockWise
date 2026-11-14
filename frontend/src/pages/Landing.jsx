import { Link } from "react-router-dom";
import { ArrowRight, BarChart3, Boxes, ClipboardList, FlaskConical, LineChart, ShieldCheck, ShoppingCart, Truck } from "lucide-react";

const FEATURES = [
  { icon: Boxes, title: "Inventory that keeps a history", body: "Every quantity change is a recorded movement. Stock is never overwritten quietly." },
  { icon: ShoppingCart, title: "Sales, use, and wastage", body: "Separate what was sold, cooked, or thrown away so demand is not mixed with loss." },
  { icon: ClipboardList, title: "Restock by urgency", body: "Rank products by how soon they run out compared with the supplier's delivery time." },
  { icon: LineChart, title: "Plain-language forecasts", body: "Seven-day and thirty-day averages estimate stockout dates, and weak history is labeled as weak." },
  { icon: BarChart3, title: "Budget plans you can compare", body: "A fast greedy shortlist and a dynamic-programming optimum sit side by side before anyone approves an order." },
  { icon: Truck, title: "Suppliers with lead times", body: "Prices, minimum orders, and delivery performance stay attached to the products they supply." },
  { icon: FlaskConical, title: "What-if simulations", body: "Test a demand spike, a late truck, or a smaller budget without touching live stock." },
  { icon: ShieldCheck, title: "Separate workspaces", body: "Owners and staff share one business. They cannot see another business's inventory." },
];

export default function Landing() {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-6 py-5">
        <p className="text-lg font-semibold text-navy-900">StockWise</p>
        <div className="flex gap-2">
          <Link to="/login" className="rounded-lg px-3 py-2 text-sm font-medium text-slate-700 hover:bg-white">Log in</Link>
          <Link to="/register" className="rounded-lg bg-teal-700 px-3 py-2 text-sm font-semibold text-white hover:bg-teal-800">Create workspace</Link>
        </div>
      </header>
      <main>
        <section className="mx-auto grid max-w-6xl items-center gap-10 px-6 py-12 lg:grid-cols-[1.2fr_0.8fr]">
          <div>
            <p className="text-sm font-semibold uppercase tracking-wide text-teal-800">Inventory intelligence</p>
            <h1 className="mt-3 text-4xl font-semibold tracking-tight text-navy-900 sm:text-5xl">Know what to restock before the shelf is empty.</h1>
            <p className="mt-4 max-w-xl text-base leading-7 text-slate-600">
              StockWise helps grocery stores, college canteens, and small businesses watch consumption, estimate stockouts, and spend a limited purchasing budget on the products that will run out first.
            </p>
            <div className="mt-6 flex flex-wrap gap-3">
              <Link to="/register" className="inline-flex items-center gap-2 rounded-lg bg-teal-700 px-4 py-2.5 text-sm font-semibold text-white hover:bg-teal-800">
                Start a workspace <ArrowRight size={16} />
              </Link>
              <Link to="/login" className="rounded-lg border border-slate-300 bg-white px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-100">I already have an account</Link>
            </div>
          </div>
          <div className="rounded-2xl bg-navy-900 p-6 text-white shadow-lg">
            <p className="text-sm text-teal-200">Example · Rice</p>
            <p className="mt-3 text-3xl font-semibold">18 kg left</p>
            <p className="mt-2 text-sm text-slate-300">About 6 kg a day · supplier needs 4 days</p>
            <div className="mt-6 rounded-xl bg-white/10 p-4">
              <p className="text-sm font-medium text-red-200">Critical</p>
              <p className="mt-2 text-sm leading-6 text-slate-200">Estimated stockout in 3 days, before the next delivery can arrive. Restock this before slower-moving items.</p>
            </div>
          </div>
        </section>
        <section className="mx-auto max-w-6xl px-6 py-8">
          <h2 className="text-2xl font-semibold text-slate-900">What the workspace covers</h2>
          <div className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {FEATURES.map((feature) => {
              const Icon = feature.icon;
              return (
                <article key={feature.title} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
                  <Icon className="text-teal-700" size={20} />
                  <h3 className="mt-3 font-semibold text-slate-900">{feature.title}</h3>
                  <p className="mt-2 text-sm leading-6 text-slate-600">{feature.body}</p>
                </article>
              );
            })}
          </div>
        </section>
        <section className="mx-auto max-w-6xl px-6 py-8">
          <div className="grid gap-6 rounded-2xl bg-white p-6 shadow-sm md:grid-cols-3">
            <Benefit title="Fewer surprise stockouts" body="Lead time is part of the decision, so a product with days of cover shorter than delivery is flagged even when the quantity still looks reasonable." />
            <Benefit title="A budget with a reason" body="The planner shows what fits, what is left out, and why the greedy shortlist can differ from the optimal combination." />
            <Benefit title="Owners and staff, separated" body="Staff can record sales and read recommendations. Approving purchase orders, users, and business settings stays with the owner." />
          </div>
        </section>
      </main>
      <footer className="mx-auto max-w-6xl px-6 py-8 text-sm text-slate-500">StockWise · inventory intelligence and restocking decisions.</footer>
    </div>
  );
}

function Benefit({ title, body }) {
  return (
    <div>
      <h3 className="font-semibold text-slate-900">{title}</h3>
      <p className="mt-2 text-sm leading-6 text-slate-600">{body}</p>
    </div>
  );
}
