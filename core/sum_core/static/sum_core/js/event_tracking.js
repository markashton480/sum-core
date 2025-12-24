/**
 * SUM Platform - Event Tracking
 *
 * Handle pushing key conversion events to window.dataLayer for GTM/GA4.
 * Tracks:
 * - Form submissions (contact, quote_request, newsletter)
 * - Click events (phone, email, CTAs)
 *
 * Implements M4-002 requirements.
 */
(function() {
    'use strict';

    // 1. Initialize dataLayer
    // Ensure it exists even if no analytics script loaded it yet
    window.dataLayer = window.dataLayer || [];

    // Helper to push to dataLayer safely
    function pushEvent(eventData) {
        try {
            window.dataLayer.push(eventData);
            // Uncomment for debugging:
            // console.log('dataLayer push:', eventData);
        } catch (e) {
            console.warn('SUM Event Tracking: Failed to push to dataLayer', e);
        }
    }

    /**
     * Helper to determine based on scopes if we should ignore a target.
     * @param {Element} el - The element to check.
     * @param {boolean} checkScopes - Whether to check for data-track-scope="ignore", nav, modal, etc.
     * @returns {boolean} - True if trackable (not ignored), False if ignored.
     */
    function isHardIgnored(el) {
        // "Never track list" (Tier 3)
        // Hard exclusions based on selector matches
        if (el.matches('a[href^="#"], button[type="button"][aria-expanded], button[disabled]')) {
             return true;
        }

        // Hard exclusions based on containers
        // Ignore clicks inside nav, cookie banner, modal, dialog
        if (el.closest('nav, .cookie-banner, [aria-label*="cookie" i], .modal, [role="dialog"]')) {
             return true;
        }

        return false;
    }

    function isInsideIgnoreScope(el) {
        // [data-track-scope="ignore"]
        return !!el.closest('[data-track-scope="ignore"]');
    }

    // --- Click Handler ---
    document.addEventListener('click', function(e) {
        // Climb to find closest a or button (or element with data-track)
        // We use closest because the click might be on a span inside a button

        // Admin check: Never track in Wagtail admin
        if (document.body.classList.contains('wagtail') || window.location.pathname.startsWith('/admin/')) {
            return;
        }

        // We need to find the "trackable entity".
        // Logic:
        // 1. Check for data-track="cta" on element or parents.
        // 2. If not found, check for a/button and apply implicit rules.

        const explicitCta = e.target.closest('[data-track="cta"]');
        if (explicitCta) {
            // Tier 1: Explicit CTA (Recommended)
            // We ignore scopes/hard-ignores because the developer explicitly tagged this.

            const text = explicitCta.getAttribute('data-cta-text') || explicitCta.textContent.trim();
            const destination = explicitCta.getAttribute('data-destination') || explicitCta.getAttribute('href');
            // Optional: kind
            // const kind = explicitCta.getAttribute('data-cta-kind');

            pushEvent({
                event: 'cta_click',
                button_text: text,
                destination: destination
            });
            return;
        }

        // If no explicit CTA, look for links/buttons for implicit tracking
        const target = e.target.closest('a, button');
        if (!target) return;

        const href = target.getAttribute('href') || '';

        // --- Tier 3 Checks (Never Track List) applied to Implicit Targets ---
        // But note: "Phone/Email tracking" says "Exclude if inside ignored scopes".
        // And "Explicit CTA" says "Recommended default".
        // Does Tier 3 apply to Phone/Email?
        // "Ignore click if the target is: inside nav". Yes.

        // Check for Phone/Email first, as they are specific
        if (href.startsWith('tel:') || href.startsWith('mailto:')) {
            // "Exclude if inside ignored scopes"
            if (isInsideIgnoreScope(target)) return;
            // Also apply "Never track list" (e.g. inside cookie banner, or nav? Maybe utility links in nav)
            // The task says: "Exclude if inside ignored scopes ... to avoid tracking utility links in headers/footers unless you actually want them."
            // This implies header/footer are NOT automatically hard ignores for Phone/email unless wrapped in ignore scope,
            // OR unless they hit the "Never track list" which explicitly includes `nav`.

            // Wait, "Never track list" includes `nav`. So a phone number in <nav> is ignored.
            // If we WANT to track a header phone number, we must ensure it's not in a `<nav>` or we put `data-track="cta"`?
            // "Phone/Email tracking" is a separate section.
            // It says "Exclude if inside ignored scopes". It DOES NOT explicitly reference the "Never track list".
            // However, "Never track list" says "Ignore click if the target is..." (generic).
            // This implies it applies to everything unless Explicit opt-in.
            // So default assumption: Phone in Nav -> Ignored.

            if (isHardIgnored(target)) return;

            if (href.startsWith('tel:')) {
                 pushEvent({
                     event: 'phone_click',
                     phone_number: href.replace('tel:', '')
                 });
            } else {
                 pushEvent({
                     event: 'email_click',
                     email_address: href.replace('mailto:', '')
                 });
            }
            return;
        }

        // --- Tier 2: Safe Implicit CTA Fallback ---
        // Track .btn/.button
        if (target.matches('.btn, .button')) {
            // Exclusions
            if (isInsideIgnoreScope(target)) return;
            if (isHardIgnored(target)) return;

            // Also exclude header/footer for implicit CTAs unless explicitly opted-in
            if (target.closest('header, footer')) return;

            pushEvent({
                event: 'cta_click',
                button_text: target.textContent.trim(),
                destination: href
            });
        }
    });

    // --- Form Submit Handler ---
    document.addEventListener('submit', function(e) {
        // Admin check
        if (document.body.classList.contains('wagtail') || window.location.pathname.startsWith('/admin/')) {
            return;
        }

        const form = e.target;

        // Only track forms with data-form-type (Explicit opt-in)
        const formType = form.getAttribute('data-form-type');

        if (formType) {
            pushEvent({
                event: 'form_submission',
                form_type: formType,
                page_url: window.location.href
            });
        }
    });

})();
