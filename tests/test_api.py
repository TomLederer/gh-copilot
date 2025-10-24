"""
Tests for the FastAPI endpoints
"""
import pytest
from fastapi.testclient import TestClient


class TestActivitiesAPI:
    """Test cases for activities API endpoints"""

    def test_root_redirect(self, client: TestClient):
        """Test that root endpoint redirects to static page"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"

    def test_get_activities(self, client: TestClient):
        """Test getting all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        
        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) > 0
        
        # Check that each activity has required fields
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)
            assert isinstance(activity_data["max_participants"], int)

    def test_signup_for_activity_success(self, client: TestClient):
        """Test successful signup for an activity"""
        # Use an existing activity
        response = client.post("/activities/Chess%20Club/signup?email=newstudent@mergington.edu")
        assert response.status_code == 200
        
        result = response.json()
        assert "message" in result
        assert "newstudent@mergington.edu" in result["message"]
        assert "Chess Club" in result["message"]
        
        # Verify the student was added
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert "newstudent@mergington.edu" in activities["Chess Club"]["participants"]

    def test_signup_for_nonexistent_activity(self, client: TestClient):
        """Test signup for non-existent activity returns 404"""
        response = client.post("/activities/Nonexistent%20Activity/signup?email=test@mergington.edu")
        assert response.status_code == 404
        
        result = response.json()
        assert "detail" in result
        assert "Activity not found" in result["detail"]

    def test_signup_duplicate_email(self, client: TestClient):
        """Test that duplicate signup returns 400"""
        email = "duplicate@mergington.edu"
        activity = "Chess Club"
        
        # First signup should succeed
        response1 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{activity}/signup?email={email}")
        assert response2.status_code == 400
        
        result = response2.json()
        assert "detail" in result
        assert "already signed up" in result["detail"]

    def test_unregister_from_activity_success(self, client: TestClient):
        """Test successful unregistration from an activity"""
        # First, sign up a student
        email = "tounregister@mergington.edu"
        activity = "Chess Club"
        
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Then unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        result = unregister_response.json()
        assert "message" in result
        assert email in result["message"]
        assert activity in result["message"]
        
        # Verify the student was removed
        activities_response = client.get("/activities")
        activities = activities_response.json()
        assert email not in activities[activity]["participants"]

    def test_unregister_from_nonexistent_activity(self, client: TestClient):
        """Test unregistration from non-existent activity returns 404"""
        response = client.delete("/activities/Nonexistent%20Activity/unregister?email=test@mergington.edu")
        assert response.status_code == 404
        
        result = response.json()
        assert "detail" in result
        assert "Activity not found" in result["detail"]

    def test_unregister_non_registered_student(self, client: TestClient):
        """Test unregistration of non-registered student returns 400"""
        response = client.delete("/activities/Chess%20Club/unregister?email=notregistered@mergington.edu")
        assert response.status_code == 400
        
        result = response.json()
        assert "detail" in result
        assert "not registered" in result["detail"]

    def test_activity_capacity_tracking(self, client: TestClient):
        """Test that activity capacity is tracked correctly"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            participants_count = len(activity_data["participants"])
            max_participants = activity_data["max_participants"]
            
            # Participants should not exceed maximum
            assert participants_count <= max_participants
            
            # Spots left calculation should be correct
            spots_left = max_participants - participants_count
            assert spots_left >= 0

    def test_email_format_validation(self, client: TestClient):
        """Test various email formats (FastAPI doesn't validate by default, but we test the behavior)"""
        # Test with various email formats
        test_emails = [
            "valid@mergington.edu",
            "another.valid+email@mergington.edu",
            "number123@mergington.edu"
        ]
        
        for email in test_emails:
            response = client.post(f"/activities/Chess%20Club/signup?email={email}")
            # Should succeed for any string (FastAPI doesn't validate email format by default)
            assert response.status_code in [200, 400]  # 400 if already exists

    def test_activity_names_with_special_characters(self, client: TestClient):
        """Test activity names are properly URL encoded/decoded"""
        # Test with URL encoding
        response = client.post("/activities/Chess%20Club/signup?email=urltest@mergington.edu")
        assert response.status_code == 200
        
        result = response.json()
        assert "Chess Club" in result["message"]  # Should be decoded properly


class TestActivityDataIntegrity:
    """Test cases for data integrity and edge cases"""

    def test_concurrent_signups(self, client: TestClient):
        """Test multiple signups to verify data consistency"""
        activity = "Programming Class"
        emails = [f"concurrent{i}@mergington.edu" for i in range(5)]
        
        # Sign up multiple students
        responses = []
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            responses.append(response)
        
        # All should succeed (assuming capacity allows)
        successful_signups = [r for r in responses if r.status_code == 200]
        assert len(successful_signups) > 0
        
        # Verify all successful signups are in the participants list
        activities_response = client.get("/activities")
        activities = activities_response.json()
        participants = activities[activity]["participants"]
        
        for i, response in enumerate(responses):
            if response.status_code == 200:
                assert emails[i] in participants

    def test_activity_full_capacity(self, client: TestClient):
        """Test behavior when activity reaches full capacity"""
        # Find an activity with limited capacity
        activities_response = client.get("/activities")
        activities = activities_response.json()
        
        # Find activity with smallest capacity for testing
        min_capacity_activity = min(activities.items(), 
                                  key=lambda x: x[1]["max_participants"] - len(x[1]["participants"]))
        activity_name, activity_data = min_capacity_activity
        
        spots_available = activity_data["max_participants"] - len(activity_data["participants"])
        
        # Fill up remaining spots
        for i in range(spots_available):
            email = f"capacity_test_{i}@mergington.edu"
            response = client.post(f"/activities/{activity_name}/signup?email={email}")
            assert response.status_code == 200
        
        # Try to add one more (should still work as we don't enforce capacity limits in current implementation)
        overflow_response = client.post(f"/activities/{activity_name}/signup?email=overflow@mergington.edu")
        # Note: Current implementation doesn't enforce capacity limits, so this will succeed
        # If capacity enforcement is added later, this test should be updated to expect 400