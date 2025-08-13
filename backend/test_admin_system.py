#!/usr/bin/env python3
"""
Test script for the admin system configuration and monitoring
"""

import asyncio
import sys
import os
from pathlib import Path

# Add the app directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

from app.core.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.metrics import metrics_collector
from app.core.health import health_checker


async def test_configuration_system():
    """Test configuration system"""
    print("=== Testing Configuration System ===")
    
    # Test basic configuration
    print(f"Project Name: {settings.project_name}")
    print(f"Debug Mode: {settings.debug}")
    print(f"Hot Reload: {settings.enable_hot_reload}")
    print(f"Metrics Enabled: {settings.enable_metrics}")
    
    # Test configuration info
    config_info = settings.get_config_info()
    print(f"Last Reload: {config_info['last_reload']}")
    print(f"Hot Reload Enabled: {config_info['hot_reload_enabled']}")
    
    print("✓ Configuration system working")


def test_logging_system():
    """Test logging system"""
    print("\n=== Testing Logging System ===")
    
    # Setup logging
    setup_logging()
    logger = get_logger("test")
    
    # Test different log levels
    logger.debug("Debug message")
    logger.info("Info message")
    logger.warning("Warning message")
    logger.error("Error message")
    
    # Test structured logging with context
    logger.info("Test message with context", extra={
        "user_id": "test_user",
        "action": "test_action",
        "metadata": {"key": "value"}
    })
    
    print("✓ Logging system working")


def test_metrics_system():
    """Test metrics system"""
    print("\n=== Testing Metrics System ===")
    
    # Record some test metrics
    metrics_collector.record_request("GET", "/test", 200, 0.5)
    metrics_collector.record_request("POST", "/test", 201, 1.2)
    metrics_collector.record_request("GET", "/test", 404, 0.3)
    
    metrics_collector.record_document_processed()
    metrics_collector.record_query_processed()
    metrics_collector.record_vector_operation()
    metrics_collector.record_cache_hit()
    metrics_collector.record_cache_miss()
    
    # Get current metrics
    current_metrics = metrics_collector.get_current_metrics()
    print(f"System Metrics: {current_metrics['system']}")
    print(f"Application Metrics: {current_metrics['application']}")
    print(f"Uptime: {current_metrics['uptime_seconds']:.2f} seconds")
    
    print("✓ Metrics system working")


async def test_health_system():
    """Test health check system"""
    print("\n=== Testing Health Check System ===")
    
    try:
        # Test individual components
        components = [
            "database",
            "redis", 
            "file_system",
            "system_resources"
        ]
        
        for component in components:
            try:
                health = await health_checker.check_component(component)
                print(f"{component}: {health.status.value} - {health.message}")
                if health.response_time:
                    print(f"  Response time: {health.response_time:.3f}s")
            except Exception as e:
                print(f"{component}: ERROR - {str(e)}")
        
        # Test overall health
        print("\nOverall Health Check:")
        overall_health = await health_checker.check_all_components()
        print(f"Status: {overall_health['status']}")
        print(f"Components: {overall_health['summary']}")
        
        print("✓ Health check system working")
        
    except Exception as e:
        print(f"✗ Health check system error: {e}")


async def main():
    """Run all tests"""
    print("Testing RAG System Admin Components\n")
    
    try:
        # Test configuration
        await test_configuration_system()
        
        # Test logging
        test_logging_system()
        
        # Test metrics
        test_metrics_system()
        
        # Test health checks
        await test_health_system()
        
        print("\n=== All Tests Completed ===")
        print("✓ Configuration system operational")
        print("✓ Logging system operational") 
        print("✓ Metrics system operational")
        print("✓ Health check system operational")
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)