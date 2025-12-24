document.addEventListener('DOMContentLoaded', () => {
    // 1. Intersection Observer for Scroll Animations
    const observerOptions = {
        root: null,
        rootMargin: '0px',
        threshold: 0.15
    };

    const observer = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('is-in-view');
                observer.unobserve(entry.target); // Only animate once
            }
        });
    }, observerOptions);

    // Observe groups and individual reveal elements if they are not children of a group (or just all of them)
    // The CSS handles nested reveals if the parent has is-in-view
    const revealElements = document.querySelectorAll('.reveal-group, .reveal-text, .reveal-img-wrapper, .observe-me');
    revealElements.forEach(el => {
        // Avoid double observation if an element has multiple reveal classes
        observer.observe(el);
    });


    // 2. Before/After Slider Logic
    const sliderContainer = document.getElementById('compare-slider');
    if (sliderContainer) {
        const sliderRange = sliderContainer.querySelector('.slider-range');
        const foreground = sliderContainer.querySelector('.img-foreground');
        const handle = sliderContainer.querySelector('.slider-handle');

        if (sliderRange && foreground && handle) {
            sliderRange.addEventListener('input', (e) => {
                const value = e.target.value + "%";
                foreground.style.width = value;
                handle.style.left = value;
            });
        }
    }


    // 3. Header Scroll Effect & Sticky CTA
    const header = document.querySelector('.header');
    const stickyCta = document.getElementById('stickyCta');

    const handleScroll = () => {
        const scrollY = window.scrollY;

        // Header Glassmorphism
        if (header) {
            if (scrollY > 50) {
                header.classList.add('scrolled');
            } else {
                header.classList.remove('scrolled');
            }
        }

        // Sticky CTA Reveal
        if (stickyCta) {
            if (scrollY > 400) {
                stickyCta.classList.add('visible');
            } else {
                stickyCta.classList.remove('visible');
            }
        }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });


    // 4. Smooth FAQ Accordion Logic
    // Handles "Auto -> Pixel -> Auto" height transition for smooth animation
    const toggleAccordion = (btn) => {
        const item = btn.closest('.faq-item');
        const answer = item.querySelector('.faq-answer');
        const isOpen = item.getAttribute('aria-expanded') === 'true';
        const section = item.closest('[data-faq-block]');
        const allowMultiple = section ? section.getAttribute('data-allow-multiple') === 'true' : false;

        // Close other items if not allowing multiple
        if (!allowMultiple) {
            section.querySelectorAll('.faq-item').forEach(other => {
                if (other !== item && other.getAttribute('aria-expanded') === 'true') {
                    const otherAnswer = other.querySelector('.faq-answer');
                    // Force height to current pixel value so we can animate from it
                    const currentHeight = otherAnswer.scrollHeight;
                    otherAnswer.style.height = `${currentHeight}px`;

                    // Force reflow
                    otherAnswer.offsetHeight;

                    // Animate to 0
                    requestAnimationFrame(() => {
                         otherAnswer.style.height = '0px';
                    });

                    other.setAttribute('aria-expanded', 'false');
                }
            });
        }

        if (isOpen) {
            // CLOSE:
            // 1. Set height to current scrollHeight (because it might be 'auto')
            answer.style.height = `${answer.scrollHeight}px`;
            // 2. Force reflow so browser registers the pixel height
            answer.offsetHeight;
            // 3. Animate to 0
            requestAnimationFrame(() => {
                answer.style.height = '0px';
            });
            item.setAttribute('aria-expanded', 'false');
        } else {
            // OPEN:
            item.setAttribute('aria-expanded', 'true');
            // 1. Set height to scrollHeight to start animation
            const targetHeight = answer.scrollHeight;
            answer.style.height = `${targetHeight}px`;

            // 2. After transition, set to 'auto' so it adapts to window resizing
            const setAuto = () => {
                if (item.getAttribute('aria-expanded') === 'true') {
                    answer.style.height = 'auto';
                }
                answer.removeEventListener('transitionend', setAuto);
            };
            answer.addEventListener('transitionend', setAuto);
        }
    };

    // Attach listeners
    document.querySelectorAll('.faq-toggle').forEach(btn => {
        btn.addEventListener('click', (e) => {
             e.preventDefault(); // Prevent standard button behavior if any
             toggleAccordion(btn);
        });
    });
});
