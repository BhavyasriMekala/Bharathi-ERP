import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { listBharathiSupplierSummary } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";

export default function SupplierInvoiceSummary() {
  const [items, setItems] = useState([]);
  const [error, setError] = useState("");

  useEffect(() => {
    listBharathiSupplierSummary()
      .then((r) => setItems(r.data?.items || []))
      .catch((e) => setError(e?.response?.data?.detail || e?.message || "Could not load suppliers"));
  }, []);

  return (
    <StandardPageLayout
      title="Supplier-wise invoices"
      subtitle="Fictional demo suppliers — invoice counts and approval totals"
    >
      <div className="p-4">
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <p className="mb-3 text-xs text-slate-500">{items.length} supplier(s) with captured invoices</p>
        <div className="overflow-x-auto rounded border">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-600">
              <tr>
                <th className="px-3 py-2">Supplier</th>
                <th className="px-3 py-2">GSTIN</th>
                <th className="px-3 py-2">Invoices</th>
                <th className="px-3 py-2">Pending</th>
                <th className="px-3 py-2">Approved (INR)</th>
                <th className="px-3 py-2" />
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.supplier_identity_key} className="border-t">
                  <td className="px-3 py-2 font-medium">{row.supplier_name || "—"}</td>
                  <td className="px-3 py-2 text-xs">{row.supplier_gstin || "—"}</td>
                  <td className="px-3 py-2">{row.invoice_count}</td>
                  <td className="px-3 py-2">{row.pending_count}</td>
                  <td className="px-3 py-2">₹{row.approved_total}</td>
                  <td className="px-3 py-2">
                    <Link
                      className="text-blue-600 underline"
                      to={`/bharathi/register?supplier=${encodeURIComponent(row.supplier_name || "")}`}
                    >
                      Invoices
                    </Link>
                  </td>
                </tr>
              ))}
              {!items.length && !error ? (
                <tr>
                  <td colSpan={6} className="px-3 py-8 text-center text-slate-500">
                    No supplier invoices yet. Run the demo seed script on a Phase 1-ready database.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </StandardPageLayout>
  );
}