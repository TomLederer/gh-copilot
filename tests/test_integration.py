"""
Integration tests for the complete application workflow
"""
import pytest
from fastapi.testclient import TestClient


class TestApplicationWorkflow:
    """Test complete user workflows"""

    def test_complete_signup_workflow(self, client: TestClient):
        """Test the complete signup and unregister workflow"""
        email = "workflow@mergington.edu"
        activity = "Drama Society"
        
        # Step 1: Get initial activities
        initial_response = client.get("/activities")
        initial_activities = initial_response.json()
        initial_participants = initial_activities[activity]["participants"].copy()
        
        # Step 2: Sign up for activity
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Step 3: Verify signup
        after_signup_response = client.get("/activities")
        after_signup_activities = after_signup_response.json()
        assert email in after_signup_activities[activity]["participants"]
        assert len(after_signup_activities[activity]["participants"]) == len(initial_participants) + 1
        
        # Step 4: Unregister from activity
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Step 5: Verify unregistration
        final_response = client.get("/activities")
        final_activities = final_response.json()
        assert email not in final_activities[activity]["participants"]
        assert len(final_activities[activity]["participants"]) == len(initial_participants)

    def test_multiple_activities_signup(self, client: TestClient):
        """Test signing up for multiple activities"""
        email = "multi@mergington.edu"
        activities = ["Art Club", "Math Olympiad", "Debate Club"]
        
        # Sign up for multiple activities
        for activity in activities:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify user is in all activities
        activities_response = client.get("/activities")
        all_activities = activities_response.json()
        
        for activity in activities:
            assert email in all_activities[activity]["participants"]

    def test_error_handling_chain(self, client: TestClient):
        """Test various error conditions in sequence"""
        email = "error_test@mergington.edu"
        
        # 1. Try to unregister from activity without being registered
        unregister_response = client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        assert unregister_response.status_code == 400
        
        # 2. Try to sign up for non-existent activity
        nonexistent_response = client.post(f"/activities/Fake%20Activity/signup?email={email}")
        assert nonexistent_response.status_code == 404
        
        # 3. Sign up successfully
        signup_response = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert signup_response.status_code == 200
        
        # 4. Try to sign up again (duplicate)
        duplicate_response = client.post(f"/activities/Chess%20Club/signup?email={email}")
        assert duplicate_response.status_code == 400
        
        # 5. Unregister successfully
        final_unregister = client.delete(f"/activities/Chess%20Club/unregister?email={email}")
        assert final_unregister.status_code == 200


class TestDataConsistency:
    """Test data consistency across operations"""

    def test_participant_count_consistency(self, client: TestClient):
        """Test that participant counts remain consistent"""
        # Get initial state
        initial_response = client.get("/activities")
        initial_activities = initial_response.json()
        
        # Record initial counts
        initial_counts = {
            name: len(data["participants"]) 
            for name, data in initial_activities.items()
        }
        
        # Perform several operations
        test_email = "consistency@mergington.edu"
        
        # Sign up for multiple activities
        test_activities = list(initial_activities.keys())[:3]
        for activity in test_activities:
            client.post(f"/activities/{activity}/signup?email={test_email}")
        
        # Check counts increased correctly
        after_signup_response = client.get("/activities")
        after_signup_activities = after_signup_response.json()
        
        for activity in test_activities:
            expected_count = initial_counts[activity] + 1
            actual_count = len(after_signup_activities[activity]["participants"])
            assert actual_count == expected_count
        
        # Unregister from all
        for activity in test_activities:
            client.delete(f"/activities/{activity}/unregister?email={test_email}")
        
        # Check counts returned to original
        final_response = client.get("/activities")
        final_activities = final_response.json()
        
        for activity in test_activities:
            expected_count = initial_counts[activity]
            actual_count = len(final_activities[activity]["participants"])
            assert actual_count == expected_count

    def test_activities_structure_integrity(self, client: TestClient):
        """Test that activities maintain their structure after operations"""
        # Get initial structure
        response = client.get("/activities")
        activities = response.json()
        
        # Verify all activities have required structure
        required_fields = ["description", "schedule", "max_participants", "participants"]
        
        for activity_name, activity_data in activities.items():
            assert isinstance(activity_name, str)
            assert len(activity_name) > 0
            
            for field in required_fields:
                assert field in activity_data
            
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)
            assert activity_data["max_participants"] > 0
        
        # Perform some operations
        test_email = "structure@mergington.edu"
        activity_name = list(activities.keys())[0]
        
        client.post(f"/activities/{activity_name}/signup?email={test_email}")
        client.delete(f"/activities/{activity_name}/unregister?email={test_email}")
        
        # Verify structure is still intact
        final_response = client.get("/activities")
        final_activities = final_response.json()
        
        for activity_name, activity_data in final_activities.items():
            for field in required_fields:
                assert field in activity_data
            
            assert isinstance(activity_data["description"], str)
            assert isinstance(activity_data["schedule"], str)  
            assert isinstance(activity_data["max_participants"], int)
            assert isinstance(activity_data["participants"], list)
            assert activity_data["max_participants"] > 0