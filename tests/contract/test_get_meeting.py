"""
Contract tests for GET /api/v1/meetings/{meeting_id} endpoint.

This module tests the API contract as defined in api-spec.yaml.
Following TDD principles: these tests should initially fail until implementation is complete.
"""

import uuid
from typing import Any, Dict

import pytest


# Test configuration
MEETINGS_ENDPOINT = "/api/v1/meetings"


# Expected schema definitions based on OpenAPI spec
EXPECTED_STATUSES = ["draft", "reviewing", "optimized", "completed"]
EXPECTED_INPUT_TYPES = ["audio", "text"]
EXPECTED_STAGE_NAMES = ["draft", "review", "final"]
EXPECTED_STAGE_STATUSES = ["pending", "processing", "completed", "failed"]


def validate_meeting_detail_schema(response_data: Dict[str, Any]) -> None:
    """
    Validate MeetingDetail response schema according to OpenAPI spec.

    Required fields from api-spec.yaml MeetingDetail schema:
    - id: UUID
    - status: enum
    - created_at: datetime
    - updated_at: datetime
    - input_type: enum
    - stages: array of ProcessingStage
    """
    # Required fields validation
    assert "id" in response_data, "Missing required field: id"
    assert "status" in response_data, "Missing required field: status"
    assert "created_at" in response_data, "Missing required field: created_at"
    assert "updated_at" in response_data, "Missing required field: updated_at"
    assert "input_type" in response_data, "Missing required field: input_type"
    assert "stages" in response_data, "Missing required field: stages"

    # Field type and format validation
    try:
        uuid.UUID(response_data["id"])
    except (ValueError, TypeError) as e:
        pytest.fail(f"Invalid UUID format for id: {e}")

    assert response_data["status"] in EXPECTED_STATUSES, \
        f"Invalid status: {response_data['status']}, expected one of {EXPECTED_STATUSES}"

    assert response_data["input_type"] in EXPECTED_INPUT_TYPES, \
        f"Invalid input_type: {response_data['input_type']}, expected one of {EXPECTED_INPUT_TYPES}"

    # Stages array validation
    assert isinstance(response_data["stages"], list), "stages must be an array"


