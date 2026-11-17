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
