import { env } from '$env/dynamic/public';
import { createAllocationClient } from './allocation';
import { getStudentApiToken } from './student-api-session';

export function createConfiguredAllocationClient(fetcher: typeof fetch = fetch) {
  const baseUrl = env.PUBLIC_API_BASE_URL?.replace(/\/+$/, '');
  if (!baseUrl) {
    throw new Error('PUBLIC_API_BASE_URL is not configured.');
  }

  return {
    async getAllocation(indexNumber: string) {
      const token = await getStudentApiToken();
      return createAllocationClient({
        fetcher,
        requestForIndex: (requestedIndex) => ({
          input: `${baseUrl}/api/allocation/${encodeURIComponent(requestedIndex)}`,
          init: { headers: { Authorization: `Bearer ${token}` } }
        })
      }).getAllocation(indexNumber);
    }
  };
}
