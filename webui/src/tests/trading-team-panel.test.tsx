import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { TradingTeamPanel } from "@/components/trading/TradingTeamPanel";

describe("TradingTeamPanel", () => {
  it("renders agent roles and summaries", () => {
    render(
      <TradingTeamPanel
        teamMode="swarm:gold_analysis_committee"
        agents={[
          {
            agentId: "macro_analyst",
            role: "Macro Analyst",
            status: "done",
            summary: "USD softer, gold supported.",
            layer: 0,
          },
        ]}
      />,
    );

    expect(screen.getByText("Macro Analyst")).toBeInTheDocument();
    expect(screen.getByText("USD softer, gold supported.")).toBeInTheDocument();
  });
});
