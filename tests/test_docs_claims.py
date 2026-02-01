"""
Documentation accuracy tests - prevent overstated claims.

These tests ensure that documentation does not make claims that
cannot be guaranteed by the code alone.

Overstated claims erode trust and create false expectations.
This test makes overstatement a failing test.
"""

import pytest
import os


class TestDocumentationAccuracy:
    """Test that documentation claims match actual guarantees"""

    def test_readme_does_not_claim_structural_impossibility(self):
        """
        README must not claim things are "structurally impossible"
        unless tests, CI, and review gates enforce it.
        
        Accurate claim: "prevented by default and detected immediately"
        Overstated claim: "structurally impossible"
        """
        readme_path = os.path.join(
            os.path.dirname(__file__), '..', 'README.md'
        )
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            text = f.read().lower()

        forbidden_phrases = [
            'structurally impossible',
            'cannot happen under any circumstance',
            'impossible to violate',
            'guaranteed to never',
        ]

        for phrase in forbidden_phrases:
            assert phrase not in text, \
                f"Documentation overstates guarantee: '{phrase}' found in README.md. " \
                f"Use 'prevented by default and detected immediately' instead."

    def test_readme_does_not_claim_absolute_prevention(self):
        """
        README must not claim absolute prevention without enforcement.
        
        Accurate: "violations are prevented by default"
        Overstated: "violations are impossible"
        """
        readme_path = os.path.join(
            os.path.dirname(__file__), '..', 'README.md'
        )
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            text = f.read().lower()

        # These phrases are too absolute without CI/test enforcement
        risky_phrases = [
            'will never fail',
            'cannot fail',
            'always succeeds',
            'guaranteed success',
        ]

        for phrase in risky_phrases:
            assert phrase not in text, \
                f"Documentation makes absolute claim: '{phrase}' found in README.md. " \
                f"Use 'designed to prevent' or 'enforced by' instead."

    def test_commit_messages_do_not_overstate(self):
        """
        Recent commit messages should not overstate achievements.
        
        This is a softer check - we only check the most recent commit.
        """
        import subprocess
        
        try:
            # Get the most recent commit message
            result = subprocess.run(
                ['git', 'log', '-1', '--pretty=%B'],
                capture_output=True,
                text=True,
                cwd=os.path.dirname(__file__) + '/..'
            )
            
            if result.returncode == 0:
                commit_msg = result.stdout.lower()
                
                forbidden_in_commits = [
                    'structurally impossible',
                    'impossible to',
                    'cannot happen',
                ]
                
                for phrase in forbidden_in_commits:
                    assert phrase not in commit_msg, \
                        f"Commit message overstates: '{phrase}' found. " \
                        f"Use 'prevented by default' instead."
        
        except FileNotFoundError:
            # Git not available - skip this test
            pytest.skip("Git not available")


class TestDocumentationCompleteness:
    """Test that documentation is complete and accurate"""

    def test_readme_documents_all_app_states(self):
        """README must document all AppState values"""
        readme_path = os.path.join(
            os.path.dirname(__file__), '..', 'README.md'
        )
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_text = f.read().lower()

        # Expected backend states
        backend_states = [
            'starting',
            'ready',
            'busy',
            'degraded',
            'shutting_down',
        ]

        for state in backend_states:
            assert state in readme_text, \
                f"README.md must document backend state: {state}"

    def test_readme_documents_all_error_tiers(self):
        """README must document all ErrorTier values"""
        readme_path = os.path.join(
            os.path.dirname(__file__), '..', 'README.md'
        )
        
        with open(readme_path, 'r', encoding='utf-8') as f:
            readme_text = f.read().lower()

        # Expected error tiers
        error_tiers = ['user', 'system', 'operator']

        for tier in error_tiers:
            # Check if tier is mentioned in error context
            assert tier in readme_text, \
                f"README.md must document error tier: {tier}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

