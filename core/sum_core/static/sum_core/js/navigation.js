/**
 * Name: Navigation JS
 * Path: core/sum_core/static/sum_core/js/navigation.js
 * Purpose: Minimal JavaScript for mobile menu toggle and dropdown behaviour.
 * Family: SUM Platform – Navigation System
 * Dependencies: None (vanilla JS)
 */

(function() {
    'use strict';

    // =============================================================================
    // Selectors
    // =============================================================================
    const SELECTORS = {
        menuBtn: '#menuBtn, .menu-btn',
        mobileDrawer: '#mobileDrawer, .mobile-drawer',
        dropdownToggle: '.nav-dropdown__toggle, .nav-nested-dropdown__toggle',
        dropdownMenu: '.nav-dropdown__menu',
        dropdown: '.nav-dropdown',
        mobileGroup: '.mobile-group',
        mobileGroupToggle: 'button.mobile-link.has-submenu',
        header: '.header'
    };

    // =============================================================================
    // State
    // =============================================================================
    let mobileDrawerOpen = false;

    // =============================================================================
    // Helper Functions
    // =============================================================================

    /**
     * Close all dropdown menus
     */
    function closeAllDropdowns() {
        document.querySelectorAll(SELECTORS.dropdownToggle).forEach(toggle => {
            toggle.setAttribute('aria-expanded', 'false');
        });
    }

    /**
     * Close all open mobile drawer groups (accordions)
     */
    function closeAllMobileGroups() {
        const drawer = document.querySelector(SELECTORS.mobileDrawer);
        if (!drawer) return;

        drawer.querySelectorAll(SELECTORS.mobileGroup).forEach(group => {
            group.classList.remove('is-open');
        });

        drawer.querySelectorAll(SELECTORS.mobileGroupToggle).forEach(toggle => {
            toggle.setAttribute('aria-expanded', 'false');
            const controlsId = toggle.getAttribute('aria-controls');
            if (!controlsId) return;
            const panel = document.getElementById(controlsId);
            if (panel) {
                panel.setAttribute('aria-hidden', 'true');
            }
        });
    }

    /**
     * Close the mobile drawer
     */
    function closeMobileDrawer() {
        const menuBtn = document.querySelector(SELECTORS.menuBtn);
        const drawer = document.querySelector(SELECTORS.mobileDrawer);

        if (!menuBtn || !drawer) return;

        menuBtn.setAttribute('aria-expanded', 'false');
        drawer.classList.remove('is-open');
        drawer.setAttribute('aria-hidden', 'true');
        document.body.classList.remove('nav-scroll-lock');
        mobileDrawerOpen = false;

        // Reset open states when closing the drawer
        closeAllMobileGroups();

        // Close all dropdowns when closing mobile drawer
        closeAllDropdowns();
    }

    /**
     * Open the mobile drawer
     */
    function openMobileDrawer() {
        const menuBtn = document.querySelector(SELECTORS.menuBtn);
        const drawer = document.querySelector(SELECTORS.mobileDrawer);

        if (!menuBtn || !drawer) return;

        menuBtn.setAttribute('aria-expanded', 'true');
        drawer.classList.add('is-open');
        drawer.setAttribute('aria-hidden', 'false');
        document.body.classList.add('nav-scroll-lock');
        mobileDrawerOpen = true;

        // Focus the first interactive element inside the drawer for keyboard users
        const firstFocusable = drawer.querySelector('a, button');
        if (firstFocusable && typeof firstFocusable.focus === 'function') {
            firstFocusable.focus();
        }
    }

    /**
     * Toggle the mobile drawer
     */
    function toggleMobileDrawer() {
        if (mobileDrawerOpen) {
            closeMobileDrawer();
        } else {
            openMobileDrawer();
        }
    }

    /**
     * Toggle a dropdown menu
     * @param {HTMLElement} toggle - The dropdown toggle button
     */
    function toggleDropdown(toggle) {
        const isExpanded = toggle.getAttribute('aria-expanded') === 'true';
        const isOpening = !isExpanded;

        // Toggle this dropdown
        toggle.setAttribute('aria-expanded', isOpening);

        if (isOpening) {
            // Close other dropdowns NOT in the ancestry of this one
            document.querySelectorAll(SELECTORS.dropdownToggle).forEach(otherToggle => {
                if (otherToggle === toggle) return;

                const otherMenu = otherToggle.nextElementSibling;
                // If the clicked toggle is INSIDE the other menu, then otherToggle is a parent
                // Don't close parents
                if (otherMenu && otherMenu.contains(toggle)) {
                    return;
                }

                otherToggle.setAttribute('aria-expanded', 'false');
            });
        } else {
            // If closing, close all children dropdowns
            const menu = toggle.nextElementSibling;
            if (menu) {
                menu.querySelectorAll(SELECTORS.dropdownToggle).forEach(childToggle => {
                    childToggle.setAttribute('aria-expanded', 'false');
                });
            }
        }
    }

    // =============================================================================
    // Event Handlers
    // =============================================================================

    /**
     * Handle clicks on the mobile menu button
     */
    function handleMenuBtnClick(event) {
        event.preventDefault();
        toggleMobileDrawer();
    }

    /**
     * Toggle a mobile accordion group
     * @param {HTMLButtonElement} toggleBtn
     */
    function toggleMobileGroup(toggleBtn) {
        const group = toggleBtn.closest(SELECTORS.mobileGroup);
        if (!group) return;

        const isOpen = group.classList.contains('is-open');
        group.classList.toggle('is-open', !isOpen);
        toggleBtn.setAttribute('aria-expanded', String(!isOpen));

        const controlsId = toggleBtn.getAttribute('aria-controls');
        if (!controlsId) return;

        const panel = document.getElementById(controlsId);
        if (panel) {
            panel.setAttribute('aria-hidden', String(isOpen));
        }
    }

    /**
     * Handle clicks inside the mobile drawer (accordion toggles and link close behaviour)
     */
    function handleMobileDrawerClick(event) {
        const drawer = document.querySelector(SELECTORS.mobileDrawer);
        if (!drawer) return;

        const toggleBtn = event.target.closest(SELECTORS.mobileGroupToggle);
        if (toggleBtn && drawer.contains(toggleBtn)) {
            event.preventDefault();
            toggleMobileGroup(toggleBtn);
            return;
        }

        // Close drawer when clicking any link inside it (navigation is about to change)
        const link = event.target.closest('a');
        if (link && drawer.contains(link)) {
            closeMobileDrawer();
        }
    }

    /**
     * Handle clicks on dropdown toggles
     */
    function handleDropdownToggleClick(event) {
        event.preventDefault();
        event.stopPropagation();
        toggleDropdown(event.currentTarget);
    }

    /**
     * Handle keyboard events for accessibility
     */
    function handleKeydown(event) {
        // Escape key closes any open menu/dropdown
        if (event.key === 'Escape') {
            closeAllDropdowns();

            // Also close mobile drawer if open
            if (mobileDrawerOpen) {
                closeMobileDrawer();
                // Return focus to menu button
                const menuBtn = document.querySelector(SELECTORS.menuBtn);
                if (menuBtn) {
                    menuBtn.focus();
                }
            }
        }
    }

    /**
     * Handle clicks outside dropdowns to close them
     */
    function handleDocumentClick(event) {
        // Don't close if clicking inside a dropdown
        if (event.target.closest(SELECTORS.dropdown)) {
            return;
        }

        closeAllDropdowns();
    }

    /**
     * Handle window resize - close mobile menu on desktop breakpoint
     */
    function handleResize() {
        if (window.innerWidth >= 1024 && mobileDrawerOpen) {
            closeMobileDrawer();
        }
    }

    // =============================================================================
    // Initialization
    // =============================================================================

    function init() {
        // Mobile menu button
        const menuBtn = document.querySelector(SELECTORS.menuBtn);
        if (menuBtn) {
            menuBtn.addEventListener('click', handleMenuBtnClick);
        }

        // Dropdown toggles
        document.querySelectorAll(SELECTORS.dropdownToggle).forEach(toggle => {
            toggle.addEventListener('click', handleDropdownToggleClick);
        });

        // Mobile drawer delegation (accordion + close-on-link)
        const drawer = document.querySelector(SELECTORS.mobileDrawer);
        if (drawer) {
            drawer.addEventListener('click', handleMobileDrawerClick);
        }

        // Keyboard navigation
        document.addEventListener('keydown', handleKeydown);

        // Click outside to close dropdowns
        document.addEventListener('click', handleDocumentClick);

        // Window resize handler
        window.addEventListener('resize', handleResize, { passive: true });
    }

    // Run on DOM ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

})();
