export const colors = {
  bg: "#0b0f14",
  surface: "#121821",
  surfaceRaised: "#1a222d",
  border: "#243040",
  text: "#e8edf3",
  textMuted: "#8b98a8",
  accent: "#f5b833",
  accentText: "#1a1200",
  success: "#2fbf71",
  warning: "#f2a33a",
  danger: "#e5484d",
  info: "#4c9aff",
  buy: "#2fbf71",
  sell: "#e5484d",
  wait: "#8b98a8",
} as const;

export const spacing = { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 } as const;

export const radius = { sm: 8, md: 12, lg: 16, pill: 999 } as const;

export const font = {
  xs: 11,
  sm: 13,
  md: 15,
  lg: 18,
  xl: 24,
} as const;

export type StateTone = "working" | "waiting" | "completed" | "error";

export function toneColor(tone: StateTone): string {
  switch (tone) {
    case "working":
      return colors.info;
    case "waiting":
      return colors.warning;
    case "completed":
      return colors.success;
    case "error":
      return colors.danger;
  }
}
