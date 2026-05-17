import React from "react";
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

function SmokeComponent() {
  return <div>Frontend vitest is active!</div>;
}

describe("Smoke Test", () => {
  it("renders a component", () => {
    render(<SmokeComponent />);
    expect(screen.getByText("Frontend vitest is active!")).toBeInTheDocument();
  });
});
