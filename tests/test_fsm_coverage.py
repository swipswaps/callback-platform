"""
FSM transition coverage tests - exhaustive testing of all state transitions.

These tests ensure:
1. Every allowed transition works correctly
2. Every disallowed transition fails immediately
3. No silent transition gaps exist
4. No untested paths remain

If FSM behavior changes, these tests will catch it.
"""

import pytest
import sys
import os

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app import AppState, ALLOWED_TRANSITIONS, transition_to, current_state


class TestAllowedTransitions:
    """Test that all allowed transitions work correctly"""

    def test_all_allowed_transitions_succeed(self):
        """Every transition in ALLOWED_TRANSITIONS must work"""
        for source_state, allowed_targets in ALLOWED_TRANSITIONS.items():
            for target_state in allowed_targets:
                # Create a mock scenario where we're in source_state
                # Note: This test verifies the FSM logic, not the global state
                import app
                original_state = app.current_state
                
                try:
                    # Set up the source state
                    app.current_state = source_state
                    
                    # Attempt the transition
                    transition_to(target_state)
                    
                    # Verify we ended up in the target state
                    assert app.current_state == target_state, \
                        f"Transition {source_state} → {target_state} failed: " \
                        f"ended in {app.current_state}"
                
                finally:
                    # Restore original state
                    app.current_state = original_state


class TestDisallowedTransitions:
    """Test that all disallowed transitions fail immediately"""

    def test_all_disallowed_transitions_fail(self):
        """Every transition NOT in ALLOWED_TRANSITIONS must raise RuntimeError"""
        all_states = set(AppState)

        for source_state, allowed_targets in ALLOWED_TRANSITIONS.items():
            # Calculate disallowed targets: all states except allowed ones and self
            disallowed_targets = all_states - allowed_targets - {source_state}

            for target_state in disallowed_targets:
                # Create a mock scenario where we're in source_state
                import app
                original_state = app.current_state

                try:
                    # Set up the source state
                    app.current_state = source_state

                    # Attempt the disallowed transition - must raise RuntimeError
                    with pytest.raises(RuntimeError, match="Invalid state transition"):
                        transition_to(target_state)

                    # Verify state didn't change
                    assert app.current_state == source_state, \
                        f"Disallowed transition {source_state} → {target_state} " \
                        f"should not change state"

                finally:
                    # Restore original state
                    app.current_state = original_state


class TestTransitionCoverage:
    """Test that FSM coverage is complete"""

    def test_every_state_has_at_least_one_outgoing_transition_or_is_terminal(self):
        """Every state must either have outgoing transitions or be explicitly terminal"""
        for state in AppState:
            allowed = ALLOWED_TRANSITIONS[state]
            
            # SHUTTING_DOWN is the only terminal state
            if state == AppState.SHUTTING_DOWN:
                assert len(allowed) == 0, \
                    f"Terminal state {state} must have no outgoing transitions"
            else:
                assert len(allowed) > 0, \
                    f"Non-terminal state {state} must have at least one outgoing transition"

    def test_every_non_starting_state_is_reachable(self):
        """Every state (except STARTING) must be reachable from some other state"""
        reachable_states = set()
        
        for source_state, allowed_targets in ALLOWED_TRANSITIONS.items():
            reachable_states.update(allowed_targets)
        
        # All states except STARTING should be reachable
        for state in AppState:
            if state != AppState.STARTING:
                assert state in reachable_states, \
                    f"State {state} is not reachable from any other state"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

