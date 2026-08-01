export interface AdminCredentials {
  username: string;
  password: string;
}

let credentials: AdminCredentials | null = null;

export function setAdminCredentials(value: AdminCredentials): void {
  credentials = value;
}

export function getAdminCredentials(): AdminCredentials | null {
  return credentials;
}

export function clearAdminCredentials(): void {
  credentials = null;
}
