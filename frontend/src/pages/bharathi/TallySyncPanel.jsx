import { useState } from "react";

import { runTallySync } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";

export default function TallySyncPanel() {
  const [log, setLog] = useState("");

  async function sync(direction) {
    const res = await runTallySync({ direction, dry_run: true });
    setLog(JSON.stringify(res.data, null, 2));
  }

  return (
    <StandardPageLayout title="Tally synchronization" subtitle="Mock connector (dry-run only)">
      <div className="flex flex-col gap-3 p-4">
        <p className="text-sm text-slate-600">
          Live Tally connectivity is BLOCKED EXTERNAL until the office connector is deployed.
        </p>
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