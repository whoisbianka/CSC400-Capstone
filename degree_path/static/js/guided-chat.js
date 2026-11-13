(async function () {
  "use strict";

  const messages = document.getElementById("chatMessages");
  const input = document.getElementById("userInput");
  const sendButton = document.getElementById("sendButton");
  const status = document.getElementById("chatStatus");
  const storageNote = document.getElementById("chatStorageNote");
  const reloadButton = document.getElementById("reloadChat");
  const recommendationCards = document.getElementById("recommendationCards");
  const majorUrl = document.getElementById("guided-chat").dataset.majorUrl;
  const exploreUrl = document.getElementById("guided-chat").dataset.exploreUrl;
  let api = null;
  let busy = false;

  function setStatus(message) {
    status.textContent = message;
  }

  function setBusy(value) {
    busy = value;

    input.disabled = value;
    sendButton.disabled = value;

    messages.setAttribute("aria-busy", String(value));
  }

  function showStorageNote(mode) {
    if (mode === "user") {
      storageNote.textContent =
        "Your chat and interests are saved to your account.";
    } else {
      storageNote.textContent =
        "Guest chat is saved temporarily in this browser's session. " +
        "It expires 24 hours after the last successful message.";
    }
  }

  function addMessage(role, content) {
    const bubble = document.createElement("div");

    bubble.className =
      role === "user" ? "user-message" : "bot-message";

    const label = document.createElement("strong");

    label.textContent =
      role === "user" ? "You:" : "Pathfinder:";

    const text = document.createElement("span");

    // Treat user and Gemini output as text, never executable HTML.
    text.textContent = content;
    text.style.whiteSpace = "pre-wrap";

    bubble.append(
      label,
      document.createElement("br"),
      text
    );

    messages.appendChild(bubble);
    messages.scrollTop = messages.scrollHeight;
  }

  function renderHistory(history) {
    messages.replaceChildren();

    if (history.length === 0) {
      addMessage(
        "assistant",
        "Hi! I can help you explore majors based on your interests. " +
        "What subjects or activities do you enjoy?"
      );

      return;
    }

    for (const message of history) {
      addMessage(message.role, message.content);
    }
  }

  function renderRecommendations(recommendations) {
    recommendationCards.replaceChildren();
    if (!recommendations.length) {
      const empty = document.createElement("p");
      empty.className = "recommendations-empty";
      empty.textContent = "Your recommendations will appear as we learn about your interests.";
      recommendationCards.append(empty);
    }
    for (const recommendation of recommendations) {
      const card = document.createElement("article");
      card.className = "major-recommendation";
      const details = document.createElement("div");
      const title = document.createElement("h3");
      const link = document.createElement("a");
      link.href = majorUrl.replace(/0$/, String(recommendation.cipcode));
      link.textContent = recommendation.major;
      title.append(link);
      const count = document.createElement("p");
      const number = recommendation.matching_keywords;
      count.textContent = `${number} matching ${number === 1 ? "interest" : "interests"}`;
      const colleges = document.createElement("a");
      const destination = new URL(exploreUrl, window.location.origin);
      destination.searchParams.set("view", "programs");
      destination.searchParams.set("cipcode", String(recommendation.cipcode));
      colleges.href = destination.href;
      colleges.className = "recommendation-colleges";
      colleges.textContent = "Explore colleges that offer this major →";
      details.append(title, count, colleges);
      const heart = document.createElement("button");
      heart.type = "button";
      heart.className = "save-major-button recommendation-heart";
      heart.dataset.saveMajor = String(recommendation.cipcode);
      heart.dataset.majorName = recommendation.major;
      heart.dataset.favoriteIcon = "heart";
      heart.textContent = "♡";
      heart.setAttribute("aria-pressed", "false");
      heart.setAttribute("aria-label", `Save ${recommendation.major} to favorites`);
      card.append(details, heart);
      recommendationCards.append(card);
    }
    // Use the same favorite state, sign-in prompt and save/undo flow as Explore.
    document.dispatchEvent(new Event("major-controls:render"));
  }
  async function sendMessage() {
    if (busy || api === null) {
      return;
    }

    const message = input.value.trim();

    if (!message) {
      setStatus("Enter a message first.");
      input.focus();
      return;
    }

    if (message.length > 4000) {
      setStatus("Please keep your message under 4,001 characters.");
      input.focus();
      return;
    }

    reloadButton.hidden = true;
    setBusy(true);
    setStatus("The advisor is thinking…");

    try {
      const result = await api.send(message);

      // Display the exchange after the server confirms it was saved.
      addMessage("user", message);
      addMessage("assistant", result.reply);

      input.value = "";

      showStorageNote(result.mode);
      renderRecommendations(result.recommendations ?? []);
      setStatus("");
    } catch (error) {
      // Keep the typed message so the user does not lose it.
      setStatus(
        error instanceof Error
          ? error.message
          : "Unable to send your message. Please try again."
      );

      reloadButton.hidden = false;
    } finally {
      setBusy(false);
      input.focus();
    }
  }

  sendButton.addEventListener("click", sendMessage);

  input.addEventListener("keydown", (event) => {
    if (
      event.key === "Enter" &&
      !event.shiftKey &&
      !event.isComposing
    ) {
      event.preventDefault();
      sendMessage();
    }
  });

  reloadButton.addEventListener("click", () => {
    window.location.reload();
  });

  // Recover this visitor's saved conversation using the Flask session.
  setBusy(true);

  try {
    if (!window.chatApiReady) {
      throw new Error(
        "The chat API did not load. Please reload the page."
      );
    }

    api = await window.chatApiReady;

    const saved = await api.load();
    renderHistory(saved.messages);
    showStorageNote(saved.mode);
    renderRecommendations(saved.recommendations ?? []);

    setStatus("");
    setBusy(false);

    input.focus();
  } catch (error) {
    setStatus(
      error instanceof Error
        ? error.message
        : "Unable to load your chat. Please reload the page."
    );

    messages.setAttribute("aria-busy", "false");

    // Keep sending disabled if initialization failed.
    reloadButton.hidden = false;
  }
})();