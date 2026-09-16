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

    expect(screen.getByText("buy")).toBeInTheDocument();
    expect(screen.getByText("Breakout setup")).toBeInTheDocument();
    expect(screen.getByText("News & event shield")).toBeInTheDocument();
    expect(screen.getByText("Unavailable")).toBeInTheDocument();
    expect(screen.queryByText(/"kind": "decision"/)).not.toBeInTheDocument();
  });

  it("shows i18n names for G8–G20 and never the raw ids", () => {
    render(
      <AgentCards
        locale="en"
        cards={[
          {
            kind: "gate_checklist",
            allowed: false,
            verdicts: [
              { id: "G8", status: "veto", reason: "RR too low" },
              { id: "G20", status: "pass", reason: "" },
            ],
          },
        ]}
      />,
    );

    expect(screen.getByText("Minimum reward-to-risk")).toBeInTheDocument();
    expect(screen.getByText("Position sizing")).toBeInTheDocument();
    expect(screen.queryByText("G8")).not.toBeInTheDocument();
    expect(screen.queryByText("G20")).not.toBeInTheDocument();
  });

  it("uses Arabic gate names from the language map", () => {
    render(
      <AgentCards
        locale="ar"
        cards={[
          {
            kind: "gate_checklist",
            allowed: false,
            verdicts: [{ id: "G12", status: "veto", reason: "" }],
          },
        ]}
      />,
    );

    expect(screen.getByText("قاطع التراجع ومفتاح الإيقاف")).toBeInTheDocument();
    expect(screen.queryByText("G12")).not.toBeInTheDocument();
  });
});
