export interface PinEntry {
  fixtureId: string;
  homeName: string;
  awayName: string;
  homeCode: string | null;
  awayCode: string | null;
  kickoffIso: string;
  pinnedAt: number;
}
