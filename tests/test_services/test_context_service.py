#!/usr/bin/env python3

"""
Tests for ContextService

Critical path tests for context service business logic.
"""

from src.services import ContextService


def test_context_service_initialization(context_manager):
    """Test ContextService initialization."""
    service = ContextService(context_manager)

    assert service is not None
    assert service.context_manager == context_manager
