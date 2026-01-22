# Agentic Reasoning Features

Comprehensive guide to the advanced agentic reasoning capabilities in Grok-CLI.

## Table of Contents

1. [Overview](#overview)
2. [Foundational Features](#foundational-features)
3. [Self-Evolving Features](#self-evolving-features)
4. [Collective Features](#collective-features)
5. [Orchestration](#orchestration)
6. [Commands](#commands)
7. [Tools](#tools)
8. [Usage Examples](#usage-examples)
9. [Architecture](#architecture)

---

## Overview

Grok-CLI now includes advanced agentic reasoning capabilities inspired by recent research in autonomous AI systems. These features enable:

- **Structured Planning**: ReAct-style planning for complex multi-step tasks
- **Reflection & Critique**: Automatic self-correction and learning from failures
- **Episodic Memory**: Trajectory-based memory that captures full task episodes
- **Multi-Agent Coordination**: Specialized agents working together on complex problems

### Key Benefits

- **Better Task Decomposition**: Complex tasks are broken down into manageable steps
- **Improved Error Handling**: Automatic reflection on failures leads to better solutions
- **Learning from Experience**: Episodic memory enables the agent to learn from past successes and failures
- **Parallel Processing**: Multiple specialized agents can work on different aspects of a problem

---

## Foundational Features

### 1. Structured Planning (ReAct-Style)

The planning system breaks down complex tasks into step-by-step action sequences.

#### How It Works

1. **Goal Analysis**: The system analyzes the high-level goal
2. **Plan Generation**: Creates a structured plan with specific steps
3. **Execution**: Each step is executed with tools
4. **Observation**: Results are observed and analyzed
5. **Adaptation**: Plan is adjusted based on observations

#### Using Planning

**Via Command:**
```bash
/plan Refactor the authentication system to use OAuth2
```

**Via Tool:**
The AI can invoke the `generate_plan` tool directly during conversations:
```python
# The AI will automatically use this when faced with complex tasks
{
  "tool": "generate_plan",
  "parameters": {
    "goal": "Migrate database from PostgreSQL to MongoDB",
    "context": "Current schema has 10 tables with complex relationships",
    "max_steps": 8
  }
}
```

#### Plan Structure

Plans follow this JSON structure:
```json
{
  "goal": "High-level goal description",
  "steps": [
    {
      "step_number": 1,
      "action": "Tool or action to perform",
      "description": "Detailed description of what to do",
      "expected_outcome": "What should result from this step",
      "dependencies": []
    }
  ]
}
```

---

### 2. Reflection & Critique Loops

The system automatically reflects on tool execution outcomes, especially failures.

#### How It Works

1. **Action Execution**: A tool is executed
2. **Outcome Detection**: Success or failure is detected
3. **Reflection Trigger**: On failure, reflection is triggered
4. **Critique Generation**: The system analyzes what went wrong
5. **Improved Approach**: Generates a revised approach
6. **Memory Storage**: Reflection is stored for future reference

#### Automatic Reflection

Reflection happens automatically when:
- A tool execution fails
- An error occurs during execution
- The outcome doesn't match expectations

#### Manual Reflection

Use the `reflect` tool to manually trigger reflection:
```python
{
  "tool": "reflect",
  "parameters": {
    "action": "write_file",
    "outcome": "Permission denied error",
    "expected": "File written successfully",
    "error": "PermissionError: [Errno 13] Permission denied"
  }
}
```

#### Reflection Output

```
Analysis: The action 'write_file' failed with error: Permission denied

Suggested approach:
1. Review the error message carefully
2. Check file permissions (chmod)
3. Verify the user has write access to the directory
4. Consider using sudo or changing the target directory
5. Try again with corrected permissions
```

---

## Self-Evolving Features

### 1. Episodic Memory System

Episodic memory captures full task trajectories including planning, execution, and outcomes.

#### Episode Structure

Each episode contains:
- **Goal**: The high-level objective
- **Plan**: The generated plan (if any)
- **Actions**: All actions taken with results
- **Reflections**: Critiques and learnings
- **Outcome**: Final result and success status

#### Viewing Episodes

```bash
# View recent episodes
/episodes

# View specific number of episodes
/episodes 20
```

#### Episode Data

Episodes are stored in:
- **Global**: `~/.grok_global_episodes.json`
- **Project**: `.grok_episodes.json` (per directory)

Example episode:
```json
{
  "episode_id": "ep_a1b2c3d4",
  "goal": "Add user authentication",
  "created": "2024-01-15T10:30:00",
  "completed": "2024-01-15T11:45:00",
  "plan": {
    "goal": "Add user authentication",
    "steps": [...]
  },
  "actions": [
    {
      "timestamp": "2024-01-15T10:35:00",
      "type": "tool_call",
      "description": "read_file: auth.py",
      "result": "File read successfully",
      "success": true
    }
  ],
  "reflections": [
    {
      "timestamp": "2024-01-15T11:00:00",
      "content": "Password hashing should use bcrypt instead of md5"
    }
  ],
  "outcome": "Authentication system implemented successfully",
  "success": true
}
```

---

### 2. Self-Improvement Loops

The system analyzes past episodes to identify improvement opportunities.

#### Using Self-Improvement

```bash
/improve
```

This command:
1. **Analyzes** recent episodes
2. **Identifies** common failure patterns
3. **Suggests** improvements and optimizations
4. **Generates** actionable recommendations

#### Example Output

```
🔍 Analyzing recent episodes for improvement opportunities...

Episode Statistics:
  Total episodes: 45
  Completed: 42
  Successful: 38
  Success rate: 90.5%

Found 4 failed episodes to analyze

Most common failure types:
  • file_operations: 3 failures
  • shell_execution: 2 failures
  • api_calls: 1 failure

Actionable improvements:
1. Consider creating specialized tools for frequently failing operations
2. Review error handling in tools that fail often
3. Add validation checks before executing risky operations
4. Create helper functions for common task patterns
```

---

### 3. Memory Summarization

Episodic memory automatically summarizes old episodes to manage storage.

#### How It Works

- **Size Monitoring**: Checks episode file size
- **Threshold Detection**: Triggers at configurable size (default: 10KB)
- **Summarization**: Condenses old episodes to key insights
- **Preservation**: Keeps recent and important episodes intact

#### Manual Summarization

```python
# Programmatically trigger summarization
manager = session.episodic_memory
stats = manager.summarize_episodes(max_size_kb=10)
```

---

## Collective Features

### 1. Role-Based Multi-Agent System

Multiple specialized agents can work together on complex tasks.

#### Available Agent Roles

| Role | Purpose | Use Cases |
|------|---------|-----------|
| **Planner** | Creates detailed plans | Complex task decomposition |
| **Coder** | Implements code changes | Writing and modifying code |
| **Reviewer** | Reviews code quality | Code review, security audits |
| **Researcher** | Searches and explores | Documentation lookup, codebase exploration |
| **Tester** | Writes and runs tests | Test creation, verification |

#### Spawning Agents

```bash
# Spawn a reviewer agent
/spawn reviewer Review the authentication module for security vulnerabilities

# Spawn a tester agent
/spawn tester Create comprehensive tests for the user registration flow

# Spawn a researcher agent
/spawn researcher Find all API endpoints that handle user data
```

---

### 2. Shared Blackboard Communication

Agents communicate through a shared blackboard using the blackboard pattern.

#### How It Works

1. **Message Posting**: Agents post messages to the blackboard
2. **Message Reading**: Other agents read relevant messages
3. **Shared Data**: Agents can share data structures
4. **Coordination**: Agents coordinate through message types

#### Blackboard Tools

**Write to Blackboard:**
```python
{
  "tool": "write_to_blackboard",
  "parameters": {
    "message": "Authentication module reviewed - found 2 SQL injection risks",
    "message_type": "result"
  }
}
```

**Read from Blackboard:**
```python
{
  "tool": "read_blackboard",
  "parameters": {
    "message_type": "result",  // optional filter
    "new_only": true           // only new messages
  }
}
```

#### Message Types

- **info**: General information
- **request**: Request for action from other agents
- **result**: Results of completed work
- **error**: Error reports

#### Blackboard File

The blackboard is stored at: `.grok_blackboard.json`

```json
{
  "created": 1705320000,
  "messages": [
    {
      "timestamp": 1705320100,
      "agent_id": "reviewer_1705320050",
      "type": "result",
      "content": "Code review complete - 2 issues found"
    }
  ],
  "shared_data": {
    "current_task": "Security audit",
    "progress": 75
  }
}
```

---

## Orchestration

### Multi-Agent Orchestrator

The orchestrator is a powerful feature that automatically coordinates multiple specialized agents to work together on very complex tasks.

#### How It Works

1. **Task Decomposition**: The orchestrator analyzes a complex goal and breaks it into sub-tasks
2. **Role Assignment**: Each sub-task is assigned to the most appropriate agent role
3. **Dependency Management**: Tasks are ordered based on dependencies
4. **Parallel Execution**: Multiple agents work simultaneously on independent tasks
5. **Progress Monitoring**: The orchestrator monitors all agents via the blackboard
6. **Result Aggregation**: When all tasks complete, results are synthesized

#### Orchestration Flow

```
Complex Goal
    ↓
Decomposition → [Task 1] [Task 2] [Task 3] [Task 4] [Task 5]
    ↓               ↓        ↓        ↓        ↓        ↓
Role Assignment → Planner Researcher Coder  Reviewer Tester
    ↓
Dependency Graph:
    Planner (Task 1) ────────┐
                              ↓
    Researcher (Task 2) ──→ Coder (Task 3) ──┬→ Reviewer (Task 4)
                                              └→ Tester (Task 5)
    ↓
Parallel Execution:
    [Planner & Researcher run in parallel]
    [Wait for both to complete]
    [Coder runs using their results]
    [Reviewer & Tester run in parallel on coder's output]
    ↓
Result Aggregation → Comprehensive Summary
```

#### Using the Orchestrator

**Via Command:**
```bash
/orchestrate Implement a complete e-commerce checkout flow with payment processing, inventory management, and order tracking
```

**Via Tool:**
```python
{
  "tool": "orchestrate",
  "parameters": {
    "goal": "Build a microservices architecture with API gateway, auth service, and data service",
    "max_agents": 5,
    "timeout_seconds": 600
  }
}
```

#### Orchestrator Parameters

| Parameter | Type | Description | Default |
|-----------|------|-------------|---------|
| `goal` | string | The complex goal to orchestrate | Required |
| `max_agents` | integer | Maximum concurrent agents | 3 |
| `timeout_seconds` | integer | Maximum orchestration time | 300 |

#### Example Orchestration

**Input:**
```bash
/orchestrate Implement user authentication with OAuth2, 2FA, session management, and audit logging
```

**Decomposition:**
```json
{
  "goal": "Implement user authentication...",
  "sub_tasks": [
    {
      "id": 0,
      "description": "Create detailed implementation plan for authentication system",
      "role": "planner",
      "dependencies": []
    },
    {
      "id": 1,
      "description": "Research OAuth2 best practices and 2FA implementations",
      "role": "researcher",
      "dependencies": []
    },
    {
      "id": 2,
      "description": "Implement OAuth2 authentication flow",
      "role": "coder",
      "dependencies": [0, 1]
    },
    {
      "id": 3,
      "description": "Implement 2FA with TOTP",
      "role": "coder",
      "dependencies": [0, 1]
    },
    {
      "id": 4,
      "description": "Review authentication code for security vulnerabilities",
      "role": "reviewer",
      "dependencies": [2, 3]
    },
    {
      "id": 5,
      "description": "Create comprehensive authentication tests",
      "role": "tester",
      "dependencies": [2, 3]
    }
  ]
}
```

**Execution Timeline:**
```
t=0s:   Planner & Researcher start (parallel)
t=30s:  Both complete
t=30s:  Coder agents start for OAuth2 and 2FA (parallel)
t=120s: Both coders complete
t=120s: Reviewer & Tester start (parallel)
t=180s: Both complete
t=180s: Orchestration complete - results aggregated
```

**Output:**
```
Orchestration completed for: Implement user authentication...

Orchestration Summary:
Goal: Implement user authentication with OAuth2, 2FA, session management...
Total Tasks: 6
Completed: 6
Success Rate: 100.0%

Task Results:
  ✓ [planner] Create detailed implementation plan
     Result: Created 8-step implementation plan with security considerations...

  ✓ [researcher] Research OAuth2 best practices
     Result: Identified 5 critical security patterns and 3 libraries...

  ✓ [coder] Implement OAuth2 authentication flow
     Result: Implemented OAuth2 with PKCE flow, token refresh, and revocation...

  ✓ [coder] Implement 2FA with TOTP
     Result: Implemented TOTP 2FA with QR code generation and backup codes...

  ✓ [reviewer] Review authentication code
     Result: Found and fixed 2 timing attack vulnerabilities...

  ✓ [tester] Create comprehensive tests
     Result: Created 45 test cases covering all auth flows...

See blackboard messages for detailed agent communications.
```

#### When to Use Orchestration

Use orchestration for:

- **Very Complex Tasks**: Tasks that would take 20+ steps manually
- **Multi-Aspect Projects**: Projects requiring diverse expertise (planning, coding, security, testing)
- **Parallel Work**: Tasks with independent sub-tasks that can run simultaneously
- **Critical Projects**: Important work that benefits from multiple reviewers

**Don't use orchestration for:**
- Simple single-file changes
- Tasks that must be done sequentially
- Quick fixes or small updates
- Tasks that are already well-understood

#### Monitoring Orchestration

**Check Blackboard:**
```bash
# The orchestrator posts regular updates
read_blackboard

# Output:
# [10:30:15] orchestrator (info): Starting orchestration orch_1705320015
# [10:30:16] orchestrator (info): Assigned task 0 to agent planner_orch_1705320015_0
# [10:30:16] orchestrator (info): Assigned task 1 to agent researcher_orch_1705320015_1
# [10:32:45] planner_orch_1705320015_0 (result): Task 0 completed: Created plan
# [10:33:12] researcher_orch_1705320015_1 (result): Task 1 completed: Research done
```

**Check Progress:**
```python
# Progress is stored in blackboard shared data
blackboard.get_shared_data("orchestration_orch_1705320015_progress")

# Returns:
# {
#   "total": 6,
#   "completed": 2,
#   "running": 2,
#   "pending": 2,
#   "progress_pct": 33.3
# }
```

---

## Commands

### Planning Commands

#### `/plan <goal>`

Create a structured plan for a complex task.

**Example:**
```bash
/plan Migrate the application from REST to GraphQL
```

**Output:**
- Detailed step-by-step plan
- Expected outcomes for each step
- Dependencies between steps

---

### Self-Improvement Commands

#### `/improve`

Analyze past episodes and suggest improvements.

**Example:**
```bash
/improve
```

**Output:**
- Episode statistics
- Common failure patterns
- Actionable recommendations

---

### Multi-Agent Commands

#### `/spawn <role> <task>`

Spawn a specialized agent with a specific role.

**Example:**
```bash
/spawn reviewer Audit the payment processing code for PCI compliance
```

**Roles:**
- `planner`: Create plans
- `coder`: Write code
- `reviewer`: Review code
- `researcher`: Research and explore
- `tester`: Write and run tests

---

#### `/orchestrate <complex goal>`

Orchestrate multiple agents to work together on a very complex task.

**Example:**
```bash
/orchestrate Build a complete CI/CD pipeline with automated testing, security scanning, and deployment to Kubernetes
```

**What it does:**
1. Decomposes the complex goal into sub-tasks
2. Assigns appropriate agent roles to each sub-task
3. Manages dependencies between tasks
4. Spawns agents in the correct order
5. Monitors progress and aggregates results

**Best for:**
- Very complex multi-part projects
- Tasks requiring multiple types of expertise
- Projects that can benefit from parallel execution

---

### Memory Commands

#### `/episodes [limit]`

View recent episodes from episodic memory.

**Example:**
```bash
# View last 10 episodes
/episodes

# View last 25 episodes
/episodes 25
```

**Output:**
```
Recent Episodes (showing 3):

✓ Add user authentication
   ID: ep_a1b2c3d4
   Created: 2024-01-15T10:30:00
   Completed: 2024-01-15T11:45:00
   Outcome: Authentication system implemented successfully
   Actions: 12, Reflections: 3

✗ Fix database migration
   ID: ep_e5f6g7h8
   Created: 2024-01-15T14:00:00
   Completed: 2024-01-15T14:30:00
   Outcome: Migration failed due to schema conflicts
   Actions: 8, Reflections: 2

Total episodes: 45 | Success rate: 90.5%
```

---

## Tools

### Planning Tools

#### `generate_plan`

Generate a structured plan for a goal.

**Parameters:**
```json
{
  "goal": "string (required)",
  "context": "string (optional)",
  "max_steps": "integer (optional, default: 10)"
}
```

**Example:**
```json
{
  "tool": "generate_plan",
  "parameters": {
    "goal": "Implement real-time notifications",
    "context": "Using WebSockets, need to support 10k concurrent users",
    "max_steps": 6
  }
}
```

---

#### `reflect`

Reflect on an action's outcome and generate critique.

**Parameters:**
```json
{
  "action": "string (required)",
  "outcome": "string (required)",
  "expected": "string (optional)",
  "error": "string (optional)"
}
```

**Example:**
```json
{
  "tool": "reflect",
  "parameters": {
    "action": "deploy_application",
    "outcome": "Deployment failed - health check timeout",
    "expected": "Application deployed and healthy",
    "error": "HTTPError: Health check endpoint not responding"
  }
}
```

---

### Multi-Agent Tools

#### `orchestrate`

Orchestrate multiple specialized agents to work together on a complex task.

**Parameters:**
```json
{
  "goal": "string (required)",
  "max_agents": "integer (optional, default: 3)",
  "timeout_seconds": "integer (optional, default: 300)"
}
```

**Example:**
```json
{
  "tool": "orchestrate",
  "parameters": {
    "goal": "Implement a real-time analytics dashboard with WebSocket updates, Redis caching, and PostgreSQL persistence",
    "max_agents": 5,
    "timeout_seconds": 600
  }
}
```

**Returns:**
- Task decomposition
- Role assignments
- Execution timeline
- Aggregated results from all agents
- Progress statistics

---

#### `spawn_agent`

Spawn a specialized agent instance.

**Parameters:**
```json
{
  "role": "planner|coder|reviewer|researcher|tester (required)",
  "task": "string (required)",
  "context": "string (optional)",
  "background": "boolean (optional, default: true)"
}
```

**Example:**
```json
{
  "tool": "spawn_agent",
  "parameters": {
    "role": "tester",
    "task": "Create integration tests for the payment API",
    "context": "Using pytest, need to mock Stripe API",
    "background": true
  }
}
```

---

#### `write_to_blackboard`

Write a message to the shared blackboard.

**Parameters:**
```json
{
  "message": "string (required)",
  "message_type": "info|request|result|error (optional, default: info)"
}
```

---

#### `read_blackboard`

Read messages from the shared blackboard.

**Parameters:**
```json
{
  "message_type": "info|request|result|error (optional)",
  "new_only": "boolean (optional, default: true)"
}
```

---

## Usage Examples

### Example 1: Complex Refactoring Task

```bash
# Step 1: Create a plan
/plan Refactor the user service to use dependency injection

# The AI generates a detailed plan with steps:
# 1. Analyze current user service dependencies
# 2. Create dependency interfaces
# 3. Implement dependency injection container
# 4. Refactor user service to use constructor injection
# 5. Update tests to use dependency injection
# 6. Verify all tests pass

# Step 2: Execute the plan
# The AI will use tools to implement each step

# Step 3: Review progress
/episodes

# If something fails, the system automatically reflects
# and generates an improved approach
```

---

### Example 2: Multi-Agent Workflow

```bash
# Spawn a planner to create a detailed plan
/spawn planner Create a plan for implementing user notifications

# Spawn a researcher to investigate best practices
/spawn researcher Research notification systems that scale to millions of users

# Spawn a coder to implement the plan
/spawn coder Implement the notification system based on the plan

# Spawn a reviewer to audit the code
/spawn reviewer Review the notification code for performance and security

# Monitor progress via blackboard
# The AI will use read_blackboard to check agent progress
```

---

### Example 3: Self-Improvement Workflow

```bash
# After working on multiple tasks, analyze performance
/improve

# Review episodes that failed
/episodes 50

# The system identifies patterns:
# - File permission errors are common
# - Database connection timeouts happen frequently
# - Complex regex patterns often fail

# Based on this, you can:
# 1. Create helper tools for common operations
# 2. Add retry logic for database operations
# 3. Improve validation before execution
```

---

### Example 4: Orchestration for Very Complex Projects

```bash
# Use orchestration for projects requiring multiple specialized agents
/orchestrate Implement a complete user management system with RBAC, SSO, audit logging, and admin dashboard

# The orchestrator automatically:
# 1. Decomposes into sub-tasks:
#    - Plan the system architecture (planner)
#    - Research RBAC patterns and SSO protocols (researcher)
#    - Implement authentication and authorization (coder)
#    - Implement audit logging (coder)
#    - Build admin dashboard (coder)
#    - Review security and code quality (reviewer)
#    - Create comprehensive test suite (tester)

# 2. Determines dependencies:
#    - Planner & Researcher run first (parallel)
#    - Coders wait for plan and research
#    - Multiple coders can work simultaneously on independent features
#    - Reviewer & Tester run after all coding completes (parallel)

# 3. Executes with coordination:
#    - Spawns agents in dependency order
#    - Monitors progress via blackboard
#    - Handles failures and retries
#    - Aggregates all results

# 4. Returns comprehensive summary:
#    - All sub-task results
#    - Success metrics
#    - Integration status
#    - Blackboard communication log

# Monitor progress
read_blackboard

# View the episode
/episodes 1
```

**Benefits of Orchestration:**
- **Parallel Execution**: Independent tasks run simultaneously
- **Specialized Expertise**: Each agent focuses on their strengths
- **Automatic Coordination**: No manual agent management needed
- **Comprehensive Coverage**: Planning, implementation, review, and testing all included
- **Failure Handling**: Individual agent failures don't derail the entire orchestration

---

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                      Grok-CLI Main Loop                         │
│  ┌───────────────────────────────────────────────────────┐     │
│  │           Planning & Reflection Layer                 │     │
│  │  • generate_plan tool                                │     │
│  │  • reflect tool                                      │     │
│  │  • Automatic reflection on failures                  │     │
│  └───────────────────────────────────────────────────────┘     │
│                           ↓                                     │
│  ┌───────────────────────────────────────────────────────┐     │
│  │           Episodic Memory Layer                       │     │
│  │  • Episode tracking                                   │     │
│  │  • Plan storage                                       │     │
│  │  • Action logging                                     │     │
│  │  • Reflection storage                                 │     │
│  │  • Automatic summarization                            │     │
│  └───────────────────────────────────────────────────────┘     │
│                           ↓                                     │
│  ┌───────────────────────────────────────────────────────┐     │
│  │         Orchestration Layer (NEW!)                    │     │
│  │  • Task decomposition                                 │     │
│  │  • Role assignment                                    │     │
│  │  • Dependency management                              │     │
│  │  • Multi-agent coordination                           │     │
│  │  • Progress monitoring                                │     │
│  │  • Result aggregation                                 │     │
│  └───────────────────────────────────────────────────────┘     │
│                           ↓                                     │
│  ┌───────────────────────────────────────────────────────┐     │
│  │         Multi-Agent Coordination Layer                │     │
│  │  • Agent spawning (individual)                        │     │
│  │  • Blackboard communication                           │     │
│  │  • Role-based specialization                          │     │
│  │  • Shared data management                             │     │
│  └───────────────────────────────────────────────────────┘     │
│                           ↓                                     │
│  ┌───────────────────────────────────────────────────────┐     │
│  │         Tool Execution Layer                          │     │
│  │  • File operations                                    │     │
│  │  • Shell commands                                     │     │
│  │  • Code analysis                                      │     │
│  │  • Memory operations                                  │     │
│  └───────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────┘

                    Specialized Agents (Spawned)
        ┌──────────┬──────────┬──────────┬──────────┬──────────┐
        │ Planner  │Researcher│  Coder   │ Reviewer │  Tester  │
        └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
             └──────────┴──────────┴──────────┴──────────┘
                            Blackboard
                    (Shared Communication)
```

---

### Data Flow

1. **User Input** → Planning system (if complex task)
2. **Plan Generation** → Episode creation
3. **Tool Execution** → Action logging
4. **Failure Detection** → Automatic reflection
5. **Reflection** → Episode update
6. **Episode Completion** → Memory storage
7. **Self-Improvement** → Episode analysis

---

### File Structure

```
~/.grok_global_episodes.json     # Global episodes
~/.grok_global_memory.json       # Global memories (flat)

<project>/.grok_episodes.json    # Project episodes
<project>/.grok_memory.json      # Project memories (flat)
<project>/.grok_blackboard.json  # Multi-agent blackboard
```

---

## Best Practices

### When to Use Planning

Use `/plan` or the `generate_plan` tool for:
- Multi-file refactoring
- Complex feature implementation
- System-wide changes
- Tasks with many dependencies

### When to Use Reflection

Reflection happens automatically on failures, but manually trigger it when:
- You want to analyze a specific approach
- Need to document learnings
- Want to improve future similar tasks

### When to Use Multi-Agent

Use `/spawn` for:
- Large tasks that can be parallelized
- Tasks requiring different expertise (planning + coding + review)
- When you want specialized focus on subtasks

### Memory Management

- Review episodes periodically with `/episodes`
- Use `/improve` after major projects to learn from experience
- Episodic memory automatically summarizes old entries
- Failed episodes are valuable learning opportunities

---

## Configuration

### Enable Agentic Features

Agentic features are enabled by default. Configuration options:

```python
# In config
config.agent_mode = True          # Enable autonomous mode
config.max_reasoning_steps = 100  # Max steps for planning
config.self_mode = True           # Enable self-improvement tools
```

### Command-Line Flags

```bash
# Enable agent mode (skip confirmations)
grok-cli --agent

# Enable self mode (can create tools)
grok-cli --self

# Set max reasoning steps
grok-cli --max-steps 50
```

---

## Troubleshooting

### Plans Not Being Generated

**Issue**: The AI doesn't generate plans automatically.

**Solution**: Explicitly request planning:
```bash
/plan <your goal>
```
Or mention "create a plan" in your message.

---

### Agents Not Spawning

**Issue**: `/spawn` command doesn't work.

**Solution**:
1. Check that you're using a valid role
2. Verify the task is clearly specified
3. Ensure you have proper permissions to spawn subprocesses

---

### Blackboard Messages Not Appearing

**Issue**: Can't see agent messages.

**Solution**:
```bash
# Read all messages
read_blackboard with new_only=false

# Check the blackboard file directly
cat .grok_blackboard.json
```

---

### Episode Memory Growing Too Large

**Issue**: `.grok_episodes.json` is very large.

**Solution**:
1. Automatic summarization will trigger at 10KB
2. Manually trigger: Use the episodic memory manager API
3. Archive old episodes to a backup file

---

## Future Enhancements

Planned improvements to agentic reasoning:

1. **Enhanced Planning**
   - Hierarchical planning for very complex tasks
   - Plan templates for common task types
   - Plan versioning and rollback

2. **Advanced Reflection**
   - Comparative reflection (comparing multiple approaches)
   - Reflection-based tool creation
   - Automated improvement implementation

3. **Smarter Multi-Agent**
   - Dynamic role assignment
   - Agent voting on decisions
   - Automatic agent coordination

4. **Memory Enhancements**
   - Semantic search over episodes
   - Cross-project episode sharing
   - Episode visualization

5. **Self-Improvement**
   - Automatic tool generation from patterns
   - A/B testing of approaches
   - Success pattern extraction

---

## References

This implementation is inspired by:

- **ReAct**: Reasoning and Acting in Language Models
- **Reflexion**: Language Agents with Verbal Reinforcement Learning
- **AutoGPT**: Autonomous agent architecture
- **Multi-Agent Systems**: Blackboard pattern for coordination

---

## Support

For issues or questions about agentic features:

1. Check this documentation
2. Review `/help` for command syntax
3. Use `/episodes` to debug episode tracking
4. Use `/improve` to get suggestions

---

**Version**: 1.0.0
**Last Updated**: 2024-01-22
