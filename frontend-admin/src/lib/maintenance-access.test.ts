import { describe, expect, it } from 'vitest';
import { isMaintenancePreviewStudent } from './maintenance-access';

describe('maintenance preview access', () => {
  it('allows only the two approved student index numbers', () => {
    expect(isMaintenancePreviewStudent('250314p')).toBe(true);
    expect(isMaintenancePreviewStudent(' 250544U ')).toBe(true);
    expect(isMaintenancePreviewStudent('250745L')).toBe(false);
    expect(isMaintenancePreviewStudent(null)).toBe(false);
  });
});
