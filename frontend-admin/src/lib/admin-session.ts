export interface AdminSession {
  username: string;
  token: string;
}

let adminSession: AdminSession | null = null;

export function setAdminSession(value: AdminSession): void {
  adminSession = { ...value };
}

export function getAdminSession(): AdminSession | null {
  return adminSession ? { ...adminSession } : null;
}

export function clearAdminSession(): void {
  adminSession = null;
}
