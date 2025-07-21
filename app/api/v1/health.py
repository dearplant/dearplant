# 📄 File: app/api/v1/health.py
# 🧭 Purpose (Layman Explanation): 
# This file provides health check endpoints that tell us if our plant care app is working properly,
# like a doctor's checkup for our system to make sure the database, cache, and other services are healthy.
# 🧪 Purpose (Technical Summary): 
# Implements health check and system monitoring endpoints for infrastructure components,
# providing real-time status of database, cache, external APIs, and overall system health.
# 🔗 Dependencies: 
# FastAPI, app.shared.infrastructure (database, cache, external_apis), datetime, psutil
# 🔄 Connected Modules / Calls From: 
# app.api.v1.router, app.main.py, monitoring systems, load balancers

import asyncio
import logging
import platform
import sys
from datetime import datetime
from typing import Dict, Any, Optional

import psutil
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import JSONResponse

from app.shared.config.settings import get_settings
from app.shared.infrastructure.database.connection import database_health_check as db_health_check
from app.shared.infrastructure.cache.redis_client import health_check as redis_health_check
from app.shared.infrastructure.external_apis.circuit_breaker import circuit_breaker_manager

logger = logging.getLogger(__name__)

# Create router for health endpoints
health_router = APIRouter()

# Application start time for uptime calculation
_app_start_time = datetime.now()


@health_router.get("/health", 
                  summary="Basic Health Check",
                  description="Basic health check endpoint for load balancers and monitoring",
                  tags=["Health Check"])
async def health_check() -> JSONResponse:
    """
    Basic health check endpoint
    
    Returns simple OK status for quick health verification.
    This endpoint is designed for load balancers and basic monitoring.
    """
    return JSONResponse(
        status_code=200,
        content={
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "service": "plant-care-api",
            "version": get_settings().APP_VERSION
        }
    )


@health_router.get("/health/detailed",
                  summary="Detailed Health Check", 
                  description="Comprehensive health check including all system components",
                  tags=["Health Check"])
