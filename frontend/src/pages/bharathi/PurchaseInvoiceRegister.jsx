import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { listBharathiBillsPaginated } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";

export default function PurchaseInvoiceRegister() {
  const [searchParams] = useSearchParams();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [status, setStatus] = useState(searchParams.get("status") || "");
  const [supplier, setSupplier] = useState(searchParams.get("supplier") || "");
  const [invoiceNumber, setInvoiceNumber] = useState(searchParams.get("invoice_number") || "");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function load() {
    setLoading(true);
    setError("");
    try {
      const res = await listBharathiBillsPaginated({
        status: status || undefined,
        supplier: supplier || undefined,
        invoice_number: invoiceNumber || undefined,
        offset: 0,
        limit: 50,
      });
      setItems(res.data?.items || []);
      setTotal(res.data?.total || 0);
    } catch (e) {
      setError(e?.response?.data?.detail || e?.message || "Failed to load invoices");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- initial URL-driven filters
  }, []);

  return (
    <StandardPageLayout title="Purchase invoice register" subtitle="Search and review supplier invoices">
      <div className="flex flex-col gap-4 p-4">
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-4">
          <input
            className="rounded border px-3 py-2 text-sm"
            placeholder="Supplier"
            value={supplier}
            onChange={(e) => setSupplier(e.target.value)}
          />
          <input
            className="rounded border px-3 py-2 text-sm"
            placeholder="Invoice number"
            value={invoiceNumber}
            onChange={(e) => setInvoiceNumber(e.target.value)}
          />
          <select className="rounded border px-3 py-2 text-sm" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All statuses</option>
            <option value="PENDING_VERIFICATION">Pending verification</option>
            <option value="VERIFIED">Verified</option>
            <option value="APPROVED">Approved</option>
            <option value="REJECTED">Rejected</option>
            <option value="DUPLICATE_REVIEW">Duplicate review</option>
            <option value="EXTRACTION_FAILED">Extraction failed</option>
          </select>
          <button type="button" className="rounded bg-slate-800 px-4 py-2 text-sm text-white" onClick={load} disabled={loading}>
            {loading ? "Loading…" : "Search"}
          </button>
        </div>
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <p className="text-xs text-slate-500">{total} invoice(s)</p>
        <div className="overflow-x-auto rounded border">
          <table className="min-w-full text-left text-sm">
            <thead className="bg-slate-50 text-xs uppercase text-slate-600">
              <tr>
                <th className="px-3 py-2">Invoice</th>
                <th className="px-3 py-2">Supplier</th>
                <th className="px-3 py-2">Date</th>
                <th className="px-3 py-2">Amount</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2">Duplicate</th>
                <th className="px-3 py-2">Tally</th>
              </tr>
            </thead>
            <tbody>
              {items.map((row) => (
                <tr key={row.id} className="border-t">
                  <td className="px-3 py-2">
                    <Link className="text-blue-600 underline" to={`/bharathi/invoices/${row.id}`}>
                      {row.invoice_number || `#${row.id}`}
                    </Link>
                  </td>
                  <td className="px-3 py-2">{row.supplier_name || row.vendor_hint || "—"}</td>
                  <td className="px-3 py-2">{row.invoice_date || "—"}</td>
                  <td className="px-3 py-2">{row.grand_total != null ? `₹${row.grand_total}` : "—"}</td>
                  <td className="px-3 py-2">{row.status}</td>
                  <td className="px-3 py-2">{row.duplicate_status || "—"}</td>
                  <td className="px-3 py-2">{row.tally_sync_status || "not_configured"}</td>
                </tr>
              ))}
              {!items.length && !loading ? (
                <tr>
                  <td colSpan={7} className="px-3 py-6 text-center text-slate-500">
                    No invoices found.
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