"""
Utils module for Grok Assistant

Contains utility functions organized by domain.
"""

from .async_utils import InterruptedError, InterruptiblePoller, interruptible_sleep
from .file_utils import (
    add_file_context_smartly,
    apply_fuzzy_diff_edit,
    detect_file_encoding,
    enhanced_binary_detection,
    find_best_matching_file,
    is_binary_file,
    safe_file_read,
)
from .path_utils import (
    ensure_directory_exists,
    get_directory_tree_summary,
    get_relative_path,
    is_excluded_file,
    is_path_safe,
    normalize_path,
)
from .shell_utils import (
    detect_available_shells,
    get_shell_for_os,
    is_dangerous_command,
    run_bash_command,
    run_powershell_command,
    sanitize_command,
    validate_working_directory,
)
from .text_utils import (
    count_lines,
    estimate_token_usage,
    extract_code_blocks,
    format_file_size,
    get_context_usage_info,
    similarity_score,
    smart_truncate_history,
    truncate_text,
    validate_tool_calls,
)

__all__ = [
    # Path utilities
    'normalize_path', 'get_directory_tree_summary', 'is_path_safe',
    'get_relative_path', 'ensure_directory_exists', 'is_excluded_file',

    # File utilities
    'is_binary_file', 'detect_file_encoding', 'enhanced_binary_detection',
    'safe_file_read', 'find_best_matching_file', 'apply_fuzzy_diff_edit',
    'add_file_context_smartly',

    # Text utilities
    'estimate_token_usage', 'get_context_usage_info', 'smart_truncate_history',
    'validate_tool_calls', 'truncate_text', 'count_lines', 'extract_code_blocks',
    'format_file_size', 'similarity_score',

    # Shell utilities
    'detect_available_shells', 'run_bash_command', 'run_powershell_command',
    'get_shell_for_os', 'is_dangerous_command', 'sanitize_command',
    'validate_working_directory',

    # Async utilities
    'interruptible_sleep', 'InterruptiblePoller', 'InterruptedError'
]
