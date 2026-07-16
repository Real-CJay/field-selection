import type { FieldSelectionApi } from '$lib/types';
import { httpApi } from './http';
import { mockApi } from './mock';

export const apiMode = import.meta.env.PUBLIC_API_MODE === 'http' ? 'http' : 'mock';
export const api: FieldSelectionApi = apiMode === 'http' ? httpApi : mockApi;
