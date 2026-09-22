// ============================================
// Help & Support Page Logic - SkillX
// ============================================

let currentStudent = null;

document.addEventListener('DOMContentLoaded', async () => {
    requireAuth();
    renderNavUser();

    currentStudent = getCurrentStudent();
    if (!currentStudent) return;

    setupAccordions();
    setupCategoryFilters();
    setupFaqSearch();
    await loadMyTickets();

    const ticketModal = document.getElementById('ticket-details-modal');
    if (ticketModal) {
        ticketModal.addEventListener('click', (e) => {
            if (e.target === ticketModal) {
                closeTicketDetailsModal();
            }
        });
    }
});

// Setup expandable FAQ accordions
function setupAccordions() {
    const headers = document.querySelectorAll('.accordion-header');
    headers.forEach(hdr => {
        hdr.addEventListener('click', () => {
            const item = hdr.closest('.accordion-item');
            const isActive = item.classList.contains('active');

            // Close all items in the group or toggle current
            item.classList.toggle('active', !isActive);
        });
    });
}

// Category filter cards navigation & filtering
function setupCategoryFilters() {
    const catCards = document.querySelectorAll('.category-card');
    catCards.forEach(card => {
        card.addEventListener('click', () => {
            const cat = card.dataset.category;
            catCards.forEach(c => c.classList.toggle('active', c === card));

            filterFaqsByCategory(cat);
        });
    });
}

function filterFaqsByCategory(category) {
    const faqGroups = document.querySelectorAll('.faq-group');
    faqGroups.forEach(group => {
        if (category === 'all' || group.dataset.category === category) {
            group.style.display = 'block';
        } else {
            group.style.display = 'none';
        }
    });
}

// Real-time FAQ search filter
function setupFaqSearch() {
    const searchInput = document.getElementById('faq-search');
    if (!searchInput) return;

    searchInput.addEventListener('input', (e) => {
        const query = e.target.value.toLowerCase().trim();
        const items = document.querySelectorAll('.accordion-item');
        const faqGroups = document.querySelectorAll('.faq-group');

        if (!query) {
            // Reset visibility to category filter
            const activeCard = document.querySelector('.category-card.active');
            const activeCat = activeCard ? activeCard.dataset.category : 'all';
            filterFaqsByCategory(activeCat);
            items.forEach(item => { item.style.display = 'block'; });
            return;
        }

        // Search mode — display all groups and filter individual FAQ items
        faqGroups.forEach(g => { g.style.display = 'block'; });

        items.forEach(item => {
            const q = item.querySelector('.accordion-header').textContent.toLowerCase();
            const a = item.querySelector('.accordion-body').textContent.toLowerCase();
            if (q.includes(query) || a.includes(query)) {
                item.style.display = 'block';
                item.classList.add('active'); // Auto-expand matching results
            } else {
                item.style.display = 'none';
                item.classList.remove('active');
            }
        });
    });
}

// Submit Support Ticket Form
async function handleSubmitSupport(e) {
    e.preventDefault();
    const categorySelect = document.getElementById('support-category');
    const descriptionText = document.getElementById('support-description');
    const alertBox = document.getElementById('support-form-alert');

    const category = categorySelect.value;
    const description = descriptionText.value.trim();

    if (!category || !description) {
        showAlert(alertBox, 'Please select a category and provide a description of your issue.', 'error');
        return;
    }

    // Uses authenticated student ID
    const res = await Support.create(category, description, currentStudent.id);
    if (res.ok) {
        showAlert(alertBox, 'Your support ticket has been submitted! Our team will review it shortly.', 'success');
        descriptionText.value = '';
        await loadMyTickets();
    } else {
        showAlert(alertBox, res.data.error || 'Failed to submit support request.', 'error');
    }
}

let userTicketsMap = {};

