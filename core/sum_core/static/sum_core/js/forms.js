/**
 * SUM Core Forms
 * Path: core/sum_core/static/sum_core/js/forms.js
 *
 * Auto-binds to [data-dynamic-form] elements and handles:
 * - AJAX submission with CSRF
 * - Loading states
 * - Success/error message rendering
 * - Form reset on success
 * - Redirect on success (if configured)
 *
 * Themes can hook into events for visual enhancements (closing modals, animations).
 *
 * Events (dispatched on the form element, bubble up):
 *   - sum:form:submit  - When submission starts, detail: {form}
 *   - sum:form:success - On success, detail: {form, data}
 *   - sum:form:error   - On error, detail: {form, errors, networkError}
 *
 * Data attributes:
 *   - data-dynamic-form          - Marks form for auto-binding
 *   - data-success-message       - Custom success message (default: "Thank you for your submission.")
 *   - data-error-message         - Custom fallback error message
 *   - data-success-redirect      - URL to redirect to on success
 *   - data-dynamic-form-submit   - Identifies submit button (falls back to button[type="submit"])
 *
 * API (for advanced usage):
 *   SumForms.submit(form)                    - Manual submission, returns Promise
 *   SumForms.renderErrors(container, errors) - Render error messages
 *   SumForms.clearErrors(container)          - Clear error messages
 *   SumForms.setSuccessMessage(container, msg) - Show success message
 */

(function () {
  'use strict';

  if (window.SumForms) {
    return;
  }

  // ============================================================
  // Utilities
  // ============================================================

  function getCsrfToken(form) {
    var input = form.querySelector('input[name="csrfmiddlewaretoken"]');
    return input ? input.value : '';
  }

  function dispatchEvent(form, eventName, detail) {
    var event = new CustomEvent(eventName, {
      bubbles: true,
      cancelable: true,
      detail: detail || {},
    });
    form.dispatchEvent(event);
  }

  function setTimestamp(form) {
    var input = form.querySelector('.js-dynamic-form-timestamp');
    if (input) {
      input.value = Date.now().toString();
    }
  }

  // ============================================================
  // Message Rendering
  // ============================================================

  function clearErrors(container) {
    if (!container) return;
    container.className = 'form-messages text-sm';
    container.innerHTML = '';
  }

  function renderErrors(container, errors, fallbackMessage) {
    if (!container) return;

    container.className = 'form-messages form-messages--error text-sm';
    container.innerHTML = '';

    if (errors && typeof errors === 'object') {
      Object.keys(errors).forEach(function (field) {
        var fieldErrors = errors[field];
        if (Array.isArray(fieldErrors)) {
          fieldErrors.forEach(function (msg) {
            var el = document.createElement('p');
            el.className = 'form-error-msg';
            el.textContent = msg;
            container.appendChild(el);
          });
        }
      });
    }

    if (!container.hasChildNodes() && fallbackMessage) {
      var el = document.createElement('p');
      el.className = 'form-error-msg';
      el.textContent = fallbackMessage;
      container.appendChild(el);
    }
  }

  function setSuccessMessage(container, message) {
    if (!container) return;
    container.className = 'form-messages form-messages--success text-sm';
    container.innerHTML = '';

    if (message) {
      var el = document.createElement('p');
      el.className = 'form-success-msg';
      el.textContent = message;
      container.appendChild(el);
    }
  }

  // ============================================================
  // Form Submission
  // ============================================================

  function submit(form) {
    if (!form || !form.action) {
      return Promise.reject(new Error('Invalid form element'));
    }

    var csrfToken = getCsrfToken(form);
    var formData = new FormData(form);

    dispatchEvent(form, 'sum:form:submit', { form: form });

    return fetch(form.action, {
      method: 'POST',
      body: formData,
      credentials: 'same-origin',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'X-CSRFToken': csrfToken,
      },
    })
      .then(function (response) {
        return response
          .json()
          .then(function (data) {
            return { status: response.status, data: data };
          })
          .catch(function () {
            return { status: response.status, data: {} };
          });
      })
      .then(function (result) {
        var success = result.data && result.data.success;

        if (success) {
          dispatchEvent(form, 'sum:form:success', {
            form: form,
            data: result.data,
          });
        } else {
          dispatchEvent(form, 'sum:form:error', {
            form: form,
            errors: result.data ? result.data.errors : null,
            networkError: false,
          });
        }

        return {
          success: success,
          data: result.data,
          status: result.status,
          errors: result.data ? result.data.errors : null,
        };
      })
      .catch(function (error) {
        dispatchEvent(form, 'sum:form:error', {
          form: form,
          errors: null,
          networkError: true,
          error: error,
        });

        return {
          success: false,
          data: null,
          status: 0,
          errors: null,
          networkError: true,
        };
      });
  }

  // ============================================================
  // Form Handler (full lifecycle)
  // ============================================================

  function handleSubmit(form) {
    var submitBtn =
      form.querySelector('[data-dynamic-form-submit]') ||
      form.querySelector('button[type="submit"]');
    var messagesDiv = form.querySelector('.form-messages');
    var originalBtnText = submitBtn ? submitBtn.textContent : '';
    var successMsg = form.dataset.successMessage || 'Thank you for your submission.';
    var errorMsg = form.dataset.errorMessage || 'Something went wrong. Please try again.';
    var syncFallback = false;

    // Loading state
    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.textContent = 'Sending...';
    }
    clearErrors(messagesDiv);

    return submit(form)
      .then(function (result) {
        if (result.success) {
          setSuccessMessage(messagesDiv, successMsg);
          form.reset();
          setTimestamp(form);

          var redirectUrl = form.dataset.successRedirect;
          if (redirectUrl) {
            window.location.href = redirectUrl;
          }
        } else if (result.networkError) {
          // Network error: fall back to synchronous form submission
          // Don't re-enable button since page will navigate away
          syncFallback = true;
          renderErrors(messagesDiv, null, errorMsg);
          form.dataset.ajaxDisabled = 'true';
          form.submit();
        } else {
          renderErrors(messagesDiv, result.errors, errorMsg);
        }
        return result;
      })
      .finally(function () {
        // Only reset button if we're not falling back to sync submit
        if (submitBtn && !syncFallback) {
          submitBtn.disabled = false;
          submitBtn.textContent = originalBtnText;
        }
      });
  }

  // ============================================================
  // Auto-binding
  // ============================================================

  function bindForm(form) {
    if (form.dataset.sumFormsBound === 'true') {
      return;
    }
    form.dataset.sumFormsBound = 'true';

    // Set initial timestamp
    setTimestamp(form);

    form.addEventListener('submit', function (event) {
      if (form.dataset.ajaxDisabled === 'true' || !window.fetch) {
        return;
      }
      event.preventDefault();
      handleSubmit(form);
    });
  }

  function bindAll() {
    var forms = document.querySelectorAll('[data-dynamic-form]');
    forms.forEach(bindForm);
  }

  // Bind on DOMContentLoaded and expose for dynamic content
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', bindAll);
  } else {
    bindAll();
  }

  // ============================================================
  // Public API
  // ============================================================

  window.SumForms = {
    submit: submit,
    renderErrors: renderErrors,
    clearErrors: clearErrors,
    setSuccessMessage: setSuccessMessage,
    bindForm: bindForm,
    bindAll: bindAll,
  };
})();
