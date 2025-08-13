"""
Comprehensive metrics collection and monitoring system
"""

import time
import psutil
import threading
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from collections import defaultdict, deque
from dataclasses import dataclass, field
from prometheus_client import Counter, Histogram, Gauge, Info, start_http_server
import logging

from .config import settings

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """System performance metrics"""
    cpu_percent: float
    memory_percent: float
    memory_used: int
    memory_available: int
    disk_usage_percent: float
    disk_free: int
    network_sent: int
    network_recv: int
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ApplicationMetrics:
    """Application-specific metrics"""
    active_requests: int
    total_requests: int
    error_count: int
    avg_response_time: float
    documents_processed: int
    queries_processed: int
    vector_operations: int
    cache_hits: int
    cache_misses: int
    timestamp: datetime = field(default_factory=datetime.now)


class MetricsCollector:
    """Centralized metrics collection system"""
    
    def __init__(self):
        self.enabled = settings.enable_metrics
        self._lock = threading.Lock()
        self._system_metrics_history = deque(maxlen=1000)
        self._app_metrics_history = deque(maxlen=1000)
        self._request_times = deque(maxlen=1000)
        self._error_counts = defaultdict(int)
        self._active_requests = 0
        self._total_requests = 0
        self._start_time = datetime.now()
        
        # Prometheus metrics
        self._setup_prometheus_metrics()
        
        # Start metrics collection thread
        if self.enabled:
            self._collection_thread = threading.Thread(
                target=self._collect_metrics_loop,
                daemon=True
            )
            self._collection_thread.start()
            
            # Start Prometheus metrics server
            try:
                start_http_server(settings.metrics_port)
                logger.info(f"Metrics server started on port {settings.metrics_port}")
            except Exception as e:
                logger.warning(f"Failed to start metrics server: {e}")
    
    def _setup_prometheus_metrics(self):
        """Setup Prometheus metrics"""
        # Request metrics
        self.request_counter = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status_code']
        )
        
        self.request_duration = Histogram(
            'http_request_duration_seconds',
            'HTTP request duration',
            ['method', 'endpoint']
        )
        
        # System metrics
        self.cpu_usage = Gauge('system_cpu_percent', 'CPU usage percentage')
        self.memory_usage = Gauge('system_memory_percent', 'Memory usage percentage')
        self.disk_usage = Gauge('system_disk_percent', 'Disk usage percentage')
        
        # Application metrics
        self.active_requests_gauge = Gauge('app_active_requests', 'Active requests')
        self.documents_processed = Counter('app_documents_processed_total', 'Documents processed')
        self.queries_processed = Counter('app_queries_processed_total', 'Queries processed')
        self.vector_operations = Counter('app_vector_operations_total', 'Vector operations')
        self.cache_hits = Counter('app_cache_hits_total', 'Cache hits')
        self.cache_misses = Counter('app_cache_misses_total', 'Cache misses')
        
        # Application info
        self.app_info = Info('app_info', 'Application information')
        self.app_info.info({
            'version': '1.0.0',
            'start_time': self._start_time.isoformat()
        })
    
    def _collect_metrics_loop(self):
        """Background thread for collecting system metrics"""
        while True:
            try:
                self._collect_system_metrics()
                self._collect_application_metrics()
                time.sleep(30)  # Collect every 30 seconds
            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")
                time.sleep(60)  # Wait longer on error
    
    def _collect_system_metrics(self):
        """Collect system performance metrics"""
        try:
            # CPU and memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            network = psutil.net_io_counters()
            
            metrics = SystemMetrics(
                cpu_percent=cpu_percent,
                memory_percent=memory.percent,
                memory_used=memory.used,
                memory_available=memory.available,
                disk_usage_percent=disk.percent,
                disk_free=disk.free,
                network_sent=network.bytes_sent,
                network_recv=network.bytes_recv
            )
            
            with self._lock:
                self._system_metrics_history.append(metrics)
            
            # Update Prometheus metrics
            self.cpu_usage.set(cpu_percent)
            self.memory_usage.set(memory.percent)
            self.disk_usage.set(disk.percent)
            
        except Exception as e:
            logger.error(f"Error collecting system metrics: {e}")
    
    def _collect_application_metrics(self):
        """Collect application-specific metrics"""
        try:
            with self._lock:
                avg_response_time = (
                    sum(self._request_times) / len(self._request_times)
                    if self._request_times else 0
                )
                
                metrics = ApplicationMetrics(
                    active_requests=self._active_requests,
                    total_requests=self._total_requests,
                    error_count=sum(self._error_counts.values()),
                    avg_response_time=avg_response_time,
                    documents_processed=0,  # Will be updated by services
                    queries_processed=0,    # Will be updated by services
                    vector_operations=0,    # Will be updated by services
                    cache_hits=0,          # Will be updated by services
                    cache_misses=0         # Will be updated by services
                )
                
                self._app_metrics_history.append(metrics)
                
                # Update Prometheus gauge
                self.active_requests_gauge.set(self._active_requests)
                
        except Exception as e:
            logger.error(f"Error collecting application metrics: {e}")
    
    def record_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """Record HTTP request metrics"""
        if not self.enabled:
            return
            
        with self._lock:
            self._total_requests += 1
            self._request_times.append(duration)
            
            if status_code >= 400:
                self._error_counts[status_code] += 1
        
        # Update Prometheus metrics
        self.request_counter.labels(
            method=method,
            endpoint=endpoint,
            status_code=status_code
        ).inc()
        
        self.request_duration.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)
    
    def increment_active_requests(self):
        """Increment active request counter"""
        if not self.enabled:
            return
            
        with self._lock:
            self._active_requests += 1
    
    def decrement_active_requests(self):
        """Decrement active request counter"""
        if not self.enabled:
            return
            
        with self._lock:
            self._active_requests = max(0, self._active_requests - 1)
    
    def record_document_processed(self):
        """Record document processing"""
        if self.enabled:
            self.documents_processed.inc()
    
    def record_query_processed(self):
        """Record query processing"""
        if self.enabled:
            self.queries_processed.inc()
    
    def record_vector_operation(self):
        """Record vector database operation"""
        if self.enabled:
            self.vector_operations.inc()
    
    def record_cache_hit(self):
        """Record cache hit"""
        if self.enabled:
            self.cache_hits.inc()
    
    def record_cache_miss(self):
        """Record cache miss"""
        if self.enabled:
            self.cache_misses.inc()
    
    def get_current_metrics(self) -> Dict[str, Any]:
        """Get current system and application metrics"""
        with self._lock:
            system_metrics = self._system_metrics_history[-1] if self._system_metrics_history else None
            app_metrics = self._app_metrics_history[-1] if self._app_metrics_history else None
            
            return {
                "system": system_metrics.__dict__ if system_metrics else {},
                "application": app_metrics.__dict__ if app_metrics else {},
                "uptime_seconds": (datetime.now() - self._start_time).total_seconds(),
                "error_breakdown": dict(self._error_counts)
            }
    
    def get_metrics_history(self, hours: int = 1) -> Dict[str, List[Dict[str, Any]]]:
        """Get metrics history for the specified number of hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        
        with self._lock:
            system_history = [
                m.__dict__ for m in self._system_metrics_history
                if m.timestamp >= cutoff_time
            ]
            
            app_history = [
                m.__dict__ for m in self._app_metrics_history
                if m.timestamp >= cutoff_time
            ]
            
            return {
                "system": system_history,
                "application": app_history
            }


# Global metrics collector instance
metrics_collector = MetricsCollector()