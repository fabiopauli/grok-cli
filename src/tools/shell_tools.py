#!/usr/bin/env python3

"""
Shell execution tools for Grok Assistant

Handles bash and PowerShell command execution with security controls.
"""

from typing import Any

from ..utils.shell_utils import run_bash_command, run_powershell_command
from .base import BaseTool, ToolResult


class BashTool(BaseTool):
    """Handle run_bash function calls."""

    def get_name(self) -> str:
        return "run_bash"

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Execute bash command with security confirmation."""
        try:
            command = args["command"]
            result = run_bash_command(command, self.config)
            return ToolResult.ok(result)
        except Exception as e:
            return ToolResult.fail(f"Error executing bash command: {str(e)}")


class PowerShellTool(BaseTool):
    """Handle run_powershell function calls."""

    def get_name(self) -> str:
        return "run_powershell"

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Execute PowerShell command with security confirmation."""
        try:
            command = args["command"]
            result = run_powershell_command(command, self.config)
            return ToolResult.ok(result)
        except Exception as e:
            return ToolResult.fail(f"Error executing PowerShell command: {str(e)}")


class BackgroundBashTool(BaseTool):
    """Handle run_bash_background function calls."""

    def get_name(self) -> str:
        return "run_bash_background"

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Execute bash command in background."""
        try:
            command = args["command"]
            from ..core.background_manager import BackgroundProcessManager

            # Get or create background manager
            if not hasattr(self.config, '_background_manager'):
                self.config._background_manager = BackgroundProcessManager()

            manager = self.config._background_manager
            job_id = manager.start_job(command, "bash", self.config.base_dir)

            return ToolResult.ok(
                f"Background job started with ID: {job_id}\n"
                f"Command: {command}\n"
                f"Use check_background_job({job_id}) to check status\n"
                f"Use kill_background_job({job_id}) to stop it"
            )
        except Exception as e:
            return ToolResult.fail(f"Error starting background job: {str(e)}")


class BackgroundPowerShellTool(BaseTool):
    """Handle run_powershell_background function calls."""

    def get_name(self) -> str:
        return "run_powershell_background"

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Execute PowerShell command in background."""
        try:
            command = args["command"]
            from ..core.background_manager import BackgroundProcessManager

            # Get or create background manager
            if not hasattr(self.config, '_background_manager'):
                self.config._background_manager = BackgroundProcessManager()

            manager = self.config._background_manager
            job_id = manager.start_job(command, "powershell", self.config.base_dir)

            return ToolResult.ok(
                f"Background job started with ID: {job_id}\n"
                f"Command: {command}\n"
                f"Use check_background_job({job_id}) to check status\n"
                f"Use kill_background_job({job_id}) to stop it"
            )
        except Exception as e:
            return ToolResult.fail(f"Error starting background job: {str(e)}")


class CheckBackgroundJobTool(BaseTool):
    """Handle check_background_job function calls."""

    def get_name(self) -> str:
        return "check_background_job"

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Check status of a background job."""
        try:
            job_id = int(args["job_id"])

            if not hasattr(self.config, '_background_manager'):
                return ToolResult.fail("No background jobs running")

            manager = self.config._background_manager
            output = manager.get_job_output(job_id)

            if "error" in output:
                return ToolResult.fail(output["error"])

            # Format output
            result_lines = [
                f"Job ID: {output['job_id']}",
                f"Command: {output['command']}",
                f"Status: {output['status']}",
                f"Running: {output['is_running']}",
                f"Runtime: {output['runtime_seconds']:.1f}s",
            ]

            if output.get('exit_code') is not None:
                result_lines.append(f"Exit Code: {output['exit_code']}")

            result_lines.append(f"\nStdout ({output['stdout_lines']} lines):")
            if output['stdout']:
                result_lines.append(output['stdout'])
            else:
                result_lines.append("(no output yet)")

            if output.get('stderr'):
                result_lines.append(f"\nStderr ({output['stderr_lines']} lines):")
                result_lines.append(output['stderr'])

            return ToolResult.ok("\n".join(result_lines))

        except Exception as e:
            return ToolResult.fail(f"Error checking background job: {str(e)}")


class KillBackgroundJobTool(BaseTool):
    """Handle kill_background_job function calls."""

    def get_name(self) -> str:
        return "kill_background_job"

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """Kill a background job."""
        try:
            job_id = int(args["job_id"])

            if not hasattr(self.config, '_background_manager'):
                return ToolResult.fail("No background jobs running")

            manager = self.config._background_manager
            if manager.kill_job(job_id):
                return ToolResult.ok(f"Job {job_id} killed successfully")
            else:
                return ToolResult.fail(f"Failed to kill job {job_id} (may not exist or already finished)")

        except Exception as e:
            return ToolResult.fail(f"Error killing background job: {str(e)}")


class ListBackgroundJobsTool(BaseTool):
    """Handle list_background_jobs function calls."""

    def get_name(self) -> str:
        return "list_background_jobs"

    def execute(self, args: dict[str, Any]) -> ToolResult:
        """List all background jobs."""
        try:
            if not hasattr(self.config, '_background_manager'):
                return ToolResult.ok("No background jobs running")

            manager = self.config._background_manager
            jobs = manager.list_jobs()

            if not jobs:
                return ToolResult.ok("No background jobs")

            result_lines = [f"Total background jobs: {len(jobs)}\n"]

            for job in jobs:
                is_running = job.is_running()
                result_lines.append(
                    f"[{job.job_id}] {job.status} | "
                    f"{job.shell_type} | "
                    f"{job.get_runtime():.1f}s | "
                    f"{'RUNNING' if is_running else 'FINISHED'} | "
                    f"{job.command[:50]}{'...' if len(job.command) > 50 else ''}"
                )

            return ToolResult.ok("\n".join(result_lines))

        except Exception as e:
            return ToolResult.fail(f"Error listing background jobs: {str(e)}")


def create_shell_tools(config) -> list[BaseTool]:
    """Create all shell tools."""
    return [
        BashTool(config),
        PowerShellTool(config),
        BackgroundBashTool(config),
        BackgroundPowerShellTool(config),
        CheckBackgroundJobTool(config),
        KillBackgroundJobTool(config),
        ListBackgroundJobsTool(config),
    ]
