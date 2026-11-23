import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { getBharathiDashboard } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";

export default function BharathiDashboard() {
  const [data, setData] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    getBharathiDashboard()
      .then((r) => setData(r.data))
      .catch((e) => setError(e?.response?.data?.detail || e?.message || "Dashboard unavailable"));
  }, []);

  const cards = data
    ? [
        {
          label: "Pending approvals",
          value: data.pending_approval_total ?? data.pending_bill_verification,
          to: "/bharathi/verification",
        },
        { label: "Approved invoices", value: data.approved_invoice_count ?? 0, to: "/bharathi/register?status=APPROVED" },
        { label: "Approved amount (INR)", value: data.approved_amount_inr ?? "0", to: "/bharathi/register" },
        { label: "Active suppliers", value: data.supplier_count ?? 0, to: "/bharathi/suppliers" },
      ]
    : [];

  return (
    <StandardPageLayout title="Bharathi dashboard" subtitle="Purchase invoices, approvals, and supplier activity">
      {error ? <p className="px-4 text-sm text-red-600">{error}</p> : null}
      {!data && !error ? <p className="px-4 text-sm text-slate-500">Loading…</p> : null}
      {data ? (
        <div className="flex flex-col gap-6 p-4">
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {cards.map((c) => (
              <Link
                key={c.label}
                to={c.to}
                className="rounded-lg border bg-white p-4 shadow-sm transition hover:border-emerald-600"
              >
                <p className="text-xs uppercase tracking-wide text-slate-500">{c.label}</p>
                <p className="mt-2 text-2xl font-semibold text-slate-900">{c.value}</p>
              </Link>
            ))}
          </div>
          {data.supplier_summaries?.length ? (
            <div>
              <div className="mb-2 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-slate-800">Supplier snapshot</h2>
                <Link className="text-sm text-blue-600 underline" to="/bharathi/suppliers">
                  View all
                </Link>
              </div>
              <div className="overflow-x-auto rounded border">
                <table className="min-w-full text-left text-sm">
                  <thead className="bg-slate-50 text-xs text-slate-600">
                    <tr>
                      <th className="px-3 py-2">Supplier</th>
                      <th className="px-3 py-2">Invoices</th>
                      <th className="px-3 py-2">Pending</th>
                      <th className="px-3 py-2">Approved (INR)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.supplier_summaries.map((row) => (
                      <tr key={row.supplier_identity_key} className="border-t">
                        <td className="px-3 py-2">
                          <Link
                            className="text-blue-600 underline"
                            to={`/bharathi/register?supplier=${encodeURIComponent(row.supplier_name || "")}`}
                          >
                            {row.supplier_name || "—"}
                          </Link>
                        </td>
                        <td className="px-3 py-2">{row.invoice_count}</td>
                        <td className="px-3 py-2">{row.pending_count}</td>
                        <td className="px-3 py-2">₹{row.approved_total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
          <p className="text-xs text-slate-500">Role view: {data.role_view}</p>
        </div>
      ) : null}
    </StandardPageLayout>
  );
}