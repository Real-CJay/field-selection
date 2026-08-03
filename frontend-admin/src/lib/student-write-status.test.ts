import { describe, expect, it } from 'vitest';
import {
  CORRECTION_REQUESTS_UNAVAILABLE,
  GRADE_EDITING_UNAVAILABLE,
  PREFERENCE_EDITING_UNAVAILABLE
} from './student-write-status';

describe('read-only student write messages', () => {
  it('clearly marks every student write workflow as unavailable', () => {
    for (const message of [
      PREFERENCE_EDITING_UNAVAILABLE,
      GRADE_EDITING_UNAVAILABLE,
      CORRECTION_REQUESTS_UNAVAILABLE
    ]) {
      expect(message).toContain('currently under work');
      expect(message).toContain('Please try again later.');
    }
  });
});
