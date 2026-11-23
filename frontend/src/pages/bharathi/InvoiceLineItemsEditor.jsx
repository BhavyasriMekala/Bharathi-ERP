import { useEffect, useState } from "react";

import { verifyBharathiBill } from "../../api/bharathiApi";

const FIELDS = [
  "description",
  "hsn_sac",
  "quantity",
  "unit",
  "unit_price",
  "tax_rate",
  "tax_amount",
  "line_total",
];

function emptyLine(n) {
  return {
    line_number: n,
    description: "",
    hsn_sac: "",
    quantity: "",
    unit: "",
    unit_price: "",
    tax_rate: "",
    tax_amount: "",
    line_total: "",
  };
}

function mapLine(row, idx) {
  return {
    line_number: row.line_number ?? idx + 1,
    description: row.description ?? "",
    hsn_sac: row.hsn_sac ?? "",
    quantity: row.quantity ?? "",
    unit: row.unit ?? "",
    unit_price: row.unit_price ?? "",
    tax_rate: row.tax_rate ?? "",
    tax_amount: row.tax_amount ?? "",
    line_total: row.line_total ?? "",
  };
}

export default function InvoiceLineItemsEditor({ submissionId, lineItems, supplierName, invoiceNumber, onSaved }) {
  const [supplier, setSupplier] = useState(supplierName || "");
  const [invoiceNum, setInvoiceNum] = useState(invoiceNumber || "");
  const [lines, setLines] = useState([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setSupplier(supplierName || "");
    setInvoiceNum(invoiceNumber || "");
    const base = (lineItems || []).length ? lineItems.map(mapLine) : [emptyLine(1)];
    setLines(base);
  }, [submissionId, lineItems, supplierName, invoiceNumber]);

  function updateLine(idx, field, value) {
    setLines((prev) => prev.map((row, i) => (i === idx ? { ...row, [field]: value } : row)));
  }

  function addLine() {
    setLines((prev) => [...prev, emptyLine(prev.length + 1)]);
  }

  function toPayload(row) {
    const out = { line_number: Number(row.line_number) || undefined };
    for (const f of FIELDS) {
      const v = row[f];
      if (v === "" || v == null) continue;
      out[f] = ["quantity", "unit_price", "tax_rate", "tax_amount", "line_total"].includes(f) ? Number(v) : v;
    }
    return out;
  }

  async function save() {
    setBusy(true);
    setMessage("");
    try {
      await verifyBharathiBill(submissionId, {
        action: "save_corrections",
        comment: "Manual line corrections",
        corrected_fields: { supplier_name: supplier, invoice_number: invoiceNum },
        corrected_line_items: lines.map(toPayload),
      });
      setMessage("Corrections saved (original OCR extraction preserved).");
      onSaved?.();
    } catch (e) {
      setMessage(e?.response?.data?.detail || e?.message || "Save failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mt-4 space-y-3">
      <p className="text-xs font-semibold text-slate-700">Corrected fields (persisted separately from OCR)</p>
      <div className="grid gap-2 sm:grid-cols-2">
        <label className="text-xs font-medium">
          Supplier
          <input className="mt-1 w-full rounded border px-2 py-1 text-sm" value={supplier} onChange={(e) => setSupplier(e.target.value)} />
        </label>
        <label className="text-xs font-medium">
          Invoice number
          <input className="mt-1 w-full rounded border px-2 py-1 text-sm" value={invoiceNum} onChange={(e) => setInvoiceNum(e.target.value)} />
        </label>
      </div>
      <div className="overflow-x-auto rounded border">
        <table className="min-w-full text-left text-xs">
          <thead className="bg-slate-50">
            <tr>
              <th className="px-2 py-1">#</th>
              <th className="px-2 py-1">Description</th>
              <th className="px-2 py-1">HSN</th>
              <th className="px-2 py-1">Qty</th>
              <th className="px-2 py-1">Unit</th>
              <th className="px-2 py-1">Unit price</th>
              <th className="px-2 py-1">Tax %</th>
              <th className="px-2 py-1">Tax amt</th>
              <th className="px-2 py-1">Line total</th>
            </tr>
          </thead>
          <tbody>
            {lines.map((row, idx) => (
              <tr key={`${submissionId}-line-${idx}`} className="border-t">
                <td className="px-1 py-1">{idx + 1}</td>
                {FIELDS.map((field) => (
                  <td key={field} className="px-1 py-1">
                    <input
                      className="w-full min-w-[4rem] rounded border px-1 py-0.5"
                      value={row[field]}
                      onChange={(e) => updateLine(idx, field, e.target.value)}
                    />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="flex flex-wrap gap-2">
        <button type="button" className="rounded border px-3 py-1 text-sm" onClick={addLine} disabled={busy}>
          Add line
        </button>
        <button type="button" className="rounded bg-slate-800 px-3 py-1 text-sm text-white" onClick={save} disabled={busy}>
          {busy ? "Saving…" : "Save line corrections"}
        </button>
      </div>
      {message ? <p className="text-xs text-slate-600">{message}</p> : null}
    </div>
  );
}
