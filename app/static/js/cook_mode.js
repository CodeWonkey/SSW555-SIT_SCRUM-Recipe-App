/* US-37: voice navigation with always-available manual controls. */
(function () {
  "use strict";

  // Match complete short commands; random noisy phrases do not move a step.
  function commandFor(transcript) {
    const words = String(transcript || "").toLowerCase()
      .replace(/[^a-z\s]/g, " ").replace(/\s+/g, " ").trim();
    if (["next", "next step", "forward", "go forward", "go to next step"].includes(words)) return 1;
    if (["back", "previous", "previous step", "go back", "go to previous step"].includes(words)) return -1;
    return 0;
  }

  if (typeof module !== "undefined" && module.exports) {
    module.exports = { commandFor };
  }
  if (typeof document === "undefined") return;

  const root = document.getElementById("cook-mode");
  if (!root) return;
  const steps = Array.from(root.querySelectorAll("[data-cook-step]"));
  if (!steps.length) return;
  const previous = document.getElementById("cook-previous");
  const next = document.getElementById("cook-next");
  const counter = document.getElementById("cook-counter");
  const start = document.getElementById("cook-listen");
  const stop = document.getElementById("cook-stop");
  const status = document.getElementById("cook-status");
  let position = 0;
  let recognition = null;
  let listening = false;

  function message(text) { status.textContent = text; }
  function showStep(index) {
    position = Math.min(Math.max(index, 0), steps.length - 1);
    steps.forEach((step, i) => { step.hidden = (i !== position); });
    counter.textContent = `Step ${position + 1} of ${steps.length}`;
    previous.disabled = (position === 0);
    next.disabled = (position === steps.length - 1);
  }
  previous.addEventListener("click", () => showStep(position - 1));
  next.addEventListener("click", () => showStep(position + 1));
  showStep(0);

  const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SpeechRecognition) {
    start.disabled = true;
    message("Voice recognition is unavailable in this browser. Use the Previous and Next buttons.");
    return;
  }

  function setListening(value) {
    listening = value;
    start.disabled = value;
    stop.disabled = !value;
  }

  start.addEventListener("click", () => {
    if (listening) return;
    recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = (event) => {
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i];
        if (!result.isFinal) continue;
        const direction = commandFor(result[0].transcript);
        if (direction) {
          showStep(position + direction);
          message(`Heard command. Step ${position + 1} of ${steps.length}.`);
        } else {
          message("Command not recognized. Say 'next step' or 'previous step', or use the buttons.");
        }
      }
    };
    recognition.onerror = (event) => {
      const blocked = ["not-allowed", "service-not-allowed", "audio-capture"].includes(event.error);
      message(blocked
        ? "Microphone denied or unavailable. Use the Previous and Next buttons."
        : "Voice input was unclear or interrupted. Try again, or use the buttons.");
      if (blocked) { try { recognition.stop(); } catch (_) { /* already stopped */ } }
    };
    recognition.onend = () => {
      setListening(false);
      // Do not silently restart or listen without a fresh user click.
      if (status.textContent.startsWith("Listening")) message("Microphone off. Use buttons or enable voice again.");
    };
    try {
      recognition.start();
      setListening(true);
      message("Listening. Say 'next step' or 'previous step'.");
    } catch (_) {
      setListening(false);
      message("Could not start the microphone. Use the Previous and Next buttons.");
    }
  });
  stop.addEventListener("click", () => {
    if (listening && recognition) recognition.stop();
    setListening(false);
    message("Microphone off. You can use the buttons.");
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && listening && recognition) {
      recognition.stop();
      setListening(false);
      message("Microphone off while the page is hidden.");
    }
  });
})();
