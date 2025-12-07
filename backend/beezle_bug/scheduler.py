"""
Scheduler component for autonomous agent behavior.

The Scheduler manages timed triggers for agents, allowing them to
perform autonomous actions without explicit user input.
"""

import time
from loguru import logger
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Callable, Any
from enum import Enum

# Try to use eventlet if available (for Flask-SocketIO compatibility)
try:
    import eventlet
    USING_EVENTLET = True
except ImportError:
    USING_EVENTLET = False
    import threading


class TriggerType(Enum):
    """Types of scheduler triggers."""
    ONCE = "once"           # Fire once at a specific time
    INTERVAL = "interval"   # Fire repeatedly at fixed intervals
    CRON = "cron"          # Fire based on cron-like schedule (future)


@dataclass
class ScheduledTask:
    """A scheduled task for an agent."""
    id: str
    agent_id: str
    trigger_type: TriggerType
    callback: Callable[[], Any]
    
    # For ONCE triggers
    run_at: Optional[datetime] = None
    
    # For INTERVAL triggers
    interval_seconds: float = 0
    last_run: Optional[datetime] = None
    
    # State
    enabled: bool = True
    run_count: int = 0
    
    def should_run(self, now: datetime) -> bool:
        """Check if this task should run now."""
        if not self.enabled:
            return False
            
        if self.trigger_type == TriggerType.ONCE:
            return self.run_at is not None and now >= self.run_at and self.run_count == 0
            
        elif self.trigger_type == TriggerType.INTERVAL:
            if self.last_run is None:
                return True
            elapsed = (now - self.last_run).total_seconds()
            return elapsed >= self.interval_seconds
            
        return False


class Scheduler:
    """
    Manages scheduled tasks for agents.
    
    The scheduler runs in a background greenlet/thread and executes callbacks
    based on configured schedules (e.g. sending messages to agents).
    """
    
    def __init__(self, tick_interval: float = 1.0):
        """
        Initialize the scheduler.
        
        Args:
            tick_interval: How often to check for due tasks (seconds)
        """
        self.tasks: Dict[str, ScheduledTask] = {}
        self.tick_interval = tick_interval
        self.running = False
        self._greenlet = None
        self._thread = None
        
    def start(self):
        """Start the scheduler background loop."""
        if not self.running:
            self.running = True
            if USING_EVENTLET:
                self._greenlet = eventlet.spawn(self._run_loop)
                logger.info("Scheduler started (eventlet greenlet)")
            else:
                import threading
                self._thread = threading.Thread(target=self._run_loop, daemon=True)
                self._thread.start()
                logger.info("Scheduler started (thread)")
    
    def stop(self):
        """Stop the scheduler."""
        self.running = False
        if USING_EVENTLET and self._greenlet:
            self._greenlet.kill()
        elif self._thread:
            self._thread.join(timeout=5)
        logger.info("Scheduler stopped")
    
    def _run_loop(self):
        """Main scheduler loop."""
        while self.running:
            now = datetime.now()
            
            # Copy tasks to avoid modification during iteration
            tasks_to_check = list(self.tasks.values())
            
            for task in tasks_to_check:
                if task.should_run(now):
                    try:
                        logger.debug(f"Running task: {task.id}")
                        task.callback()
                        task.run_count += 1
                        task.last_run = now
                        
                        # Disable one-time tasks after execution
                        if task.trigger_type == TriggerType.ONCE:
                            task.enabled = False
                            
                    except Exception as e:
                        logger.error(f"Scheduler task {task.id} failed: {e}")
            
            # Sleep using eventlet or time
            if USING_EVENTLET:
                eventlet.sleep(self.tick_interval)
            else:
                time.sleep(self.tick_interval)
    
    def schedule_once(
        self, 
        task_id: str, 
        agent_id: str, 
        callback: Callable[[], Any],
        run_at: datetime
    ) -> ScheduledTask:
        """
        Schedule a one-time task.
        
        Args:
            task_id: Unique identifier for this task
            agent_id: Id of the agent this task belongs to
            callback: Function to call when triggered
            run_at: When to run the task
            
        Returns:
            The created task
        """
        task = ScheduledTask(
            id=task_id,
            agent_id=agent_id,
            trigger_type=TriggerType.ONCE,
            callback=callback,
            run_at=run_at
        )
        
        self.tasks[task_id] = task
        logger.info(f"Scheduled one-time task '{task_id}' for {run_at}")
        return task
    
    def schedule_interval(
        self,
        task_id: str,
        agent_id: str,
        callback: Callable[[], Any],
        interval_seconds: float,
        start_immediately: bool = False
    ) -> ScheduledTask:
        """
        Schedule a recurring task.
        
        Args:
            task_id: Unique identifier for this task
            agent_id: Id of the agent this task belongs to
            callback: Function to call when triggered
            interval_seconds: Seconds between executions
            start_immediately: If True, run immediately on first tick
            
        Returns:
            The created task
        """
        task = ScheduledTask(
            id=task_id,
            agent_id=agent_id,
            trigger_type=TriggerType.INTERVAL,
            callback=callback,
            interval_seconds=interval_seconds,
            last_run=None if start_immediately else datetime.now()
        )
        
        self.tasks[task_id] = task
        logger.info(f"Scheduled interval task '{task_id}' every {interval_seconds}s")
        return task
    
    def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a scheduled task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was found and cancelled
        """
        if task_id in self.tasks:
            del self.tasks[task_id]
            logger.info(f"Cancelled task '{task_id}'")
            return True
        return False
    
    def pause_task(self, task_id: str) -> bool:
        """Pause a task (can be resumed later)."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = False
            return True
        return False
    
    def resume_task(self, task_id: str) -> bool:
        """Resume a paused task."""
        if task_id in self.tasks:
            self.tasks[task_id].enabled = True
            return True
        return False
    
    def get_tasks_for_agent(self, agent_id: str) -> List[ScheduledTask]:
        """Get all tasks for a specific agent."""
        return [t for t in self.tasks.values() if t.agent_id == agent_id]
    
    def clear_agent_tasks(self, agent_id: str):
        """Remove all tasks for a specific agent."""
        to_remove = [tid for tid, t in self.tasks.items() if t.agent_id == agent_id]
        for tid in to_remove:
            del self.tasks[tid]
        logger.info(f"Cleared {len(to_remove)} tasks for agent '{agent_id}'")
