(function () {
  "use strict";

  function injectStyles() {
    if (document.getElementById("group-search-v2-styles")) return;

    const style = document.createElement("style");
    style.id = "group-search-v2-styles";
    style.textContent = `
      .group-search-v2 {
        position: relative;
        width: 100%;
        margin: 0 0 12px;
        z-index: 60;
      }

      .group-search-v2-field {
        display: flex;
        align-items: center;
        gap: 12px;
        width: 100%;
        min-height: 58px;
        padding: 13px 16px;
        border: 1px solid rgba(255,255,255,.10);
        border-radius: 20px;
        background: rgba(16,19,28,.82);
        box-shadow: 0 12px 30px rgba(0,0,0,.16);
      }

      .group-search-v2-field:focus-within {
        border-color: rgba(66,217,255,.35);
        box-shadow: 0 0 0 2px rgba(66,217,255,.08), 0 12px 30px rgba(0,0,0,.18);
      }

      .group-search-v2-icon {
        flex: 0 0 auto;
        font-size: 25px;
        line-height: 1;
        filter: grayscale(.1);
      }

      .group-search-v2-input {
        min-width: 0;
        flex: 1;
        border: 0;
        outline: 0;
        background: transparent;
        color: #fff;
        font-size: 17px;
        line-height: 1.35;
      }

      .group-search-v2-input::placeholder {
        color: #697184;
      }

      .group-search-v2-clear {
        display: none;
        flex: 0 0 auto;
        width: 32px;
        height: 32px;
        border: 0;
        border-radius: 10px;
        background: rgba(255,255,255,.07);
        color: #aeb6c5;
        font-size: 21px;
        line-height: 1;
        cursor: pointer;
      }

      .group-search-v2.has-query .group-search-v2-clear {
        display: grid;
        place-items: center;
      }

      .group-search-v2-results {
        position: absolute;
        left: 0;
        right: 0;
        top: calc(100% + 7px);
        max-height: min(52vh, 430px);
        overflow: auto;
        border: 1px solid rgba(255,255,255,.12);
        border-radius: 18px;
        background: linear-gradient(160deg,#111624,#090b12);
        box-shadow: 0 24px 70px rgba(0,0,0,.55);
        overscroll-behavior: contain;
      }

      .group-search-v2-results[hidden] {
        display: none;
      }

      .group-search-v2-count {
        padding: 9px 14px;
        color: #70798b;
        font-size: 11px;
        border-bottom: 1px solid rgba(255,255,255,.07);
      }

      .group-search-v2-option {
        display: block;
        width: 100%;
        padding: 13px 15px;
        border: 0;
        border-bottom: 1px solid rgba(255,255,255,.045);
        background: transparent;
        color: #dce2ed;
        text-align: left;
        font-size: 15px;
        line-height: 1.35;
        cursor: pointer;
      }

      .group-search-v2-option:last-child {
        border-bottom: 0;
      }

      .group-search-v2-option:hover,
      .group-search-v2-option.active {
        background: rgba(66,217,255,.09);
        color: #fff;
      }

      .group-search-v2-empty {
        padding: 22px 15px;
        color: #8e96a8;
        font-size: 13px;
        line-height: 1.45;
        text-align: center;
      }

      .group-search-v2-selected {
        margin: 7px 2px 0;
        color: #70798b;
        font-size: 11px;
      }

      @media (max-width: 640px) {
        .group-search-v2-field {
          min-height: 58px;
          border-radius: 20px;
          padding: 13px 15px;
        }

        .group-search-v2-input {
          font-size: 16px;
        }

        .group-search-v2-option {
          padding: 14px 15px;
          font-size: 15px;
        }
      }
    `;

    document.head.appendChild(style);
  }

  function normalize(value) {
    return String(value || "")
      .toLocaleLowerCase("ru-RU")
      .normalize("NFKC")
      .replace(/ё/g, "е")
      .replace(/\s+/g, " ")
      .trim();
  }

  function init() {
    const select = document.getElementById("groupPickerButton");
    if (!select || select.dataset.groupSearchV2Ready === "true") return;

    injectStyles();
    select.dataset.groupSearchV2Ready = "true";

    const options = Array.from(select.options).map(option => ({
      value: String(option.value),
      label: option.textContent.trim()
    }));

    const root = document.createElement("div");
    root.className = "group-search-v2";

    const field = document.createElement("div");
    field.className = "group-search-v2-field";

    const icon = document.createElement("span");
    icon.className = "group-search-v2-icon";
    icon.textContent = "🔎";
    icon.setAttribute("aria-hidden", "true");

    const input = document.createElement("input");
    input.type = "search";
    input.className = "group-search-v2-input";
    input.placeholder = "Найти группу...";
    input.autocomplete = "off";
    input.autocapitalize = "none";
    input.spellcheck = false;
    input.setAttribute("aria-label", "Поиск учебной группы");

    const clear = document.createElement("button");
    clear.type = "button";
    clear.className = "group-search-v2-clear";
    clear.textContent = "×";
    clear.setAttribute("aria-label", "Очистить поиск группы");

    field.append(icon, input, clear);

    const results = document.createElement("div");
    results.className = "group-search-v2-results";
    results.hidden = true;
    results.setAttribute("role", "listbox");
    results.setAttribute("aria-label", "Результаты поиска групп");

    root.append(field, results);

    const selected = document.createElement("div");
    selected.className = "group-search-v2-selected";
    root.appendChild(selected);

    select.parentNode.insertBefore(root, select);

    // Keep the existing native selector as a fallback/accessibility control,
    // but don't let it compete visually with the new search field.
    select.style.position = "absolute";
    select.style.width = "1px";
    select.style.height = "1px";
    select.style.opacity = "0";
    select.style.pointerEvents = "none";

    let activeIndex = -1;
    let filtered = [];

    function currentOption() {
      return options.find(item => item.value === String(select.value)) || null;
    }

    function updateSelected() {
      const current = currentOption();
      selected.textContent = current ? `Выбрано: ${current.label}` : "";
    }

    function closeResults() {
      results.hidden = true;
      activeIndex = -1;
    }

    function choose(item) {
      select.value = item.value;
      select.dispatchEvent(new Event("change", { bubbles: true }));
      input.value = "";
      root.classList.remove("has-query");
      closeResults();
      updateSelected();
    }

    function render() {
      const query = normalize(input.value);
      root.classList.toggle("has-query", Boolean(query));

      if (!query) {
        closeResults();
        return;
      }

      filtered = options.filter(item =>
        normalize(item.label + " " + item.value).includes(query)
      );
      activeIndex = filtered.length ? 0 : -1;
      results.replaceChildren();

      const count = document.createElement("div");
      count.className = "group-search-v2-count";
      count.textContent = `Найдено: ${filtered.length}`;
      results.appendChild(count);

      if (!filtered.length) {
        const empty = document.createElement("div");
        empty.className = "group-search-v2-empty";
        empty.textContent = "Ничего не найдено. Попробуйте код группы или название направления.";
        results.appendChild(empty);
      } else {
        const fragment = document.createDocumentFragment();
        filtered.forEach((item, index) => {
          const option = document.createElement("button");
          option.type = "button";
          option.className = "group-search-v2-option";
          option.setAttribute("role", "option");
          option.setAttribute("aria-selected", item.value === String(select.value) ? "true" : "false");
          option.textContent = item.label;
          option.addEventListener("mouseenter", () => {
            activeIndex = index;
            syncActive();
          });
          option.addEventListener("click", () => choose(item));
          fragment.appendChild(option);
        });
        results.appendChild(fragment);
      }

      results.hidden = false;
      syncActive();
    }

    function syncActive() {
      const items = results.querySelectorAll(".group-search-v2-option");
      items.forEach((item, index) => item.classList.toggle("active", index === activeIndex));
      if (activeIndex >= 0 && items[activeIndex]) {
        items[activeIndex].scrollIntoView({ block: "nearest" });
      }
    }

    input.addEventListener("input", render);
    input.addEventListener("focus", () => {
      if (input.value.trim()) render();
    });

    input.addEventListener("keydown", event => {
      const items = results.querySelectorAll(".group-search-v2-option");
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
        if (activeIndex >= 0 && filtered[activeIndex]) choose(filtered[activeIndex]);
      } else if (event.key === "Escape") {
        closeResults();
      }
    });

    clear.addEventListener("click", () => {
      input.value = "";
      root.classList.remove("has-query");
      closeResults();
      input.focus();
    });

    select.addEventListener("change", updateSelected);

    document.addEventListener("pointerdown", event => {
      if (!root.contains(event.target)) closeResults();
    });

    updateSelected();
  }

  function boot() {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", init, { once: true });
    } else {
      init();
    }
  }

  boot();
})();
