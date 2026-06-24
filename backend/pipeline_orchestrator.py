"""
Pipeline Orchestration Engine

Manages the execution of the 4-agent PMF pipeline:
- Dependency resolution
- Sequential/parallel execution
- State management
- Error handling and retry logic
- Logging and monitoring
- Result aggregation

Usage:
    orchestrator = PipelineOrchestrator('pipeline_config.yaml')
    result = orchestrator.run('full_pipeline')  # or 'incremental', 'agent_debug'
"""

import json
import yaml
import subprocess
import logging
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict, field
from typing import Dict, List, Optional, Tuple
import hashlib
import time
from enum import Enum


# ============================================================================
# ENUMS
# ============================================================================

class TaskStatus(Enum):
    """Status of a task"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRY = "retry"


class AgentDependency(Enum):
    """How to handle dependency failures"""
    REQUIRED = "required"      # Block if dependency fails
    OPTIONAL = "optional"      # Continue even if optional dependency fails


# ============================================================================
# DATA MODELS
# ============================================================================

@dataclass
class TaskExecution:
    """Track execution of a single task"""
    task_id: str
    agent_id: str
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Input/output
    input_files: List[str] = field(default_factory=list)
    output_files: List[str] = field(default_factory=list)
    input_hashes: Dict[str, str] = field(default_factory=dict)
    
    # Execution details
    command: str = ""
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    
    # Retries
    attempt_number: int = 1
    max_retries: int = 0
    last_error: Optional[str] = None
    
    # Monitoring
    cpu_percent: float = 0.0
    memory_mb: float = 0.0


@dataclass
class AgentExecution:
    """Track execution of an entire agent"""
    agent_id: str
    agent_name: str
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Tasks
    tasks: List[TaskExecution] = field(default_factory=list)
    succeeded_tasks: int = 0
    failed_tasks: int = 0
    skipped_tasks: int = 0
    
    # Dependencies
    dependencies_met: bool = False
    dependency_status: Dict[str, TaskStatus] = field(default_factory=dict)


@dataclass
class PipelineExecution:
    """Track overall pipeline execution"""
    run_id: str
    mode: str  # 'full_pipeline', 'incremental', etc.
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    
    # Agents
    agents: List[AgentExecution] = field(default_factory=list)
    total_agents: int = 0
    succeeded_agents: int = 0
    failed_agents: int = 0
    skipped_agents: int = 0
    
    # Overall
    total_tasks: int = 0
    succeeded_tasks: int = 0
    failed_tasks: int = 0
    total_evidence_items: int = 0
    total_cells_scored: int = 0
    
    # Errors
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ============================================================================
# ORCHESTRATION ENGINE
# ============================================================================

class PipelineOrchestrator:
    """Main orchestration engine for the PMF pipeline"""
    
    def __init__(self, config_path: str, state_dir: str = "state/"):
        """Initialize orchestrator with configuration"""
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.state_dir = Path(state_dir)
        self.state_dir.mkdir(parents=True, exist_ok=True)
        
        self.logger = self._setup_logging()
        self.logger.info(f"Pipeline Orchestrator initialized (v{self.config['version']})")
        
        # Generate run ID
        self.run_id = self._generate_run_id()
        self.execution = None
    
    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _setup_logging(self) -> logging.Logger:
        """Setup logging"""
        logger = logging.getLogger('PipelineOrchestrator')
        logger.setLevel(logging.DEBUG)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        
        return logger
    
    def _generate_run_id(self) -> str:
        """Generate unique run ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"run_{timestamp}"
    
    def run(self, mode: str = 'full_pipeline', skip_confirmations: bool = False) -> bool:
        """
        Execute the pipeline in specified mode
        
        Args:
            mode: Execution mode ('full_pipeline', 'incremental', 'agent_debug')
            skip_confirmations: If True, don't prompt for confirmation
        
        Returns:
            True if pipeline succeeded, False otherwise
        """
        
        # Get execution plan
        execution_plan = self._get_execution_plan(mode)
        
        if not execution_plan:
            self.logger.error(f"Invalid execution mode: {mode}")
            return False
        
        # Display plan
        self._display_execution_plan(execution_plan)
        
        # Confirm
        if not skip_confirmations:
            response = input("\nProceed with execution? (y/n): ").strip().lower()
            if response != 'y':
                self.logger.info("Pipeline execution cancelled by user")
                return False
        
        # Initialize execution tracking
        self.execution = PipelineExecution(
            run_id=self.run_id,
            mode=mode,
            status=TaskStatus.RUNNING,
            start_time=datetime.now(),
            total_agents=len(execution_plan['agents'])
        )
        
        self.logger.info(f"Starting pipeline execution: {self.run_id} ({mode})")
        
        # Execute agents in sequence
        for agent_id in execution_plan['agents']:
            if not self._execute_agent(agent_id):
                # Check if failure is fatal
                agent_config = self.config['agents'][agent_id]
                if agent_config['on_failure'] == 'stop':
                    self.logger.error(f"Critical agent {agent_id} failed. Stopping pipeline.")
                    self.execution.status = TaskStatus.FAILED
                    break
                else:
                    self.logger.warning(f"Agent {agent_id} failed but continuing (non-critical)")
        
        # Finalize
        self.execution.end_time = datetime.now()
        self.execution.duration_seconds = (self.execution.end_time - self.execution.start_time).total_seconds()
        
        # Determine overall status
        if self.execution.status != TaskStatus.FAILED:
            self.execution.status = TaskStatus.SUCCESS if self.execution.failed_agents == 0 else TaskStatus.FAILED
        
        # Save execution record
        self._save_execution_record()
        
        # Display summary
        self._display_summary()
        
        # Send notifications
        self._send_notifications()
        
        return self.execution.status == TaskStatus.SUCCESS
    
    def _get_execution_plan(self, mode: str) -> Optional[Dict]:
        """Get agents to execute for a given mode"""
        execution_mode = self.config['execution_modes'].get(mode)
        if not execution_mode:
            return None
        
        return {
            'mode': mode,
            'agents': execution_mode['agents'],
            'skip_cache': execution_mode.get('skip_cache', False),
            'estimated_duration': execution_mode.get('estimated_duration_minutes', 0)
        }
    
    def _display_execution_plan(self, plan: Dict):
        """Display the execution plan to the user"""
        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION PLAN")
        print("=" * 80)
        print(f"Mode: {plan['mode']}")
        print(f"Estimated Duration: {plan['estimated_duration']} minutes")
        print(f"Skip Cache: {plan['skip_cache']}")
        print(f"\nAgents to Execute:")
        for agent_id in plan['agents']:
            agent = self.config['agents'][agent_id]
            print(f"  • {agent['name']}")
            for task in agent['tasks']:
                required = "REQUIRED" if task['required'] else "optional"
                print(f"    - {task['name']} [{required}]")
        print("=" * 80)
    
    def _execute_agent(self, agent_id: str) -> bool:
        """Execute all tasks for an agent"""
        
        agent_config = self.config['agents'][agent_id]
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"Starting agent: {agent_id}")
        self.logger.info(f"{'='*60}")
        
        # Check dependencies
        deps_met, dep_status = self._check_dependencies(agent_id)
        if not deps_met:
            self.logger.error(f"Agent {agent_id} dependencies not met: {dep_status}")
            self.execution.failed_agents += 1
            return False
        
        # Create agent execution record
        agent_exec = AgentExecution(
            agent_id=agent_id,
            agent_name=agent_config['name'],
            status=TaskStatus.RUNNING,
            start_time=datetime.now(),
            dependency_status=dep_status
        )
        
        # Execute tasks
        for task_config in agent_config['tasks']:
            task_id = task_config['task_id']
            task_exec = self._execute_task(task_id, task_config)
            agent_exec.tasks.append(task_exec)
            
            if task_exec.status == TaskStatus.SUCCESS:
                agent_exec.succeeded_tasks += 1
            elif task_exec.status == TaskStatus.FAILED:
                agent_exec.failed_tasks += 1
                if task_config['required']:
                    # Required task failed - fail the agent
                    self.logger.error(f"Required task {task_id} failed")
                    agent_exec.status = TaskStatus.FAILED
                    break
            elif task_exec.status == TaskStatus.SKIPPED:
                agent_exec.skipped_tasks += 1
        
        # Finalize agent execution
        agent_exec.end_time = datetime.now()
        agent_exec.duration_seconds = (agent_exec.end_time - agent_exec.start_time).total_seconds()
        
        if agent_exec.status != TaskStatus.FAILED:
            agent_exec.status = TaskStatus.SUCCESS if agent_exec.failed_tasks == 0 else TaskStatus.FAILED
        
        self.execution.agents.append(agent_exec)
        self.execution.total_tasks += len(agent_exec.tasks)
        self.execution.succeeded_tasks += agent_exec.succeeded_tasks
        self.execution.failed_tasks += agent_exec.failed_tasks
        
        if agent_exec.status == TaskStatus.SUCCESS:
            self.execution.succeeded_agents += 1
            self.logger.info(f"✓ Agent {agent_id} completed successfully ({agent_exec.duration_seconds:.1f}s)")
        else:
            self.execution.failed_agents += 1
            self.logger.error(f"✗ Agent {agent_id} failed")
        
        return agent_exec.status == TaskStatus.SUCCESS
    
    def _check_dependencies(self, agent_id: str) -> Tuple[bool, Dict]:
        """Check if an agent's dependencies are met"""
        agent_config = self.config['agents'][agent_id]
        dependencies = agent_config.get('dependencies', [])
        
        dep_status = {}
        all_met = True
        
        for dep_agent_id in dependencies:
            # Find this agent in execution history
            dep_exec = None
            for agent_exec in self.execution.agents:
                if agent_exec.agent_id == dep_agent_id:
                    dep_exec = agent_exec
                    break
            
            if not dep_exec:
                dep_status[dep_agent_id] = "not_started"
                all_met = False
            else:
                dep_status[dep_agent_id] = dep_exec.status.value
                if dep_exec.status != TaskStatus.SUCCESS:
                    all_met = False
        
        return all_met, dep_status
    
    def _execute_task(self, task_id: str, task_config: Dict) -> TaskExecution:
        """Execute a single task"""
        
        task_exec = TaskExecution(
            task_id=task_id,
            agent_id=task_config.get('agent_id', ''),
            status=TaskStatus.RUNNING,
            start_time=datetime.now(),
            command=task_config.get('script', ''),
            max_retries=task_config.get('retry_count', 0)
        )
        
        self.logger.info(f"  Executing task: {task_id}")
        
        # Build command
        script = task_config.get('script', '')
        command = f"python {script}"
        
        # Attempt execution with retries
        attempt = 1
        while attempt <= task_config.get('retry_count', 1) + 1:
            try:
                task_exec.attempt_number = attempt
                
                # Run the script
                self.logger.debug(f"    Attempt {attempt}: {command}")
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=task_config.get('timeout_minutes', 60) * 60
                )
                
                task_exec.exit_code = result.returncode
                task_exec.stdout = result.stdout
                task_exec.stderr = result.stderr
                
                if result.returncode == 0:
                    task_exec.status = TaskStatus.SUCCESS
                    task_exec.end_time = datetime.now()
                    task_exec.duration_seconds = (task_exec.end_time - task_exec.start_time).total_seconds()
                    self.logger.info(f"    ✓ {task_id} completed ({task_exec.duration_seconds:.1f}s)")
                    return task_exec
                else:
                    # Non-zero exit code
                    task_exec.last_error = result.stderr or "Non-zero exit code"
                    self.logger.warning(f"    ✗ Attempt {attempt} failed: {task_exec.last_error[:100]}")
            
            except subprocess.TimeoutExpired as e:
                task_exec.last_error = f"Timeout after {task_config.get('timeout_minutes', 60)} minutes"
                self.logger.warning(f"    ✗ Attempt {attempt} timeout")
            
            except Exception as e:
                task_exec.last_error = str(e)
                self.logger.warning(f"    ✗ Attempt {attempt} error: {str(e)}")
            
            attempt += 1
            
            # Wait before retry
            if attempt <= task_config.get('retry_count', 0) + 1:
                delay = self._calculate_retry_delay(attempt - 1)
                self.logger.info(f"    Retrying in {delay}s...")
                time.sleep(delay)
        
        # All attempts failed
        task_exec.status = TaskStatus.FAILED
        task_exec.end_time = datetime.now()
        task_exec.duration_seconds = (task_exec.end_time - task_exec.start_time).total_seconds()
        
        if task_config.get('required', False):
            self.logger.error(f"    ✗ REQUIRED task {task_id} failed after {attempt-1} attempts")
        else:
            self.logger.warning(f"    ✗ OPTIONAL task {task_id} failed after {attempt-1} attempts")
        
        return task_exec
    
    def _calculate_retry_delay(self, attempt_number: int) -> int:
        """Calculate exponential backoff delay"""
        retry_config = self.config['error_handling']['retry_strategy']
        base_delay = retry_config['base_delay_seconds']
        max_delay = retry_config['max_delay_seconds']
        exponential_base = retry_config['exponential_base']
        
        delay = base_delay * (exponential_base ** attempt_number)
        return min(int(delay), max_delay)
    
    def _save_execution_record(self):
        """Save execution record to state file"""
        state_file = self.state_dir / f"execution_{self.run_id}.json"
        
        exec_dict = {
            'run_id': self.execution.run_id,
            'mode': self.execution.mode,
            'status': self.execution.status.value,
            'start_time': self.execution.start_time.isoformat() if self.execution.start_time else None,
            'end_time': self.execution.end_time.isoformat() if self.execution.end_time else None,
            'duration_seconds': self.execution.duration_seconds,
            'agents': [
                {
                    'agent_id': agent.agent_id,
                    'status': agent.status.value,
                    'duration_seconds': agent.duration_seconds,
                    'tasks': len(agent.tasks),
                    'succeeded': agent.succeeded_tasks,
                    'failed': agent.failed_tasks
                }
                for agent in self.execution.agents
            ],
            'summary': {
                'total_agents': self.execution.total_agents,
                'succeeded': self.execution.succeeded_agents,
                'failed': self.execution.failed_agents,
                'total_tasks': self.execution.total_tasks,
                'succeeded_tasks': self.execution.succeeded_tasks,
                'failed_tasks': self.execution.failed_tasks
            }
        }
        
        with open(state_file, 'w') as f:
            json.dump(exec_dict, f, indent=2)
        
        self.logger.info(f"Execution record saved to {state_file}")
    
    def _display_summary(self):
        """Display execution summary"""
        print("\n" + "=" * 80)
        print("PIPELINE EXECUTION SUMMARY")
        print("=" * 80)
        print(f"Run ID: {self.execution.run_id}")
        print(f"Mode: {self.execution.mode}")
        print(f"Status: {self.execution.status.value.upper()}")
        print(f"Duration: {self.execution.duration_seconds:.1f} seconds ({self.execution.duration_seconds/60:.1f} minutes)")
        print()
        print(f"Agents: {self.execution.succeeded_agents}/{self.execution.total_agents} succeeded")
        print(f"Tasks: {self.execution.succeeded_tasks}/{self.execution.total_tasks} succeeded")
        
        if self.execution.agents:
            print("\nAgent Details:")
            for agent in self.execution.agents:
                status_icon = "✓" if agent.status == TaskStatus.SUCCESS else "✗"
                print(f"  {status_icon} {agent.agent_name}: {agent.duration_seconds:.1f}s")
        
        print("=" * 80)
    
    def _send_notifications(self):
        """Send notifications based on execution result"""
        notifications_config = self.config['notifications']
        
        if self.execution.status == TaskStatus.SUCCESS:
            self.logger.info("Pipeline execution successful!")
        else:
            self.logger.error("Pipeline execution failed!")
            # Here you would send Slack, email, etc. based on config


if __name__ == '__main__':
    import sys
    
    # Simple CLI
    if len(sys.argv) < 2:
        mode = 'full_pipeline'
    else:
        mode = sys.argv[1]
    
    orchestrator = PipelineOrchestrator('pipeline_config.yaml')
    success = orchestrator.run(mode)
    sys.exit(0 if success else 1)
