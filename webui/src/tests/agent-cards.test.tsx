import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AgentCards } from "@/components/trading/AgentCards";

describe("AgentCards", () => {
  it("renders decision and gate checklist without raw JSON", () => {
    render(
      <AgentCards
        cards={[
          {
            kind: "decision",
            decision: "buy",
            summary: "Breakout setup",
            confidence: 0.72,
          },
          {
            kind: "gate_checklist",
            allowed: true,
            verdicts: [
              { id: "G1", name: "News", status: "unavailable", reason: "not configured" },
              { id: "G6", name: "Risk geometry", status: "pass", reason: "" },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText("BUY")).toBeInTheDocument();
    expect(screen.getByText("Breakout setup")).toBeInTheDocument();
    expect(screen.getByText("G1")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/"kind": "decision"/)).not.toBeInTheDocument();
  });
});
