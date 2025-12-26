#!/usr/bin/env python3
"""
Codebase Analyzer - Analyzes Python codebase structure and quality.
"""
import ast
import glob
import os
from typing import Dict, List, Any
from collections import Counter
import argparse

def analyze_codebase(root_dir: str = '.', file_pattern: str = '**/*.py', max_files: int = 50) -> str:
    """
    Analyze Python codebase structure, patterns, and issues.
    """
    py_files = [os.path.abspath(os.path.join(root_dir, f)) for f in glob.glob(file_pattern, root_dir=root_dir, recursive=True)]
    py_files = py_files[:max_files]
    
    stats = {
        'total_files': len(py_files),
        'classes': 0,
        'functions': 0,
        'imports': [],
        'issues': [],
        'file_sizes': []
    }
    
    for file_path in py_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                stats['file_sizes'].append(len(content.splitlines()))
            
            tree = ast.parse(content)
            file_stats = _analyze_ast(tree, file_path)
            
            stats['classes'] += file_stats['classes']
            stats['functions'] += file_stats['functions']
            stats['imports'].extend(file_stats['imports'])
            stats['issues'].extend(file_stats['issues'])
            
        except Exception as e:
            stats['issues'].append(f'{file_path}: Parse error - {str(e)}')
    
    return _format_report(stats)

def _analyze_ast(tree: ast.AST, file_path: str) -> Dict[str, Any]:
    stats = {'classes': 0, 'functions': 0, 'imports': [], 'issues': []}
    
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            stats['classes'] += 1
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            stats['functions'] += 1
            if not ast.get_docstring(node):
                stats['issues'].append(f'{file_path}:{node.lineno} - Function missing docstring')
        elif isinstance(node, ast.Import):
            for alias in node.names:
                stats['imports'].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            stats['imports'].append(node.module or 'relative')
    
    return stats

def _format_report(stats: Dict[str, Any]) -> str:
    import_counter = Counter(stats['imports'])
    
    avg_lines = sum(stats['file_sizes']) / len(stats['file_sizes']) if stats['file_sizes'] else 0
    
    report = """
CODEBASE ANALYSIS REPORT
==================================================
STATS:
  Total Python files: {}
  Total classes: {}
  Total functions/methods: {}
  Avg lines per file: {:.0f}

TOP IMPORTS (most used):
""".format(
        stats['total_files'],
        stats['classes'], 
        stats['functions'],
        avg_lines
    )
    
    for imp, count in import_counter.most_common(10):
        report += f'  {imp}: {count}\n'
    
    report += f'\nPOTENTIAL ISSUES ({len(stats["issues"])} found):\n'
    if stats['issues']:
        for issue in stats['issues'][:20]:
            report += f'  {issue}\n'
    else:
        report += '  No major issues detected!\n'
    
    return report.strip()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze Python codebase')
    parser.add_argument('--root', default='.', help='Root directory')
    parser.add_argument('--pattern', default='**/*.py', help='File pattern')
    parser.add_argument('--max-files', type=int, default=50, help='Max files to analyze')
    args = parser.parse_args()
    
    print(analyze_codebase(args.root, args.pattern, args.max_files))
