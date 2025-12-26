#!/usr/bin/env python3

"""
Background process management for Grok Assistant

Handles background shell commands and process tracking.
"""

import subprocess
import threading
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path


@dataclass
class BackgroundJob:
    """Represents a background job."""

    job_id: int
    command: str
    shell_type: str  # 'bash' or 'powershell'
    process: subprocess.Popen
    started_at: datetime
    output_buffer: List[str] = field(default_factory=list)
    error_buffer: List[str] = field(default_factory=list)
    status: str = "running"  # running, completed, failed, killed
    exit_code: Optional[int] = None
    cwd: Optional[Path] = None

    def is_running(self) -> bool:
        """Check if the job is still running."""
        if self.process.poll() is None:
            return True
        else:
            # Process finished, update status
            self.exit_code = self.process.returncode
            if self.status == "running":
                self.status = "completed" if self.exit_code == 0 else "failed"
            return False

    def get_runtime(self) -> float:
        """Get runtime in seconds."""
        return (datetime.now() - self.started_at).total_seconds()

    def kill(self) -> bool:
        """Kill the running process."""
        try:
            self.process.kill()
            self.status = "killed"
            return True
        except:
            return False


class BackgroundProcessManager:
    """
    Manages background shell processes.

    Allows running shell commands in the background while
    continuing to interact with the AI assistant.
    """

    def __init__(self):
        """Initialize the background process manager."""
        self.jobs: Dict[int, BackgroundJob] = {}
        self.next_job_id = 1
        self._lock = threading.Lock()

    def start_job(
        self,
        command: str,
        shell_type: str = "bash",
        cwd: Optional[Path] = None
    ) -> int:
        """
        Start a background job.

        Args:
            command: Shell command to execute
            shell_type: 'bash' or 'powershell'
            cwd: Working directory

        Returns:
            Job ID for tracking
        """
        with self._lock:
            job_id = self.next_job_id
            self.next_job_id += 1

        # Start the process
        if shell_type == "bash":
            process = subprocess.Popen(
                ['bash', '-c', command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(cwd) if cwd else None,
                bufsize=1
            )
        else:  # powershell
            powershell_exe = 'pwsh' if subprocess.run(['which', 'pwsh'], capture_output=True).returncode == 0 else 'powershell'
            process = subprocess.Popen(
                [powershell_exe, '-Command', command],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(cwd) if cwd else None,
                bufsize=1
            )

        # Create job
        job = BackgroundJob(
            job_id=job_id,
            command=command,
            shell_type=shell_type,
            process=process,
            started_at=datetime.now(),
            cwd=cwd
        )

        # Start output capture threads
        threading.Thread(
            target=self._capture_output,
            args=(job, process.stdout, job.output_buffer),
            daemon=True
        ).start()

        threading.Thread(
            target=self._capture_output,
            args=(job, process.stderr, job.error_buffer),
            daemon=True
        ).start()

        with self._lock:
            self.jobs[job_id] = job

        return job_id

    def _capture_output(self, job: BackgroundJob, stream, buffer: List[str]):
        """Capture output from a stream to a buffer."""
        try:
            for line in stream:
                with self._lock:
                    buffer.append(line.rstrip())
        except:
            pass

    def get_job(self, job_id: int) -> Optional[BackgroundJob]:
        """Get a job by ID."""
        with self._lock:
            return self.jobs.get(job_id)

    def list_jobs(self) -> List[BackgroundJob]:
        """List all jobs."""
        with self._lock:
            return list(self.jobs.values())

    def kill_job(self, job_id: int) -> bool:
        """Kill a running job."""
        job = self.get_job(job_id)
        if job:
            return job.kill()
        return False

    def get_job_output(self, job_id: int, include_errors: bool = True) -> Dict[str, Any]:
        """
        Get job output.

        Args:
            job_id: Job ID
            include_errors: Include stderr in output

        Returns:
            Dictionary with job status and output
        """
        job = self.get_job(job_id)
        if not job:
            return {"error": f"Job {job_id} not found"}

        # Check if job is still running
        is_running = job.is_running()

        with self._lock:
            output = {
                "job_id": job.job_id,
                "command": job.command,
                "status": job.status,
                "is_running": is_running,
                "exit_code": job.exit_code,
                "runtime_seconds": job.get_runtime(),
                "stdout": "\n".join(job.output_buffer),
                "stdout_lines": len(job.output_buffer)
            }

            if include_errors:
                output["stderr"] = "\n".join(job.error_buffer)
                output["stderr_lines"] = len(job.error_buffer)

        return output

    def cleanup_finished_jobs(self, max_age_seconds: int = 3600):
        """
        Clean up finished jobs older than max_age_seconds.

        Args:
            max_age_seconds: Maximum age to keep finished jobs
        """
        with self._lock:
            to_remove = []
            for job_id, job in self.jobs.items():
                if not job.is_running():
                    age = (datetime.now() - job.started_at).total_seconds()
                    if age > max_age_seconds:
                        to_remove.append(job_id)

            for job_id in to_remove:
                del self.jobs[job_id]

    def kill_all_jobs(self):
        """Kill all running jobs."""
        with self._lock:
            for job in self.jobs.values():
                if job.is_running():
                    job.kill()
