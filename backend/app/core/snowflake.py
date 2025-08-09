"""
Snowflake ID generator for distributed unique ID generation

Snowflake ID structure (64 bits):
- 1 bit: unused (always 0)
- 41 bits: timestamp (milliseconds since epoch)
- 10 bits: machine/worker ID
- 12 bits: sequence number
"""

import time
import threading
from typing import Optional


class SnowflakeIDGenerator:
    """
    Snowflake ID generator for distributed unique ID generation
    """
    
    def __init__(self, worker_id: int = 1, datacenter_id: int = 1):
        # Validate worker and datacenter IDs
        if worker_id > 31 or worker_id < 0:
            raise ValueError("Worker ID must be between 0 and 31")
        if datacenter_id > 31 or datacenter_id < 0:
            raise ValueError("Datacenter ID must be between 0 and 31")
            
        self.worker_id = worker_id
        self.datacenter_id = datacenter_id
        self.sequence = 0
        self.last_timestamp = -1
        self.lock = threading.Lock()
        
        # Epoch timestamp (2024-01-01 00:00:00 UTC)
        self.epoch = 1704067200000
        
        # Bit shifts
        self.worker_id_bits = 5
        self.datacenter_id_bits = 5
        self.sequence_bits = 12
        
        # Max values
        self.max_worker_id = (1 << self.worker_id_bits) - 1
        self.max_datacenter_id = (1 << self.datacenter_id_bits) - 1
        self.max_sequence = (1 << self.sequence_bits) - 1
        
        # Bit shifts for ID generation
        self.worker_id_shift = self.sequence_bits
        self.datacenter_id_shift = self.sequence_bits + self.worker_id_bits
        self.timestamp_shift = (self.sequence_bits + self.worker_id_bits + 
                               self.datacenter_id_bits) 
   
    def generate_id(self) -> int:
        """Generate a unique Snowflake ID"""
        with self.lock:
            timestamp = self._current_timestamp()
            
            if timestamp < self.last_timestamp:
                raise Exception("Clock moved backwards. Refusing to generate ID")
            
            if timestamp == self.last_timestamp:
                self.sequence = (self.sequence + 1) & self.max_sequence
                if self.sequence == 0:
                    # Sequence exhausted, wait for next millisecond
                    timestamp = self._wait_next_timestamp(self.last_timestamp)
            else:
                self.sequence = 0
            
            self.last_timestamp = timestamp
            
            # Generate the ID
            snowflake_id = (
                ((timestamp - self.epoch) << self.timestamp_shift) |
                (self.datacenter_id << self.datacenter_id_shift) |
                (self.worker_id << self.worker_id_shift) |
                self.sequence
            )
            
            return snowflake_id
    
    def _current_timestamp(self) -> int:
        """Get current timestamp in milliseconds"""
        return int(time.time() * 1000)
    
    def _wait_next_timestamp(self, last_timestamp: int) -> int:
        """Wait until next millisecond"""
        timestamp = self._current_timestamp()
        while timestamp <= last_timestamp:
            timestamp = self._current_timestamp()
        return timestamp
    
    def parse_id(self, snowflake_id: int) -> dict:
        """Parse a Snowflake ID into its components"""
        timestamp = ((snowflake_id >> self.timestamp_shift) + self.epoch)
        datacenter_id = ((snowflake_id >> self.datacenter_id_shift) & 
                        self.max_datacenter_id)
        worker_id = (snowflake_id >> self.worker_id_shift) & self.max_worker_id
        sequence = snowflake_id & self.max_sequence
        
        return {
            'timestamp': timestamp,
            'datacenter_id': datacenter_id,
            'worker_id': worker_id,
            'sequence': sequence,
            'datetime': time.strftime('%Y-%m-%d %H:%M:%S', 
                                    time.localtime(timestamp / 1000))
        }


# Global instance
snowflake_generator = SnowflakeIDGenerator()


def generate_id() -> int:
    """Generate a unique ID using Snowflake algorithm"""
    return snowflake_generator.generate_id()