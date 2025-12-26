#!/usr/bin/env python3

"""
Tests for UI Adapter

Critical path tests for UI adapter abstraction and mocking.
"""

from rich.table import Table

from src.ui.adapter import MockUIAdapter


def test_mock_ui_show_info():
    """Test mock UI records info messages."""
    ui = MockUIAdapter()
    ui.show_info("Test info message")

    assert len(ui.messages) == 1
    assert ui.messages[0] == ("info", "Test info message")


def test_mock_ui_show_error():
    """Test mock UI records error messages."""
    ui = MockUIAdapter()
    ui.show_error("Test error message")

    assert len(ui.messages) == 1
    assert ui.messages[0] == ("error", "Test error message")


def test_mock_ui_show_success():
    """Test mock UI records success messages."""
    ui = MockUIAdapter()
    ui.show_success("Operation completed")

    assert len(ui.messages) == 1
    assert ui.messages[0] == ("success", "Operation completed")


def test_mock_ui_show_warning():
    """Test mock UI records warning messages."""
    ui = MockUIAdapter()
    ui.show_warning("Warning message")

    assert len(ui.messages) == 1
    assert ui.messages[0] == ("warning", "Warning message")


def test_mock_ui_multiple_messages():
    """Test mock UI records multiple messages."""
    ui = MockUIAdapter()

    ui.show_info("Info 1")
    ui.show_error("Error 1")
    ui.show_success("Success 1")
    ui.show_warning("Warning 1")

    assert len(ui.messages) == 4
    assert ui.messages[0][0] == "info"
    assert ui.messages[1][0] == "error"
    assert ui.messages[2][0] == "success"
    assert ui.messages[3][0] == "warning"


def test_mock_ui_show_table():
    """Test mock UI records tables."""
    ui = MockUIAdapter()
    table = Table(title="Test Table")
    table.add_column("Name")
    table.add_row("Test")

    ui.show_table(table)

    assert len(ui.tables) == 1
    assert ui.tables[0] == table


def test_mock_ui_print():
    """Test mock UI records print calls."""
    ui = MockUIAdapter()

    ui.print("Test print 1")
    ui.print("Test print 2", "arg2")

    assert len(ui.prints) == 2


def test_mock_ui_clear():
    """Test mock UI records clear action."""
    ui = MockUIAdapter()

    assert ui.cleared is False

    ui.clear()

    assert ui.cleared is True


def test_mock_ui_prompt_with_default():
    """Test mock UI prompt returns default when no responses queued."""
    ui = MockUIAdapter()

    response = ui.prompt("Test question?", default="default_answer")

    assert response == "default_answer"
    assert len(ui.messages) == 1
    assert ui.messages[0] == ("prompt", "Test question?")


def test_mock_ui_prompt_with_queued_responses():
    """Test mock UI returns queued responses."""
    ui = MockUIAdapter()
    ui.set_responses(["answer1", "answer2", "answer3"])

    response1 = ui.prompt("Question 1?")
    response2 = ui.prompt("Question 2?")
    response3 = ui.prompt("Question 3?")

    assert response1 == "answer1"
    assert response2 == "answer2"
    assert response3 == "answer3"

    # Verify prompts were recorded
    assert len(ui.messages) == 3
    assert all(msg_type == "prompt" for msg_type, _ in ui.messages)


def test_mock_ui_prompt_exhausts_responses():
    """Test mock UI falls back to default after exhausting responses."""
    ui = MockUIAdapter()
    ui.set_responses(["answer1"])

    response1 = ui.prompt("Question 1?")
    response2 = ui.prompt("Question 2?", default="default")

    assert response1 == "answer1"
    assert response2 == "default"


def test_mock_ui_get_messages_by_type():
    """Test filtering messages by type."""
    ui = MockUIAdapter()

    ui.show_info("Info 1")
    ui.show_error("Error 1")
    ui.show_info("Info 2")
    ui.show_success("Success 1")
    ui.show_error("Error 2")

    info_messages = ui.get_messages_by_type("info")
    error_messages = ui.get_messages_by_type("error")
    success_messages = ui.get_messages_by_type("success")

    assert len(info_messages) == 2
    assert len(error_messages) == 2
    assert len(success_messages) == 1
    assert info_messages == ["Info 1", "Info 2"]
    assert error_messages == ["Error 1", "Error 2"]


def test_mock_ui_clear_history():
    """Test clearing mock UI history."""
    ui = MockUIAdapter()

    # Add some history
    ui.show_info("Test")
    ui.show_error("Error")
    ui.set_responses(["answer"])
    ui.print("Print")
    ui.clear()

    # Verify history exists
    assert len(ui.messages) > 0
    assert len(ui.prints) > 0
    assert ui.cleared is True

    # Clear history
    ui.clear_history()

    # Verify everything cleared
    assert len(ui.messages) == 0
    assert len(ui.responses) == 0
    assert len(ui.tables) == 0
    assert len(ui.prints) == 0
    assert ui.cleared is False


def test_mock_ui_integration_scenario():
    """Test a realistic interaction scenario."""
    ui = MockUIAdapter()
    ui.set_responses(["yes", "John", "30"])

    # Simulate a command execution
    ui.show_info("Starting operation...")

    confirmation = ui.prompt("Proceed? (yes/no): ")
    assert confirmation == "yes"

    if confirmation == "yes":
        name = ui.prompt("Enter name: ")
        age = ui.prompt("Enter age: ")

        ui.show_success(f"Created user: {name}, age {age}")

    # Verify the interaction
    messages = ui.get_messages_by_type("info")
    assert "Starting operation..." in messages

    prompts = ui.get_messages_by_type("prompt")
    assert len(prompts) == 3

    success = ui.get_messages_by_type("success")
    assert "Created user: John, age 30" in success
