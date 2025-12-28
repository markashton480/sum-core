/**
 * Name: Analytics Loader
 * Path: core/sum_core/static/sum_core/js/analytics_loader.js
 * Purpose: Load analytics scripts after consent using server-emitted config.
 * Family: Analytics
 */

(function () {
  'use strict';

  const CONFIG_ID = 'sum-analytics-config';
  const CONSENT_COOKIE = 'sum_cookie_consent';
  const CONSENT_VERSION_COOKIE = 'sum_cookie_consent_v';
  const CONSENT_ACCEPTED = 'accepted';

  let hasLoaded = false;

  function getConfig() {
    const configEl = document.getElementById(CONFIG_ID);
    if (!configEl) {
      return null;
    }

    try {
      return JSON.parse(configEl.textContent || '{}');
    } catch (error) {
      return null;
    }
  }

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) {
      const encodedValue = parts.pop().split(';').shift();
      try {
        return decodeURIComponent(encodedValue);
      } catch (error) {
        return encodedValue;
      }
    }
    return null;
  }

  function getConsentVersion() {
    const versionMeta = document.querySelector('meta[name="sum:cookie-consent-version"]');
    return versionMeta ? versionMeta.content : '1';
  }

  function isConsentAccepted(consentRequired) {
    if (!consentRequired) {
      return true;
    }

    const consent = getCookie(CONSENT_COOKIE);
    const version = getCookie(CONSENT_VERSION_COOKIE);
    return consent === CONSENT_ACCEPTED && version === getConsentVersion();
  }

  function loadScript(src) {
    if (document.querySelector(`script[src="${src}"]`)) {
      return;
    }

    const script = document.createElement('script');
    script.async = true;
    script.src = src;
    document.head.appendChild(script);
  }

  function loadGtm(gtmId) {
    if (!gtmId) {
      return;
    }

    window.dataLayer = window.dataLayer || [];
    window.dataLayer.push({
      'gtm.start': new Date().getTime(),
      event: 'gtm.js'
    });

    loadScript(`https://www.googletagmanager.com/gtm.js?id=${encodeURIComponent(gtmId)}`);
  }

  function loadGa4(gaId) {
    if (!gaId) {
      return;
    }

    window.dataLayer = window.dataLayer || [];
    window.gtag = window.gtag || function () {
      window.dataLayer.push(arguments);
    };

    window.gtag('js', new Date());
    window.gtag('config', gaId);

    loadScript(`https://www.googletagmanager.com/gtag/js?id=${encodeURIComponent(gaId)}`);
  }

  function maybeLoadAnalytics() {
    if (hasLoaded) {
      return;
    }

    const config = getConfig();
    if (!config) {
      return;
    }

    const consentRequired = Boolean(config.cookie_banner_enabled);
    if (!isConsentAccepted(consentRequired)) {
      return;
    }

    // Set flag BEFORE loading to prevent race conditions from rapid event firing
    hasLoaded = true;

    if (config.gtm_container_id) {
      loadGtm(config.gtm_container_id);
    } else if (config.ga_measurement_id) {
      loadGa4(config.ga_measurement_id);
    }
  }

  function handleConsentEvent(event) {
    if (event && event.detail && event.detail.consent === CONSENT_ACCEPTED) {
      maybeLoadAnalytics();
    }
  }

  function init() {
    maybeLoadAnalytics();
    document.addEventListener('cookieConsentChanged', handleConsentEvent);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
