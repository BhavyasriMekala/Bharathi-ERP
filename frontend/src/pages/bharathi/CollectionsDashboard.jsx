import { useEffect, useState } from "react";

import { getCollectionsOutstanding } from "../../api/bharathiApi";
import StandardPageLayout from "../../components/common/StandardPageLayout";

export default function CollectionsDashboard() {
  const [items, setItems] = useState([]);

  useEffect(() => {
    getCollectionsOutstanding().then((r) => setItems(r.data?.items || []));
  }, []);

  return (
    <StandardPageLayout title="Collections" subtitle="Outstanding and follow-ups (INR)">
      <div className="overflow-x-auto p-4">
        <table className="min-w-full text-sm">
          <thead>
            <tr className="border-b text-left">
              <th className="p-2">Invoice</th>
              <th className="p-2">Outstanding</th>
              <th className="p-2">Bucket</th>
              <th className="p-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {items.map((row) => (
              <tr key={row.id} className="border-b">
                <td className="p-2">{row.invoice_ref || "—"}</td>
                <td className="p-2">{row.outstanding_amount}</td>
                <td className="p-2">{row.aging_bucket}</td>
                <td className="p-2">{row.collection_status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </StandardPageLayout>
  );
}