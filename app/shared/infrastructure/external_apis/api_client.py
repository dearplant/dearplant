# 📄 File: app/shared/infrastructure/external_apis/api_client.py

# 🧭 Purpose (Layman Explanation):
# This file creates a smart HTTP client that knows how to talk to external services reliably,
# handling timeouts, retries, and errors gracefully when communicating with plant identification or weather APIs.

# 🧪 Purpose (Technical Summary):
# Generic async HTTP client with comprehensive error handling, retry logic, rate limiting,
# request/response caching, and monitoring for all external API integrations.

# 🔗 Dependencies:
# - aiohttp: Async HTTP client
# - tenacity: Retry logic and backoff strategies
# - redis: Response caching
# - prometheus: Metrics collection

# 🔄 Connected Modules / Calls From:
# Used by: PlantNet, Trefle, OpenWeatherMap clients, AI service clients,
# Payment gateway clients, Translation service clients

import asyncio
import json
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Union, List
from urllib.parse import urljoin, urlencode
import aiohttp
from aiohttp import ClientTimeout, ClientError, ClientSession
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)

from app.shared.infrastructure.cache.cache_manager import get_cache_manager
from app.shared.core.exceptions import (
    ExternalAPIError,
    APIQuotaExceededError as APIRateLimitError,
    APITimeoutError,
    APIAuthenticationError,
    APIQuotaExceededError
)
from app.shared.utils.logging import get_logger

logger = get_logger(__name__)


