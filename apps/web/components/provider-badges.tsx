import type { Job } from "@/types/jobs";
import { dateLabel } from "@/lib/format";

export function closingLabel(value: string, now = Date.now()) {
  const days = Math.ceil((new Date(value).getTime() - now) / 86400000);
  return days <= 0
    ? "Closed"
    : days <= 7
      ? `Closes in ${days} ${days === 1 ? "day" : "days"}`
      : `Closes ${dateLabel(value)}`;
}

export function ProviderBadges({ job }: { job: Job }) {
  const metadata = job.provider_metadata || {};
  return (
    <>
      {metadata.federal === true && <span className="badge">Federal</span>}
      {metadata.recent_graduate === true && (
        <span className="badge green">Recent Graduate</span>
      )}
      {metadata.pathways === true && <span className="badge">Pathways</span>}
      {metadata.student === true && <span className="badge">Students</span>}
      {job.requires_us_citizenship === true && (
        <span className="badge">Citizenship Required</span>
      )}
      {job.requires_security_clearance === true && (
        <span className="badge">Clearance Required</span>
      )}
      {job.closing_at && (
        <span className="badge">{closingLabel(job.closing_at)}</span>
      )}
    </>
  );
}
