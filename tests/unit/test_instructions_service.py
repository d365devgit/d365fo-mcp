"""
Tests for the InstructionsService
"""

import pytest
from d365fo_mcp.services.instructions.service import InstructionsService


@pytest.mark.unit
class TestInstructionsService:
    @pytest.fixture
    async def instructions_service(self, test_database):
        """Create instructions service with test database"""
        from d365fo_mcp.repositories.sqlite import SQLiteInstructionsRepository
        
        # Use the database path from the test_database fixture
        repository = SQLiteInstructionsRepository(test_database.db_path)
        await repository.initialize()
        return InstructionsService(repository)

    async def test_save_instruction(self, instructions_service, sample_instruction):
        """Test saving an instruction"""
        instruction_id = await instructions_service.save_or_update_instruction(
            "TestEntity", "create", sample_instruction
        )

        assert isinstance(instruction_id, str)
        assert len(instruction_id) > 0  # Should be a UUID string

    async def test_get_entity_instructions_empty(self, instructions_service):
        """Test getting instructions for entity with no instructions"""
        result = await instructions_service.get_entity_instructions("NonExistentEntity")

        assert result["entity_name"] == "NonExistentEntity"
        assert result["instructions"] == []
        assert result["count"] == 0
        assert len(result["suggestions"]) > 0

    async def test_get_entity_instructions_with_data(
        self, instructions_service, sample_instruction
    ):
        """Test getting instructions for entity with saved instructions"""
        # Save an instruction first
        instruction_id = await instructions_service.save_or_update_instruction(
            "TestEntity", "create", sample_instruction
        )

        # Get instructions
        result = await instructions_service.get_entity_instructions("TestEntity", "create")

        assert result["entity_name"] == "TestEntity"
        assert result["operation_type"] == "create"
        assert len(result["instructions"]) == 1
        assert result["instructions"][0]["title"] == sample_instruction["title"]
        assert result["instructions"][0]["id"] == instruction_id

    async def test_rate_instruction(self, instructions_service, sample_instruction):
        """Test rating an instruction"""
        # Save an instruction
        instruction_id = await instructions_service.save_or_update_instruction(
            "TestEntity", "create", sample_instruction
        )

        # Rate it as successful
        await instructions_service.rate_instruction_success(instruction_id, True)

        # Get instructions and check success count
        result = await instructions_service.get_entity_instructions("TestEntity")
        instruction = result["instructions"][0]

        assert instruction["success_count"] == 1
        assert instruction["failure_count"] == 0

    async def test_search_instructions(self, instructions_service, sample_instruction):
        """Test searching instructions"""
        # Save some instructions
        await instructions_service.save_or_update_instruction("TestEntity", "create", sample_instruction)

        another_instruction = sample_instruction.copy()
        another_instruction["title"] = "Update Test Record"
        another_instruction["description"] = "Example of updating a record"

        await instructions_service.save_or_update_instruction("TestEntity", "update", another_instruction)

        # Search for instructions
        results = await instructions_service.search_instructions("Test Record")

        assert len(results) == 2
        assert all("Test Record" in inst["title"] for inst in results)

    async def test_invalid_operation_type(self, instructions_service, sample_instruction):
        """Test saving instruction with invalid operation type"""
        from d365fo_mcp.repositories.sqlite.database import DatabaseError
        
        with pytest.raises(DatabaseError, match="CHECK constraint failed"):
            await instructions_service.save_or_update_instruction(
                "TestEntity", "invalid_operation", sample_instruction
            )

    async def test_missing_required_fields(self, instructions_service):
        """Test saving instruction with missing required fields"""
        from d365fo_mcp.repositories.sqlite.database import DatabaseError
        
        incomplete_instruction = {"description": "Missing title"}

        # Should raise DatabaseError for missing title
        with pytest.raises(DatabaseError, match="Instruction title is required"):
            await instructions_service.save_or_update_instruction(
                "TestEntity", "create", incomplete_instruction
            )
