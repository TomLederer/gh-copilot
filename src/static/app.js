document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const messageDiv = document.getElementById("message");

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("email").value;
    const activity = document.getElementById("activity").value;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup?email=${encodeURIComponent(email)}`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        // Refresh the activities list to show updated participants
        await fetchActivities();
        
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  fetchActivities();
});

// Function to fetch activities from API
async function fetchActivities() {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");

  try {
    const response = await fetch("/activities");
    const activities = await response.json();

    // Save the currently selected activity before clearing
    const selectedActivity = activitySelect.value;

    // Clear loading message and existing options
    activitiesList.innerHTML = "";
    
    // Clear existing activity options (keep the default option)
    activitySelect.innerHTML = "";
    const defaultOption = document.createElement("option");
    defaultOption.value = "";
    defaultOption.textContent = "-- Select an activity --";
    activitySelect.appendChild(defaultOption);

    // Populate activities list
    Object.entries(activities).forEach(([name, details]) => {
      const activityCard = document.createElement("div");
      activityCard.className = "activity-card";

      const spotsLeft = details.max_participants - details.participants.length;

      activityCard.innerHTML = `
        <h4>${name}</h4>
        <p>${details.description}</p>
        <p><strong>Schedule:</strong> ${details.schedule}</p>
        <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
        <div class="participants-section">
          <h5>Current Participants:</h5>
          ${details.participants.length > 0 
            ? `<ul class="participants-list">
                 ${details.participants.map(participant => `
                   <li>
                     <span class="participant-email">${participant}</span>
                     <button class="delete-icon" onclick="unregisterParticipant('${name}', '${participant}')" title="Remove participant">×</button>
                   </li>
                 `).join('')}
               </ul>`
            : '<p class="no-participants">No participants yet</p>'
          }
        </div>
      `;

      activitiesList.appendChild(activityCard);

      // Add option to select dropdown
      const option = document.createElement("option");
      option.value = name;
      option.textContent = name;
      activitySelect.appendChild(option);
    });

    // Restore the previously selected activity if it still exists
    if (selectedActivity && activities[selectedActivity]) {
      activitySelect.value = selectedActivity;
    }
  } catch (error) {
    activitiesList.innerHTML = "<p>Failed to load activities. Please try again later.</p>";
    console.error("Error fetching activities:", error);
  }
}

// Global function to unregister a participant
async function unregisterParticipant(activityName, participantEmail) {
  if (!confirm(`Are you sure you want to remove ${participantEmail} from ${activityName}?`)) {
    return;
  }

  try {
    const response = await fetch(
      `/activities/${encodeURIComponent(activityName)}/unregister?email=${encodeURIComponent(participantEmail)}`,
      {
        method: "DELETE",
      }
    );

    const result = await response.json();
    const messageDiv = document.getElementById("message");

    if (response.ok) {
      // Refresh the activities list to show updated participants
      await fetchActivities();

      // Show success message
      messageDiv.textContent = result.message;
      messageDiv.className = "success";
      messageDiv.classList.remove("hidden");

      // Hide message after 3 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 3000);

    } else {
      // Show error message
      messageDiv.textContent = result.detail || "Failed to unregister participant";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    }
  } catch (error) {
    console.error("Error unregistering participant:", error);
    
    // Show error message
    const messageDiv = document.getElementById("message");
    messageDiv.textContent = "Failed to unregister participant. Please try again.";
    messageDiv.className = "error";
    messageDiv.classList.remove("hidden");

    // Hide message after 5 seconds
    setTimeout(() => {
      messageDiv.classList.add("hidden");
    }, 5000);
  }
}
