export function isQatarTeam(team: { name: string; code: string | null }): boolean {
  return team.code?.toUpperCase() === "QAT" || team.name.toLowerCase() === "qatar";
}
