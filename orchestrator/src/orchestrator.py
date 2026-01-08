import logging
from typing import Dict, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import redis
import json
from kubernetes import client, config


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DeploymentStatus(Enum):
    """Deployment status enum"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


class FailureType(Enum):
    """Types of failures"""
    BUILD_FAILURE = "build_failure"
    TEST_FAILURE = "test_failure"
    DEPLOYMENT_FAILURE = "deployment_failure"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    TIMEOUT = "timeout"


@dataclass
class DeploymentState:
    """Deployment state tracking"""
    deployment_id: str
    namespace: str
    app_name: str
    version: str
    status: DeploymentStatus
    previous_version: Optional[str]
    retry_count: int
    failure_type: Optional[FailureType]
    timestamp: float
    metadata: Dict


class SelfHealingOrchestrator:
    """
    Self-healing orchestrator for CI/CD pipeline
    Monitors deployments and automatically handles failures
    """
    
    def __init__(
        self,
        redis_host: str = 'localhost',
        redis_port: int = 6379,
        max_retries: int = 3,
        rollback_threshold: int = 2
    ):
        """Initialize orchestrator"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            decode_responses=True
        )
        self.max_retries = max_retries
        self.rollback_threshold = rollback_threshold
        
        # Load Kubernetes config
        try:
            config.load_incluster_config()
        except:
            config.load_kube_config()
        
        self.k8s_apps = client.AppsV1Api()
        self.k8s_core = client.CoreV1Api()
        
        logger.info("Self-Healing Orchestrator initialized")
    
    def save_deployment_state(self, state: DeploymentState) -> None:
        """Save deployment state to Redis"""
        key = f"deployment:{state.deployment_id}"
        self.redis_client.setex(
            key,
            86400,  # 24 hours TTL
            json.dumps(asdict(state), default=str)
        )
        logger.info(f"Saved deployment state: {state.deployment_id}")
    
    def get_deployment_state(self, deployment_id: str) -> Optional[DeploymentState]:
        """Retrieve deployment state from Redis"""
        key = f"deployment:{deployment_id}"
        data = self.redis_client.get(key)
        if data:
            state_dict = json.loads(data)
            state_dict['status'] = DeploymentStatus(state_dict['status'])
            if state_dict.get('failure_type'):
                state_dict['failure_type'] = FailureType(state_dict['failure_type'])
            return DeploymentState(**state_dict)
        return None