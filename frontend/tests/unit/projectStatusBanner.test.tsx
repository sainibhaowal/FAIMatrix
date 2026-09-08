import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import ProjectStatusBanner from "@/components/landing/ProjectStatusBanner";

describe("ProjectStatusBanner", () => {
  it("clearly identifies the public alpha research preview", () => {
    render(<ProjectStatusBanner />);

    const banner = screen.getByTestId("project-status-banner");
    expect(banner).toHaveTextContent("FAIMATRIX");
    expect(banner).toHaveTextContent("Project experiment");
    expect(banner).toHaveTextContent("Alpha version");
    expect(banner).toHaveTextContent("capabilities and performance are still being validated");
  });
});
