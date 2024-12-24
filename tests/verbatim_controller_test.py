import pytest
from mongomock import MongoClient
from llm4quality_api.models.models import Verbatim, Result, Status
from llm4quality_api.controllers.verbatim_controller import VerbatimController


@pytest.fixture
def mock_controller():
    """
    Create a VerbatimController instance with a mocked MongoDB collection.
    """
    # Mock MongoDB client and inject into VerbatimController
    mock_client = MongoClient()
    mock_controller = VerbatimController()
    mock_controller.collection = mock_client.llm4quality.verbatims
    return mock_controller


@pytest.mark.asyncio
async def test_create_verbatims(mock_controller):
    lines = ["Verbatim 1", "Verbatim 2", "Verbatim 3"]
    year = 2024

    # Call the create_verbatims method
    created_verbatims = await mock_controller.create_verbatims(lines, year)

    # Verify the results
    assert len(created_verbatims) == len(lines)
    for idx, verbatim in enumerate(created_verbatims):
        assert verbatim.content == lines[idx]
        assert verbatim.status == Status.RUN
        assert verbatim.result is None
        assert verbatim.year == year


@pytest.mark.asyncio
async def test_get_verbatims(mock_controller):
    # Seed the mock database
    mock_controller.collection.insert_many(
        [
            {"content": "Test 1", "status": "RUN", "result": None, "year": 2024},
            {"content": "Test 2", "status": "SUCCESS", "result": None, "year": 2024},
            {"content": "Test 3", "status": "ERROR", "result": None, "year": 2023},
        ]
    )

    query = {"year": 2024}
    verbatims = await mock_controller.get_verbatims(query, pagination=1, per_page=2)

    # Verify the results
    assert len(verbatims) == 2
    assert all(v.year == 2024 for v in verbatims)


@pytest.mark.asyncio
async def test_delete_verbatims(mock_controller):
    # Seed the mock database
    inserted_ids = mock_controller.collection.insert_many(
        [
            {"content": "Test 1", "status": "RUN", "result": None, "year": 2024},
            {"content": "Test 2", "status": "SUCCESS", "result": None, "year": 2024},
        ]
    ).inserted_ids

    # Call the delete_verbatims method
    deleted_count = await mock_controller.delete_verbatims(
        [str(oid) for oid in inserted_ids]
    )

    # Verify the results
    assert deleted_count == 2
    assert mock_controller.collection.count_documents({}) == 0


@pytest.mark.asyncio
async def test_update_verbatim_status(mock_controller):
    # Seed the mock database
    inserted_id = mock_controller.collection.insert_one(
        {"content": "Test Verbatim", "status": "RUN", "result": None, "year": 2024}
    ).inserted_id

    # Call the update_verbatim_status method
    result = Result(
        circuit={
            "positive": "50%",
            "negative": "20%",
            "neutral": "30%",
            "not mentioned": "0%",
        },
        qualite={
            "positive": "40%",
            "negative": "30%",
            "neutral": "20%",
            "not mentioned": "10%",
        },
        professionnalisme={
            "positive": "60%",
            "negative": "10%",
            "neutral": "20%",
            "not mentioned": "10%",
        },
    )
    updated = await mock_controller.update_verbatim_status(
        verbatim_id=str(inserted_id),
        status=Status.SUCCESS,
        result=result,
    )

    # Verify the results
    assert updated
    updated_verbatim = mock_controller.collection.find_one({"_id": inserted_id})
    assert updated_verbatim["status"] == "SUCCESS"
    assert updated_verbatim["result"] == result.model_dump()


@pytest.mark.asyncio
async def test_find_verbatim_by_id(mock_controller):
    # Seed the mock database
    inserted_id = mock_controller.collection.insert_one(
        {"content": "Test Verbatim", "status": "RUN", "result": None, "year": 2024}
    )

    # Call the find_verbatim_by_id method
    verbatim = await mock_controller.find_verbatim_by_id(str(inserted_id.inserted_id))

    # Verify the results
    assert verbatim is not None
    assert verbatim.content == "Test Verbatim"
    assert verbatim.status == Status.RUN
