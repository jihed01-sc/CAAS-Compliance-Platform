// Fixed countdown timer implementation
function updateCountdowns() {
    document.querySelectorAll('.countdown[data-deadline]').forEach(element => {
        const deadlineString = element.dataset.deadline;

        // Skip if no deadline is set
        if (!deadlineString || deadlineString === 'None' || deadlineString === '' || deadlineString === 'null') {
            element.textContent = 'No deadline';
            element.classList.remove('urgent');
            return;
        }

        try {
            // Parse the deadline - handle different formats
            let deadline;

            // Handle ISO format (2023-12-31T23:59:59) or Django isoformat
            if (deadlineString.includes('T')) {
                deadline = new Date(deadlineString);
            }
            // Handle Django default date format
            else {
                deadline = new Date(deadlineString);
            }

            // Check if date is valid
            if (isNaN(deadline.getTime())) {
                console.warn('Invalid deadline format:', deadlineString);
                element.textContent = 'Invalid date';
                return;
            }

            const now = new Date();
            const diff = deadline - now;

            if (diff > 0) {
                const totalMinutes = Math.floor(diff / (1000 * 60));
                const days = Math.floor(totalMinutes / (60 * 24));
                const hours = Math.floor((totalMinutes % (60 * 24)) / 60);
                const minutes = totalMinutes % 60;

                // Remove urgent class first
                element.classList.remove('urgent');

                // Add urgent class for items due within 7 days
                if (days < 7) {
                    element.classList.add('urgent');
                }

                // Format the countdown display based on time remaining
                if (days > 30) {
                    element.textContent = `${days} days remaining`;
                } else if (days > 0) {
                    element.textContent = `${days}d ${hours}h remaining`;
                } else if (hours > 0) {
                    element.textContent = `${hours}h ${minutes}m remaining`;
                } else if (minutes > 0) {
                    element.textContent = `${minutes} minutes remaining`;
                } else {
                    element.textContent = 'Due now';
                    element.classList.add('urgent');
                }
            } else {
                const overdueDays = Math.floor(Math.abs(diff) / (1000 * 60 * 60 * 24));
                if (overdueDays > 0) {
                    element.textContent = `Overdue by ${overdueDays} days`;
                } else {
                    element.textContent = 'Overdue';
                }
                element.classList.add('urgent');
            }
        } catch (error) {
            console.error('Error parsing deadline:', deadlineString, error);
            element.textContent = 'Date error';
        }
    });
}

// Initialize countdown functionality
function initializeCountdowns() {
    // Update countdowns immediately
    updateCountdowns();

    // Update countdowns every minute
    setInterval(updateCountdowns, 60000);

    // Log countdown elements for debugging
    const countdownElements = document.querySelectorAll('.countdown[data-deadline]');
    console.log(`Found ${countdownElements.length} countdown elements`);
    countdownElements.forEach((el, index) => {
        console.log(`Countdown ${index + 1}:`, el.dataset.deadline);
    });
}

// Wait for DOM to be ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeCountdowns);
} else {
    initializeCountdowns();
}

