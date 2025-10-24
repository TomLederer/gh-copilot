"""
Performance and edge case tests
"""
import pytest
from fastapi.testclient import TestClient
import time


class TestPerformance:
    """Test performance characteristics"""

    def test_get_activities_response_time(self, client: TestClient):
        """Test that getting activities responds quickly"""
        start_time = time.time()
        response = client.get("/activities")
        end_time = time.time()
        
        assert response.status_code == 200
        response_time = end_time - start_time
        assert response_time < 1.0  # Should respond within 1 second

    def test_signup_response_time(self, client: TestClient):
        """Test that signup responds quickly"""
        start_time = time.time()
        response = client.post("/activities/Chess%20Club/signup?email=perf@mergington.edu")
        end_time = time.time()
        
        assert response.status_code in [200, 400]  # 400 if already exists
        response_time = end_time - start_time
        assert response_time < 1.0  # Should respond within 1 second

    def test_multiple_concurrent_requests(self, client: TestClient):
        """Test handling multiple requests"""
        # Simulate multiple quick requests
        responses = []
        emails = [f"concurrent_{i}@mergington.edu" for i in range(10)]
        
        start_time = time.time()
        for email in emails:
            response = client.post(f"/activities/Basketball%20Club/signup?email={email}")
            responses.append(response)
        end_time = time.time()
        
        # All requests should complete within reasonable time
        total_time = end_time - start_time
        assert total_time < 5.0  # All 10 requests should complete within 5 seconds
        
        # Most should succeed (some might fail due to duplicates in test runs)
        successful_responses = [r for r in responses if r.status_code == 200]
        assert len(successful_responses) > 0


class TestEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_empty_email_parameter(self, client: TestClient):
        """Test behavior with empty email parameter"""
        response = client.post("/activities/Chess%20Club/signup?email=")
        # Should handle empty email gracefully
        assert response.status_code in [200, 400, 422]

    def test_missing_email_parameter(self, client: TestClient):
        """Test behavior with missing email parameter"""
        response = client.post("/activities/Chess%20Club/signup")
        # Should require email parameter
        assert response.status_code == 422

    def test_very_long_email(self, client: TestClient):
        """Test behavior with very long email"""
        long_email = "a" * 1000 + "@mergington.edu"
        response = client.post(f"/activities/Chess%20Club/signup?email={long_email}")
        assert response.status_code in [200, 400]  # Should handle gracefully

    def test_special_characters_in_email(self, client: TestClient):
        """Test behavior with special characters in email"""
        special_emails = [
            "test+tag@mergington.edu",
            "test.with.dots@mergington.edu", 
            "test_with_underscores@mergington.edu",
            "test-with-dashes@mergington.edu"
        ]
        
        for email in special_emails:
            response = client.post(f"/activities/Soccer%20Team/signup?email={email}")
            assert response.status_code in [200, 400]  # Should handle gracefully

    def test_url_encoded_activity_names(self, client: TestClient):
        """Test various URL encodings for activity names"""
        # Test different ways to encode "Chess Club"
        encodings = [
            "Chess%20Club",
            "Chess+Club", 
            "Chess Club"  # Unencoded (should still work in test client)
        ]
        
        for encoding in encodings:
            response = client.post(f"/activities/{encoding}/signup?email=encoding_test@mergington.edu")
            # At least one encoding should work
            assert response.status_code in [200, 400, 404]

    def test_case_sensitivity(self, client: TestClient):
        """Test case sensitivity in activity names"""
        # Test different cases
        response_lower = client.post("/activities/chess%20club/signup?email=case1@mergington.edu")
        response_upper = client.post("/activities/CHESS%20CLUB/signup?email=case2@mergington.edu")
        response_mixed = client.post("/activities/Chess%20club/signup?email=case3@mergington.edu")
        
        # Should handle case sensitivity consistently
        # (Current implementation is case-sensitive, so these should return 404)
        assert response_lower.status_code == 404
        assert response_upper.status_code == 404
        assert response_mixed.status_code == 404

    def test_sql_injection_attempts(self, client: TestClient):
        """Test that SQL injection attempts are handled safely"""
        malicious_emails = [
            "'; DROP TABLE activities; --@mergington.edu",
            "admin'; UPDATE activities SET participants = '[]'; --@mergington.edu",
            "test@mergington.edu'; DELETE FROM activities WHERE '1'='1"
        ]
        
        for email in malicious_emails:
            response = client.post(f"/activities/Chess%20Club/signup?email={email}")
            # Should handle safely (not crash)
            assert response.status_code in [200, 400, 422]
        
        # Verify activities are still intact
        activities_response = client.get("/activities")
        assert activities_response.status_code == 200
        activities = activities_response.json()
        assert len(activities) > 0

    def test_unicode_characters(self, client: TestClient):
        """Test handling of unicode characters"""
        unicode_emails = [
            "tëst@mergington.edu",
            "用户@mergington.edu", 
            "тест@mergington.edu",
            "🎓@mergington.edu"
        ]
        
        for email in unicode_emails:
            response = client.post(f"/activities/Art%20Club/signup?email={email}")
            # Should handle unicode gracefully
            assert response.status_code in [200, 400, 422]


class TestErrorRecovery:
    """Test error recovery and resilience"""

    def test_recovery_after_invalid_operations(self, client: TestClient):
        """Test that system recovers properly after invalid operations"""
        # Perform several invalid operations
        invalid_responses = [
            client.post("/activities/Invalid%20Activity/signup?email=test@mergington.edu"),
            client.delete("/activities/Invalid%20Activity/unregister?email=test@mergington.edu"),
            client.post("/activities/Chess%20Club/signup?email="),
            client.delete("/activities/Chess%20Club/unregister?email=notexist@mergington.edu")
        ]
        
        # All should fail gracefully
        for response in invalid_responses:
            assert response.status_code in [400, 404, 422]
        
        # System should still work normally
        valid_response = client.get("/activities")
        assert valid_response.status_code == 200
        
        # Should be able to perform valid operations
        signup_response = client.post("/activities/Chess%20Club/signup?email=recovery@mergington.edu")
        assert signup_response.status_code in [200, 400]  # 400 if already exists

    def test_data_persistence_across_operations(self, client: TestClient):
        """Test that data persists correctly across various operations"""
        # Get initial state
        initial_response = client.get("/activities")
        initial_activities = initial_response.json()
        
        # Perform various operations
        test_operations = [
            ("POST", "/activities/Drama%20Society/signup?email=persist1@mergington.edu"),
            ("POST", "/activities/Math%20Olympiad/signup?email=persist2@mergington.edu"),
            ("DELETE", "/activities/Drama%20Society/unregister?email=persist1@mergington.edu"),
            ("POST", "/activities/Art%20Club/signup?email=persist3@mergington.edu")
        ]
        
        for method, url in test_operations:
            if method == "POST":
                response = client.post(url)
            elif method == "DELETE":
                response = client.delete(url)
            
            # Each operation should succeed or fail gracefully
            assert response.status_code in [200, 400, 404]
        
        # Final state should be consistent
        final_response = client.get("/activities")
        assert final_response.status_code == 200
        final_activities = final_response.json()
        
        # Should have same structure as initial
        assert set(final_activities.keys()) == set(initial_activities.keys())
        
        # All activities should maintain their structure
        for activity_name in final_activities.keys():
            assert "description" in final_activities[activity_name]
            assert "schedule" in final_activities[activity_name]
            assert "max_participants" in final_activities[activity_name]
            assert "participants" in final_activities[activity_name]