"""
Tests for Snowflake ID generator
"""

import pytest
import time
import threading
from app.core.snowflake import SnowflakeIDGenerator, generate_id


class TestSnowflakeIDGenerator:
    """Test cases for SnowflakeIDGenerator"""
    
    def test_generator_initialization(self):
        """Test generator initialization with valid parameters"""
        generator = SnowflakeIDGenerator(worker_id=1, datacenter_id=1)
        assert generator.worker_id == 1
        assert generator.datacenter_id == 1
        assert generator.sequence == 0
        assert generator.last_timestamp == -1
    
    def test_invalid_worker_id(self):
        """Test generator initialization with invalid worker ID"""
        with pytest.raises(ValueError, match="Worker ID must be between 0 and 31"):
            SnowflakeIDGenerator(worker_id=32)
        
        with pytest.raises(ValueError, match="Worker ID must be between 0 and 31"):
            SnowflakeIDGenerator(worker_id=-1)
    
    def test_invalid_datacenter_id(self):
        """Test generator initialization with invalid datacenter ID"""
        with pytest.raises(ValueError, match="Datacenter ID must be between 0 and 31"):
            SnowflakeIDGenerator(datacenter_id=32)
        
        with pytest.raises(ValueError, match="Datacenter ID must be between 0 and 31"):
            SnowflakeIDGenerator(datacenter_id=-1)
    
    def test_generate_unique_ids(self):
        """Test that generated IDs are unique"""
        generator = SnowflakeIDGenerator()
        ids = set()
        
        # Generate 1000 IDs and ensure they are all unique
        for _ in range(1000):
            id_val = generator.generate_id()
            assert id_val not in ids
            ids.add(id_val)
    
    def test_generate_sequential_ids(self):
        """Test that IDs are generated in ascending order"""
        generator = SnowflakeIDGenerator()
        prev_id = 0
        
        for _ in range(100):
            current_id = generator.generate_id()
            assert current_id > prev_id
            prev_id = current_id
    
    def test_parse_id(self):
        """Test parsing of generated ID"""
        generator = SnowflakeIDGenerator(worker_id=5, datacenter_id=3)
        id_val = generator.generate_id()
        
        parsed = generator.parse_id(id_val)
        
        assert 'timestamp' in parsed
        assert 'datacenter_id' in parsed
        assert 'worker_id' in parsed
        assert 'sequence' in parsed
        assert 'datetime' in parsed
        
        assert parsed['datacenter_id'] == 3
        assert parsed['worker_id'] == 5
        assert parsed['sequence'] >= 0
    
    def test_concurrent_generation(self):
        """Test ID generation in concurrent environment"""
        generator = SnowflakeIDGenerator()
        ids = set()
        lock = threading.Lock()
        
        def generate_ids():
            for _ in range(100):
                id_val = generator.generate_id()
                with lock:
                    assert id_val not in ids
                    ids.add(id_val)
        
        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=generate_ids)
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Should have 500 unique IDs
        assert len(ids) == 500
    
    def test_global_generate_id_function(self):
        """Test the global generate_id function"""
        id1 = generate_id()
        id2 = generate_id()
        
        assert isinstance(id1, int)
        assert isinstance(id2, int)
        assert id1 != id2
        assert id2 > id1