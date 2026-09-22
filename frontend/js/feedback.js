// ============================================
// Give Feedback Page Logic - SkillX
// ============================================

let currentStudent = null;
let selectedRating = 0;

const ratingLabels = {
    1: '1/5 - Needs Improvement 😞',
    2: '2/5 - Below Average 😐',
    3: '3/5 - Average 🙂',
    4: '4/5 - Good 😊',
    5: '5/5 - Excellent! 🔥'
};

document.addEventListener('DOMContentLoaded', async () => {
    requireAuth();
    renderNavUser();

    currentStudent = getCurrentStudent();
    if (!currentStudent) return;

    setupStarRating();
    await loadMyFeedback();
});

// Interactive Star Rating Widget
function setupStarRating() {
    const stars = document.querySelectorAll('.star-rating .star');
    const label = document.getElementById('rating-text');

    stars.forEach(star => {
        const val = parseInt(star.dataset.value, 10);

        star.addEventListener('mouseenter', () => {
            highlightStars(val);
            if (label) label.textContent = ratingLabels[val] || '';
        });

        star.addEventListener('mouseleave', () => {
            highlightStars(selectedRating);
            if (label) label.textContent = selectedRating ? ratingLabels[selectedRating] : 'Click to rate (1–5 stars)';
        });

        star.addEventListener('click', () => {
            selectedRating = val;
            highlightStars(selectedRating);
            if (label) label.textContent = ratingLabels[selectedRating];
        });
    });
}

function highlightStars(count) {
    const stars = document.querySelectorAll('.star-rating .star');
    stars.forEach(s => {
        const val = parseInt(s.dataset.value, 10);
        s.classList.toggle('selected', val <= count);
    });
}

// Submit Feedback Handler
async function handleSubmitFeedback(e) {
    e.preventDefault();
    const alertBox = document.getElementById('feedback-form-alert');
    const categorySelect = document.getElementById('feedback-category');
    const messageText = document.getElementById('feedback-message');
    const allowContactCheck = document.getElementById('feedback-contact');

    const category = categorySelect.value;
    const message = messageText.value.trim();
    const allowContact = allowContactCheck ? allowContactCheck.checked : false;

    if (!selectedRating || selectedRating < 1 || selectedRating > 5) {
        showAlert(alertBox, 'Please select a star rating (1–5 stars).', 'error');
        return;
    }

    if (!category || !message) {
        showAlert(alertBox, 'Please select a category and enter your feedback message.', 'error');
        return;
    }

    // Uses authenticated student ID
    const res = await Feedback.create(selectedRating, category, message, allowContact, currentStudent.id);
    if (res.ok) {
        showAlert(alertBox, 'Thank you! Your feedback has been submitted successfully.', 'success');

        // Reset form
        selectedRating = 0;
        highlightStars(0);
        const label = document.getElementById('rating-text');
        if (label) label.textContent = 'Click to rate (1–5 stars)';
        categorySelect.value = '';
        messageText.value = '';
        if (allowContactCheck) allowContactCheck.checked = false;

        await loadMyFeedback();
    } else {
        showAlert(alertBox, res.data.error || 'Failed to submit feedback.', 'error');
    }
}

// Load previous feedback submitted by logged-in user
async function loadMyFeedback() {
    const container = document.getElementById('feedback-history-list');
    const card = document.getElementById('my-feedback-card');
    if (!container) return;

    const res = await Feedback.getByStudent(currentStudent.id);
    if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
        if (card) card.style.display = 'block';
        container.innerHTML = res.data.map(item => {
            const starsHtml = '★'.repeat(item.rating || 5) + '☆'.repeat(5 - (item.rating || 5));
            const statusClass = (item.status || 'open').toLowerCase().replace(' ', '-');
            const formattedDate = formatDate(item.created_at || new Date());
            const contactTag = item.allow_contact ? '<span class="contact-badge">📞 Contact Allowed</span>' : '';

            return `
                <div class="feedback-item">
                    <div class="feedback-item-header">
                        <div>
                            <span class="feedback-item-cat">[${escapeHtml(item.category)}]</span>
                            <span class="feedback-item-stars">${starsHtml} (${item.rating}/5)</span>
                        </div>
                        <span class="status-badge ${statusClass}">${escapeHtml(item.status || 'Open')}</span>
                    </div>
                    <div class="feedback-item-msg">${escapeHtml(item.message)}</div>
                    <div class="feedback-item-footer">
                        <span>Submitted on ${formattedDate}</span>
                        ${contactTag}
                    </div>
                </div>
            `;
        }).join('');
    } else {
        if (card) card.style.display = 'none';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}
