(function () {
  "use strict";

  function injectStyles() {
    if (document.getElementById("group-search-styles")) return;
    const style = document.createElement("style");
    style.id = "group-search-styles";
    style.textContent = `
      .group-picker-wrap { position:relative; }
      .group-search-picker { position:relative; width:100%; }
      .group-search-trigger {
        width:100%; min-height:38px; display:flex; align-items:center; justify-content:space-between; gap:10px;
        border:1px solid rgba(255,255,255,.10); border-radius:12px; padding:7px 11px;
        background:rgba(255,255,255,.045); color:#cbd1dd; font-size:13px; font-weight:750;
        cursor:pointer; text-align:left; touch-action:manipulation;
      }
      .group-search-trigger:hover { background:rgba(255,255,255,.065); }
      .group-search-trigger:focus { outline:2px solid rgba(66,217,255,.35); outline-offset:2px; }
      .group-search-trigger-label { min-width:0; overflow:hidden; text-overflow:ellipsis; white-space:nowrap; }
      .group-search-trigger-arrow { color:#8e96a8; flex:0 0 auto; }
      .group-search-panel {
        position:absolute; left:0; right:0; top:calc(100% + 7px); z-index:140;
        border:1px solid rgba(255,255,255,.12); border-radius:16px; overflow:hidden;
        background:linear-gradient(160deg,#111624,#090b12); box-shadow:0 24px 70px rgba(0,0,0,.55);
      }
      .group-search-row {
        display:flex; align-items:center; gap:8px; padding:9px;
        background:rgba(255,255,255,.035); border-bottom:1px solid rgba(255,255,255,.08);
      }
      .group-search-icon { color:#8e96a8; font-size:20px; line-height:1; }
      .group-search-input {
        min-width:0; flex:1; border:0; outline:0; background:transparent; color:#fff;
        font-size:14px; padding:5px 0;
      }
      .group-search-input::placeholder { color:#697184; }
      .group-search-clear {
        width:30px; height:30px; border:0; border-radius:9px; background:rgba(255,255,255,.06);
        color:#aeb6c5; font-size:20px; line-height:1; cursor:pointer;
      }
      .group-search-status { padding:7px 11px; color:#70798b; font-size:11px; border-bottom:1px solid rgba(255,255,255,.06); }
      .group-search-list { max-height:min(55vh,430px); overflow:auto; overscroll-behavior:contain; }
      .group-search-option {
        display:block; width:100%; border:0; border-bottom:1px solid rgba(255,255,255,.045);
        background:transparent; color:#cbd1dd; text-align:left; padding:11px 12px; font-size:13px; line-height:1.3; cursor:pointer;
      }
      .group-search-option:hover, .group-search-option.active { background:rgba(66,217,255,.09); color:#fff; }
      .group-search-option[aria-selected="true"] { box-shadow:inset 3px 0 0 #42d9ff; }
      .group-search-empty { padding:22px 14px; color:#8e96a8; font-size:12px; line-height:1.45; text-align:center; }
      @media(max-width:640px){
        .group-search-trigger { min-height:42px; font-size:14px; }
        .group-search-panel { top:calc(100% + 6px); }
        .group-search-list { max-height:58vh; }
        .group-search-option { padding:12px; font-size:14px; }
      }
    `;
    document.head.appendChild(style);
  }

  function init() {
    const select = document.getElementById("groupPickerButton");
    const wrap = select && select.closest(".group-picker-wrap");
    if (!select || !wrap || select.dataset.searchPickerReady === "true") return;

    injectStyles();
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
