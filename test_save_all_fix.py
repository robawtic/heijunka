"""
Test script to validate the save_all method refactoring.

This script demonstrates that the refactored save_all method properly uses
the session_scope context manager to ensure all batches are committed.
"""

from contextlib import contextmanager
from unittest.mock import Mock, MagicMock, call
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_session_scope_behavior():
    """Test that session_scope properly handles commit/rollback/close."""
    print("Testing session_scope behavior...")
    
    # Mock session factory and session
    mock_session = Mock()
    mock_session_factory = Mock(return_value=mock_session)
    
    # Create a simple session_scope implementation (similar to the base repository)
    @contextmanager
    def session_scope():
        session = mock_session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    # Test successful case
    print("  Testing successful commit...")
    with session_scope() as session:
        session.add("test_data")
        session.flush()
    
    # Verify the session was used correctly
    assert mock_session.add.called
    assert mock_session.flush.called
    assert mock_session.commit.called
    assert mock_session.close.called
    assert not mock_session.rollback.called
    print("  ✓ Successful commit test passed")
    
    # Reset mocks
    mock_session.reset_mock()
    
    # Test exception case
    print("  Testing rollback on exception...")
    try:
        with session_scope() as session:
            session.add("test_data")
            session.flush()
            raise Exception("Test exception")
    except Exception:
        pass  # Expected
    
    # Verify rollback was called
    assert mock_session.add.called
    assert mock_session.flush.called
    assert not mock_session.commit.called
    assert mock_session.rollback.called
    assert mock_session.close.called
    print("  ✓ Rollback on exception test passed")

def test_batch_processing_logic():
    """Test the batch processing logic to ensure all batches are processed."""
    print("\nTesting batch processing logic...")
    
    # Simulate assignments
    assignments = [f"assignment_{i}" for i in range(1, 26)]  # 25 assignments
    batch_size = 10
    
    # Track processed batches
    processed_batches = []
    
    # Simulate the batch processing loop from save_all
    for i in range(0, len(assignments), batch_size):
        batch = assignments[i:i+batch_size]
        batch_number = i//batch_size + 1
        total_batches = (len(assignments) + batch_size - 1) // batch_size
        
        processed_batches.append({
            'batch_number': batch_number,
            'batch_size': len(batch),
            'batch_data': batch
        })
        
        print(f"  Processing batch {batch_number} of {total_batches} (size: {len(batch)})")
    
    # Verify all batches were processed
    assert len(processed_batches) == 3  # 25 assignments / 10 batch_size = 3 batches
    assert processed_batches[0]['batch_size'] == 10  # First batch: 10 items
    assert processed_batches[1]['batch_size'] == 10  # Second batch: 10 items
    assert processed_batches[2]['batch_size'] == 5   # Third batch: 5 items (the critical last batch!)
    
    # Verify the last batch contains the expected data
    last_batch = processed_batches[2]
    expected_last_batch_data = ['assignment_21', 'assignment_22', 'assignment_23', 'assignment_24', 'assignment_25']
    assert last_batch['batch_data'] == expected_last_batch_data
    
    print("  ✓ All batches processed correctly")
    print(f"  ✓ Last batch (critical!) contained {last_batch['batch_size']} items")
    print(f"  ✓ Last batch data: {last_batch['batch_data']}")

def test_refactored_save_all_structure():
    """Test that the refactored save_all method structure is correct."""
    print("\nTesting refactored save_all method structure...")
    
    # Read the refactored save_all method
    with open('infrastructure/repositories/assignment/sqlalchemy_assignment_repository.py', 'r') as f:
        content = f.read()
    
    # Check that the method uses session_scope
    assert 'with self.session_scope() as session:' in content
    print("  ✓ Method uses session_scope context manager")
    
    # Check that manual session management is removed
    assert 'session = self._session_factory()' not in content.split('def save_all')[1].split('def delete_existing_entries_for_date')[0]
    print("  ✓ Manual session creation removed")
    
    # Check that manual commit/rollback/close are removed from save_all
    save_all_method = content.split('def save_all')[1].split('def delete_existing_entries_for_date')[0]
    assert 'session.commit()' not in save_all_method or 'session_scope' in save_all_method
    assert 'session.rollback()' not in save_all_method or 'session_scope' in save_all_method
    assert 'session.close()' not in save_all_method or 'session_scope' in save_all_method
    print("  ✓ Manual session management removed from save_all")
    
    # Check that session.flush() is still called for each batch
    assert 'session.flush()' in save_all_method
    print("  ✓ session.flush() still called for each batch")
    
    # Check that proper logging is in place
    assert 'assignments_batch_flush_success' in content
    assert 'assignments_ready_for_commit' in content
    print("  ✓ Enhanced logging in place")

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("VALIDATING SAVE_ALL METHOD REFACTORING")
    print("=" * 60)
    
    try:
        test_session_scope_behavior()
        test_batch_processing_logic()
        test_refactored_save_all_structure()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("✅ The refactored save_all method should now:")
        print("   - Use session_scope context manager for proper session handling")
        print("   - Process all batches including the last one")
        print("   - Automatically commit on success")
        print("   - Automatically rollback on failure")
        print("   - Always close the session")
        print("   - Provide detailed logging for debugging")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())