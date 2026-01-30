document.addEventListener('DOMContentLoaded', function() {
    'use strict';

    const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;

    function showFlash(element, type = 'success') {
        const originalColor = element.style.borderColor;
        const flashColor = type === 'success' ? 'var(--w-color-success)' : 'var(--w-color-critical)';

        element.style.transition = 'border-color 0.3s';
        element.style.borderColor = flashColor;

        setTimeout(() => {
            element.style.borderColor = originalColor;
        }, 1500);
    }

    const statusSelect = document.getElementById('id_status_select');
    if(statusSelect) {
        statusSelect.addEventListener('change', function() {
            const newValue = this.value;
            const leadId = this.dataset.leadId;

            this.disabled = true;

            fetch(`/admin/leads/lead/${leadId}/update-status/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ status: newValue })
            })
            .then(response => response.json())
            .then(data => {
                this.disabled = false;
                if(data.success) {
                    showFlash(this, 'success');
                    window.location.reload();
                } else {
                    showFlash(this, 'error');
                    alert('Error updating status: ' + (data.error || 'Unknown error'));
                }
            })
            .catch(err => {
                console.error(err);
                this.disabled = false;
                showFlash(this, 'error');
                alert('Network error updating status');
            });
        });
    }

    const assignSelect = document.getElementById('id_assignment_select');
    if(assignSelect) {
        assignSelect.addEventListener('change', function() {
            const newValue = this.value;
            const leadId = this.dataset.leadId;

            this.disabled = true;

            fetch(`/admin/leads/lead/${leadId}/update-assignment/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken
                },
                body: JSON.stringify({ assigned_to: newValue })
            })
            .then(response => response.json())
            .then(data => {
                this.disabled = false;
                if(data.success) {
                    showFlash(this, 'success');
                    if (!data.no_change) {
                        window.location.reload();
                    }
                } else {
                    showFlash(this, 'error');
                    alert('Error updating assignment');
                }
            })
            .catch(err => {
                console.error(err);
                this.disabled = false;
                showFlash(this, 'error');
                alert('Network error updating assignment');
            });
        });
    }

    document.querySelectorAll('.js-quick-note').forEach(btn => {
        btn.addEventListener('click', function() {
            const content = this.dataset.content;
            const textarea = document.querySelector('textarea[name="content"]');
            if (textarea) {
                const currentVal = textarea.value;
                textarea.value = currentVal ? currentVal + '\n' + content : content;
                textarea.focus();

                btn.style.backgroundColor = 'var(--w-color-primary-100)';
                setTimeout(() => {
                    btn.style.backgroundColor = '';
                }, 200);
            }
        });
    });

    window.copyToClipboard = function(text, btn) {
        if (!text) return;
        navigator.clipboard.writeText(text).then(() => {
            const originalHTML = btn.innerHTML;
            const originalClasses = btn.className;

            btn.innerHTML = '<svg class="icon icon-check w-w-4 w-h-4" aria-hidden="true"><use href="#icon-check"></use></svg> Copied';
            btn.classList.add('button-positive');
            btn.classList.remove('button-secondary');

            setTimeout(() => {
                btn.innerHTML = originalHTML;
                btn.className = originalClasses;
            }, 1500);
        });
    };

    const noteForm = document.querySelector('form[action*="add_note"]');
    if (noteForm) {
        noteForm.addEventListener('submit', function(e) {
            e.preventDefault();

            const submitBtn = this.querySelector('button[type="submit"]');
            const originalText = submitBtn.innerText;
            const textarea = this.querySelector('textarea');

            if (!textarea.value.trim()) return;

            submitBtn.disabled = true;
            submitBtn.innerText = 'Adding...';

            const formData = new FormData(this);

            fetch(this.action, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    textarea.value = '';
                    window.location.reload();
                } else {
                    alert(data.error || 'Error adding note');
                    submitBtn.disabled = false;
                    submitBtn.innerText = originalText;
                }
            })
            .catch(err => {
                console.error(err);
                alert('Network error');
                submitBtn.disabled = false;
                submitBtn.innerText = originalText;
            });
        });
    }
});
