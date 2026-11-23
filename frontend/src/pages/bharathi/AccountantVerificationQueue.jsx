import { useEffect, useState } from "react";

import { listBharathiBills, verifyBharathiBill } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";

export default function AccountantVerificationQueue() {
  const [rows, setRows] = useState([]);
  const [selected, setSelected] = useState(null);

  async function load() {
    const res = await listBharathiBills({ status: "PENDING_VERIFICATION" });
    setRows(res.data || []);
  }

  useEffect(() => {
    load();
  }, []);

  async function act(action) {
    if (!selected) return;
    await verifyBharathiBill(selected.id, { action, comment: `${action} via queue` });
    setSelected(null);
    await load();
  }

  return (
    <StandardPageLayout title="Bill verification" subtitle="Review OCR extraction before posting">
      <div className="grid gap-4 p-4 lg:grid-cols-2">
        <ul className="divide-y rounded border">
          {rows.map((r) => (
            <li key={r.id}>
              <button type="button" className="w-full p-3 text-left text-sm hover:bg-slate-50" onClick={() => setSelected(r)}>
                #{r.id} — {r.vendor_hint || "Vendor TBD"}
              </button>
            </li>
          ))}
        </ul>
        <div className="rounded border p-4 text-sm">
          {selected ? (
            <>
              <p className="font-semibold">Extracted preview</p>
              <pre className="mt-2 max-h-64 overflow-auto rounded bg-slate-50 p-2 text-xs">
                {JSON.stringify(selected.latest_extraction?.extracted || {}, null, 2)}
              </pre>
              <div className="mt-4 flex gap-2">
                <button type="button" className="rounded bg-emerald-600 px-3 py-2 text-white" onClick={() => act("verify")}>
                  Verify
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
        </div>
      </div>
    </StandardPageLayout>
  );
}