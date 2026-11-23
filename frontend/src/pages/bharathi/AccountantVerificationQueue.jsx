import { useEffect, useState } from "react";

import {
  approveBharathiBill,
  getBharathiBillAudit,
  listBharathiBills,
  verifyBharathiBill,
} from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";
import InvoiceLineItemsEditor from "./InvoiceLineItemsEditor";

export default function AccountantVerificationQueue() {
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);
  const [audit, setAudit] = useState([]);

  async function load() {
    const res = await listBharathiBills();
    const data = res.data || [];
    const queue = data.filter((r) =>
      ["PENDING_VERIFICATION", "NEEDS_REVIEW", "DUPLICATE_REVIEW", "VERIFIED", "EXTRACTED"].includes(r.status)
    );
    setRows(queue.length ? queue : data);
  }

  useEffect(() => {
    load();
  }, []);

  async function selectRow(row) {
    setSelected(row);
    const auditRes = await getBharathiBillAudit(row.id);
    setAudit(auditRes.data?.events || []);
  }

  async function act(action) {
    if (!selected) return;
    if (action === "approve") {
      await approveBharathiBill(selected.id, { action: "approve", comment: "Approved via queue" });
    } else {
      await verifyBharathiBill(selected.id, { action, comment: `${action} via queue` });
    }
    setSelected(null);
    setAudit([]);
    await load();
  }

  return (
    <StandardPageLayout title="Bill verification" subtitle="Review OCR extraction before posting">
      <div className="grid gap-4 p-4 lg:grid-cols-2">
        <ul className="divide-y rounded border">
          {rows.map((r) => (
            <li key={r.id}>
              <button type="button" className="w-full p-3 text-left text-sm hover:bg-slate-50" onClick={() => selectRow(r)}>
                #{r.id} — {r.supplier_name || r.vendor_hint || "Vendor TBD"} ({r.status})
              </button>
            </li>
          ))}
        </ul>
        <div className="rounded border p-4 text-sm">
          {selected ? (
            <>
              {selected.duplicate_status ? (
                <p className="mb-2 rounded bg-amber-50 p-2 text-amber-900">Duplicate flag: {selected.duplicate_status}</p>
              ) : null}
              {selected.validation_warnings?.length ? (
                <ul className="mb-2 list-disc rounded bg-amber-50 p-2 pl-6 text-xs text-amber-900">
                  {selected.validation_warnings.map((w) => (
                    <li key={w.code}>{w.code}</li>
                  ))}
                </ul>
              ) : null}
              <p className="font-semibold">Extracted preview</p>
              <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-50 p-2 text-xs">
                {JSON.stringify(selected.latest_extraction?.extracted || {}, null, 2)}
              </pre>
              <InvoiceLineItemsEditor
                submissionId={selected.id}
                lineItems={selected.line_items}
                supplierName={selected.supplier_name}
                invoiceNumber={selected.invoice_number}
                onSaved={async () => {
                  await load();
                  const match = (await listBharathiBills()).data?.find((r) => r.id === selected.id);
                  if (match) setSelected(match);
                }}
              />
              <div className="mt-4 flex flex-wrap gap-2">
                <button type="button" className="rounded bg-emerald-600 px-3 py-2 text-white" onClick={() => act("verify")}>
                  Verify
                </button>
                <button type="button" className="rounded bg-blue-700 px-3 py-2 text-white" onClick={() => act("approve")}>
                  Approve
                </button>
                <button type="button" className="rounded bg-amber-600 px-3 py-2 text-white" onClick={() => act("request_correction")}>
                  Request correction
                </button>
                <button type="button" className="rounded bg-rose-600 px-3 py-2 text-white" onClick={() => act("reject")}>
                  Reject
                </button>
              </div>
            </>
          ) : (
            <p className="text-slate-500">Select a pending bill.</p>
          )}
          {audit.length ? (
            <div className="mt-4 border-t pt-4">
              <p className="font-semibold">Audit history</p>
              <ul className="mt-2 text-xs text-slate-600">
                {audit.map((e) => (
                  <li key={e.id}>
                    {e.action} — {e.created_at}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      </div>
    </StandardPageLayout>
  );
}