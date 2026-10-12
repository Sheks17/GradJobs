import Link from "next/link";
export default function NotFound() {
  return (
    <main className="empty-state">
      <h1>Page not found</h1>
      <p>Let’s get back to finding your next opportunity.</p>
      <Link className="primary-button" href="/">
        Back to GradJobs
      </Link>
    </main>
  );
}
