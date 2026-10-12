import Link from "next/link";
import { ArrowUpRight, Compass, Globe2 } from "lucide-react";

export function Header({
  active = "discover",
}: {
  active?: "discover" | "saved" | "sources";
}) {
  return (
    <header className="site-header">
      <div className="header-inner">
        <Link href="/" className="brand" aria-label="GradJobs home">
          <span className="brand-mark">
            <ArrowUpRight size={23} strokeWidth={2.6} />
          </span>
          GradJobs<span className="phase-badge">BETA</span>
        </Link>
        <nav aria-label="Main navigation">
          <Link href="/" className={active === "discover" ? "active" : ""}>
            <Compass size={16} />
            Discover jobs
          </Link>
          <Link href="/saved" className={active === "saved" ? "active" : ""}>
            My applications
          </Link>
          <Link
            href="/sources"
            className={active === "sources" ? "active" : ""}
          >
            Sources
          </Link>
        </nav>
        <span className="region">
          <Globe2 size={16} /> United States
        </span>
      </div>
    </header>
  );
}
