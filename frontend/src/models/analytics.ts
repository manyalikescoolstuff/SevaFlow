/**
 * Hourly aggregated operational metric for operational hours.
 */
export interface HourlyOperationalMetric {
  /** Hour of day (e.g. 9 for 09:00) */
  hour: number;
  /** Formatted hour label (e.g. "09:00" or "09:00–10:00") */
  label: string;
  /** Total visitor footfall in this hour */
  footfall: number;
  /** Average waiting time in seconds in this hour */
  avgWaitSec: number;
}

/**
 * Historical service performance and volume metrics.
 * Separates demand (tokens generated) from successfully completed/served, waiting, and missed tokens.
 */
export interface ServicePerformanceRecord {
  serviceId: string;
  serviceName: string;
  /** Total service requests / tokens generated for this service (Demand) */
  tokensGenerated: number;
  /** Tokens successfully completed and served */
  customersServed: number;
  /** Tokens currently waiting in queue */
  currentlyWaiting: number;
  /** Average wait time of completed tokens in seconds */
  avgWaitTimeSec: number;
  /** Average handling / service time of completed tokens in seconds */
  avgServiceTimeSec: number;
  /** Missed / no-show tokens */
  missedTokens: number;
}

/**
 * Aggregated analytics / KPI data for the service centre.
 * Represents historical / current-day operational metrics with strict lifecycle distinction.
 *
 * NOTE ON V1 PROTOTYPE DATA-MODEL ASSUMPTION:
 * For the V1 frontend prototype, we assume:
 *   1 registered visitor = 1 service request/token
 * This is why Total Visitors Today (79) currently equals total Service Demand / Tokens Issued (79).
 * Later, physical footfall from IR sensors and actual token kiosk generations will be tracked as separate metrics.
 *
 * Current lifecycle relationship preserved across centralized data:
 *   79 requests = 59 completed + 9 waiting + 6 missed + 5 currently serving
 */
export interface AnalyticsSnapshot {
  /** Total visitors registered/entered the centre today */
  totalFootfallToday: number;

  /** Total service tokens generated today across all services */
  totalTokensIssued: number;
  /** Total customers successfully served / completed today */
  totalServedToday: number;
  /** Total tokens currently waiting across all queues */
  totalWaitingToday: number;
  /** Total missed tokens today */
  totalMissedToday: number;
  /** Weighted average waiting time in seconds (across all completed tokens today) */
  avgWaitTimeSec: number;
  /** Weighted average service handling time in seconds (across all completed tokens today) */
  avgServiceTimeSec: number;
  /** Peak hour of the day (0-23) based on historical data */
  peakHour: number;
  /** Hourly footfall breakdown: index = hour (0-23), value = count */
  hourlyFootfall: number[];
  /** Hourly average wait time in seconds: index = hour */
  hourlyAvgWaitSec: number[];
  /** Operating hours breakdown (09:00 – 17:00) */
  operatingHours: HourlyOperationalMetric[];
  /** Historical per-service performance breakdown */
  servicePerformance: Record<string, ServicePerformanceRecord>;
}


