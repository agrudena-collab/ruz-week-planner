(function () {
  "use strict";

  function init() {
    const select = document.getElementById("groupPickerButton");
    const wrap = select && select.closest(".group-picker-wrap");
    if (!select || !wrap || select.dataset.searchPickerReady === "true") return;

    select.dataset.searchPickerReady = "true";
    select.setAttribute("aria-hidden", "true");
    select.tabIndex = -1;
    select.style.position = "absolute";
    select.style.width = "1px";
    select.style.height = "1px";
    select.style.padding = "0";
    select.style.margin = "-1px";
    select.style.overflow = "hidden";
    select.style.clip = "rect(0 0 0 0)";
    select.style.whiteSpace = "nowrap";
    select.style.border = "0";

    const options = Array.from(select.options).map(option => ({
      value: String(option.value),
      label: option.textContent.trim()
    }));

    const root = document.createElement("div");
    root.className = "group-search-picker";

    const button = document.createElement("button");
    button.type = "button";
    button.className = "group-search-trigger";
    button.setAttribute("aria-haspopup", "listbox");
    button.setAttribute("aria-expanded", "false");
    button.setAttribute("aria-label", "Выбрать учебную группу");

    const label = document.createElement("span");
    label.className = "group-search-trigger-label";

    const arrow = document.createElement("span");
    arrow.className = "group-search-trigger-arrow";
    arrow.textContent = "⌄";
    arrow.setAttribute("aria-hidden", "true");

    button.append(label, arrow);

    const panel = document.createElement("div");
    panel.className = "group-search-panel";
    panel.hidden = true;

    const searchRow = document.createElement("div");
    searchRow.className = "group-search-row";

    const icon = document.createElement("span");
    icon.className = "group-search-icon";
    icon.textContent = "⌕";
    icon.setAttribute("aria-hidden", "true");

    const input = document.createElement("input");
    input.type = "search";
    input.className = "group-search-input";
    input.placeholder = "Найти группу или направление...";
    input.autocomplete = "off";
    input.autocapitalize = "none";
    input.spellcheck = false;
    input.setAttribute("aria-label", "Поиск группы или направления");

    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "group-search-clear";
    clear.textContent = "×";
    clear.setAttribute("aria-label", "Очистить поиск");

    searchRow.append(icon, input, clear);

    const status = document.createElement("div");
    status.className = "group-search-status";
    status.setAttribute("aria-live", "polite");

    const list = document.createElement("div");
    list.className = "group-search-list";
    list.setAttribute("role", "listbox");
    list.setAttribute("aria-label", "Учебные группы");

    panel.append(searchRow, status, list);
    root.append(button, panel);
    wrap.appendChild(root);

    let activeIndex = -1;

    function normalize(value) {
      return String(value || "")
        .toLocaleLowerCase("ru-RU")
        .normalize("NFKC")
        .replace(/ё/g, "е")
        .replace(/\s+/g, " ")
        .trim();
    }

    function selectedOption() {
      const selected = options.find(item => item.value === String(select.value));
      return selected || options[0] || null;
    }

    function updateLabel() {
      const selected = selectedOption();
      label.textContent = selected ? selected.label : "Выберите группу";
      button.title = selected ? selected.label : "Выберите группу";
    }

    function close() {
      if (panel.hidden) return;
      panel.hidden = true;
      button.setAttribute("aria-expanded", "false");
      activeIndex = -1;
    }

    function open() {
      panel.hidden = false;
      button.setAttribute("aria-expanded", "true");
      render();
      requestAnimationFrame(() => input.focus({ preventScroll: true }));
    }

    function toggle() {
      if (panel.hidden) open();
      else close();
    }

    function selectGroup(item) {
      select.value = item.value;
      updateLabel();
      select.dispatchEvent(new Event("change", { bubbles: true }));
      close();
      button.focus({ preventScroll: true });
    }

    function render() {
      const query = normalize(input.value);
      const filtered = query
        ? options.filter(item => normalize(item.label + " " + item.value).includes(query))
        : options;

      activeIndex = filtered.length ? 0 : -1;
      list.replaceChildren();

      status.textContent = query
        ? `Найдено: ${filtered.length}`
        : `Всего групп: ${options.length}`;

      if (!filtered.length) {
        const empty = document.createElement("div");
        empty.className = "group-search-empty";
        empty.textContent = "Ничего не найдено. Попробуйте код группы или название направления.";
        list.appendChild(empty);
        return;
      }

      const fragment = document.createDocumentFragment();
      filtered.forEach((item, index) => {
        const option = document.createElement("button");
        option.type = "button";
        option.className = "group-search-option";
        option.setAttribute("role", "option");
        option.dataset.value = item.value;
        option.setAttribute("aria-selected", item.value === String(select.value) ? "true" : "false");
        option.textContent = item.label;
        option.addEventListener("mouseenter", () => {
          activeIndex = index;
          syncActive();
        });
        option.addEventListener("click", () => selectGroup(item));
        fragment.appendChild(option);
      });
      list.appendChild(fragment);
      syncActive();
    }

    function syncActive() {
      const items = list.querySelectorAll(".group-search-option");
      items.forEach((item, index) => item.classList.toggle("active", index === activeIndex));
      if (activeIndex >= 0 && items[activeIndex]) items[activeIndex].scrollIntoView({ block: "nearest" });
    }

    button.addEventListener("click", toggle);
    input.addEventListener("input", render);
    input.addEventListener("keydown", event => {
      const items = list.querySelectorAll(".group-search-option");
      if (event.key === "ArrowDown") {
        event.preventDefault();
        if (items.length) {
          activeIndex = Math.min(activeIndex + 1, items.length - 1);
          syncActive();
        }
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        if (items.length) {
          activeIndex = Math.max(activeIndex - 1, 0);
          syncActive();
        }
      } else if (event.key === "Enter") {
        event.preventDefault();
        if (activeIndex >= 0 && items[activeIndex]) items[activeIndex].click();
      } else if (event.key === "Escape") {
        event.preventDefault();
        close();
        button.focus({ preventScroll: true });
      }
    });
    clear.addEventListener("click", () => {
      input.value = "";
      render();
      input.focus({ preventScroll: true });
    });
    document.addEventListener("pointerdown", event => {
      if (!root.contains(event.target)) close();
    });
    document.addEventListener("keydown", event => {
      if (event.key === "Escape" && !panel.hidden) {
        close();
        button.focus({ preventScroll: true });
      }
    });
    select.addEventListener("change", updateLabel);

    updateLabel();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init, { once: true });
  } else {
    init();
  }
})();
