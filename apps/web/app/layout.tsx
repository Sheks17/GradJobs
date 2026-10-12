import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "GradJobs · Your next beginning",
  description:
    "Find the opportunities built for the start of your career. Transparent early-career job discovery.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <a className="skip-link" href="#main-content">
          Skip to content
        </a>
        <div id="main-content">{children}</div>
        <footer className="site-footer">
          <strong>GradJobs</strong>
          <span>A clearer path to your first next step.</span>
          <span>Early-career discovery · Public employer boards</span>
        </footer>
      </body>
    </html>
  );
}
