# Agentic Reasoning Features

Comprehensive guide to the advanced agentic reasoning capabilities in Grok-CLI.

## Table of Contents

1. [Overview](#overview)
2. [Foundational Features](#foundational-features)
3. [Self-Evolving Features](#self-evolving-features)
4. [Collective Features](#collective-features)
5. [Commands](#commands)
6. [Tools](#tools)
7. [Usage Examples](#usage-examples)
8. [Architecture](#architecture)

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

## Architecture

### Component Diagram

```
┌─────────────────────────────────────────────────────────┐
│                  Grok-CLI Main Loop                     │
│  ┌────────────────────────────────────────────────┐   │
│  │         Planning & Reflection Layer            │   │
│  │  • generate_plan tool                         │   │
│  │  • reflect tool                               │   │
│  │  • Automatic reflection on failures           │   │
│  └────────────────────────────────────────────────┘   │
│                         ↓                              │
│  ┌────────────────────────────────────────────────┐   │
│  │         Episodic Memory Layer                  │   │
│  │  • Episode tracking                            │   │
│  │  • Plan storage                                │   │
│  │  • Action logging                              │   │
│  │  • Reflection storage                          │   │
│  │  • Automatic summarization                     │   │
│  └────────────────────────────────────────────────┘   │
│                         ↓                              │
│  ┌────────────────────────────────────────────────┐   │
│  │         Multi-Agent Coordination Layer         │   │
│  │  • Agent spawning                              │   │
│  │  • Blackboard communication                    │   │
│  │  • Role-based specialization                   │   │
│  │  • Shared data management                      │   │
│  └────────────────────────────────────────────────┘   │
│                         ↓                              │
│  ┌────────────────────────────────────────────────┐   │
│  │         Tool Execution Layer                   │   │
│  │  • File operations                             │   │
│  │  • Shell commands                              │   │
│  │  • Code analysis                               │   │
│  │  • Memory operations                           │   │
│  └────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
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
