import unittest
from unittest.mock import patch, MagicMock
from main import discGenerator, DISCAnalysis
import datetime
class TestDiscGenerator(unittest.TestCase):
    @patch('main.ChatOpenAI')
    def test_disc_generator(self, MockChatOpenAI):
        # Mock the ChatOpenAI instance and its methods
        mock_llm = MockChatOpenAI.return_value
        mock_structured_llm = mock_llm.with_structured_output.return_value
        mock_structured_llm.invoke.return_value = DISCAnalysis(
            id="123",
            name="John Doe",
            email="john.doe@example.com",
            profile_source="LinkedIn",
            assessment_date=datetime.datetime.now(),
            profile_completeness=100,
            dominance=DISCAnalysis.DISCAttribute(score=75, traits=["assertive", "confident"], behavioral_indicators="goal-oriented"),
            influence=DISCAnalysis.DISCAttribute(score=60, traits=["persuasive", "outgoing"], behavioral_indicators="enthusiastic"),
            steadiness=DISCAnalysis.DISCAttribute(score=50, traits=["patient", "reliable"], behavioral_indicators="team-oriented"),
            conscientiousness=DISCAnalysis.DISCAttribute(score=80, traits=["detail-oriented", "analytical"], behavioral_indicators="systematic"),
            primary_type="Conscientiousness",
            secondary_type="Dominance",
            summary="John is a detail-oriented and goal-driven individual.",
            strengths=["analytical skills", "goal-oriented"],
            potential_challenges=["overthinking", "perfectionism"],
            best_communication_style="Direct and clear",
            best_role_fit="Project Manager"
        )

        # Call the function with a mock LinkedIn profile
        linkedin_person = "Mock LinkedIn Profile Data"
        result = discGenerator(linkedin_person)

        # Assert the result
        self.assertIn("person", result)
        self.assertIsInstance(result["person"], DISCAnalysis)

if __name__ == '__main__':
    unittest.main()