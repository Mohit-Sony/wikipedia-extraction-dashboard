"""
Performance Monitor

Centralized performance tracking and monitoring for Wikidata integration.
Provides system-wide metrics collection, analysis, and reporting.

Implemented in Phase 4 (Step 11): Performance Optimization.
"""

import logging
import time
from typing import Dict, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """
    Centralized performance monitoring for Wikidata enrichment pipeline.

    Tracks metrics from all components (client, parser, enricher, cache)
    and provides unified reporting and analysis.
    """

    def __init__(self):
        """Initialize performance monitor."""
        self.start_time = time.time()
        self.metrics = {
            # Client metrics
            'client_api_calls': 0,
            'client_cache_hits': 0,
            'client_cache_misses': 0,
            'client_total_fetch_time': 0.0,
            'client_errors': 0,

            # Parser metrics
            'parser_entities_parsed': 0,
            'parser_total_parse_time': 0.0,
            'parser_properties_extracted': 0,
            'parser_parse_errors': 0,

            # Enricher metrics
            'enricher_total_enriched': 0,
            'enricher_successful': 0,
            'enricher_failed': 0,
            'enricher_total_time': 0.0,

            # Cache metrics
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_size': 0,
            'cache_saves': 0,

            # Overall metrics
            'total_entities_processed': 0,
            'total_pipeline_time': 0.0,
            'peak_memory_mb': 0.0
        }

        logger.info("PerformanceMonitor initialized")

    def record_client_call(self, fetch_time: float, cache_hit: bool = False, error: bool = False):
        """
        Record a client API call.

        Args:
            fetch_time: Time taken for the fetch operation
            cache_hit: Whether this was a cache hit
            error: Whether an error occurred
        """
        if cache_hit:
            self.metrics['client_cache_hits'] += 1
        else:
            self.metrics['client_cache_misses'] += 1
            self.metrics['client_api_calls'] += 1
            self.metrics['client_total_fetch_time'] += fetch_time

        if error:
            self.metrics['client_errors'] += 1

    def record_parse(self, parse_time: float, properties_count: int, error: bool = False):
        """
        Record a parsing operation.

        Args:
            parse_time: Time taken to parse
            properties_count: Number of properties extracted
            error: Whether an error occurred
        """
        self.metrics['parser_entities_parsed'] += 1
        self.metrics['parser_total_parse_time'] += parse_time
        self.metrics['parser_properties_extracted'] += properties_count

        if error:
            self.metrics['parser_parse_errors'] += 1

    def record_enrichment(self, enrich_time: float, success: bool = True):
        """
        Record an enrichment operation.

        Args:
            enrich_time: Time taken for enrichment
            success: Whether enrichment was successful
        """
        self.metrics['enricher_total_enriched'] += 1
        self.metrics['enricher_total_time'] += enrich_time

        if success:
            self.metrics['enricher_successful'] += 1
        else:
            self.metrics['enricher_failed'] += 1

    def record_cache_operation(self, hit: bool = False, miss: bool = False, save: bool = False):
        """
        Record a cache operation.

        Args:
            hit: Cache hit occurred
            miss: Cache miss occurred
            save: Cache save occurred
        """
        if hit:
            self.metrics['cache_hits'] += 1
        if miss:
            self.metrics['cache_misses'] += 1
        if save:
            self.metrics['cache_saves'] += 1

    def update_cache_size(self, size: int):
        """
        Update current cache size.

        Args:
            size: Current number of items in cache
        """
        self.metrics['cache_size'] = size

    def get_metrics(self) -> Dict:
        """
        Get current metrics with calculated statistics.

        Returns:
            Dictionary with all metrics and derived statistics
        """
        metrics = self.metrics.copy()

        # Calculate derived metrics
        total_requests = metrics['client_cache_hits'] + metrics['client_cache_misses']
        if total_requests > 0:
            metrics['client_cache_hit_rate'] = (
                metrics['client_cache_hits'] / total_requests * 100
            )
        else:
            metrics['client_cache_hit_rate'] = 0.0

        if metrics['client_api_calls'] > 0:
            metrics['client_avg_fetch_time'] = (
                metrics['client_total_fetch_time'] / metrics['client_api_calls']
            )
        else:
            metrics['client_avg_fetch_time'] = 0.0

        if metrics['parser_entities_parsed'] > 0:
            metrics['parser_avg_parse_time'] = (
                metrics['parser_total_parse_time'] / metrics['parser_entities_parsed']
            )
            metrics['parser_avg_properties_per_entity'] = (
                metrics['parser_properties_extracted'] / metrics['parser_entities_parsed']
            )
        else:
            metrics['parser_avg_parse_time'] = 0.0
            metrics['parser_avg_properties_per_entity'] = 0.0

        if metrics['enricher_total_enriched'] > 0:
            metrics['enricher_success_rate'] = (
                metrics['enricher_successful'] / metrics['enricher_total_enriched'] * 100
            )
            metrics['enricher_avg_time'] = (
                metrics['enricher_total_time'] / metrics['enricher_total_enriched']
            )
        else:
            metrics['enricher_success_rate'] = 0.0
            metrics['enricher_avg_time'] = 0.0

        total_cache_ops = metrics['cache_hits'] + metrics['cache_misses']
        if total_cache_ops > 0:
            metrics['cache_hit_rate'] = (
                metrics['cache_hits'] / total_cache_ops * 100
            )
        else:
            metrics['cache_hit_rate'] = 0.0

        # Overall metrics
        metrics['total_elapsed_time'] = time.time() - self.start_time

        if metrics['total_elapsed_time'] > 0:
            metrics['entities_per_second'] = (
                metrics['enricher_total_enriched'] / metrics['total_elapsed_time']
            )
        else:
            metrics['entities_per_second'] = 0.0

        # Calculate overhead
        if metrics['enricher_total_time'] > 0:
            api_overhead = (
                metrics['client_total_fetch_time'] / metrics['enricher_total_time'] * 100
            )
            parse_overhead = (
                metrics['parser_total_parse_time'] / metrics['enricher_total_time'] * 100
            )
            metrics['api_time_overhead_pct'] = api_overhead
            metrics['parse_time_overhead_pct'] = parse_overhead
        else:
            metrics['api_time_overhead_pct'] = 0.0
            metrics['parse_time_overhead_pct'] = 0.0

        return metrics

    def log_metrics(self, detailed: bool = True):
        """
        Log performance metrics.

        Args:
            detailed: Whether to log detailed metrics or summary only
        """
        metrics = self.get_metrics()

        logger.info("=" * 70)
        logger.info("WIKIDATA INTEGRATION PERFORMANCE METRICS")
        logger.info("=" * 70)

        # Overall metrics
        logger.info("OVERALL PERFORMANCE:")
        logger.info(f"  Total Elapsed Time:     {metrics['total_elapsed_time']:.2f}s")
        logger.info(f"  Entities Processed:     {metrics['enricher_total_enriched']}")
        logger.info(f"  Entities/Second:        {metrics['entities_per_second']:.2f}")
        logger.info(f"  Success Rate:           {metrics['enricher_success_rate']:.1f}%")

        if detailed:
            logger.info("")
            logger.info("CLIENT METRICS:")
            logger.info(f"  API Calls:              {metrics['client_api_calls']}")
            logger.info(f"  Cache Hits:             {metrics['client_cache_hits']}")
            logger.info(f"  Cache Misses:           {metrics['client_cache_misses']}")
            logger.info(f"  Cache Hit Rate:         {metrics['client_cache_hit_rate']:.1f}%")
            logger.info(f"  Avg Fetch Time:         {metrics['client_avg_fetch_time']:.3f}s")
            logger.info(f"  Total Fetch Time:       {metrics['client_total_fetch_time']:.2f}s")
            logger.info(f"  Errors:                 {metrics['client_errors']}")

            logger.info("")
            logger.info("PARSER METRICS:")
            logger.info(f"  Entities Parsed:        {metrics['parser_entities_parsed']}")
            logger.info(f"  Properties Extracted:   {metrics['parser_properties_extracted']}")
            logger.info(f"  Avg Properties/Entity:  {metrics['parser_avg_properties_per_entity']:.1f}")
            logger.info(f"  Avg Parse Time:         {metrics['parser_avg_parse_time']:.3f}s")
            logger.info(f"  Total Parse Time:       {metrics['parser_total_parse_time']:.2f}s")
            logger.info(f"  Parse Errors:           {metrics['parser_parse_errors']}")

            logger.info("")
            logger.info("ENRICHER METRICS:")
            logger.info(f"  Total Enriched:         {metrics['enricher_total_enriched']}")
            logger.info(f"  Successful:             {metrics['enricher_successful']}")
            logger.info(f"  Failed:                 {metrics['enricher_failed']}")
            logger.info(f"  Avg Enrichment Time:    {metrics['enricher_avg_time']:.3f}s")
            logger.info(f"  Total Enrichment Time:  {metrics['enricher_total_time']:.2f}s")

            logger.info("")
            logger.info("CACHE METRICS:")
            logger.info(f"  Cache Hits:             {metrics['cache_hits']}")
            logger.info(f"  Cache Misses:           {metrics['cache_misses']}")
            logger.info(f"  Cache Hit Rate:         {metrics['cache_hit_rate']:.1f}%")
            logger.info(f"  Cache Size:             {metrics['cache_size']}")
            logger.info(f"  Cache Saves:            {metrics['cache_saves']}")

            logger.info("")
            logger.info("PERFORMANCE BREAKDOWN:")
            logger.info(f"  API Time Overhead:      {metrics['api_time_overhead_pct']:.1f}%")
            logger.info(f"  Parse Time Overhead:    {metrics['parse_time_overhead_pct']:.1f}%")

        logger.info("=" * 70)

    def get_summary_report(self) -> str:
        """
        Get a formatted summary report.

        Returns:
            Formatted string report
        """
        metrics = self.get_metrics()

        report = []
        report.append("=" * 70)
        report.append("WIKIDATA INTEGRATION PERFORMANCE SUMMARY")
        report.append("=" * 70)
        report.append(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Total Runtime: {metrics['total_elapsed_time']:.2f}s")
        report.append("")
        report.append(f"Entities Processed: {metrics['enricher_total_enriched']}")
        report.append(f"Success Rate: {metrics['enricher_success_rate']:.1f}%")
        report.append(f"Processing Speed: {metrics['entities_per_second']:.2f} entities/sec")
        report.append("")
        report.append(f"API Calls: {metrics['client_api_calls']}")
        report.append(f"Cache Hit Rate: {metrics['client_cache_hit_rate']:.1f}%")
        report.append(f"Avg Fetch Time: {metrics['client_avg_fetch_time']:.3f}s")
        report.append("")
        report.append(f"Avg Properties/Entity: {metrics['parser_avg_properties_per_entity']:.1f}")
        report.append(f"Avg Enrichment Time: {metrics['enricher_avg_time']:.3f}s")
        report.append("=" * 70)

        return "\n".join(report)

    def check_performance_targets(self) -> Dict[str, bool]:
        """
        Check if performance meets targets defined in implementation plan.

        Targets from Phase 4 Step 11:
        - Enrichment overhead < 20%
        - Cache hit rate > 60%
        - Avg fetch time < 2s
        - Memory usage < 200MB

        Returns:
            Dictionary with target checks
        """
        metrics = self.get_metrics()

        targets = {
            'cache_hit_rate_above_60pct': metrics['client_cache_hit_rate'] >= 60.0,
            'avg_fetch_time_under_2s': metrics['client_avg_fetch_time'] < 2.0,
            'success_rate_above_90pct': metrics['enricher_success_rate'] >= 90.0,
            'entities_per_sec_above_15': metrics['entities_per_second'] >= 15.0,
        }

        return targets

    def reset_metrics(self):
        """Reset all metrics to zero."""
        self.start_time = time.time()
        self.metrics = {
            'client_api_calls': 0,
            'client_cache_hits': 0,
            'client_cache_misses': 0,
            'client_total_fetch_time': 0.0,
            'client_errors': 0,
            'parser_entities_parsed': 0,
            'parser_total_parse_time': 0.0,
            'parser_properties_extracted': 0,
            'parser_parse_errors': 0,
            'enricher_total_enriched': 0,
            'enricher_successful': 0,
            'enricher_failed': 0,
            'enricher_total_time': 0.0,
            'cache_hits': 0,
            'cache_misses': 0,
            'cache_size': 0,
            'cache_saves': 0,
            'total_entities_processed': 0,
            'total_pipeline_time': 0.0,
            'peak_memory_mb': 0.0
        }
        logger.info("Performance metrics reset")


# Global performance monitor instance (singleton pattern)
_global_monitor: Optional[PerformanceMonitor] = None


def get_global_monitor() -> PerformanceMonitor:
    """
    Get or create the global performance monitor instance.

    Returns:
        PerformanceMonitor singleton instance
    """
    global _global_monitor
    if _global_monitor is None:
        _global_monitor = PerformanceMonitor()
    return _global_monitor


def reset_global_monitor():
    """Reset the global performance monitor."""
    global _global_monitor
    if _global_monitor:
        _global_monitor.reset_metrics()
    else:
        _global_monitor = PerformanceMonitor()
