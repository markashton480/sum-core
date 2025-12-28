/**
 * Name: Cookie Consent Manager
 * Path: core/sum_core/static/sum_core/js/cookie_consent.js
 * Purpose: Manages cookie consent banner behavior and consent cookie lifecycle.
 * Family: Part of consent + legal framework (v0.6.0).
 * Dependencies: Requires DOM hooks from cookie_banner.html.
 */

(function () {
  'use strict';

  // Cookie names
  const COOKIE_CONSENT = 'sum_cookie_consent';
  const COOKIE_CONSENT_VERSION = 'sum_cookie_consent_v';

  // Cookie values
  const CONSENT_ACCEPTED = 'accepted';
  const CONSENT_REJECTED = 'rejected';

  // Cookie expiry (180 days in seconds)
  const COOKIE_MAX_AGE = 180 * 24 * 60 * 60;

  /**
   * Get the consent version from the banner element's data attribute.
   * Falls back to '1' if not found.
   */
  function getConsentVersion() {
    const banner = document.querySelector('.cookie-banner');
    if (!banner) return '1';

    // Look for data-consent-version attribute (can be added to banner if needed)
    // For now, we'll extract it from site settings via a meta tag
    const versionMeta = document.querySelector('meta[name="sum:cookie-consent-version"]');
    return versionMeta ? versionMeta.content : '1';
  }

  /**
   * Get a cookie value by name.
   * Values are URL-decoded to handle special characters.
   */
  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      const encodedValue = parts.pop().split(';').shift();
      try {
        return decodeURIComponent(encodedValue);
      } catch (e) {
        // Return raw value if decoding fails (backwards compatibility)
        return encodedValue;
      }
    }
    return null;
  }

  /**
   * Set a cookie with the specified name, value, and max age.
   * Value is URL-encoded to handle special characters.
   */
  function setCookie(name, value, maxAge) {
    const isSecure = window.location.protocol === 'https:';
    const secureFlag = isSecure ? '; Secure' : '';

    document.cookie = `${name}=${encodeURIComponent(value)}; Path=/; SameSite=Lax; Max-Age=${maxAge}${secureFlag}`;
  }

  /**
   * Delete a cookie by setting its max age to 0.
   */
  function deleteCookie(name) {
    document.cookie = `${name}=; Path=/; Max-Age=0`;
  }

  /**
   * Check if consent is valid (exists, has an expected value, and version matches).
   */
  function isConsentValid() {
    const consent = getCookie(COOKIE_CONSENT);
    const version = getCookie(COOKIE_CONSENT_VERSION);
    const currentVersion = getConsentVersion();

    return (
      (consent === CONSENT_ACCEPTED || consent === CONSENT_REJECTED) &&
      version === currentVersion
    );
  }

  /**
   * Show the cookie banner.
   */
  function showBanner() {
    const banner = document.querySelector('.cookie-banner');
    if (banner) {
      banner.style.display = 'block';
      banner.setAttribute('aria-hidden', 'false');
    }
  }

  /**
   * Hide the cookie banner.
   */
  function hideBanner() {
    const banner = document.querySelector('.cookie-banner');
    if (banner) {
      banner.style.display = 'none';
      banner.setAttribute('aria-hidden', 'true');
    }
  }

  /**
   * Set consent cookies and hide banner.
   */
  function setConsent(choice) {
    const version = getConsentVersion();

    setCookie(COOKIE_CONSENT, choice, COOKIE_MAX_AGE);
    setCookie(COOKIE_CONSENT_VERSION, version, COOKIE_MAX_AGE);

    // Update status message for screen readers BEFORE hiding banner
    const statusElement = document.querySelector('.cookie-banner__status');
    if (statusElement) {
      const message = choice === CONSENT_ACCEPTED
        ? 'Cookie preferences saved. You have accepted cookies.'
        : 'Cookie preferences saved. You have rejected cookies.';
      statusElement.textContent = message;
    }

    // Brief delay to allow screen reader announcement, then hide banner
    setTimeout(() => {
      hideBanner();
    }, 100);

    // Dispatch custom event for other scripts (like analytics loader) to listen to
    const event = new CustomEvent('cookieConsentChanged', {
      detail: { consent: choice, version: version }
    });
    document.dispatchEvent(event);
  }

  /**
   * Handle accept button click.
   */
  function handleAccept() {
    setConsent(CONSENT_ACCEPTED);
  }

  /**
   * Handle reject button click.
   */
  function handleReject() {
    setConsent(CONSENT_REJECTED);
  }

  /**
   * Handle manage cookies link click.
   * Clears existing consent and re-shows the banner.
   */
  function handleManage(event) {
    event.preventDefault();

    // Clear existing consent cookies
    deleteCookie(COOKIE_CONSENT);
    deleteCookie(COOKIE_CONSENT_VERSION);

    // Show banner again
    showBanner();

    // Update status for screen readers
    const statusElement = document.querySelector('.cookie-banner__status');
    if (statusElement) {
      statusElement.textContent = 'Cookie preferences cleared. Please choose your preferences again.';
    }

    // Scroll banner into view
    const banner = document.querySelector('.cookie-banner');
    if (banner) {
      banner.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  /**
   * Initialize cookie consent behavior.
   */
  function init() {
    const banner = document.querySelector('.cookie-banner');
    if (!banner) return; // Banner disabled or not present

    // Check if consent is valid
    if (!isConsentValid()) {
      showBanner();
    } else {
      hideBanner();
    }

    // Set up event listeners for accept/reject buttons
    const acceptButton = document.querySelector('[data-cookie-consent="accept"]');
    const rejectButton = document.querySelector('[data-cookie-consent="reject"]');

    if (acceptButton) {
      acceptButton.addEventListener('click', handleAccept);
    }

    if (rejectButton) {
      rejectButton.addEventListener('click', handleReject);
    }

    // Set up event listeners for all "manage" links (may be in footer, etc.)
    const manageLinks = document.querySelectorAll('[data-cookie-consent="manage"]');
    manageLinks.forEach(link => {
      link.addEventListener('click', handleManage);
    });
  }

  // Initialize when DOM is ready
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  // Expose public API for testing/debugging
  window.SumCookieConsent = {
    getConsent: () => getCookie(COOKIE_CONSENT),
    getConsentVersion: () => getCookie(COOKIE_CONSENT_VERSION),
    isValid: isConsentValid,
    showBanner: showBanner,
    hideBanner: hideBanner
  };
})();
