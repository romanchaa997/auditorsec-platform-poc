#!/usr/bin/env python3
"""
Redis-backed Job Queue for Task Management

Phase 2 Component: Task Queue Management System
- Priority levels for urgent cases
- Dead letter queue for failed tasks
- Task scheduling & retry policies
- Integration with workflow orchestration
"""

import json
import logging
import redis
import uuid
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from enum import Enum
from dataclasses import dataclass, asdict

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Task priority levels for job queue"""
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"
    DEAD_LETTERED = "dead_lettered"


@dataclass
class TaskMetadata:
    """Task metadata for tracking and scheduling"""
    task_id: str
    name: str
    priority: TaskPriority
    status: TaskStatus
    created_at: str
    scheduled_at: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: Optional[str] = None
    timeout_seconds: int = 3600


class TaskQueue:
    """Redis-backed task queue with priority and retry management"""

    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379, db: int = 0):
        """Initialize Redis connection"""
        self.redis_client = redis.Redis(
            host=redis_host,
            port=redis_port,
            db=db,
            decode_responses=True
        )
        self.queue_prefix = "task_queue:"
        self.metadata_prefix = "task_meta:"
        self.dead_letter_queue = "task_queue:dead_letter"
        self._verify_connection()

    def _verify_connection(self) -> bool:
        """Verify Redis connection"""
        try:
            self.redis_client.ping()
            logger.info("Redis connection established")
            return True
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def enqueue_task(self, task_name: str, payload: Dict[str, Any], 
                     priority: TaskPriority = TaskPriority.NORMAL,
                     scheduled_delay: Optional[int] = None) -> str:
        """Enqueue a new task with priority"""
        task_id = str(uuid.uuid4())
        metadata = TaskMetadata(
            task_id=task_id,
            name=task_name,
            priority=priority,
            status=TaskStatus.PENDING,
            created_at=datetime.utcnow().isoformat(),
            scheduled_at=None if not scheduled_delay 
                else (datetime.utcnow() + timedelta(seconds=scheduled_delay)).isoformat()
        )
        
        queue_key = f"{self.queue_prefix}{priority.name}"
        
        task_data = {
            "task_id": task_id,
            "name": task_name,
            "payload": json.dumps(payload),
            "priority": priority.value,
            "created_at": metadata.created_at
        }
        
        self.redis_client.lpush(queue_key, json.dumps(task_data))
        self.redis_client.setex(
            f"{self.metadata_prefix}{task_id}",
            86400,  # 24-hour expiry
            json.dumps(asdict(metadata), default=str)
        )
        
        logger.info(f"Task enqueued: {task_id} ({task_name}) with priority {priority.name}")
        return task_id

    def dequeue_task(self) -> Optional[Dict[str, Any]]:
        """Dequeue next task from highest priority queue"""
        for priority in sorted(TaskPriority, key=lambda x: x.value, reverse=True):
            queue_key = f"{self.queue_prefix}{priority.name}"
            task_data = self.redis_client.rpop(queue_key)
            
            if task_data:
                task = json.loads(task_data)
                task_id = task['task_id']
                
                # Update status to RUNNING
                self._update_task_status(task_id, TaskStatus.RUNNING)
                logger.info(f"Task dequeued: {task_id}")
                return task
        
        return None

    def mark_task_completed(self, task_id: str, result: Optional[Dict] = None) -> bool:
        """Mark task as completed"""
        return self._update_task_status(task_id, TaskStatus.COMPLETED, result=result)

    def mark_task_failed(self, task_id: str, error: str) -> bool:
        """Mark task as failed and handle retry logic"""
        metadata_key = f"{self.metadata_prefix}{task_id}"
        metadata_data = self.redis_client.get(metadata_key)
        
        if not metadata_data:
            logger.error(f"Task metadata not found: {task_id}")
            return False
        
        metadata = json.loads(metadata_data)
        retry_count = metadata.get('retry_count', 0)
        max_retries = metadata.get('max_retries', 3)
        
        if retry_count < max_retries:
            # Schedule retry
            retry_count += 1
            metadata['retry_count'] = retry_count
            metadata['status'] = TaskStatus.RETRYING.value
            metadata['error_message'] = error
            
            self.redis_client.setex(
                metadata_key,
                86400,
                json.dumps(metadata, default=str)
            )
            
            # Re-enqueue for retry with delay
            task_data = {
                "task_id": task_id,
                "name": metadata['name'],
                "payload": metadata.get('payload', '{}'),
                "priority": metadata.get('priority', TaskPriority.NORMAL.value),
                "retry_count": retry_count
            }
            
            queue_key = f"{self.queue_prefix}{TaskPriority(metadata['priority']).name}"
            self.redis_client.lpush(queue_key, json.dumps(task_data))
            
            logger.info(f"Task scheduled for retry: {task_id} (attempt {retry_count}/{max_retries})")
            return True
        else:
            # Move to dead letter queue
            return self._move_to_dead_letter(task_id, error)

    def _move_to_dead_letter(self, task_id: str, error: str) -> bool:
        """Move failed task to dead letter queue"""
        metadata_key = f"{self.metadata_prefix}{task_id}"
        metadata_data = self.redis_client.get(metadata_key)
        
        if not metadata_data:
            return False
        
        metadata = json.loads(metadata_data)
        metadata['status'] = TaskStatus.DEAD_LETTERED.value
        metadata['error_message'] = error
        
        self.redis_client.lpush(
            self.dead_letter_queue,
            json.dumps({
                "task_id": task_id,
                "metadata": metadata,
                "dead_lettered_at": datetime.utcnow().isoformat()
            }, default=str)
        )
        
        logger.warning(f"Task moved to dead letter queue: {task_id} - {error}")
        return True

    def _update_task_status(self, task_id: str, status: TaskStatus, 
                           result: Optional[Dict] = None) -> bool:
        """Update task status metadata"""
        metadata_key = f"{self.metadata_prefix}{task_id}"
        metadata_data = self.redis_client.get(metadata_key)
        
        if not metadata_data:
            logger.error(f"Task metadata not found: {task_id}")
            return False
        
        metadata = json.loads(metadata_data)
        metadata['status'] = status.value
        
        if status == TaskStatus.RUNNING:
            metadata['started_at'] = datetime.utcnow().isoformat()
        elif status == TaskStatus.COMPLETED:
            metadata['completed_at'] = datetime.utcnow().isoformat()
        
        self.redis_client.setex(
            metadata_key,
            86400,
            json.dumps(metadata, default=str)
        )
        
        logger.info(f"Task status updated: {task_id} -> {status.value}")
        return True

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get current task status and metadata"""
        metadata_key = f"{self.metadata_prefix}{task_id}"
        metadata_data = self.redis_client.get(metadata_key)
        
        if not metadata_data:
            return None
        
        return json.loads(metadata_data)

    def get_queue_stats(self) -> Dict[str, int]:
        """Get current queue statistics"""
        stats = {}
        
        for priority in TaskPriority:
            queue_key = f"{self.queue_prefix}{priority.name}"
            queue_length = self.redis_client.llen(queue_key)
            stats[f"{priority.name}_queue"] = queue_length
        
        dead_letter_length = self.redis_client.llen(self.dead_letter_queue)
        stats['dead_letter_queue'] = dead_letter_length
        
        return stats

    def get_dead_letter_tasks(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve tasks from dead letter queue"""
        tasks = self.redis_client.lrange(self.dead_letter_queue, 0, limit - 1)
        return [json.loads(task) for task in tasks]

    def clear_queue(self, priority: Optional[TaskPriority] = None) -> bool:
        """Clear queue (for testing/maintenance)"""
        if priority:
            queue_key = f"{self.queue_prefix}{priority.name}"
            self.redis_client.delete(queue_key)
            logger.info(f"Cleared {priority.name} queue")
        else:
            for p in TaskPriority:
                queue_key = f"{self.queue_prefix}{p.name}"
                self.redis_client.delete(queue_key)
            logger.info("Cleared all queues")
        return True


if __name__ == "__main__":
    # Example usage
    queue = TaskQueue()
    
    # Enqueue tasks
    task_id1 = queue.enqueue_task(
        "detect_anomaly",
        {"source": "network_monitor", "threshold": 0.95},
        priority=TaskPriority.HIGH
    )
    
    task_id2 = queue.enqueue_task(
        "generate_report",
        {"case_id": 123, "format": "pdf"},
        priority=TaskPriority.NORMAL
    )
    
    # Get queue stats
    stats = queue.get_queue_stats()
    print(f"Queue stats: {stats}")
    
    # Dequeue and process
    task = queue.dequeue_task()
    if task:
        print(f"Processing task: {task['task_id']}")
        # Simulate task processing
        queue.mark_task_completed(task['task_id'], {"result": "success"})
