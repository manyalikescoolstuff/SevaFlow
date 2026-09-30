/**
 * A service offered at the service centre (e.g. "KYC", "New account").
 * Each counter is assigned exactly one service at a time.
 * Each queue corresponds to exactly one service.
 */
export interface Service {
  id: string;
  name: string;
  /** Average expected duration in seconds for this service type */
  expectedDurationSec: number;
}
