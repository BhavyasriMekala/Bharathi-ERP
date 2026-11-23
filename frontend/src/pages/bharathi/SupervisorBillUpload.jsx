import { useRef, useState } from "react";

import { createBharathiBill, listBharathiBills, submitBharathiBill } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";

export default function SupervisorBillUpload() {
  const [rows, setRows] = useState([]);
  const [vendorHint, setVendorHint] = useState("");
  const [remarks, setRemarks] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const fileRef = useRef(null);

  async function refresh() {
    const res = await listBharathiBills();
    setRows(res.data || []);
  }

  async function onSubmit() {
    setBusy(true);
    setMessage("");
    try {
      const files = Array.from(fileRef.current?.files || []).map((f) => ({
        original_filename: f.name,
        mime_type: f.type || "application/octet-stream",
        file_size_bytes: f.size,
      }));
      const createRes = await createBharathiBill({ vendor_hint: vendorHint, remarks, files });
      const id = createRes.data?.id;
      if (id) await submitBharathiBill(id);
      setMessage("Bill submitted for OCR and verification.");
      setVendorHint("");
      setRemarks("");
      if (fileRef.current) fileRef.current.value = "";
      await refresh();
    } catch (e) {
      setMessage(e?.response?.data?.detail || "Upload failed.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <StandardPageLayout title="Upload supplier bill" subtitle="Mobile-friendly capture for Supervisors">
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4 p-4">
        <label className="text-sm font-medium">Vendor hint</label>
        <input className="rounded border px-3 py-2" value={vendorHint} onChange={(e) => setVendorHint(e.target.value)} />
        <label className="text-sm font-medium">Remarks</label>
        <textarea className="rounded border px-3 py-2" rows={2} value={remarks} onChange={(e) => setRemarks(e.target.value)} />
        <input ref={fileRef} type="file" accept="image/*,application/pdf" capture="environment" multiple className="text-sm" />
        <button
          type="button"
          disabled={busy}
          className="rounded bg-indigo-600 px-4 py-3 text-white disabled:opacity-50"
          onClick={() => refresh()}
        >
          Refresh list
        </button>
        <button
          type="button"
          disabled={busy}
          className="rounded bg-emerald-600 px-4 py-3 text-white disabled:opacity-50"
          onClick={onSubmit}
        >
          {busy ? "Uploading…" : "Submit bill"}
        </button>
        {message ? <p className="text-sm text-slate-600">{message}</p> : null}
        <ul className="divide-y rounded border">
          {rows.map((r) => (
            <li key={r.id} className="p-3 text-sm">
              <div className="font-medium">#{r.id} — {r.status}</div>
              <div>{r.vendor_hint || "—"}</div>
            </li>
          ))}
        </ul>
      </div>
    </StandardPageLayout>
  );
}