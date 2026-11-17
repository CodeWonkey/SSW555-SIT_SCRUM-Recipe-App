// Use the same row template for initial fields and newly added ingredients.
(() => {
  const container = document.getElementById("ingredient-container");
  const template = document.getElementById("ingredient-row-template");
  const addButton = document.getElementById("add-ingredient");
  if (!container || !template || !addButton) return;

  addButton.addEventListener("click", () => {
    container.appendChild(template.content.cloneNode(true));
  });

  container.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-ingredient]");
    if (!button || !container.contains(button)) return;
    if (container.querySelectorAll(".ingredient-row").length > 1) {
      button.closest(".ingredient-row").remove();
    }
  });
})();

(() => {
  const list = document.getElementById("tag-list");
  const input = document.getElementById("tags");
  if (!list || !input) return;

  list.addEventListener("click", (event) => {
    const button = event.target.closest("[data-remove-tag]");
    if (!button || !list.contains(button)) return;
    const tag = button.getAttribute("aria-label").slice("Remove tag ".length);
    input.value = input.value
      .split(",")
      .map((part) => part.trim())
      .filter((part) => part && part !== tag)
      .join(", ");
    button.closest("li").remove();
  });
})();