class APIClient:
    """
    Generic async HTTP client for external API integrations.
    
    Features:
    - Automatic retry with exponential backoff
    - Rate limiting and quota management
    - Request/response caching
    - Comprehensive error handling
    - Request/response logging
    - Performance metrics
    - Authentication handling
    """
    
    def __init__(
        self,
        base_url: str,
        api_key: str,
        api_name: str,
        timeout: int = 30,
        max_retries: int = 3,
        rate_limit_per_minute: int = 60,
        rate_limit_per_hour: int = 1000,
        cache_ttl: int = 300,  # 5 minutes default cache
        enable_caching: bool = True
    ):
        """Initialize API client with configuration."""
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.api_name = api_name
        self.timeout = timeout
        self.max_retries = max_retries
        self.cache_ttl = cache_ttl
        self.enable_caching = enable_caching
        
        # Rate limiting
        self.rate_limit_per_minute = rate_limit_per_minute
        self.rate_limit_per_hour = rate_limit_per_hour
        self._request_timestamps = []
        self._hourly_request_count = 0
        self._hourly_reset_time = datetime.utcnow() + timedelta(hours=1)
        
        # Session and cache
        self.session: Optional[ClientSession] = None
        self.cache_manager = None
        
        # Performance tracking
        self.stats = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'cache_hits': 0,
            'cache_misses': 0,
            'average_response_time': 0,
            'last_request_time': None,
            'rate_limit_hits': 0
        }
        
        # Error tracking
        self.error_history = []
        self.max_error_history = 100
    
    async def initialize(self):
        """Initialize the client session and dependencies."""
        try:
            # Create aiohttp session with custom configuration
            timeout = ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(
                limit=10,  # Connection pool size
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True
            )
            
            self.session = ClientSession(
                timeout=timeout,
                connector=connector,
                headers=self._get_default_headers()
            )
            
            # Initialize cache manager
            if self.enable_caching:
                self.cache_manager = await get_cache_manager()
            
            logger.info(f"API client initialized for {self.api_name}")
            
        except Exception as e:
            logger.error(f"Failed to initialize API client {self.api_name}: {e}")
            raise ExternalAPIError(f"Client initialization failed: {e}")
    
    def _get_default_headers(self) -> Dict[str, str]:
        """Get default headers for requests."""
        headers = {
            'User-Agent': f'PlantCareApp/1.0 ({self.api_name}-client)',
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        }
        
        # Add API key to headers based on common patterns
        if self.api_key:
            # Try different common header patterns
            if 'openweather' in self.api_name.lower():
                headers['appid'] = self.api_key
            elif 'plantnet' in self.api_name.lower():
                headers['Api-Key'] = self.api_key
            elif 'openai' in self.api_name.lower():
                headers['Authorization'] = f'Bearer {self.api_key}'
            elif 'anthropic' in self.api_name.lower() or 'claude' in self.api_name.lower():
                headers['x-api-key'] = self.api_key
                headers['anthropic-version'] = '2023-06-01'
            else:
                # Default pattern
                headers['Authorization'] = f'Bearer {self.api_key}'
        
        return headers
    
    async def _check_rate_limits(self):
        """Check and enforce rate limits."""
        now = datetime.utcnow()
        
        # Clean old timestamps (older than 1 minute)
        minute_ago = now - timedelta(minutes=1)
        self._request_timestamps = [
            ts for ts in self._request_timestamps if ts > minute_ago
        ]
        
        # Check minute rate limit
        if len(self._request_timestamps) >= self.rate_limit_per_minute:
            wait_time = 60 - (now - self._request_timestamps[0]).total_seconds()
            if wait_time > 0:
                self.stats['rate_limit_hits'] += 1
                raise APIRateLimitError(
                    f"Rate limit exceeded for {self.api_name}. "
                    f"Wait {wait_time:.1f} seconds."
                )
        
        # Check hourly rate limit
        if now > self._hourly_reset_time:
            self._hourly_request_count = 0
            self._hourly_reset_time = now + timedelta(hours=1)
        
        if self._hourly_request_count >= self.rate_limit_per_hour:
            reset_in = (self._hourly_reset_time - now).total_seconds()
            raise APIRateLimitError(
                f"Hourly rate limit exceeded for {self.api_name}. "
                f"Resets in {reset_in/60:.1f} minutes."
            )
        
        # Record this request
        self._request_timestamps.append(now)
        self._hourly_request_count += 1
    
    def _get_cache_key(self, method: str, url: str, params: Dict = None, data: Dict = None) -> str:
        """Generate cache key for request."""
        key_parts = [self.api_name, method.upper(), url]
        
        if params:
            sorted_params = sorted(params.items())
            key_parts.append(urlencode(sorted_params))
        
        if data and method.upper() in ['POST', 'PUT']:
            # For POST/PUT requests, include data in cache key
            data_str = json.dumps(data, sort_keys=True) if isinstance(data, dict) else str(data)
            key_parts.append(data_str)
        
        cache_key = ':'.join(key_parts)
        return f"api_cache:{cache_key}"
    
    async def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if available."""
        if not self.enable_caching or not self.cache_manager:
            return None
        
        try:
            cached_data = await self.cache_manager.get(cache_key)
            if cached_data:
                self.stats['cache_hits'] += 1
                logger.debug(f"Cache hit for {self.api_name}: {cache_key}")
                return cached_data
            else:
                self.stats['cache_misses'] += 1
                return None
        except Exception as e:
            logger.warning(f"Cache retrieval failed for {self.api_name}: {e}")
            return None
    
    async def _cache_response(self, cache_key: str, response_data: Dict):
        """Cache response data."""
        if not self.enable_caching or not self.cache_manager:
            return
        
        try:
            await self.cache_manager.set(cache_key, response_data, ttl=self.cache_ttl)
            logger.debug(f"Cached response for {self.api_name}: {cache_key}")
        except Exception as e:
            logger.warning(f"Failed to cache response for {self.api_name}: {e}")
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((aiohttp.ClientError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(logger, logging.WARNING)
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict] = None,
        data: Optional[Union[Dict, str, bytes]] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make HTTP request with retry logic."""
        if not self.session:
            await self.initialize()
        
        # Check rate limits
        await self._check_rate_limits()
        
        # Prepare URL
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        
        # Prepare headers
        request_headers = self._get_default_headers()
        if headers:
            request_headers.update(headers)
        
        # Prepare request parameters
        request_kwargs = {
            'method': method,
            'url': url,
            'headers': request_headers
        }
        
        if params:
            request_kwargs['params'] = params
        
        if data:
            if isinstance(data, dict):
                request_kwargs['json'] = data
            else:
                request_kwargs['data'] = data
        
        if timeout:
            request_kwargs['timeout'] = ClientTimeout(total=timeout)
        
        # Execute request
        start_time = time.time()
        
        try:
            async with self.session.request(**request_kwargs) as response:
                response_time = time.time() - start_time
                
                # Update stats
                self.stats['total_requests'] += 1
                self.stats['last_request_time'] = datetime.utcnow().isoformat()
                
                # Update average response time
                if self.stats['average_response_time'] == 0:
                    self.stats['average_response_time'] = response_time
                else:
                    self.stats['average_response_time'] = (
                        self.stats['average_response_time'] * 0.7 + response_time * 0.3
                    )
                
                # Handle response
                await self._handle_response_status(response)
                
                # Parse response
                try:
                    response_data = await response.json()
                except Exception:
                    # Fallback to text if JSON parsing fails
                    response_text = await response.text()
                    response_data = {'raw_response': response_text}
                
                self.stats['successful_requests'] += 1
                
                logger.info(
                    f"{self.api_name} API request successful: "
                    f"{method} {url} - {response.status} - {response_time:.2f}s"
                )
                
                return response_data
                
        except Exception as e:
            self.stats['failed_requests'] += 1
            self._record_error(e, method, url)
            raise self._transform_exception(e, method, url)
    
    async def _handle_response_status(self, response: aiohttp.ClientResponse):
        """Handle HTTP response status codes."""
        if response.status == 200:
            return
        elif response.status == 401:
            raise APIAuthenticationError(f"Authentication failed for {self.api_name}")
        elif response.status == 403:
            raise APIAuthenticationError(f"Access forbidden for {self.api_name}")
        elif response.status == 429:
            # Rate limit hit
            retry_after = response.headers.get('Retry-After', '60')
            raise APIRateLimitError(
                f"Rate limit exceeded for {self.api_name}. Retry after {retry_after} seconds."
            )
        elif response.status == 402 or response.status == 509:
            raise APIQuotaExceededError(f"API quota exceeded for {self.api_name}")
        elif 400 <= response.status < 500:
            response_text = await response.text()
            raise ExternalAPIError(
                f"Client error for {self.api_name} ({response.status}): {response_text}"
            )
        elif 500 <= response.status < 600:
            response_text = await response.text()
            raise ExternalAPIError(
                f"Server error for {self.api_name} ({response.status}): {response_text}"
            )
        else:
            raise ExternalAPIError(
                f"Unexpected status code for {self.api_name}: {response.status}"
            )
    
    def _transform_exception(self, exception: Exception, method: str, url: str) -> Exception:
        """Transform exceptions to appropriate API exceptions."""
        if isinstance(exception, asyncio.TimeoutError):
            return APITimeoutError(f"Timeout for {self.api_name}: {method} {url}")
        elif isinstance(exception, aiohttp.ClientError):
            return ExternalAPIError(f"Client error for {self.api_name}: {exception}")
        else:
            return exception
    
    def _record_error(self, error: Exception, method: str, url: str):
        """Record error for analysis and monitoring."""
        error_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'method': method,
            'url': url,
            'api_name': self.api_name
        }
        
        self.error_history.append(error_record)
        
        # Keep only recent errors
        if len(self.error_history) > self.max_error_history:
            self.error_history = self.error_history[-self.max_error_history:]
        
        logger.error(f"API error recorded for {self.api_name}: {error_record}")
    
    async def get(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        cache_ttl: Optional[int] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make GET request with caching support."""
        # Check cache first
        cache_key = self._get_cache_key('GET', endpoint, params)
        cached_response = await self._get_cached_response(cache_key)
        
        if cached_response:
            return cached_response
        
        # Make request
        response = await self._make_request('GET', endpoint, params, None, headers, timeout)
        
        # Cache response
        ttl = cache_ttl if cache_ttl is not None else self.cache_ttl
        if ttl > 0:
            await self._cache_response(cache_key, response)
        
        return response
    
    async def post(
        self,
        endpoint: str,
        data: Optional[Union[Dict, str, bytes]] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make POST request."""
        return await self._make_request('POST', endpoint, params, data, headers, timeout)
    
    async def put(
        self,
        endpoint: str,
        data: Optional[Union[Dict, str, bytes]] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make PUT request."""
        return await self._make_request('PUT', endpoint, params, data, headers, timeout)
    
    async def delete(
        self,
        endpoint: str,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Make DELETE request."""
        return await self._make_request('DELETE', endpoint, params, None, headers, timeout)
    
    async def upload_file(
        self,
        endpoint: str,
        file_data: bytes,
        filename: str,
        field_name: str = 'file',
        additional_fields: Optional[Dict] = None,
        timeout: Optional[int] = None
    ) -> Dict[str, Any]:
        """Upload file using multipart/form-data."""
        if not self.session:
            await self.initialize()
        
        await self._check_rate_limits()
        
        url = urljoin(self.base_url, endpoint.lstrip('/'))
        
        # Prepare multipart data
        data = aiohttp.FormData()
        data.add_field(field_name, file_data, filename=filename)
        
        if additional_fields:
            for key, value in additional_fields.items():
                data.add_field(key, str(value))
        
        # Prepare headers (don't set Content-Type for multipart)
        headers = self._get_default_headers()
        headers.pop('Content-Type', None)  # Let aiohttp set this for multipart
        
        start_time = time.time()
        
        try:
            request_timeout = ClientTimeout(total=timeout or (self.timeout * 2))
            
            async with self.session.post(
                url,
                data=data,
                headers=headers,
                timeout=request_timeout
            ) as response:
                response_time = time.time() - start_time
                
                self.stats['total_requests'] += 1
                self.stats['last_request_time'] = datetime.utcnow().isoformat()
                
                await self._handle_response_status(response)
                
                try:
                    response_data = await response.json()
                except Exception:
                    response_text = await response.text()
                    response_data = {'raw_response': response_text}
                
                self.stats['successful_requests'] += 1
                
                logger.info(
                    f"{self.api_name} file upload successful: "
                    f"{filename} - {response.status} - {response_time:.2f}s"
                )
                
                return response_data
                
        except Exception as e:
            self.stats['failed_requests'] += 1
            self._record_error(e, 'POST', url)
            raise self._transform_exception(e, 'POST', url)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client performance statistics."""
        return {
            **self.stats,
            'api_name': self.api_name,
            'rate_limits': {
                'per_minute': self.rate_limit_per_minute,
                'per_hour': self.rate_limit_per_hour,
                'current_minute_usage': len(self._request_timestamps),
                'current_hour_usage': self._hourly_request_count
            },
            'error_rate': (
                self.stats['failed_requests'] / max(self.stats['total_requests'], 1)
            ) * 100,
            'cache_hit_rate': (
                self.stats['cache_hits'] / max(
                    self.stats['cache_hits'] + self.stats['cache_misses'], 1
                )
            ) * 100
        }
    
    def get_recent_errors(self, limit: int = 10) -> List[Dict]:
        """Get recent error history."""
        return self.error_history[-limit:]
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform health check on the API."""
        try:
            # Try a simple request to test connectivity
            start_time = time.time()
            
            # Most APIs have a status or health endpoint
            health_endpoints = ['/', '/health', '/status', '/ping']
            
            for endpoint in health_endpoints:
                try:
                    await self.get(endpoint, timeout=10)
                    response_time = time.time() - start_time
                    
                    return {
                        'status': 'healthy',
                        'api_name': self.api_name,
                        'response_time': response_time,
                        'endpoint_tested': endpoint,
                        'timestamp': datetime.utcnow().isoformat()
                    }
                except Exception:
                    continue
            
            # If no standard endpoint works, the API might still be healthy
            # but doesn't have a standard health endpoint
            return {
                'status': 'unknown',
                'api_name': self.api_name,
                'message': 'No standard health endpoint found',
                'timestamp': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                'status': 'unhealthy',
                'api_name': self.api_name,
                'error': str(e),
                'timestamp': datetime.utcnow().isoformat()
            }
    
    async def close(self):
        """Close the client session and cleanup resources."""
        if self.session:
            await self.session.close()
            self.session = None
            
        logger.info(f"API client closed for {self.api_name}")


# Factory function for creating API clients
def create_api_client(
    api_name: str,
    base_url: str,
    api_key: str,
    **kwargs
) -> APIClient:
    """Factory function to create configured API client."""
    return APIClient(
        base_url=base_url,
        api_key=api_key,
        api_name=api_name,
        **kwargs
    )

async def init_api_clients() -> bool:
    """
    Initialize all external API clients
    
    Returns:
        True if initialization successful
        
    Raises:
        Exception: If API clients initialization fails
    """
    try:
        logger.info("Initializing external API clients...")
        
        # Initialize circuit breakers for APIs
        from .circuit_breaker import circuit_breaker_manager
        
        # Create circuit breakers for plant identification APIs
        circuit_breaker_manager.get_circuit_breaker("plantnet_api")
        circuit_breaker_manager.get_circuit_breaker("trefle_api")
        circuit_breaker_manager.get_circuit_breaker("plant_id_api")
        circuit_breaker_manager.get_circuit_breaker("kindwise_api")
        
        # Create circuit breakers for weather APIs
        circuit_breaker_manager.get_circuit_breaker("openweather_api")
        circuit_breaker_manager.get_circuit_breaker("tomorrow_io_api")
        circuit_breaker_manager.get_circuit_breaker("weatherstack_api")
        circuit_breaker_manager.get_circuit_breaker("visual_crossing_api")
        
        logger.info("✅ External API clients initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ External API clients initialization failed: {e}")
        raise


async def cleanup_api_clients() -> None:
    """
    Cleanup external API clients and close connections
    """
    try:
        logger.info("Cleaning up external API clients...")
        
        # Reset circuit breakers
        from .circuit_breaker import circuit_breaker_manager
        circuit_breaker_manager.reset_all_metrics()
        
        logger.info("✅ External API clients cleanup completed")
        
    except Exception as e:
        logger.error(f"❌ Error cleaning up external API clients: {e}")
        raise