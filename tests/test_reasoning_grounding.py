"""Test reasoning grounding - ensuring reasoning uses fetched data."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from app.agents.executor import ExecutorAgent
from app.schemas.request_response import ExecutionStep
from app.memory.schemas import ExecutionContext
from app.tools.base import ToolOutput


class TestReasoningGrounding:
    """Test that reasoning steps are grounded in fetched data, not generic explanations."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.executor = ExecutorAgent()
    
    def test_reasoning_receives_github_repo_context(self):
        """Test that reasoning step receives structured GitHub repo data from previous HTTP step."""
        
        # Create execution steps: HTTP fetch → Reasoning explain
        steps = [
            ExecutionStep(
                step_number=1,
                description="Fetch repository data from GitHub",
                tool_name="http",
                input_data={
                    "url": "https://api.github.com/search/repositories?q=deep+learning",
                    "method": "GET"
                },
                reasoning="Using HTTP to fetch repo data"
            ),
            ExecutionStep(
                step_number=2,
                description="Explain the repository",
                tool_name="reasoning",
                input_data={
                    "question": "What is this repository about?",
                    "context": ""  # Will be enriched
                },
                reasoning="Using reasoning to explain"
            )
        ]
        
        # Mock HTTP tool to return GitHub API response
        mock_http_output = {
            "items": [
                {
                    "full_name": "tensorflow/tensorflow",
                    "name": "tensorflow",
                    "description": "An Open Source Machine Learning Framework for Everyone",
                    "stargazers_count": 185000,
                    "forks_count": 74000,
                    "language": "C++",
                    "html_url": "https://github.com/tensorflow/tensorflow",
                    "topics": ["machine-learning", "deep-learning", "tensorflow"],
                    "created_at": "2015-11-07T01:19:20Z",
                    "updated_at": "2024-01-15T10:30:00Z"
                }
            ]
        }
        
        # Track actual input to reasoning tool
        reasoning_input_captured = None
        
        def capture_reasoning_input(**kwargs):
            nonlocal reasoning_input_captured
            reasoning_input_captured = kwargs
            return ToolOutput(
                success=True,
                result="TensorFlow is a comprehensive ML framework...",
                error=None
            )
        
        # Mock tools
        mock_http_tool = Mock()
        mock_http_tool.execute.return_value = ToolOutput(
            success=True,
            result=mock_http_output,
            error=None
        )
        
        mock_reasoning_tool = Mock()
        mock_reasoning_tool.execute.side_effect = capture_reasoning_input
        
        with patch.object(
            self.executor.tool_registry,
            "get",
            side_effect=lambda name: mock_http_tool if name == "http" else mock_reasoning_tool
        ):
            # Create execution context
            execution_context = ExecutionContext(
                execution_id="test_grounding_001",
                goal="Fetch deep learning repository and explain it",
                user_context={}
            )
            
            # Execute plan
            result_context = self.executor.execute(steps, execution_context)
            
            # Verify reasoning tool received structured context
            assert reasoning_input_captured is not None, "Reasoning tool was not called"
            assert "context" in reasoning_input_captured, "No context provided to reasoning"
            
            context = reasoning_input_captured["context"]
            
            # Context should be dict with GitHub repo metadata
            assert isinstance(context, dict), f"Context should be dict, got {type(context)}"
            assert context["name"] == "tensorflow/tensorflow", "Should contain repo name"
            assert context["description"] == "An Open Source Machine Learning Framework for Everyone"
            assert context["stars"] == 185000, "Should contain star count"
            assert context["url"] == "https://github.com/tensorflow/tensorflow"
            assert "topics" in context
            
            # Verify execution succeeded
            assert result_context.status != "failed"
    
    def test_reasoning_without_previous_tool_uses_generic_context(self):
        """Test that reasoning without previous tool step works normally."""
        
        # Create execution plan with only reasoning
        steps = [
            ExecutionStep(
                step_number=1,
                description="Explain deep learning concept",
                tool_name="reasoning",
                input_data={
                    "question": "What is deep learning?",
                    "context": "Machine learning context"
                },
                reasoning="Pure reasoning"
            )
        ]
        
        # Track reasoning input
        reasoning_input_captured = None
        
        def capture_reasoning_input(**kwargs):
            nonlocal reasoning_input_captured
            reasoning_input_captured = kwargs
            return ToolOutput(
                success=True,
                result="Deep learning is a subset of machine learning...",
                error=None
            )
        
        mock_reasoning_tool = Mock()
        mock_reasoning_tool.execute.side_effect = capture_reasoning_input
        
        with patch.object(self.executor.tool_registry, "get", return_value=mock_reasoning_tool):
            execution_context = ExecutionContext(
                execution_id="test_grounding_002",
                goal="Explain what deep learning is",
                user_context={}
            )
            
            # Execute plan
            result_context = self.executor.execute(steps, execution_context)
            
            # Verify reasoning uses original context (no grounding needed)
            assert reasoning_input_captured is not None
            assert reasoning_input_captured["context"] == "Machine learning context"
            assert result_context.status != "failed"
    
    def test_extract_structured_context_from_github_response(self):
        """Test extraction of structured context from GitHub API response."""
        
        github_response = {
            "items": [
                {
                    "full_name": "pytorch/pytorch",
                    "description": "Tensors and Dynamic neural networks",
                    "stargazers_count": 45000,
                    "forks_count": 12000,
                    "language": "Python",
                    "html_url": "https://github.com/pytorch/pytorch",
                    "topics": ["deep-learning", "pytorch"]
                }
            ]
        }
        
        result = self.executor._extract_http_context(github_response)
        
        assert isinstance(result, dict)
        assert result["name"] == "pytorch/pytorch"
        assert result["description"] == "Tensors and Dynamic neural networks"
        assert result["stars"] == 45000
        assert result["url"] == "https://github.com/pytorch/pytorch"
    
    def test_extract_structured_context_from_empty_items(self):
        """Test that empty items list is handled gracefully."""
        
        github_response = {"items": []}
        
        result = self.executor._extract_http_context(github_response)
        
        # Should return the response as-is
        assert result == github_response
    
    def test_format_context_dict_for_reasoning(self):
        """Test that reasoning tool formats dict context properly."""
        from app.tools.reasoning_tool import ReasoningTool
        
        tool = ReasoningTool()
        
        repo_context = {
            "name": "fastapi/fastapi",
            "description": "FastAPI framework, high performance",
            "stars": 65000,
            "forks": 5500,
            "language": "Python",
            "url": "https://github.com/fastapi/fastapi",
            "topics": ["fastapi", "api", "async"]
        }
        
        formatted = tool._format_context(repo_context)
        
        # Should format as readable structure
        assert "GitHub Repository:" in formatted
        assert "fastapi/fastapi" in formatted
        assert "65,000" in formatted  # Formatted with commas
        assert "https://github.com/fastapi/fastapi" in formatted
    
    def test_format_context_string_for_reasoning(self):
        """Test that reasoning tool handles string context."""
        from app.tools.reasoning_tool import ReasoningTool
        
        tool = ReasoningTool()
        
        string_context = "This is generic context"
        formatted = tool._format_context(string_context)
        
        assert formatted == "Context: This is generic context"
    
    def test_reasoning_grounding_with_memory_tool(self):
        """Test that reasoning can be grounded in memory tool output."""
        
        steps = [
            ExecutionStep(
                step_number=1,
                description="Retrieve user preference",
                tool_name="memory",
                input_data={
                    "action": "get",
                    "key": "user_theme"
                },
                reasoning="Get from memory"
            ),
            ExecutionStep(
                step_number=2,
                description="Explain the preference",
                tool_name="reasoning",
                input_data={
                    "question": "What is the user's theme preference?",
                    "context": ""
                },
                reasoning="Explain preference"
            )
        ]
        
        # Track reasoning input
        reasoning_input_captured = None
        
        def capture_reasoning_input(**kwargs):
            nonlocal reasoning_input_captured
            reasoning_input_captured = kwargs
            return ToolOutput(
                success=True,
                result="The user prefers dark mode",
                error=None
            )
        
        mock_memory_tool = Mock()
        mock_memory_tool.execute.return_value = ToolOutput(
            success=True,
            result={"value": "dark_mode"},
            error=None
        )
        
        mock_reasoning_tool = Mock()
        mock_reasoning_tool.execute.side_effect = capture_reasoning_input
        
        with patch.object(
            self.executor.tool_registry,
            "get",
            side_effect=lambda name: mock_memory_tool if name == "memory" else mock_reasoning_tool
        ):
            execution_context = ExecutionContext(
                execution_id="test_grounding_003",
                goal="Remember and explain user preference",
                user_context={}
            )
            
            result_context = self.executor.execute(steps, execution_context)
            
            # Verify reasoning received memory value
            assert reasoning_input_captured is not None
            assert reasoning_input_captured["context"] == "dark_mode", "Should extract 'value' from memory output"
            assert result_context.status != "failed"
