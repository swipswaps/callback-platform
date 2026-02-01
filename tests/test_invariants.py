"""
CI-level invariant tests to prevent UX regressions.

These tests enforce that UX invariants are never violated, even as the codebase evolves.
If any invariant breaks, CI will fail and prevent merge.
"""

import pytest
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import AppState, current_state, last_action, ALLOWED_TRANSITIONS


class TestGlobalInvariants:
    """Test that global UX invariants are always true"""

    def test_current_state_is_always_defined(self):
        """State must always be defined - never None or undefined"""
        assert current_state is not None, "UX invariant violated: State must always be defined"

    def test_current_state_is_valid_app_state(self):
        """State must always be a valid AppState enum value"""
        assert isinstance(current_state, AppState), \
            f"UX invariant violated: current_state must be AppState, got {type(current_state)}"
        assert current_state in AppState, \
            f"UX invariant violated: Invalid state {current_state}"

    def test_last_action_is_always_string(self):
        """last_action must always be a string for error context"""
        assert isinstance(last_action, str), \
            f"UX invariant violated: last_action must be string, got {type(last_action)}"
        assert len(last_action) > 0, \
            "UX invariant violated: last_action must not be empty"


class TestFSMInvariants:
    """Test that FSM transition table is correctly defined"""

    def test_all_states_have_transition_rules(self):
        """Every AppState must have an entry in ALLOWED_TRANSITIONS"""
        for state in AppState:
            assert state in ALLOWED_TRANSITIONS, \
                f"FSM invariant violated: {state} missing from ALLOWED_TRANSITIONS"

    def test_terminal_state_has_no_transitions(self):
        """SHUTTING_DOWN is terminal - must have no outgoing transitions"""
        assert ALLOWED_TRANSITIONS[AppState.SHUTTING_DOWN] == set(), \
            "FSM invariant violated: SHUTTING_DOWN must be terminal (no transitions)"

    def test_all_transitions_point_to_valid_states(self):
        """All transition targets must be valid AppState values"""
        for state, allowed in ALLOWED_TRANSITIONS.items():
            for target in allowed:
                assert target in AppState, \
                    f"FSM invariant violated: {state} → {target} (invalid target)"

    def test_no_self_transitions(self):
        """States should not transition to themselves (use idempotent operations instead)"""
        for state, allowed in ALLOWED_TRANSITIONS.items():
            assert state not in allowed, \
                f"FSM invariant violated: {state} → {state} (self-transition not allowed)"


class TestErrorTierInvariants:
    """Test that error tier model is correctly implemented"""

    def test_error_tiers_are_exhaustive(self):
        """All error tiers must be defined"""
        from app import ErrorTier
        
        expected_tiers = {'user', 'system', 'operator'}
        actual_tiers = {tier.value for tier in ErrorTier}
        
        assert actual_tiers == expected_tiers, \
            f"Error tier invariant violated: Expected {expected_tiers}, got {actual_tiers}"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