// Load submitted tickets for logged-in user
async function loadMyTickets() {
    const container = document.getElementById('tickets-list');
    const card = document.getElementById('my-tickets-card');
    if (!container) return;

    const res = await Support.getByStudent(currentStudent.id);
    if (res.ok && Array.isArray(res.data) && res.data.length > 0) {
        if (card) card.style.display = 'block';
        userTicketsMap = {};

        container.innerHTML = res.data.map(t => {
            userTicketsMap[t.request_id] = t;
            const statusClass = (t.status || 'open').toLowerCase().replace(' ', '-');
            const formattedDate = formatDate(t.created_at || new Date());
            return `
                <div class="ticket-row" data-ticket-id="${t.request_id}" onclick="openTicketDetailsModal(${t.request_id})" title="Click to view details">
                    <div class="ticket-info">
                        <h4>[${escapeHtml(t.category)}] Ticket #${t.request_id}</h4>
                        <p>${escapeHtml(t.description)}</p>
                        <div class="ticket-date">Submitted on ${formattedDate}</div>
                        <div class="ticket-click-hint">🔍 Click anywhere to view full details & response</div>
                    </div>
                    <span class="status-badge ${statusClass}" data-ticket-id="${t.request_id}" onclick="openTicketDetailsModal(${t.request_id})">${escapeHtml(t.status || 'Open')}</span>
                </div>
            `;
        }).join('');

        // Attach explicit DOM click event listeners to every ticket row
        container.querySelectorAll('.ticket-row').forEach(row => {
            row.addEventListener('click', (e) => {
                const reqId = row.dataset.ticketId || row.getAttribute('data-ticket-id');
                console.log('[Support UI] Ticket row clicked via DOM listener. Ticket ID:', reqId);
                if (reqId) openTicketDetailsModal(parseInt(reqId, 10));
            });
        });
    } else {
        if (card) card.style.display = 'none';
    }
}

function openTicketDetailsModal(ticketId) {
    console.log('[Support UI] openTicketDetailsModal called with ticketId:', ticketId);
    const id = parseInt(ticketId, 10);
    const ticket = userTicketsMap[id] || userTicketsMap[ticketId];
    if (!ticket) {
        console.warn('[Support UI] Ticket not found in userTicketsMap for ID:', ticketId, userTicketsMap);
        return;
    }

    const titleEl = document.getElementById('modal-ticket-title');
    const categoryEl = document.getElementById('modal-ticket-category');
    const dateEl = document.getElementById('modal-ticket-date');
    const descEl = document.getElementById('modal-ticket-description');
    const adminReplyEl = document.getElementById('modal-ticket-admin-reply');
    const statusBadgeEl = document.getElementById('modal-ticket-status-badge');

    if (titleEl) titleEl.textContent = `Ticket #${ticket.request_id} Details`;
    if (categoryEl) categoryEl.textContent = ticket.category || 'General';
    if (dateEl) dateEl.textContent = formatDate(ticket.created_at || new Date()) + ' ' + formatTime(ticket.created_at || new Date());
    if (descEl) descEl.textContent = ticket.description || '';

    const statusClass = (ticket.status || 'open').toLowerCase().replace(' ', '-');
    if (statusBadgeEl) {
        statusBadgeEl.className = `status-badge ${statusClass}`;
        statusBadgeEl.textContent = ticket.status || 'Open';
    }

    if (adminReplyEl) {
        if (ticket.admin_reply && ticket.admin_reply.trim()) {
            adminReplyEl.innerHTML = `<strong>💬 Support Team Response:</strong><br>${escapeHtml(ticket.admin_reply)}`;
            adminReplyEl.style.background = '#eef6ff';
            adminReplyEl.style.color = '#0c4a6e';
        } else {
            adminReplyEl.textContent = 'No response from support team yet. Our team will review your ticket soon.';
            adminReplyEl.style.background = 'var(--bg)';
            adminReplyEl.style.color = 'var(--text-muted)';
        }
    }

    const modal = document.getElementById('ticket-details-modal');
    if (modal) {
        modal.classList.add('show', 'active');
        modal.style.display = 'flex';
        console.log('[Support UI] Modal displayed successfully:', modal);
    }
}

function closeTicketDetailsModal() {
    const modal = document.getElementById('ticket-details-modal');
    if (modal) {
        modal.classList.remove('show', 'active');
        modal.style.display = 'none';
    }
}

// Expose functions globally on window object
window.openTicketDetailsModal = openTicketDetailsModal;
window.closeTicketDetailsModal = closeTicketDetailsModal;



function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}
