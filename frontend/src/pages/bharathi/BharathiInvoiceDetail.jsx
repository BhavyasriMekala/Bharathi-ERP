import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getBharathiBill } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";

export default function BharathiInvoiceDetail() {
  const { id } = useParams();
  const [bill, setBill] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!id) return;
    getBharathiBill(id)
      .then((r) => setBill(r.data))
      .catch((e) => setError(e?.response?.data?.detail || e?.message || "Invoice not found"));
  }, [id]);

  return (
    <StandardPageLayout title="Invoice details" subtitle="Read-only purchase invoice view">
      <div className="flex flex-col gap-4 p-4 text-sm">
        <Link className="text-blue-600 underline" to="/bharathi/register">
          Back to register
        </Link>
        {error ? <p className="text-red-600">{error}</p> : null}
        {bill ? (
          <>
            <div className="grid gap-2 rounded border p-4 sm:grid-cols-2">
              <p>
                <span className="text-slate-500">Supplier:</span> {bill.supplier_name || bill.vendor_hint || "—"}
              </p>
              <p>
                <span className="text-slate-500">Invoice #:</span> {bill.invoice_number || `Submission ${bill.id}`}
              </p>
              <p>
                <span className="text-slate-500">Date:</span> {bill.invoice_date || "—"}
              </p>
              <p>
                <span className="text-slate-500">Amount:</span>{" "}
                {bill.grand_total != null ? `₹${bill.grand_total}` : "—"}
              </p>
              <p>
                <span className="text-slate-500">Status:</span> {bill.status}
              </p>
              <p>
                <span className="text-slate-500">Duplicate:</span> {bill.duplicate_status || "—"}
              </p>
            </div>
            {bill.line_items?.length ? (
              <div className="overflow-x-auto rounded border">
                <table className="min-w-full text-left text-xs">
                  <thead className="bg-slate-50">
                    <tr>
                      <th className="px-2 py-2">#</th>
                      <th className="px-2 py-2">Description</th>
                      <th className="px-2 py-2">Qty</th>
                      <th className="px-2 py-2">Rate</th>
                      <th className="px-2 py-2">Tax %</th>
                      <th className="px-2 py-2">Line total</th>
                    </tr>
                  </thead>
                  <tbody>
                    {bill.line_items.map((line) => (
                      <tr key={line.line_number} className="border-t">
                        <td className="px-2 py-2">{line.line_number}</td>
                        <td className="px-2 py-2">{line.description}</td>
                        <td className="px-2 py-2">
                          {line.quantity} {line.unit || ""}
                        </td>
                        <td className="px-2 py-2">{line.unit_price}</td>
                        <td className="px-2 py-2">{line.tax_rate}</td>
                        <td className="px-2 py-2">{line.line_total}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : null}
          </>
        ) : null}
      </div>
    </StandardPageLayout>
  );
}