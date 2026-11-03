// Submit on change; the button also works when JavaScript is unavailable.
const servingsForm = document.getElementById("servings-form");
const servingsInput = document.getElementById("servings");

servingsInput.addEventListener("change", () => {
  if (servingsInput.reportValidity()) {
    servingsForm.requestSubmit();
  }
});
