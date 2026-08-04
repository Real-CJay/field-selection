import { render } from 'svelte/server';
import { describe, expect, it } from 'vitest';
import ModuleGradesPage from '../routes/module-grades/+page.svelte';
import PreferencesPage from '../routes/preferences/+page.svelte';
import ResultsPage from '../routes/results/+page.svelte';
import AdminPage from '../routes/admin/+page.svelte';
import StudentCredentialModal from './components/StudentCredentialModal.svelte';

describe('student flow', () => {
  it('renders required Fluid Mechanics and Mechanics grade fields', () => {
    const { body } = render(ModuleGradesPage);

    expect(body).toContain('Module Grades');
    expect(body).toContain('Fluid Mechanics');
    expect(body).toContain('Mechanics');
    expect(body).toContain('Continue to Preferences');
    expect(body.match(/Select your grade/g)).toHaveLength(2);
  });

  it('keeps preferences focused on department ranking', () => {
    const { body } = render(PreferencesPage);

    expect(body).toContain('Rank your preferences');
    expect(body).not.toContain('Not enough students');
    expect(body).not.toContain('Live estimated allocation');
  });

  it('provides a separate results page with grades and cold-start feedback', () => {
    const { body } = render(ResultsPage);

    expect(body).toContain('Your Results');
    expect(body).toContain('Module grades');
    expect(body).toContain('Waking up the server and calculating estimates...');
    expect(body).toContain('Edit Fluid/Mechanics grades');
  });

  it('provides the protected admin dashboard shell', () => {
    const { body } = render(AdminPage);
    expect(body).toContain('Field Selection Admin');
    expect(body).toContain('Student full records');
    expect(body).toContain('Recorrection requests');
    expect(body).toContain('Departments');
  });

  it('shows only the recovery-code path before a personal password exists', () => {
    const { body } = render(StudentCredentialModal, {
      props: {
        open: true,
        indexNumber: '250544U',
        hasPersonalPassword: false,
        onAuthenticated: () => undefined,
        onCancel: () => undefined
      }
    });

    expect(body).toContain('16-digit recovery code');
    expect(body).toContain('create your personal password');
    expect(body).toContain('please ask your E-Group representative for it');
    expect(body).not.toContain('Use personal password');
  });

  it('offers password login and recovery reset after a password exists', () => {
    const { body } = render(StudentCredentialModal, {
      props: {
        open: true,
        indexNumber: '250544U',
        hasPersonalPassword: true,
        onAuthenticated: () => undefined,
        onCancel: () => undefined
      }
    });

    expect(body).toContain('Use personal password');
    expect(body).toContain('Use/reset with 16-digit code');
  });
});
