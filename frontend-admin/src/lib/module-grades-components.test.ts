import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import ModuleGradesPage from '../routes/module-grades/+page.svelte';
import PreferencesPage from '../routes/preferences/+page.svelte';

describe('module grade flow', () => {
  it('renders required Fluid Mechanics and Mechanics grade fields', () => {
    const { body } = render(ModuleGradesPage);

    expect(body).toContain('Module Grades');
    expect(body).toContain('Fluid Mechanics');
    expect(body).toContain('Mechanics');
    expect(body).toContain('Continue to Preferences');
    expect(body.match(/Select your grade/g)).toHaveLength(2);
  });

  it('keeps estimates hidden behind the admin-approval waiting message', () => {
    const { body } = render(PreferencesPage);

    expect(body).toContain('Not enough students have filled the form yet.');
    expect(body).toContain('Fluid Mechanics and Mechanics grades');
    expect(body).toContain('after the admin approves them');
    expect(body).not.toContain('Live estimated allocation');
  });
});
