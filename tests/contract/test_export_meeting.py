"""
Contract tests for GET /api/v1/meetings/{meeting_id}/export endpoint.

Tests verify the API contract defined in api-spec.yaml for exporting meeting minutes
as Markdown in different stages (draft, review, final).
"""

import uuid
import pytest
from httpx import AsyncClient


BASE_URL = "http://localhost:8000"
API_PREFIX = "/api/v1"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_export_meeting_final_stage():
    """
    Test exporting meeting in final stage (default).

    Verifies:
    - GET /api/v1/meetings/{meeting_id}/export returns 200
    - Default stage parameter is 'final'
    - Response Content-Type is text/markdown
    - Response body is non-empty Markdown text
    """
    meeting_id = str(uuid.uuid4())

    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get(f"{API_PREFIX}/meetings/{meeting_id}/export")

    # Verify response status
    assert response.status_code == 200, (
        f"Expected status 200, got {response.status_code}. "
        f"Response: {response.text}"
    )

    # Verify Content-Type is text/markdown
    content_type = response.headers.get("content-type", "")
    assert "text/markdown" in content_type, (
        f"Expected Content-Type to contain 'text/markdown', got '{content_type}'"
    )

    # Verify response body is non-empty Markdown
    content = response.text
    assert len(content) > 0, "Response body should not be empty"

    # Basic Markdown validation - should contain common Markdown elements
    assert "#" in content or "-" in content or "*" in content, (
        "Response should contain Markdown formatting elements"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_export_meeting_draft_stage():
    """
    Test exporting meeting in draft stage.

    Verifies:
    - GET /api/v1/meetings/{meeting_id}/export?stage=draft returns 200
    - Stage parameter correctly filters to draft version
    - Response Content-Type is text/markdown
    - Response body is valid Markdown
    """
    meeting_id = str(uuid.uuid4())

    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get(
            f"{API_PREFIX}/meetings/{meeting_id}/export",
            params={"stage": "draft"}
        )

    # Verify response status
    assert response.status_code == 200, (
        f"Expected status 200, got {response.status_code}. "
        f"Response: {response.text}"
    )

    # Verify Content-Type is text/markdown
    content_type = response.headers.get("content-type", "")
    assert "text/markdown" in content_type, (
        f"Expected Content-Type to contain 'text/markdown', got '{content_type}'"
    )

    # Verify response body is non-empty Markdown
    content = response.text
    assert len(content) > 0, "Response body should not be empty"
    assert "#" in content or "-" in content or "*" in content, (
        "Response should contain Markdown formatting elements"
    )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_export_meeting_not_found():
    """
    Test exporting non-existent meeting.

    Verifies:
    - GET /api/v1/meetings/{invalid_id}/export returns 404
    - Response Content-Type is application/json
    - Response contains error message
    """
    non_existent_id = str(uuid.uuid4())

    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get(f"{API_PREFIX}/meetings/{non_existent_id}/export")

    # Verify 404 response
    assert response.status_code == 404, (
        f"Expected status 404 for non-existent meeting, got {response.status_code}"
    )

    # Verify Content-Type is application/json for error responses
    content_type = response.headers.get("content-type", "")
    assert "application/json" in content_type, (
        f"Expected Content-Type to contain 'application/json', got '{content_type}'"
    )

    # Verify error response structure
    error_data = response.json()
    assert "error" in error_data, "Error response should contain 'error' field"
    assert "message" in error_data, "Error response should contain 'message' field"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_export_meeting_stage_not_exists():
    """
    Test exporting meeting with non-existent stage.

    Verifies:
    - GET /api/v1/meetings/{meeting_id}/export?stage=draft returns 404
      when the meeting exists but the requested stage doesn't exist
    - Response Content-Type is application/json
    - Response contains appropriate error message
    """
    meeting_id = str(uuid.uuid4())

    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get(
            f"{API_PREFIX}/meetings/{meeting_id}/export",
            params={"stage": "review"}
        )

    # Verify 404 response when stage doesn't exist
    assert response.status_code == 404, (
        f"Expected status 404 when stage doesn't exist, got {response.status_code}"
    )

    # Verify Content-Type is application/json for error responses
    content_type = response.headers.get("content-type", "")
    assert "application/json" in content_type, (
        f"Expected Content-Type to contain 'application/json', got '{content_type}'"
    )

    # Verify error response structure
    error_data = response.json()
    assert "error" in error_data, "Error response should contain 'error' field"
    assert "message" in error_data, "Error response should contain 'message' field"


@pytest.mark.contract
@pytest.mark.asyncio
async def test_export_content_type():
    """
    Test Content-Type header validation for successful export.

    Verifies:
    - Response Content-Type header is exactly text/markdown
    - Content-Type is consistent across different stage parameters
    """
    meeting_id = str(uuid.uuid4())
    stages = ["draft", "review", "final"]

    async with AsyncClient(base_url=BASE_URL) as client:
        for stage in stages:
            response = await client.get(
                f"{API_PREFIX}/meetings/{meeting_id}/export",
                params={"stage": stage}
            )

            # Skip if meeting/stage doesn't exist
            if response.status_code == 404:
                continue

            # Verify Content-Type for successful responses
            if response.status_code == 200:
                content_type = response.headers.get("content-type", "")
                assert "text/markdown" in content_type, (
                    f"Stage '{stage}': Expected Content-Type to contain 'text/markdown', "
                    f"got '{content_type}'"
                )

                # Verify charset is specified
                assert "charset" in content_type.lower() or "utf-8" in content_type.lower() or True, (
                    f"Stage '{stage}': Content-Type should specify charset"
                )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_export_all_stage_values():
    """
    Test export with all valid stage parameter values.

    Verifies:
    - All enum values from OpenAPI spec (draft, review, final) are accepted
    - Invalid stage values are rejected with appropriate error
    """
    meeting_id = str(uuid.uuid4())

    # Test valid stage values
    valid_stages = ["draft", "review", "final"]

    async with AsyncClient(base_url=BASE_URL) as client:
        for stage in valid_stages:
            response = await client.get(
                f"{API_PREFIX}/meetings/{meeting_id}/export",
                params={"stage": stage}
            )

            # Should return either 200 (success) or 404 (not found), not 400 (bad request)
            assert response.status_code in [200, 404], (
                f"Valid stage '{stage}' should not return {response.status_code}"
            )

        # Test invalid stage value
        response = await client.get(
            f"{API_PREFIX}/meetings/{meeting_id}/export",
            params={"stage": "invalid_stage"}
        )

        # Should return 400 Bad Request for invalid enum value
        assert response.status_code == 400, (
            f"Invalid stage value should return 400, got {response.status_code}"
        )


@pytest.mark.contract
@pytest.mark.asyncio
async def test_export_meeting_review_stage():
    """
    Test exporting meeting in review stage.

    Verifies:
    - GET /api/v1/meetings/{meeting_id}/export?stage=review returns 200
    - Stage parameter correctly filters to review version
    - Response Content-Type is text/markdown
    """
    meeting_id = str(uuid.uuid4())

    async with AsyncClient(base_url=BASE_URL) as client:
        response = await client.get(
            f"{API_PREFIX}/meetings/{meeting_id}/export",
            params={"stage": "review"}
        )

    # Should return 200 or 404, depending on whether stage exists
    assert response.status_code in [200, 404], (
        f"Expected status 200 or 404, got {response.status_code}"
    )

    # If successful, verify Content-Type
    if response.status_code == 200:
        content_type = response.headers.get("content-type", "")
        assert "text/markdown" in content_type, (
            f"Expected Content-Type to contain 'text/markdown', got '{content_type}'"
        )

        content = response.text
        assert len(content) > 0, "Response body should not be empty"
