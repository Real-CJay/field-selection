import { env } from '$env/dynamic/public';
import { createAllocationClient } from './allocation';

export function createConfiguredAllocationClient(fetcher: typeof fetch = fetch) {
  const baseUrl = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!baseUrl) {
    throw new Error('PUBLIC_API_BASE_URL is not configured.');
  }

  return createAllocationClient({
    fetcher,
    requestForIndex: (indexNumber) => ({
      input: `${baseUrl}/api/allocation/${encodeURIComponent(indexNumber)}`
    })
  });
}
