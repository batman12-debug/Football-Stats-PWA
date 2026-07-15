export interface PinEntry {
  fixtureId: string;
  homeName: string;
  awayName: string;
  homeCode: string | null;
  awayCode: string | null;
  homeLogo: string | null;
  awayLogo: string | null;
  /** e.g. "Semi-finals" — shown on the rich notification card */
  stageLabel: string | null;
  kickoffIso: string;
  pinnedAt: number;
}