async def detailed_health_check() -> JSONResponse:
    """
    Comprehensive health check for all system components
    
    Checks the health of:
    - Database connectivity
    - Redis cache connectivity  
    - External API circuit breakers
    - System resources
    - Application metrics
    
    Returns detailed status information for monitoring and debugging.
    """
    try:
        # Start time for response time calculation
        start_time = datetime.now()
        
        # Initialize health status
        overall_status = "healthy"
        components = {}
        
        # Check database health
        try:
            db_health = await db_health_check()
            components["database"] = db_health
            if db_health["status"] != "healthy":
                overall_status = "degraded"
        except Exception as e:
            components["database"] = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            overall_status = "unhealthy"
        
        # Check Redis health
        try:
            redis_health = await redis_health_check()
            components["redis"] = redis_health
            if redis_health["status"] != "healthy":
                overall_status = "degraded"
        except Exception as e:
            components["redis"] = {
                "status": "unhealthy", 
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            overall_status = "unhealthy"
        
        # Check external APIs (circuit breakers)
        try:
            api_health = _check_external_apis_health()
            components["external_apis"] = api_health
            if api_health["status"] != "healthy":
                overall_status = "degraded"
        except Exception as e:
            components["external_apis"] = {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            overall_status = "unhealthy"
        
        # Get system metrics
        try:
            system_metrics = _get_system_metrics()
            components["system"] = system_metrics
            
            # Check system resource thresholds
            if (system_metrics["cpu_percent"] > 90 or 
                system_metrics["memory_percent"] > 90 or
                system_metrics["disk_percent"] > 95):
                overall_status = "degraded"
                
        except Exception as e:
            components["system"] = {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            overall_status = "degraded"
        
        # Calculate response time
        response_time = (datetime.now() - start_time).total_seconds()
        
        # Prepare response
        health_response = {
            "status": overall_status,
            "timestamp": datetime.now().isoformat(),
            "service": "plant-care-api",
            "version": get_settings().APP_VERSION,
            "uptime_seconds": (datetime.now() - _app_start_time).total_seconds(),
            "response_time_seconds": response_time,
            "components": components
        }
        
        # Return appropriate status code
        if overall_status == "healthy":
            status_code = 200
        elif overall_status == "degraded":
            status_code = 200  # Still operational but with issues
        else:
            status_code = 503  # Service unavailable
            
        return JSONResponse(
            status_code=status_code,
            content=health_response
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=500,
            content={
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "service": "plant-care-api"
            }
        )


@health_router.get("/health/live",
                  summary="Liveness Probe",
                  description="Kubernetes liveness probe endpoint", 
                  tags=["Health Check"])
async def liveness_probe() -> Response:
    """
    Liveness probe for Kubernetes
    
    Returns 200 if the application is alive and running.
    This is used by Kubernetes to determine if the pod should be restarted.
    """
    return Response(status_code=200, content="OK")


@health_router.get("/health/ready",
                  summary="Readiness Probe",
                  description="Kubernetes readiness probe endpoint",
                  tags=["Health Check"])
async def readiness_probe() -> JSONResponse:
    """
    Readiness probe for Kubernetes
    
    Returns 200 if the application is ready to serve traffic.
    Checks critical dependencies like database connectivity.
    """
    try:
        # Check database connectivity (critical for readiness)
        db_health = await db_health_check()
        
        if db_health["status"] == "healthy":
            return JSONResponse(
                status_code=200,
                content={"status": "ready", "timestamp": datetime.now().isoformat()}
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "not_ready", 
                    "reason": "database_unhealthy",
                    "timestamp": datetime.now().isoformat()
                }
            )
            
    except Exception as e:
        logger.error(f"Readiness probe failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "reason": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@health_router.get("/health/startup",
                  summary="Startup Probe", 
                  description="Kubernetes startup probe endpoint",
                  tags=["Health Check"])
async def startup_probe() -> JSONResponse:
    """
    Startup probe for Kubernetes
    
    Returns 200 when the application has finished starting up.
    Used to determine when the application is ready for liveness/readiness probes.
    """
    try:
        # Check if all critical systems are initialized
        settings = get_settings()
        
        # Basic startup checks
        startup_checks = {
            "database_initialized": False,
            "redis_initialized": False,
            "settings_loaded": bool(settings),
            "uptime_seconds": (datetime.now() - _app_start_time).total_seconds()
        }
        
        # Check database
        try:
            db_health = await asyncio.wait_for(db_health_check(), timeout=5.0)
            startup_checks["database_initialized"] = db_health["status"] in ["healthy", "degraded"]
        except asyncio.TimeoutError:
            startup_checks["database_initialized"] = False
        except Exception:
            startup_checks["database_initialized"] = False
        
        # Check Redis
        try:
            redis_health = await asyncio.wait_for(redis_health_check(), timeout=5.0)
            startup_checks["redis_initialized"] = redis_health["status"] in ["healthy", "degraded"]
        except asyncio.TimeoutError:
            startup_checks["redis_initialized"] = False
        except Exception:
            startup_checks["redis_initialized"] = False
        
        # Determine if startup is complete
        critical_systems_ready = (
            startup_checks["database_initialized"] and
            startup_checks["settings_loaded"]
        )
        
        if critical_systems_ready:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "started",
                    "timestamp": datetime.now().isoformat(),
                    "checks": startup_checks
                }
            )
        else:
            return JSONResponse(
                status_code=503,
                content={
                    "status": "starting",
                    "timestamp": datetime.now().isoformat(),
                    "checks": startup_checks
                }
            )
            
    except Exception as e:
        logger.error(f"Startup probe failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "startup_error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        )


@health_router.get("/metrics",
                  summary="System Metrics",
                  description="System performance and resource metrics",
                  tags=["Health Check"])
async def system_metrics() -> JSONResponse:
    """
    System metrics endpoint for monitoring
    
    Provides detailed system performance metrics including:
    - CPU usage
    - Memory usage
    - Disk usage
    - Network statistics
    - Application metrics
    """
    try:
        metrics = _get_detailed_system_metrics()
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.now().isoformat(),
                "service": "plant-care-api",
                "metrics": metrics
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get system metrics: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve system metrics: {str(e)}"
        )


