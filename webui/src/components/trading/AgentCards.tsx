export interface AgentCard {
  kind: string;
  [key: string]: unknown;
}

interface AgentCardsProps {
  cards: AgentCard[];
}

export function AgentCards({ cards }: AgentCardsProps) {
  if (!cards.length) {
    return (
      <p className="text-sm text-muted-foreground">No recommendation cards yet.</p>
    );
  }

  return (
    <div className="flex flex-col gap-3">
      {cards.map((card, index) => (
        <article
          key={`${card.kind}-${index}`}
          className="rounded-lg border bg-card p-4 text-sm shadow-sm"
        >
          <header className="mb-2 font-medium capitalize">
            {card.kind.replace(/_/g, " ")}
          </header>
          <pre className="whitespace-pre-wrap break-words text-xs text-muted-foreground">
            {JSON.stringify(card, null, 2)}
          </pre>
        </article>
      ))}
    </div>
  );
}
