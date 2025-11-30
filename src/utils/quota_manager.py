"""
API Quota Management System
Tracks API usage, enforces rate limits, and provides usage statistics.
"""
import os
import json
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional
import logging

logger = logging.getLogger(__name__)


class QuotaManager:
    """Centralized API quota management and rate limiting."""
    
    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize QuotaManager.
        
        Args:
            storage_path: Path to store usage data (default: .gemini/quota_usage.json)
        """
        if storage_path is None:
            storage_path = os.path.join(
                os.path.expanduser("~/.gemini/antigravity"),
                "quota_usage.json"
            )
        
        self.storage_path = storage_path
        os.makedirs(os.path.dirname(storage_path), exist_ok=True)
        
        # Default quota limits (can be overridden via config)
        self.limits = {
            'openai': {
                'rpm': 500,  # Requests per minute
                'window': 60,  # seconds
            },
            'pexels': {
                'rph': 200,  # Requests per hour
                'window': 3600,  # seconds
            },
            'youtube': {
                'daily_quota': 10000,  # Quota units per day
                'window': 86400,  # seconds (24 hours)
            }
        }
        
        # Load existing usage data
        self.usage = self._load_usage()
    
    def _load_usage(self) -> Dict:
        """Load usage data from storage."""
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r') as f:
                    data = json.load(f)
                    # Clean up old data
                    return self._clean_old_data(data)
            except Exception as e:
                logger.warning(f"Failed to load quota usage data: {e}")
        
        # Initialize empty usage data
        return {
            'openai': {'requests': [], 'total': 0},
            'pexels': {'requests': [], 'total': 0},
            'youtube': {'quota_units': [], 'total': 0}
        }
    
    def _save_usage(self):
        """Save usage data to storage."""
        try:
            with open(self.storage_path, 'w') as f:
                json.dump(self.usage, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save quota usage data: {e}")
    
    def _clean_old_data(self, data: Dict) -> Dict:
        """Remove usage records outside the tracking window."""
        now = time.time()
        
        for service, limits in self.limits.items():
            if service not in data:
                data[service] = {'requests': [], 'total': 0}
                continue
            
            window = limits['window']
            cutoff_time = now - window
            
            # Filter out old requests
            if service == 'youtube':
                key = 'quota_units'
            else:
                key = 'requests'
            
            if key in data[service]:
                data[service][key] = [
                    req for req in data[service][key]
                    if req['timestamp'] > cutoff_time
                ]
        
        return data
    
    def check_quota(self, service: str, units: int = 1) -> bool:
        """
        Check if quota is available for a service.
        
        Args:
            service: Service name ('openai', 'pexels', 'youtube')
            units: Number of quota units to check (default: 1)
        
        Returns:
            True if quota is available, False otherwise
        """
        if service not in self.limits:
            logger.warning(f"Unknown service: {service}")
            return True  # Allow unknown services
        
        # Clean old data first
        self.usage = self._clean_old_data(self.usage)
        
        # Get current usage in window
        current_usage = self._get_current_usage(service)
        
        # Get limit
        if service == 'openai':
            limit = self.limits[service]['rpm']
        elif service == 'pexels':
            limit = self.limits[service]['rph']
        elif service == 'youtube':
            limit = self.limits[service]['daily_quota']
        else:
            return True
        
        # Check if adding units would exceed limit
        return (current_usage + units) <= limit
    
    def _get_current_usage(self, service: str) -> int:
        """Get current usage count within the tracking window."""
        if service not in self.usage:
            return 0
        
        if service == 'youtube':
            requests = self.usage[service].get('quota_units', [])
        else:
            requests = self.usage[service].get('requests', [])
        
        return len(requests)
    
    def record_usage(self, service: str, units: int = 1):
        """
        Record API usage.
        
        Args:
            service: Service name
            units: Number of quota units used (default: 1)
        """
        if service not in self.usage:
            self.usage[service] = {'requests': [], 'total': 0}
        
        now = time.time()
        
        # Record the request
        if service == 'youtube':
            key = 'quota_units'
        else:
            key = 'requests'
        
        if key not in self.usage[service]:
            self.usage[service][key] = []
        
        self.usage[service][key].append({
            'timestamp': now,
            'units': units
        })
        
        # Update total
        self.usage[service]['total'] = self.usage[service].get('total', 0) + units
        
        # Save to disk
        self._save_usage()
        
        logger.info(f"Recorded {units} quota units for {service}")
    
    def wait_if_needed(self, service: str, units: int = 1) -> float:
        """
        Wait if rate limit is approaching.
        
        Args:
            service: Service name
            units: Number of quota units needed
        
        Returns:
            Number of seconds waited
        """
        if not self.check_quota(service, units):
            # Calculate wait time
            wait_time = self._calculate_wait_time(service)
            
            if wait_time > 0:
                logger.warning(
                    f"⚠️ {service} quota limit approaching. Waiting {wait_time:.1f}s..."
                )
                time.sleep(wait_time)
                return wait_time
        
        return 0.0
    
    def _calculate_wait_time(self, service: str) -> float:
        """Calculate how long to wait for quota to become available."""
        if service not in self.usage or service not in self.limits:
            return 0.0
        
        if service == 'youtube':
            requests = self.usage[service].get('quota_units', [])
        else:
            requests = self.usage[service].get('requests', [])
        
        if not requests:
            return 0.0
        
        # Find oldest request in window
        oldest_request = min(requests, key=lambda x: x['timestamp'])
        oldest_time = oldest_request['timestamp']
        
        # Calculate when it will expire
        window = self.limits[service]['window']
        expiry_time = oldest_time + window
        
        # Wait time is time until oldest request expires
        wait_time = max(0, expiry_time - time.time())
        
        # Add small buffer
        return wait_time + 1.0
    
    def get_usage_stats(self) -> Dict:
        """
        Get current usage statistics.
        
        Returns:
            Dictionary with usage stats for each service
        """
        self.usage = self._clean_old_data(self.usage)
        
        stats = {}
        for service in ['openai', 'pexels', 'youtube']:
            current = self._get_current_usage(service)
            
            if service == 'openai':
                limit = self.limits[service]['rpm']
                window_name = "minute"
            elif service == 'pexels':
                limit = self.limits[service]['rph']
                window_name = "hour"
            elif service == 'youtube':
                limit = self.limits[service]['daily_quota']
                window_name = "day"
            else:
                continue
            
            percentage = (current / limit * 100) if limit > 0 else 0
            
            stats[service] = {
                'current': current,
                'limit': limit,
                'percentage': percentage,
                'window': window_name,
                'total_all_time': self.usage.get(service, {}).get('total', 0)
            }
        
        return stats
    
    def print_usage_stats(self):
        """Print usage statistics to console."""
        stats = self.get_usage_stats()
        
        logger.info("\n📊 API Quota Usage Statistics")
        logger.info("=" * 60)
        
        for service, data in stats.items():
            service_name = service.upper()
            current = data['current']
            limit = data['limit']
            percentage = data['percentage']
            window = data['window']
            total = data['total_all_time']
            
            # Color coding based on usage
            if percentage >= 95:
                status = "🔴 CRITICAL"
            elif percentage >= 80:
                status = "🟡 WARNING"
            else:
                status = "🟢 OK"
            
            logger.info(f"\n{service_name}:")
            logger.info(f"  Status: {status}")
            logger.info(f"  Current: {current}/{limit} per {window} ({percentage:.1f}%)")
            logger.info(f"  Total (all time): {total:,}")
        
        logger.info("\n" + "=" * 60)


# Global quota manager instance
_quota_manager = None


def get_quota_manager() -> QuotaManager:
    """Get or create the global QuotaManager instance."""
    global _quota_manager
    if _quota_manager is None:
        _quota_manager = QuotaManager()
    return _quota_manager