def _check_external_apis_health() -> Dict[str, Any]:
    """Check health of external APIs via circuit breakers"""
    try:
        all_metrics = circuit_breaker_manager.get_all_metrics()
        
        healthy_circuits = circuit_breaker_manager.get_healthy_circuits()
        unhealthy_circuits = circuit_breaker_manager.get_unhealthy_circuits()
        
        # Determine overall API health
        total_circuits = len(all_metrics)
        healthy_count = len(healthy_circuits)
        
        if total_circuits == 0:
            status = "no_circuits"
        elif healthy_count == total_circuits:
            status = "healthy"
        elif healthy_count > total_circuits / 2:
            status = "degraded"
        else:
            status = "unhealthy"
        
        return {
            "status": status,
            "total_circuits": total_circuits,
            "healthy_circuits": healthy_count,
            "unhealthy_circuits": len(unhealthy_circuits),
            "healthy_circuit_names": healthy_circuits,
            "unhealthy_circuit_names": unhealthy_circuits,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _get_system_metrics() -> Dict[str, Any]:
    """Get basic system metrics"""
    try:
        # CPU usage
        cpu_percent = psutil.cpu_percent(interval=1)
        
        # Memory usage
        memory = psutil.virtual_memory()
        memory_percent = memory.percent
        
        # Disk usage
        disk = psutil.disk_usage('/')
        disk_percent = (disk.used / disk.total) * 100
        
        return {
            "status": "healthy",
            "cpu_percent": cpu_percent,
            "memory_percent": memory_percent,
            "disk_percent": disk_percent,
            "uptime_seconds": (datetime.now() - _app_start_time).total_seconds(),
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }


def _get_detailed_system_metrics() -> Dict[str, Any]:
    """Get detailed system performance metrics"""
    # Basic system info
    system_info = {
        "platform": platform.platform(),
        "python_version": sys.version,
        "cpu_count": psutil.cpu_count(),
        "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat(),
    }
    
    # CPU metrics
    cpu_metrics = {
        "usage_percent": psutil.cpu_percent(interval=1),
        "usage_per_cpu": psutil.cpu_percent(interval=1, percpu=True),
        "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None,
    }
    
    # Memory metrics
    memory = psutil.virtual_memory()
    memory_metrics = {
        "total_bytes": memory.total,
        "available_bytes": memory.available,
        "used_bytes": memory.used,
        "usage_percent": memory.percent,
        "cached_bytes": getattr(memory, 'cached', 0),
        "buffers_bytes": getattr(memory, 'buffers', 0),
    }
    
    # Disk metrics
    disk = psutil.disk_usage('/')
    disk_metrics = {
        "total_bytes": disk.total,
        "used_bytes": disk.used,
        "free_bytes": disk.free,
        "usage_percent": (disk.used / disk.total) * 100,
    }
    
    # Network metrics
    try:
        net_io = psutil.net_io_counters()
        network_metrics = {
            "bytes_sent": net_io.bytes_sent,
            "bytes_received": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_received": net_io.packets_recv,
            "errors_in": net_io.errin,
            "errors_out": net_io.errout,
            "drops_in": net_io.dropin,
            "drops_out": net_io.dropout,
        }
    except Exception:
        network_metrics = {"error": "Network metrics unavailable"}
    
    # Process metrics
    try:
        process = psutil.Process()
        process_metrics = {
            "pid": process.pid,
            "cpu_percent": process.cpu_percent(),
            "memory_percent": process.memory_percent(),
            "memory_info_bytes": process.memory_info().rss,
            "num_threads": process.num_threads(),
            "num_fds": process.num_fds() if hasattr(process, 'num_fds') else None,
            "create_time": datetime.fromtimestamp(process.create_time()).isoformat(),
        }
    except Exception:
        process_metrics = {"error": "Process metrics unavailable"}
    
    # Application metrics
    app_metrics = {
        "uptime_seconds": (datetime.now() - _app_start_time).total_seconds(),
        "start_time": _app_start_time.isoformat(),
        "version": get_settings().APP_VERSION,
        "environment": get_settings().ENVIRONMENT,
    }
    
    return {
        "system_info": system_info,
        "cpu": cpu_metrics,
        "memory": memory_metrics,
        "disk": disk_metrics,
        "network": network_metrics,
        "process": process_metrics,
        "application": app_metrics,
    }