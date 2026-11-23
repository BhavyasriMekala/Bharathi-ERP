import { useRef, useState } from "react";

import { createBharathiBill, listBharathiBills, submitBharathiBill } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";
import { uploadFileThroughPipeline } from "../../utils/fileUploadPipeline";

export default function SupervisorBillUpload() {
  const [rows, setRows] = useState([]);
  const [vendorHint, setVendorHint] = useState("");
  const [remarks, setRemarks] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [progress, setProgress] = useState(0);
  const fileRef = useRef(null);

  async function refresh() {
    const res = await listBharathiBills();
    setRows(res.data || []);
  }

  async function onSubmit() {
    setBusy(true);
    setMessage("");
    setProgress(0);
    try {
      const files = Array.from(fileRef.current?.files || []);
      if (!files.length) {
        setMessage("Select at least one image or PDF.");
        return;
      }
      const stored = [];
      for (const file of files) {
        const id = await uploadFileThroughPipeline(file, {
          entityType: "bharathi_bill",
          onProgress: setProgress,
        });
        stored.push({
          stored_file_id: id,
          original_filename: file.name,
          mime_type: file.type || "application/octet-stream",
          file_size_bytes: file.size,
        });
      }
      const createRes = await createBharathiBill({ vendor_hint: vendorHint, remarks, files: stored });
      const id = createRes.data?.id;
      if (id) await submitBharathiBill(id);
      setMessage("Bill submitted for OCR and verification.");
      setVendorHint("");
      setRemarks("");
      if (fileRef.current) fileRef.current.value = "";
      await refresh();
    } catch (e) {
      setMessage(e?.response?.data?.detail || e?.message || "Upload failed.");
    } finally {
      setBusy(false);
      setProgress(0);
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
        {progress > 0 && progress < 100 ? <p className="text-xs text-slate-500">Uploading… {progress}%</p> : null}
        <button type="button" disabled={busy} className="rounded border px-4 py-2" onClick={() => refresh()}>
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