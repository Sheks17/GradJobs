import type { Job } from "@/types/jobs";

export function experienceLabel(
  job: Pick<Job, "experience_min_years" | "experience_max_years"> &
    Partial<Job>,
): string {
  if (job.experience_category === "no_experience_required")
    return "No experience required";
  if (job.requirement_type === "ambiguous") return "Experience needs review";
  if (job.required_min_years !== undefined) {
    const min = job.required_min_years ?? job.preferred_min_years;
    const max =
      job.required_min_years !== null
        ? job.required_max_years
        : job.preferred_max_years;
    if (min == null) return "Experience not specified";
    const range =
      max != null
        ? `${min}–${max} years`
        : `${min}+ ${min === 1 ? "year" : "years"}`;
    return `${range} ${job.required_min_years === null ? "preferred" : "required"}`;
  }
  if (job.experience_min_years === null) return "Experience not specified";
  const min = job.experience_min_years,
    max = job.experience_max_years;
  return max !== null
    ? `${min}–${max} years`
    : `${min}+ ${min === 1 ? "year" : "years"}`;
}

export function salaryLabel(
  job: Pick<
    Job,
    "salary_min" | "salary_max" | "salary_currency" | "salary_period"
  >,
): string {
  if (job.salary_min === null && job.salary_max === null)
    return "Salary not disclosed";
  const money = (value: string) =>
    new Intl.NumberFormat("en-US", {
      style: job.salary_currency ? "currency" : "decimal",
      currency: job.salary_currency || undefined,
      maximumFractionDigits: 0,
    }).format(Number(value));
  const range =
    job.salary_min && job.salary_max
      ? `${money(job.salary_min)}–${money(job.salary_max)}`
      : job.salary_min
        ? `From ${money(job.salary_min)}`
        : `Up to ${money(job.salary_max!)}`;
  return `${range}${job.salary_period ? ` / ${job.salary_period}` : " · period unspecified"}`;
}

export function dateLabel(value: string | null): string {
  if (!value) return "Not provided";
  return new Intl.DateTimeFormat("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
    timeZone: "UTC",
  }).format(new Date(value));
}

export function relativeDate(value: string): string {
  const minutes = Math.max(
    0,
    Math.floor((Date.now() - new Date(value).getTime()) / 60000),
  );
  const hours = Math.max(
    0,
    Math.floor((Date.now() - new Date(value).getTime()) / 3600000),
  );
  return hours < 1
    ? minutes < 1
      ? "just now"
      : `${minutes} ${minutes === 1 ? "minute" : "minutes"} ago`
    : hours < 24
      ? `${hours} ${hours === 1 ? "hour" : "hours"} ago`
      : `${Math.floor(hours / 24)} days ago`;
}

export function postedLabel(value: string): string {
  const now = new Date();
  const today = Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
  );
  const posted = new Date(value);
  const day = Date.UTC(
    posted.getUTCFullYear(),
    posted.getUTCMonth(),
    posted.getUTCDate(),
  );
  const days = Math.floor((today - day) / 86400000);
  return days === 0
    ? "today"
    : days === 1
      ? "yesterday"
      : days > 1
        ? `${days} days ago`
        : dateLabel(value);
}

export function timestampLabel(value: string | null): string {
  return value
    ? new Intl.DateTimeFormat("en-US", {
        dateStyle: "medium",
        timeStyle: "short",
        timeZone: "UTC",
      }).format(new Date(value)) + " UTC"
    : "Not yet";
}

export const remoteLabels: Record<string, string> = {
  remote: "Remote",
  hybrid: "Hybrid",
  onsite: "On-site",
  unknown: "Workplace unspecified",
};
