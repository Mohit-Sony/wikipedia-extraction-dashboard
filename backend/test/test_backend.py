#!/usr/bin/env python3
"""
Strategic API Endpoint Testing Script for Wikipedia Extraction Dashboard
Tests all 42 endpoints efficiently with realistic data flows and dependencies

Usage:
    python test_all_endpoints.py [--base-url URL] [--verbose] [--report] [--category CATEGORY]

Examples:
    python test_all_endpoints.py                           # Test all endpoints
    python test_all_endpoints.py --category core           # Test only core endpoints
    python test_all_endpoints.py --verbose --report        # Detailed testing with HTML report
"""

import asyncio
import json
import time
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

# Testing dependencies
import httpx
import websockets
from dataclasses import dataclass, asdict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class EndpointResult:
    """Result of testing a single endpoint"""
    endpoint: str
    method: str
    status_code: int
    response_time: float
    success: bool
    error_message: Optional[str] = None
    response_data: Optional[Dict] = None

@dataclass
class TestSummary:
    """Overall test execution summary"""
    total_endpoints: int
    successful: int
    failed: int
    duration: float
    categories_tested: List[str]
    critical_failures: List[str]

class StrategicEndpointTester:
    """Strategic tester that handles endpoint dependencies and realistic data flows"""
    
    def __init__(self, base_url: str = "http://localhost:8000", verbose: bool = False):
        self.base_url = base_url.rstrip('/')
        self.verbose = verbose
        self.client = None
        self.results: List[EndpointResult] = []
        self.test_data: Dict[str, Any] = {}
        
        # Strategic test order - dependencies first
        self.test_categories = {
            "core": [
                ("GET", "/", "API root"),
                ("GET", "/health", "Health check"),
                ("GET", "/docs", "API documentation")
            ],
            "system": [
                ("GET", "/api/v1/validate", "System validation"),
                ("GET", "/api/v1/system/stats", "System statistics"),
                ("POST", "/api/v1/sync", "Database sync")
            ],
            "entities_basic": [
                ("GET", "/api/v1/entities", "List entities"),
                ("POST", "/api/v1/entities/manual", "Create manual entity"),
                ("GET", "/api/v1/entities/{qid}", "Get specific entity"),
                ("PUT", "/api/v1/entities/{qid}", "Update entity"),
                ("GET", "/api/v1/entities/{qid}/preview", "Entity preview"),
                ("GET", "/api/v1/entities/{qid}/relationships", "Entity relationships"),
                ("GET", "/api/v1/entities/search/suggestions", "Search suggestions")
            ],
            "queues": [
                ("GET", "/api/v1/queues", "All queues overview"),
                ("POST", "/api/v1/queues/entries", "Add to queue"),
                ("GET", "/api/v1/queues/{queue_type}", "Specific queue"),
                ("PUT", "/api/v1/queues/entries/{entry_id}", "Update queue entry"),
                ("POST", "/api/v1/queues/batch", "Batch operations"),
                ("GET", "/api/v1/queues/stats", "Queue statistics"),
                ("GET", "/api/v1/queues/review/sources", "Review sources"),
                ("POST", "/api/v1/queues/review/bulk-approve", "Bulk approve"),
                ("POST", "/api/v1/queues/review/bulk-reject", "Bulk reject"),
                ("DELETE", "/api/v1/queues/entries/{entry_id}", "Remove from queue")
            ],
            "extraction": [
                ("GET", "/api/v1/extraction/config", "Get extraction config"),
                ("POST", "/api/v1/extraction/configure", "Configure extraction"),
                ("GET", "/api/v1/extraction/status", "Extraction status"),
                ("GET", "/api/v1/extraction/queue-stats", "Extraction queue stats"),
                ("POST", "/api/v1/extraction/start", "Start extraction"),
                ("POST", "/api/v1/extraction/pause", "Pause extraction"),
                ("POST", "/api/v1/extraction/resume", "Resume extraction"),
                ("POST", "/api/v1/extraction/cancel", "Cancel extraction"),
                ("GET", "/api/v1/extraction/sessions", "Extraction sessions"),
                ("GET", "/api/v1/extraction/sessions/{id}/logs", "Session logs")
            ],
            "analytics": [
                ("GET", "/api/v1/analytics/dashboard", "Dashboard stats"),
                ("GET", "/api/v1/analytics/extraction-trends", "Extraction trends"),
                ("GET", "/api/v1/analytics/type-analysis", "Type analysis"),
                ("GET", "/api/v1/analytics/depth-analysis", "Depth analysis"),
                ("GET", "/api/v1/analytics/queue-flow", "Queue flow"),
                ("GET", "/api/v1/analytics/user-decisions", "User decisions"),
                ("GET", "/api/v1/analytics/content-quality", "Content quality"),
                ("GET", "/api/v1/analytics/extraction-performance", "Performance"),
                ("GET", "/api/v1/analytics/top-entities", "Top entities")
            ],
            "deduplication": [
                ("GET", "/api/v1/deduplication/stats", "Deduplication stats")
            ],
            "websocket": [
                ("GET", "/api/v1/websocket/stats", "WebSocket stats"),
                ("POST", "/api/v1/websocket/broadcast", "Manual broadcast"),
                ("WS", "/api/v1/ws", "WebSocket connection")
            ],
            "pipeline": [
                ("POST", "/api/v1/pipeline/entity-extracted", "Pipeline notification")
            ]
        }
    
    async def setup_client(self):
        """Initialize HTTP client"""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=30.0,
            headers={"Content-Type": "application/json"}
        )
    
    async def cleanup_client(self):
        """Cleanup HTTP client"""
        if self.client:
            await self.client.aclose()
    
    def generate_test_data(self) -> Dict[str, Any]:
        """Generate realistic test data for API calls"""
        timestamp = int(time.time())
        return {
            # Manual entity data
            "manual_entity": {
                "title": f"Test Entity {timestamp}",
                "type": "test",
                "short_desc": "A test entity for endpoint testing",
                "add_to_queue": "active",
                "priority": 2
            },
            # Queue entry data
            "queue_entry": {
                "queue_type": "active",
                "priority": 2,
                "notes": "Test queue entry"
            },
            # Batch operation data
            "batch_operation": {
                "operation": "move",
                "qids": [],  # Will be populated with test entities
                "target_queue": "on_hold",
                "priority": 2
            },
            # Extraction config
            "extraction_config": {
                "max_concurrent": 2,
                "delay_between_requests": 1.0,
                "max_retries": 3,
                "enable_deduplication": True
            },
            # Extraction start request
            "extraction_start": {
                "queue_types": ["active"],
                "session_name": f"Test Session {timestamp}"
            },
            # Bulk review operations
            "bulk_approve": {
                "qids": [],
                "target_queue": "active",
                "priority": 2
            },
            # WebSocket broadcast
            "websocket_broadcast": {
                "type": "test_message",
                "data": {"message": "Test broadcast", "timestamp": timestamp}
            },
            # Pipeline notification
            "pipeline_notification": {
                "qid": f"Q{timestamp}",
                "title": "Pipeline Test Entity",
                "type": "test",
                "status": "completed"
            }
        }
    
    async def test_endpoint(self, method: str, endpoint: str, description: str, 
                          data: Optional[Dict] = None) -> EndpointResult:
        """Test a single endpoint strategically"""
        start_time = time.time()
        
        try:
            # Handle URL parameter substitution
            test_url = self.substitute_url_params(endpoint)
            
            if self.verbose:
                logger.info(f"Testing {method} {test_url} - {description}")
            
            # Handle different HTTP methods
            if method == "GET":
                response = await self.client.get(test_url)
            elif method == "POST":
                response = await self.client.post(test_url, json=data)
            elif method == "PUT":
                response = await self.client.put(test_url, json=data)
            elif method == "DELETE":
                response = await self.client.delete(test_url)
            elif method == "WS":
                return await self.test_websocket(test_url, description)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            response_time = time.time() - start_time
            
            # Parse response data
            try:
                response_data = response.json() if response.content else {}
            except:
                response_data = {"raw_content": response.text[:200]}
            
            # Store useful data for later tests
            self.store_response_data(endpoint, response_data, response.status_code)
            
            success = 200 <= response.status_code < 300
            
            result = EndpointResult(
                endpoint=f"{method} {endpoint}",
                method=method,
                status_code=response.status_code,
                response_time=response_time,
                success=success,
                error_message=None if success else f"HTTP {response.status_code}",
                response_data=response_data if self.verbose else None
            )
            
            if self.verbose:
                status = "✅ PASS" if success else "❌ FAIL"
                logger.info(f"  {status} - {response.status_code} ({response_time:.2f}s)")
            
            return result
            
        except Exception as e:
            response_time = time.time() - start_time
            error_msg = str(e)
            
            if self.verbose:
                logger.error(f"  ❌ FAIL - {error_msg}")
            
            return EndpointResult(
                endpoint=f"{method} {endpoint}",
                method=method,
                status_code=0,
                response_time=response_time,
                success=False,
                error_message=error_msg
            )
    
    async def test_websocket(self, url: str, description: str) -> EndpointResult:
        """Test WebSocket connection"""
        start_time = time.time()
        
        try:
            ws_url = url.replace("http://", "ws://").replace("https://", "wss://")
            
            async with websockets.connect(ws_url, ping_timeout=5) as websocket:
                # Send a test message
                test_message = {"type": "ping", "data": {"timestamp": datetime.now().isoformat()}}
                await websocket.send(json.dumps(test_message))
                
                # Wait for response (with timeout)
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=3.0)
                    response_data = {"websocket_response": response}
                except asyncio.TimeoutError:
                    response_data = {"status": "connection_established", "timeout": "no_immediate_response"}
            
            response_time = time.time() - start_time
            
            return EndpointResult(
                endpoint=f"WS {url}",
                method="WS",
                status_code=200,
                response_time=response_time,
                success=True,
                response_data=response_data if self.verbose else None
            )
            
        except Exception as e:
            response_time = time.time() - start_time
            
            return EndpointResult(
                endpoint=f"WS {url}",
                method="WS",
                status_code=0,
                response_time=response_time,
                success=False,
                error_message=str(e)
            )
    
    def substitute_url_params(self, endpoint: str) -> str:
        """Substitute URL parameters with test data"""
        # Handle common parameter substitutions
        if "{qid}" in endpoint:
            qid = self.test_data.get("test_qid", "Q1")  # Use test entity or fallback
            endpoint = endpoint.replace("{qid}", qid)
        
        if "{queue_type}" in endpoint:
            endpoint = endpoint.replace("{queue_type}", "active")
        
        if "{entry_id}" in endpoint:
            entry_id = self.test_data.get("test_entry_id", "1")
            endpoint = endpoint.replace("{entry_id}", str(entry_id))
        
        if "{id}" in endpoint:
            session_id = self.test_data.get("test_session_id", "1")
            endpoint = endpoint.replace("{id}", str(session_id))
        
        return endpoint
    
    def store_response_data(self, endpoint: str, response_data: Dict, status_code: int):
        """Store useful response data for subsequent tests"""
        if status_code < 200 or status_code >= 300:
            return
        
        # Store entity QID from manual creation
        if "entities/manual" in endpoint and "qid" in response_data:
            self.test_data["test_qid"] = response_data["qid"]
        
        # Store queue entry ID
        if "queues/entries" in endpoint and "id" in response_data:
            self.test_data["test_entry_id"] = response_data["id"]
        
        # Store session ID from extraction
        if "extraction/start" in endpoint and "session_id" in response_data:
            self.test_data["test_session_id"] = response_data["session_id"]
        
        # Collect QIDs for batch operations
        if "entities" in endpoint and isinstance(response_data, dict):
            if "entities" in response_data:
                qids = [entity.get("qid") for entity in response_data["entities"][:3]]
                self.test_data["available_qids"] = [qid for qid in qids if qid]
    
    def get_request_data(self, endpoint: str, method: str) -> Optional[Dict]:
        """Get appropriate request data for endpoint"""
        test_data = self.generate_test_data()
        
        # Entity endpoints
        if "entities/manual" in endpoint:
            return test_data["manual_entity"]
        elif "entities/" in endpoint and method == "PUT":
            return {"short_desc": "Updated description"}
        
        # Queue endpoints
        elif "queues/entries" in endpoint and method == "POST":
            data = test_data["queue_entry"].copy()
            data["qid"] = self.test_data.get("test_qid", "Q1")
            return data
        elif "queues/entries" in endpoint and method == "PUT":
            return {"priority": 1, "notes": "Updated notes"}
        elif "queues/batch" in endpoint:
            data = test_data["batch_operation"].copy()
            data["qids"] = self.test_data.get("available_qids", ["Q1"])[:2]
            return data
        elif "bulk-approve" in endpoint or "bulk-reject" in endpoint:
            data = test_data["bulk_approve"].copy()
            data["qids"] = self.test_data.get("available_qids", ["Q1"])[:1]
            return data
        
        # Extraction endpoints
        elif "extraction/configure" in endpoint:
            return test_data["extraction_config"]
        elif "extraction/start" in endpoint:
            return test_data["extraction_start"]
        
        # WebSocket endpoints
        elif "websocket/broadcast" in endpoint:
            return test_data["websocket_broadcast"]
        
        # Pipeline endpoints
        elif "pipeline/entity-extracted" in endpoint:
            return test_data["pipeline_notification"]
        
        return None
    
    async def run_category_tests(self, category: str) -> List[EndpointResult]:
        """Run tests for a specific category"""
        if category not in self.test_categories:
            logger.error(f"Unknown category: {category}")
            return []
        
        logger.info(f"\n🧪 Testing {category.upper()} endpoints...")
        category_results = []
        
        for method, endpoint, description in self.test_categories[category]:
            request_data = self.get_request_data(endpoint, method)
            result = await self.test_endpoint(method, endpoint, description, request_data)
            category_results.append(result)
            self.results.append(result)
            
            # Small delay between requests
            await asyncio.sleep(0.1)
        
        return category_results
    
    async def run_all_tests(self, categories: Optional[List[str]] = None) -> TestSummary:
        """Run comprehensive endpoint testing"""
        start_time = time.time()
        
        logger.info("🚀 Starting Strategic API Endpoint Testing")
        logger.info(f"📡 Base URL: {self.base_url}")
        
        # Initialize test data
        self.test_data = {}
        
        # Determine categories to test
        test_categories = categories or list(self.test_categories.keys())
        
        # Test categories in strategic order
        strategic_order = ["core", "system", "entities_basic", "queues", "extraction", 
                          "analytics", "deduplication", "websocket", "pipeline"]
        
        ordered_categories = [cat for cat in strategic_order if cat in test_categories]
        ordered_categories.extend([cat for cat in test_categories if cat not in strategic_order])
        
        for category in ordered_categories:
            await self.run_category_tests(category)
        
        # Calculate summary
        duration = time.time() - start_time
        successful = sum(1 for r in self.results if r.success)
        failed = len(self.results) - successful
        critical_failures = [r.endpoint for r in self.results 
                           if not r.success and any(word in r.endpoint.lower() 
                           for word in ['health', 'entities', 'queues'])]
        
        summary = TestSummary(
            total_endpoints=len(self.results),
            successful=successful,
            failed=failed,
            duration=duration,
            categories_tested=ordered_categories,
            critical_failures=critical_failures
        )
        
        return summary
    
    def print_summary(self, summary: TestSummary):
        """Print comprehensive test summary"""
        print("\n" + "="*80)
        print("🏁 STRATEGIC ENDPOINT TESTING SUMMARY")
        print("="*80)
        
        # Overall stats
        success_rate = (summary.successful / summary.total_endpoints * 100) if summary.total_endpoints > 0 else 0
        print(f"📊 Total Endpoints Tested: {summary.total_endpoints}")
        print(f"✅ Successful: {summary.successful}")
        print(f"❌ Failed: {summary.failed}")
        print(f"📈 Success Rate: {success_rate:.1f}%")
        print(f"⏱️  Total Duration: {summary.duration:.2f}s")
        print(f"🏷️  Categories: {', '.join(summary.categories_tested)}")
        
        # Performance metrics
        if self.results:
            avg_response_time = sum(r.response_time for r in self.results) / len(self.results)
            max_response_time = max(r.response_time for r in self.results)
            print(f"⚡ Avg Response Time: {avg_response_time:.3f}s")
            print(f"⚡ Max Response Time: {max_response_time:.3f}s")
        
        # Critical failures
        if summary.critical_failures:
            print(f"\n🚨 CRITICAL FAILURES ({len(summary.critical_failures)}):")
            for failure in summary.critical_failures:
                print(f"  • {failure}")
        
        # Category breakdown
        print(f"\n📋 CATEGORY BREAKDOWN:")
        for category in summary.categories_tested:
            category_results = [r for r in self.results if any(endpoint[1] in r.endpoint 
                               for endpoint in self.test_categories.get(category, []))]
            cat_success = sum(1 for r in category_results if r.success)
            cat_total = len(category_results)
            cat_rate = (cat_success / cat_total * 100) if cat_total > 0 else 0
            print(f"  {category.upper()}: {cat_success}/{cat_total} ({cat_rate:.1f}%)")
        
        # Detailed failures
        failed_results = [r for r in self.results if not r.success]
        if failed_results and self.verbose:
            print(f"\n🔍 DETAILED FAILURES ({len(failed_results)}):")
            for result in failed_results:
                print(f"  • {result.endpoint}")
                print(f"    Error: {result.error_message}")
                print(f"    Response Time: {result.response_time:.3f}s")
        
        # Overall assessment
        print(f"\n🎯 ASSESSMENT:")
        if success_rate >= 95:
            print("🎉 EXCELLENT! Your API is working perfectly!")
        elif success_rate >= 85:
            print("👍 GOOD! Minor issues detected, but overall healthy.")
        elif success_rate >= 70:
            print("⚠️  MODERATE! Several endpoints need attention.")
        else:
            print("🚨 CRITICAL! Major issues detected. Immediate attention required.")
        
        print("="*80)
    
    def generate_html_report(self, summary: TestSummary, output_file: str = "endpoint_test_report.html"):
        """Generate detailed HTML report"""
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>API Endpoint Test Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .summary {{ background: #f0f8ff; padding: 20px; border-radius: 5px; }}
                .success {{ color: #008000; }}
                .failure {{ color: #ff0000; }}
                table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .category {{ background-color: #e6f3ff; font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>🧪 API Endpoint Test Report</h1>
            <div class="summary">
                <h2>📊 Summary</h2>
                <p><strong>Total Endpoints:</strong> {summary.total_endpoints}</p>
                <p><strong>Successful:</strong> <span class="success">{summary.successful}</span></p>
                <p><strong>Failed:</strong> <span class="failure">{summary.failed}</span></p>
                <p><strong>Success Rate:</strong> {(summary.successful/summary.total_endpoints*100):.1f}%</p>
                <p><strong>Duration:</strong> {summary.duration:.2f}s</p>
                <p><strong>Timestamp:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <h2>📋 Detailed Results</h2>
            <table>
                <tr>
                    <th>Endpoint</th>
                    <th>Status</th>
                    <th>Response Time</th>
                    <th>Status Code</th>
                    <th>Error</th>
                </tr>
        """
        
        current_category = None
        for result in self.results:
            # Determine category for this result
            for category, endpoints in self.test_categories.items():
                if any(endpoint[1] in result.endpoint for endpoint in endpoints):
                    if category != current_category:
                        html_content += f'<tr class="category"><td colspan="5">{category.upper()}</td></tr>'
                        current_category = category
                    break
            
            status_class = "success" if result.success else "failure"
            status_text = "✅ PASS" if result.success else "❌ FAIL"
            
            html_content += f"""
                <tr>
                    <td>{result.endpoint}</td>
                    <td class="{status_class}">{status_text}</td>
                    <td>{result.response_time:.3f}s</td>
                    <td>{result.status_code}</td>
                    <td>{result.error_message or '-'}</td>
                </tr>
            """
        
        html_content += """
            </table>
        </body>
        </html>
        """
        
        with open(output_file, 'w') as f:
            f.write(html_content)
        
        print(f"📄 HTML report generated: {output_file}")

async def main():
    """Main execution function"""
    parser = argparse.ArgumentParser(description='Strategic API Endpoint Testing')
    parser.add_argument('--base-url', default='http://localhost:8000', 
                       help='Base URL for the API (default: http://localhost:8000)')
    parser.add_argument('--verbose', action='store_true', 
                       help='Enable verbose output')
    parser.add_argument('--report', action='store_true', 
                       help='Generate HTML report')
    parser.add_argument('--category', 
                       choices=['core', 'system', 'entities_basic', 'queues', 'extraction', 
                               'analytics', 'deduplication', 'websocket', 'pipeline'],
                       help='Test only specific category')
    
    args = parser.parse_args()
    
    # Initialize tester
    tester = StrategicEndpointTester(base_url=args.base_url, verbose=args.verbose)
    
    try:
        # Setup
        await tester.setup_client()
        
        # Run tests
        categories = [args.category] if args.category else None
        summary = await tester.run_all_tests(categories)
        
        # Print results
        tester.print_summary(summary)
        
        # Generate report if requested
        if args.report:
            tester.generate_html_report(summary)
        
    except KeyboardInterrupt:
        print("\n⏹️  Testing interrupted by user")
    except Exception as e:
        print(f"\n💥 Testing failed with error: {e}")
    finally:
        # Cleanup
        await tester.cleanup_client()

if __name__ == "__main__":
    asyncio.run(main())