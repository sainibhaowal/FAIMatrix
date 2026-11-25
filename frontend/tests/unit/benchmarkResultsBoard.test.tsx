import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import BenchmarkResultsBoard from "@/components/landing/BenchmarkResultsBoard";

describe("BenchmarkResultsBoard", () => {
  it("renders signed BeIR, LoCoMo, and historical progression metrics in production framing", () => {
    render(<BenchmarkResultsBoard />);

    expect(screen.getAllByText(/0\.6900/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.6871/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.3314/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.3387/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.0710/).length).toBeGreaterThan(0);
    expect(screen.getAllByText(/0\.0517/).length).toBeGreaterThan(0);
    expect(screen.getByText(/Full Benchmark Report/i)).toHaveAttribute(
      "href",
      "/benchmarks",
    );

    fireEvent.click(screen.getByRole("button", { name: "FAIM-Pure CPU" }));
    expect(
      screen.getByText("FAIM-Pure · Zero-ML Native Engine (CPU)"),
    ).toBeInTheDocument();
  });
});
