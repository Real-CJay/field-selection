const PREVIEW_STUDENT_INDEX_NUMBERS = new Set(['250314P', '250544U']);

export function isMaintenancePreviewStudent(indexNumber: string | null | undefined): boolean {
  return typeof indexNumber === 'string'
    && PREVIEW_STUDENT_INDEX_NUMBERS.has(indexNumber.trim().toUpperCase());
}