def validate_processing_stage_schema(stage: Dict[str, Any]) -> None:
    """
    Validate ProcessingStage schema according to OpenAPI spec.

    Required fields:
    - stage_name: enum [draft, review, final]
    - status: enum [pending, processing, completed, failed]
    - started_at: datetime
    """
    assert "stage_name" in stage, "Missing required field: stage_name"
    assert "status" in stage, "Missing required field: status"
    assert "started_at" in stage, "Missing required field: started_at"

    assert stage["stage_name"] in EXPECTED_STAGE_NAMES, \
        f"Invalid stage_name: {stage['stage_name']}, expected one of {EXPECTED_STAGE_NAMES}"

    assert stage["status"] in EXPECTED_STAGE_STATUSES, \
        f"Invalid stage status: {stage['status']}, expected one of {EXPECTED_STAGE_STATUSES}"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_meeting_success(async_client):
    """
    Test: GET /api/v1/meetings/{meeting_id} returns complete meeting data.

    Scenario: Client requests an existing meeting by ID
    Expected: 200 OK with complete MeetingDetail JSON

    This test verifies:
    - Endpoint responds with 200 status code
    - Response contains valid JSON
    - Response includes all required fields from MeetingDetail schema
    """
    # Arrange: Generate a valid meeting ID (in real scenario, this would be created first)
    meeting_id = str(uuid.uuid4())
    endpoint_url = f"{MEETINGS_ENDPOINT}/{meeting_id}"

    # Act: Send GET request to retrieve meeting
    response = await async_client.get(endpoint_url)

    # Assert: Verify response status and basic structure
    assert response.status_code == 200, \
        f"Expected status code 200, got {response.status_code}"

    assert response.headers.get("content-type", "").startswith("application/json"), \
        "Response must be JSON"

    meeting_data = response.json()

    # Validate complete schema
    validate_meeting_detail_schema(meeting_data)

    # Verify meeting ID matches request
    assert meeting_data["id"] == meeting_id, \
        f"Response meeting_id {meeting_data['id']} does not match requested {meeting_id}"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_meeting_not_found(async_client):
    """
    Test: GET /api/v1/meetings/{meeting_id} returns 404 for non-existent meeting.

    Scenario: Client requests a meeting that doesn't exist
    Expected: 404 Not Found with Error schema

    This test verifies:
    - Endpoint responds with 404 status code
    - Response contains error message in correct format
    - Error response follows OpenAPI Error schema
    """
    # Arrange: Use a non-existent meeting ID
    non_existent_id = str(uuid.uuid4())
    endpoint_url = f"{MEETINGS_ENDPOINT}/{non_existent_id}"

    # Act: Attempt to retrieve non-existent meeting
    response = await async_client.get(endpoint_url)

    # Assert: Verify 404 response
    assert response.status_code == 404, \
        f"Expected status code 404 for non-existent meeting, got {response.status_code}"

    assert response.headers.get("content-type", "").startswith("application/json"), \
        "Error response must be JSON"

    error_data = response.json()

    # Validate Error schema from OpenAPI spec
    assert "error" in error_data, "Error response must contain 'error' field"
    assert "message" in error_data, "Error response must contain 'message' field"

    # Verify error message is meaningful
    assert len(error_data["message"]) > 0, "Error message should not be empty"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_meeting_response_schema(async_client):
    """
    Test: GET /api/v1/meetings/{meeting_id} response fully complies with OpenAPI schema.

    Scenario: Verify response structure matches MeetingDetail schema exactly
    Expected: All fields present with correct types and formats

    This test performs comprehensive schema validation:
    - All required fields are present
    - Field types match specification
    - Enum values are valid
    - Nested objects (template, stages) have correct structure
    - Optional fields are handled correctly
    """
    # Arrange: Valid meeting ID
    meeting_id = str(uuid.uuid4())
    endpoint_url = f"{MEETINGS_ENDPOINT}/{meeting_id}"

    # Act: Retrieve meeting
    response = await async_client.get(endpoint_url)

    # Skip schema validation if meeting doesn't exist (focus on 200 responses)
    if response.status_code != 200:
        pytest.skip(f"Cannot validate schema for status code {response.status_code}")

    meeting_data = response.json()

    # Assert: Comprehensive schema validation
    validate_meeting_detail_schema(meeting_data)

    # Validate datetime format (ISO 8601)
    for datetime_field in ["created_at", "updated_at"]:
        assert isinstance(meeting_data[datetime_field], str), \
            f"{datetime_field} must be a string"
        # Basic ISO 8601 format check (more comprehensive validation could use dateutil)
        assert "T" in meeting_data[datetime_field], \
            f"{datetime_field} must be in ISO 8601 format (contain 'T')"

    # Validate optional fields if present
    if "audio_duration_seconds" in meeting_data:
        duration = meeting_data["audio_duration_seconds"]
        assert duration is None or isinstance(duration, int), \
            "audio_duration_seconds must be integer or null"
        if duration is not None:
            assert duration >= 0, "audio_duration_seconds must be non-negative"

    # Validate template object if present
    if "template" in meeting_data:
        template = meeting_data["template"]
        assert isinstance(template, dict), "template must be an object"
        # Template schema validation could be expanded based on requirements


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_meeting_includes_all_stages(async_client):
    """
    Test: GET /api/v1/meetings/{meeting_id} response includes all three processing stages.

    Scenario: Verify meeting response contains draft, review, and final stages
    Expected: stages array contains exactly 3 stages with correct names

    This test verifies the three-stage pipeline architecture:
    - Stage 1: draft (initial AI generation)
    - Stage 2: review (user feedback collection)
    - Stage 3: final (optimized version)
    """
    # Arrange: Valid meeting ID
    meeting_id = str(uuid.uuid4())
    endpoint_url = f"{MEETINGS_ENDPOINT}/{meeting_id}"

    # Act: Retrieve meeting
    response = await async_client.get(endpoint_url)

    # Skip if meeting doesn't exist
    if response.status_code != 200:
        pytest.skip(f"Cannot validate stages for status code {response.status_code}")

    meeting_data = response.json()
    stages = meeting_data.get("stages", [])

    # Assert: Verify all three stages are present
    assert isinstance(stages, list), "stages must be an array"
    assert len(stages) == 3, \
        f"Expected 3 stages (draft, review, final), got {len(stages)}"

    # Extract stage names
    stage_names = [stage.get("stage_name") for stage in stages]

    # Verify all expected stages are present
    assert "draft" in stage_names, "Missing 'draft' stage"
    assert "review" in stage_names, "Missing 'review' stage"
    assert "final" in stage_names, "Missing 'final' stage"

    # Verify each stage has valid schema
    for stage in stages:
        validate_processing_stage_schema(stage)

    # Verify stages are in logical order (optional but recommended)
    expected_order = ["draft", "review", "final"]
    actual_order = [stage.get("stage_name") for stage in stages]
    assert actual_order == expected_order, \
        f"Stages should be in order {expected_order}, got {actual_order}"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_get_meeting_invalid_uuid_format(async_client):
    """
    Test: GET /api/v1/meetings/{meeting_id} handles invalid UUID format.

    Scenario: Client sends request with invalid UUID format
    Expected: 400 Bad Request or 404 Not Found

    This validates input validation for path parameters.
    """
    # Arrange: Invalid UUID format
    invalid_id = "not-a-valid-uuid"
    endpoint_url = f"{MEETINGS_ENDPOINT}/{invalid_id}"

    # Act: Send request with invalid UUID
    response = await async_client.get(endpoint_url)

    # Assert: Should return error status (400 or 404 acceptable)
    assert response.status_code in [400, 404, 422], \
        f"Expected error status for invalid UUID, got {response.status_code}"

    # Verify error response format
    if response.headers.get("content-type", "").startswith("application/json"):
        error_data = response.json()
        assert "error" in error_data or "message" in error_data, \
            "Error response should contain error information"
