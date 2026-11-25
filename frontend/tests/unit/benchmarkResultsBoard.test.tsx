import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BenchmarkResultsBoard from "@/components/landing/BenchmarkResultsBoard";

describe("BenchmarkResultsBoard", () => {
  it("renders signed 2026-11-24 BeIR and LoCoMo scenario results accurately", () => {
    render(<BenchmarkResultsBoard />);

    expect(screen.getAllByText(/0\.6900/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.6871/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.3314/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.3387/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.0710/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Full Benchmark Report/i)).toHaveAttribute(
      "href",
      "/benchmarks",
    );

    fireEvent.click(screen.getByRole("button", { name: "Pure FAIM CPU" }));
    expect(
      screen.getByText("Scenario 1: Pure FAIM Zero-ML (CPU Only)"),
    ).toBeInTheDocument();
  });
});
