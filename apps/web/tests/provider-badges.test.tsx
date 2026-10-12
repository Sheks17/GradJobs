import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { ProviderBadges, closingLabel } from "@/components/provider-badges";
import { demoJob } from "./fixtures";

describe("source-supported federal badges", () => {
  it("shows explicit eligibility and program metadata", () => {
    render(
      <ProviderBadges
        job={{
          ...demoJob,
          provider_metadata: {
            federal: true,
            recent_graduate: true,
            pathways: true,
          },
          requires_us_citizenship: true,
          requires_security_clearance: true,
        }}
      />,
    );
    for (const label of [
      "Federal",
      "Recent Graduate",
      "Pathways",
      "Citizenship Required",
      "Clearance Required",
    ]) {
      expect(screen.getByText(label)).toBeVisible();
    }
  });
  it("does not infer eligibility from a federal source alone", () => {
    const { container } = render(
      <ProviderBadges
        job={{
          ...demoJob,
          source: "usajobs",
          provider_metadata: {},
          requires_us_citizenship: null,
          requires_security_clearance: null,
        }}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
  it("shows deadlines and does not call elapsed deadlines upcoming", () => {
    const now = Date.parse("2030-01-01T00:00:00Z");
    expect(closingLabel("2030-01-04T00:00:00Z", now)).toBe("Closes in 3 days");
    expect(closingLabel("2029-12-31T00:00:00Z", now)).toBe("Closed");
  });
});
