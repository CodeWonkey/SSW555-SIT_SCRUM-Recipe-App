(() => {
  const text = document.getElementById("share-text");
  const copy = document.getElementById("share-copy");
  const share = document.getElementById("share-native");
  const status = document.getElementById("share-status");

  function manualCopy(message) {
    text.focus();
    text.select();
    status.textContent = message;
  }

  copy.hidden = false;
  copy.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(text.value);
      status.textContent = "Recipe copied. Paste it into a message to share.";
    } catch {
      manualCopy("Copy unavailable. Recipe text selected; use your device's Copy command, or download the file.");
    }
  });

  if (typeof navigator.share === "function") {
    share.hidden = false;
    share.addEventListener("click", async () => {
      share.disabled = true;
      try {
        await navigator.share({ title: share.dataset.title, text: text.value });
        status.textContent = "Recipe shared with the selected app.";
      } catch (error) {
        if (error.name === "AbortError") {
          status.textContent = "Sharing canceled. You can still copy or download the recipe.";
        } else {
          status.textContent = "Sharing unavailable. Copy or download the recipe instead.";
        }
      } finally {
        share.disabled = false;
      }
    });
  }
})();
