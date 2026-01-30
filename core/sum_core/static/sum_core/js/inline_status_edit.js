/**
 * Inline status editing for lead list view
 *
 * Handles AJAX status updates and visual feedback.
 */

(function() {
    'use strict';

    // Add CSS for error state
    const style = document.createElement('style');
    style.textContent = `
        .status-update-error {
            border: 2px solid #ef4444 !important;
            background-color: #fee2e2 !important;
        }
    `;
    document.head.appendChild(style);

    /**
     * Initialize inline status editing on page load
     */
    function initInlineStatusEditing() {
        console.log('Lead Admin: Initializing inline status editing');
        const selects = document.querySelectorAll('.inline-status-select');

        if (selects.length === 0) {
            console.log('Lead Admin: No inline status dropdowns found.');
            return;
        }

        console.log(`Lead Admin: Found ${selects.length} inline status dropdowns.`);

        selects.forEach(function(select) {
            // Store original value
            select.dataset.originalValue = select.value;

            // Add change event listener
            select.addEventListener('change', function(e) {
                handleStatusChange(e.target);
            });
        });
    }

    /**
     * Handle status change via AJAX
     * @param {HTMLSelectElement} selectElement - The select element that changed
     */
    function handleStatusChange(selectElement) {
        const leadId = selectElement.dataset.leadId;
        const newStatus = selectElement.value;
        const originalValue = selectElement.dataset.originalValue;

        // Disable select while updating
        selectElement.disabled = true;

        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value
            || getCookie('csrftoken');

        // Build URL - use relative path from current page
        const url = `/admin/lead/${leadId}/update-status/`;

        // Send AJAX request
        fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken
            },
            body: JSON.stringify({
                status: newStatus
            })
        })
        .then(function(response) {
            if (!response.ok) {
                throw new Error('Status update failed');
            }
            return response.json();
        })
        .then(function(data) {
            if (data.success) {
                // Update stored original value
                selectElement.dataset.originalValue = newStatus;

                // Update color based on selected option
                const selectedOption = selectElement.options[selectElement.selectedIndex];
                const color = selectedOption.dataset.color || '#64748b';
                selectElement.style.color = color;

                // Show success feedback (brief flash)
                selectElement.style.backgroundColor = '#dcfce7'; // green-100
                setTimeout(function() {
                    selectElement.style.backgroundColor = '';
                }, 1000);
            } else {
                throw new Error(data.error || 'Update failed');
            }
        })
        .catch(function(error) {
            // Revert to original value on error
            selectElement.value = originalValue;

            // Show error feedback
            const errorMsg = 'Failed to update status: ' + error.message;
            console.error('Status update failed:', errorMsg);

            // Visual error indicator
            selectElement.classList.add('status-update-error');
            selectElement.title = errorMsg;

            // Remove error state after 3 seconds
            setTimeout(function() {
                selectElement.classList.remove('status-update-error');
                selectElement.title = '';
            }, 3000);
        })
        .finally(function() {
            // Re-enable select
            selectElement.disabled = false;
        });
    }

    /**
     * Get cookie value by name
     * @param {string} name - Cookie name
     * @returns {string|null} Cookie value
     */
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }

    // Initialize on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initInlineStatusEditing);
    } else {
        initInlineStatusEditing();
    }
})();
