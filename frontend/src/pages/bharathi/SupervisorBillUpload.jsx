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
      const detail = e?.response?.data?.detail;
      const text =
        typeof detail === "object" && detail?.message
          ? detail.message
          : typeof detail === "string"
            ? detail
            : e?.message || "Upload failed.";
      setMessage(text);
    } finally {
      setBusy(false);
      setProgress(0);
    }
  }

  function openFilePicker(useCamera) {
    if (!fileRef.current) return;
    if (useCamera) {
      fileRef.current.setAttribute("capture", "environment");
    } else {
      fileRef.current.removeAttribute("capture");
    }
    fileRef.current.click();
  }

  return (
    <StandardPageLayout title="Scan purchase invoice" subtitle="Capture or upload supplier invoices (JPEG, PNG, PDF)">
      <div className="mx-auto flex w-full max-w-xl flex-col gap-4 p-4">
        <div className="flex flex-col gap-2 sm:flex-row">
          <button
            type="button"
            disabled={busy}
            className="min-h-12 flex-1 rounded-lg bg-emerald-700 px-4 py-3 text-base font-semibold text-white disabled:opacity-50"
            onClick={() => openFilePicker(true)}
          >
            Scan invoice
          </button>
          <button
            type="button"
            disabled={busy}
            className="min-h-12 flex-1 rounded-lg border border-slate-300 bg-white px-4 py-3 text-base font-semibold"
            onClick={() => openFilePicker(false)}
          >
            Upload file
          </button>
        </div>
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,application/pdf"
          multiple
          className="sr-only"
          aria-hidden
        />
        <label className="text-sm font-medium">Vendor hint (optional)</label>
        <input className="rounded border px-3 py-2" value={vendorHint} onChange={(e) => setVendorHint(e.target.value)} />
        <label className="text-sm font-medium">Remarks</label>
        <textarea className="rounded border px-3 py-2" rows={2} value={remarks} onChange={(e) => setRemarks(e.target.value)} />
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
          {busy ? "Processing…" : "Submit for OCR"}
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