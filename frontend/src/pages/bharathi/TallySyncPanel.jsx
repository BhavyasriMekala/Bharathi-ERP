import { useEffect, useState } from "react";

import { getTallyReadonlyPoc, runTallySync } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";

export default function TallySyncPanel() {
  const [log, setLog] = useState("");
  const [poc, setPoc] = useState(null);
  const [pocError, setPocError] = useState("");

  useEffect(() => {
    getTallyReadonlyPoc()
      .then((res) => setPoc(res.data))
      .catch((e) => setPocError(e?.response?.data?.detail || e?.message || "Could not load read-only PoC"));
  }, []);

  async function sync(direction) {
    const res = await runTallySync({ direction, dry_run: true });
    setLog(JSON.stringify(res.data, null, 2));
  }

  return (
    <StandardPageLayout title="Tally synchronization" subtitle="Read-only PoC + mock sync (dry-run only)">
      <div className="flex flex-col gap-3 p-4">
        <p className="text-sm text-slate-600">
          Live Tally writes and voucher import are disabled. The read-only PoC uses fixtures only — not your office Tally instance.
        </p>
        {pocError ? <p className="text-sm text-red-600">{pocError}</p> : null}
        {poc ? (
          <div className="rounded border bg-slate-50 p-3 text-sm">
            <p>
              <strong>Read-only status:</strong> {poc.mode} · live_tally={String(poc.live_tally)} · writes_disabled=
              {String(poc.writes_disabled)}
            </p>
            <p className="mt-1">
              Company: {poc.company?.name} ({poc.company?.guid})
            </p>
            <p className="mt-1 text-xs text-slate-600">{poc.note}</p>
            <p className="mt-2 text-xs">
              Ledgers: {poc.supplier_ledgers?.length ?? 0} · Purchase vouchers: {poc.purchase_vouchers?.length ?? 0}
            </p>
          </div>
        ) : null}
        <div className="flex gap-2">
          <button type="button" className="rounded bg-indigo-600 px-3 py-2 text-white" onClick={() => sync("inbound")}>
            Dry-run inbound
          </button>
          <button type="button" className="rounded bg-indigo-600 px-3 py-2 text-white" onClick={() => sync("outbound")}>
            Dry-run outbound
          </button>
        </div>
        {log ? <pre className="rounded bg-slate-50 p-3 text-xs">{log}</pre> : null}
      </div>
    </StandardPageLayout>
  );
}