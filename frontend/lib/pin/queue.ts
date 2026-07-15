import type { PinEntry } from "./types";

export const STORAGE_KEY = "checkboard.pinQueue.v1";

export function createMemoryStorage(): Storage {
  const map = new Map<string, string>();
  return {
    get length() {
      return map.size;
    },
    clear() {
      map.clear();
    },
    getItem(key: string) {
      return map.has(key) ? map.get(key)! : null;
    },
    key(index: number) {
      return Array.from(map.keys())[index] ?? null;
    },
    removeItem(key: string) {
      map.delete(key);
    },
    setItem(key: string, value: string) {
      map.set(key, value);
    },
  };
}

function isPinEntry(value: unknown): value is PinEntry {
  if (!value || typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  return typeof v.fixtureId === "string" && typeof v.homeName === "string" && typeof v.awayName === "string";
}

export function loadQueue(storage: Storage): PinEntry[] {
  try {
    const raw = storage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as unknown;
    if (!Array.isArray(parsed)) return [];
    return parsed.filter(isPinEntry);
  } catch {
    return [];
  }
}

export function saveQueue(storage: Storage, entries: PinEntry[]): void {
  storage.setItem(STORAGE_KEY, JSON.stringify(entries));
}

export function pinMatch(entries: PinEntry[], entry: PinEntry): PinEntry[] {
  if (entries.some((e) => e.fixtureId === entry.fixtureId)) return entries;
  return [...entries, entry];
}

export function unpinMatch(entries: PinEntry[], fixtureId: string): PinEntry[] {
  return entries.filter((e) => e.fixtureId !== fixtureId);
}

export function reorderQueue(entries: PinEntry[], fromIndex: number, toIndex: number): PinEntry[] {
  if (
    fromIndex < 0 ||
    toIndex < 0 ||
    fromIndex >= entries.length ||
    toIndex >= entries.length ||
    fromIndex === toIndex
  ) {
    return entries;
  }
  const next = [...entries];
  const [item] = next.splice(fromIndex, 1);
  next.splice(toIndex, 0, item);
  return next;
}

export function getActiveEntry(entries: PinEntry[]): PinEntry | null {
  return entries[0] ?? null;
}
