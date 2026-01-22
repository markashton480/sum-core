/**
 * Name: Core Main JS
 * Path: core/sum_core/static/sum_core/js/main.js
 * Purpose: Minimal JavaScript for reveal animations used by core block templates.
 * Family: SUM Platform – Core Utilities
 * Dependencies: None (vanilla JS)
 *
 * Note: Theme-specific behavior (header scroll, mobile menu, FAQ accordion, etc.)
 * is handled by theme JS files (e.g., theme_a/js/main.js).
 */

document.addEventListener('DOMContentLoaded', () => {
    // Add 'js' class for CSS progressive enhancement detection
    document.documentElement.classList.add('js');

    // Intersection Observer for Scroll Animations
    // Adds 'is-in-view' class to elements when they enter the viewport.
    // CSS handles the actual animation (see utilities.css).
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.15
    };

    const observer = new IntersectionObserver((entries, obs) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-in-view');
                obs.unobserve(entry.target); // Only animate once
            }
        });
    }, observerOptions);

    // Observe reveal elements used in core block templates
    const revealElements = document.querySelectorAll('.reveal-group, .reveal-text, .observe-me');
    revealElements.forEach(el => {
        observer.observe(el);
    });

    // Counter animations (enhancement only)
    // Used by stats blocks to animate numbers on scroll
    const counterElements = document.querySelectorAll('[data-counter-target]');
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    if (counterElements.length > 0 && 'IntersectionObserver' in window) {
        const counterObserver = new IntersectionObserver((entries, observerInstance) => {
            entries.forEach(entry => {
                if (!entry.isIntersecting) {
                    return;
                }

                const counter = entry.target;
                const target = parseFloat(counter.dataset.counterTarget || '');

                if (!Number.isFinite(target)) {
                    observerInstance.unobserve(counter);
                    return;
                }

                const suffix = counter.dataset.counterSuffix || '';
                const startValue = parseFloat(counter.dataset.counterStart || '0');
                const duration = parseInt(counter.dataset.counterDuration || '2000', 10);

                if (reduceMotion || duration <= 0) {
                    counter.textContent = `${target}${suffix}`;
                    observerInstance.unobserve(counter);
                    return;
                }

                const startTime = performance.now();

                const step = (now) => {
                    const progress = Math.min((now - startTime) / duration, 1);
                    const currentValue = Math.round(startValue + (target - startValue) * progress);
                    counter.textContent = `${currentValue}${suffix}`;

                    if (progress < 1) {
                        requestAnimationFrame(step);
                    } else {
                        counter.textContent = `${target}${suffix}`;
                    }
                };

                requestAnimationFrame(step);
                observerInstance.unobserve(counter);
            });
        }, { threshold: 0.5 });

        counterElements.forEach(el => counterObserver.observe(el));
    }

    // Sticky CTA reveal (mobile + desktop)
    const stickyCtaElements = document.querySelectorAll('.sticky-cta');
    const desktopStickyCtaElements = document.querySelectorAll('.desktop-sticky-cta');
    const desktopStickyCtaWireframe = document.getElementById('sticky-cta');
    const heroSentinel = document.getElementById('hero-sentinel');

    const hasStickyCtas =
        stickyCtaElements.length > 0 ||
        desktopStickyCtaElements.length > 0 ||
        Boolean(desktopStickyCtaWireframe);

    if (hasStickyCtas) {
        const rootStyles = window.getComputedStyle(document.documentElement);
        const parseThreshold = (value, fallback) => {
            const parsed = parseInt(value, 10);
            return Number.isFinite(parsed) ? parsed : fallback;
        };
        const mobileThreshold = parseThreshold(
            rootStyles.getPropertyValue('--sticky-cta-scroll-threshold').trim(),
            160
        );
        const desktopThreshold = parseThreshold(
            rootStyles.getPropertyValue('--desktop-sticky-cta-scroll-threshold').trim(),
            mobileThreshold
        );

        const toggleStickyCtas = () => {
            const mobileVisible = window.scrollY > mobileThreshold;
            const desktopVisible = window.scrollY > desktopThreshold;

            stickyCtaElements.forEach(element => {
                element.classList.toggle('visible', mobileVisible);
            });
            desktopStickyCtaElements.forEach(element => {
                element.classList.toggle('visible', desktopVisible);
            });

            if (desktopStickyCtaWireframe && !heroSentinel) {
                desktopStickyCtaWireframe.classList.toggle(
                    'translate-y-full',
                    !desktopVisible
                );
            }
        };

        if (
            desktopStickyCtaWireframe &&
            heroSentinel &&
            'IntersectionObserver' in window
        ) {
            const heroObserver = new IntersectionObserver(
                (entries) => {
                    entries.forEach((entry) => {
                        // Hide sticky CTA when hero is visible (intersecting)
                        // Show sticky CTA when scrolled past hero (not intersecting)
                        desktopStickyCtaWireframe.classList.toggle(
                            'translate-y-full',
                            entry.isIntersecting
                        );
                    });
                },
                { root: null, threshold: 0 }
            );
            heroObserver.observe(heroSentinel);
        }

        // Always attach scroll listener and call initial toggle
        toggleStickyCtas();
        window.addEventListener('scroll', toggleStickyCtas, { passive: true });
    }
});
