#!/usr/bin/env python3
"""
Orchestration Engine - Integration of Task Queue + Workflow Orchestrator + State Machine

Phase 2 Integration: Connects all components for unified workflow execution
"""

import logging
from typing import Dict, Any, Optional
from enum import Enum
from task_queue import TaskQueue, TaskPriority, TaskStatus
from workflow_orchestrator import WorkflowOrchestrator, WorkflowInstance
from state_machine import StateMachine, CaseState

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OrchestrationEngine:
    """Unified orchestration engine for AI-SOC workflows"""

    def __init__(self, redis_host: str = 'localhost', redis_port: int = 6379):
        self.queue = TaskQueue(redis_host, redis_port)
        self.workflow_orchestrator = WorkflowOrchestrator()
        self.state_machines: Dict[str, StateMachine] = {}
        logger.info("OrchestrationEngine initialized")

    def create_case_workflow(self, case_id: str, case_type: str, 
                            priority: TaskPriority = TaskPriority.NORMAL) -> str:
        """Create new case workflow"""
        # Create workflow instance
        workflow_id = self.workflow_orchestrator.create_workflow(
            name=f"case_{case_id}",
            workflow_type=case_type,
            case_id=case_id
        )
        
        # Initialize state machine for case
        self.state_machines[case_id] = StateMachine(case_id)
        
        # Enqueue initial task
        task_id = self.queue.enqueue_task(
            f"case_intake_{case_type}",
            {"case_id": case_id, "workflow_id": workflow_id},
            priority=priority
        )
        
        logger.info(f"Case workflow created: {case_id} with task {task_id}")
        return workflow_id

    def process_tasks(self, batch_size: int = 10) -> int:
        """Process queued tasks in batch"""
        processed = 0
        
        for _ in range(batch_size):
            task = self.queue.dequeue_task()
            if not task:
                break
            
            try:
                result = self._execute_task(task)
                self.queue.mark_task_completed(task['task_id'], result)
                processed += 1
            except Exception as e:
                logger.error(f"Task failed: {task['task_id']} - {str(e)}")
                self.queue.mark_task_failed(task['task_id'], str(e))
        
        return processed

    def _execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """Execute single task with workflow orchestration"""
        task_name = task['name']
        payload = task['payload']
        
        if 'case_intake' in task_name:
            return self._handle_case_intake(payload)
        elif 'analysis' in task_name:
            return self._handle_analysis(payload)
        elif 'remediation' in task_name:
            return self._handle_remediation(payload)
        else:
            raise ValueError(f"Unknown task: {task_name}")

    def _handle_case_intake(self, payload: Dict) -> Dict[str, Any]:
        """Handle case intake workflow"""
        case_id = payload['case_id']
        sm = self.state_machines.get(case_id)
        
        if sm:
            sm.transition(CaseState.INTAKE_VALIDATION)
        
        return {"status": "intake_completed", "case_id": case_id}

    def _handle_analysis(self, payload: Dict) -> Dict[str, Any]:
        """Handle analysis workflow"""
        case_id = payload['case_id']
        sm = self.state_machines.get(case_id)
        
        if sm:
            sm.transition(CaseState.ANALYZING)
        
        return {"status": "analysis_completed", "case_id": case_id}

    def _handle_remediation(self, payload: Dict) -> Dict[str, Any]:
        """Handle remediation workflow"""
        case_id = payload['case_id']
        sm = self.state_machines.get(case_id)
        
        if sm:
            sm.transition(CaseState.REMEDIATION_IN_PROGRESS)
            sm.transition(CaseState.REMEDIATION_COMPLETED)
        
        return {"status": "remediation_completed", "case_id": case_id}

    def get_case_status(self, case_id: str) -> Dict[str, Any]:
        """Get current case status"""
        sm = self.state_machines.get(case_id)
        if not sm:
            return {"status": "not_found"}
        
        return {
            "case_id": case_id,
            "state": sm.current_state.value,
            "duration_seconds": sm.get_duration_seconds()
        }

    def get_queue_metrics(self) -> Dict[str, Any]:
        """Get queue metrics and statistics"""
        stats = self.queue.get_queue_stats()
        total_queued = sum(v for k, v in stats.items() if 'queue' in k)
        
        return {
            "total_tasks_queued": total_queued,
            "active_cases": len(self.state_machines),
            "queue_stats": stats
        }


if __name__ == "__main__":
    engine = OrchestrationEngine()
    
    # Example workflow
    wf_id = engine.create_case_workflow(
        case_id="CASE_001",
        case_type="security_incident",
        priority=TaskPriority.HIGH
    )
    
    # Process tasks
    processed = engine.process_tasks(batch_size=5)
    print(f"Processed {processed} tasks")
    
    # Get metrics
    metrics = engine.get_queue_metrics()
    print(f"Metrics: {metrics}")
