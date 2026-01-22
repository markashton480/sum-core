(() => {
  const DESTINATION_FIELDS = ["page", "url", "path", "email", "phone", "anchor"];
  const OPTIONAL_FIELDS = ["link_text", "open_in_new_tab"];
  const LINK_TYPE_FIELDS = {
    page: ["page", "anchor"],
    anchor: ["anchor"],
    url: ["url"],
    path: ["path"],
    email: ["email"],
    phone: ["phone"],
  };
  const LINK_TYPE_SELECTOR = 'select[name$="-link_type"], select[name="link_type"]';
  const FIELD_WRAPPER_SELECTOR =
    ".w-field, .field, .field__wrapper, .struct-block__field, .struct-block__field-wrapper";

  const findFieldWrapper = (root, fieldName) => {
    const namedFields = root.querySelectorAll("[data-field-name], [data-contentpath]");
    for (const field of namedFields) {
      if (field.dataset.fieldName === fieldName || field.dataset.contentpath === fieldName) {
        return field;
      }
    }

    const inputs = root.querySelectorAll("[name]");
    let input = null;
    for (const candidate of inputs) {
      const name = candidate.getAttribute("name");
      if (name === fieldName || name.endsWith(`-${fieldName}`)) {
        input = candidate;
        break;
      }
    }
    if (!input) {
      return null;
    }

    return input.closest(FIELD_WRAPPER_SELECTOR) || input.parentElement;
  };

  const getBlockRoot = (select) =>
    select.closest(".struct-block") ||
    select.closest(".struct-block__fields") ||
    select.closest("[data-structblock]") ||
    select.closest("[data-block-id]");

  const setDestinationVisibility = (root, linkType) => {
    const visibleFields = LINK_TYPE_FIELDS[linkType] || [];

    DESTINATION_FIELDS.forEach((fieldName) => {
      const wrapper = findFieldWrapper(root, fieldName);
      if (wrapper) {
        wrapper.hidden = !visibleFields.includes(fieldName);
      }
    });

    OPTIONAL_FIELDS.forEach((fieldName) => {
      const wrapper = findFieldWrapper(root, fieldName);
      if (wrapper) {
        wrapper.hidden = false;
      }
    });
  };

  const updateBlock = (select) => {
    const root = getBlockRoot(select);
    if (!root) {
      return;
    }
    setDestinationVisibility(root, select.value);
  };

  const initSelect = (select) => {
    if (select.dataset.universalLinkInit === "initialized") {
      return;
    }
    select.dataset.universalLinkInit = "initialized";
    updateBlock(select);
    select.addEventListener("change", () => updateBlock(select));
  };

  const init = (context) => {
    (context || document)
      .querySelectorAll(LINK_TYPE_SELECTOR)
      .forEach((select) => initSelect(select));
  };

  init(document);

  const pendingNodes = new Set();
  let scheduled = false;
  // Batch DOM mutations (like StreamField add/duplicate/reorder) to rescan once per frame.
  const scheduleInit = () => {
    if (scheduled) {
      return;
    }
    scheduled = true;
    requestAnimationFrame(() => {
      scheduled = false;
      pendingNodes.forEach((node) => {
        if (node.isConnected) {
          init(node);
        }
      });
      pendingNodes.clear();
    });
  };

  const observer = new MutationObserver((mutations) => {
    for (const mutation of mutations) {
      for (const node of mutation.addedNodes) {
        if (!(node instanceof HTMLElement)) {
          continue;
        }
        if (node.matches(LINK_TYPE_SELECTOR)) {
          initSelect(node);
          continue;
        }
        if (node.querySelector(LINK_TYPE_SELECTOR)) {
          pendingNodes.add(node);
        }
      }
    }
    if (pendingNodes.size > 0) {
      scheduleInit();
    }
  });

  observer.observe(document.body, { childList: true, subtree: true });
})();
